"""Покадровая сборка: движение камеры по кадру и переходы между планами.

Компоновка идёт в Python поверх готовых кадров, а не фильтрами ffmpeg. Так
получается субпиксельная точность наездов (PIL умеет ресайз по дробной рамке,
поэтому медленный зум не дёргается) и полная свобода в переходах.

Время не растягивается: все преобразования пространственные, поэтому звук
исходника остаётся синхронным.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter

from .style import FRAME_H, FRAME_W


def ease(u: float) -> float:
    """Плавный старт и остановка."""
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


@dataclass
class Move:
    """Движение камеры внутри плана.

    zoom — во сколько раз кадр увеличен; 1.0 — исходная рамка целиком.
    Центр задаётся в долях кадра, 0.5/0.5 — середина.
    """

    zoom: tuple[float, float] = (1.0, 1.0)
    center: tuple[tuple[float, float], tuple[float, float]] = ((0.5, 0.5), (0.5, 0.5))

    def at(self, u: float) -> tuple[float, float, float]:
        e = ease(u)
        z = self.zoom[0] + (self.zoom[1] - self.zoom[0]) * e
        (x0, y0), (x1, y1) = self.center
        return z, x0 + (x1 - x0) * e, y0 + (y1 - y0) * e


@dataclass
class Shot:
    """Отрезок готового ролика: откуда берём кадры и как по ним едем.

    source — имя папки с кадрами. offset задаёт, какому времени внутри этой
    папки соответствует начало плана.
    """

    start: float
    end: float
    source: str
    move: Move = None
    offset: float = 0.0
    transition: str = "cut"      # cut | dissolve | blur
    trans_dur: float = 0.0

    def __post_init__(self) -> None:
        if self.move is None:
            self.move = Move()


class Frames:
    """Кадры одного источника, лежащие на диске."""

    def __init__(self, directory: Path, pattern: str, fps: int) -> None:
        self.dir = directory
        self.pattern = pattern
        self.fps = fps
        self._cache: dict[int, Image.Image] = {}

    def at(self, t: float) -> Image.Image:
        index = max(0, int(round(t * self.fps)))
        if index in self._cache:
            return self._cache[index]
        path = self.dir / (self.pattern % (index + 1))
        if not path.exists():                      # за концом берём последний
            existing = sorted(self.dir.glob("*"))
            path = existing[-1]
        image = Image.open(path).convert("RGB")
        # Кэш маленький: соседние кадры нужны только на время перехода.
        if len(self._cache) > 8:
            self._cache.clear()
        self._cache[index] = image
        return image


def frame_of(shot: Shot, sources: dict[str, Frames], t: float) -> Image.Image:
    """Кадр плана в момент t по времени готового ролика."""
    span = max(shot.end - shot.start, 1e-6)
    zoom, cx, cy = shot.move.at((t - shot.start) / span)
    image = sources[shot.source].at(shot.offset + (t - shot.start))
    width, height = image.size

    # Рамка вырезается по дробным координатам — иначе на медленном зуме
    # видно, как картинка скачет на целый пиксель.
    box_w = width / zoom
    box_h = height / zoom
    left = cx * width - box_w / 2
    top = cy * height - box_h / 2
    left = min(max(left, 0.0), width - box_w)
    top = min(max(top, 0.0), height - box_h)
    return image.resize(
        (FRAME_W, FRAME_H), Image.LANCZOS, box=(left, top, left + box_w, top + box_h)
    )


def compose(shots: list[Shot], sources: dict[str, Frames], duration: float,
            fps: int, out_dir: Path) -> int:
    """Считает все кадры ролика и складывает их в out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    total = int(round(duration * fps))

    for i in range(total):
        t = i / fps
        index = next(
            (n for n, s in enumerate(shots) if s.start <= t < s.end), len(shots) - 1
        )
        shot = shots[index]
        image = frame_of(shot, sources, t)

        # Переход берёт кадр предыдущего плана в тот же момент времени.
        u = (t - shot.start) / shot.trans_dur if shot.trans_dur else 2.0
        if index > 0 and u < 1.0 and shot.transition != "cut":
            previous = shots[index - 1]
            under = frame_of(previous, sources, t)
            e = ease(u)
            if shot.transition == "blur":
                # Смаз нарастает к середине перехода и гаснет к концу.
                peak = 1.0 - abs(u * 2 - 1)
                radius = 14 * peak
                if radius > 0.4:
                    image = image.filter(ImageFilter.GaussianBlur(radius))
                    under = under.filter(ImageFilter.GaussianBlur(radius))
            image = Image.blend(under, image, e)

        image.save(out_dir / f"f_{i:05d}.jpg", quality=94, subsampling=1)
    return total
