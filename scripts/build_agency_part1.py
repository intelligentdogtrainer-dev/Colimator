"""«Что собака решает сама?» — первая треть, линейный порядок.

Собирается по docs/cut-plan-agency.md. Видео есть только на первые 15 секунд
исходника, поэтому кусок заканчивается на 14.30 — ровно там, где закрывается
мысль «…чем мы привыкли двигаться».

Все времена ниже — по таймлайну готового ролика. Исходник смещён на HEAD:
ролик начинается с 0.82 с, потому что до этого в кадре только «Да. То есть».
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colimator.canvas import CameraKey, Link, Node, Scene, render  # noqa: E402
from colimator.captions import build  # noqa: E402
from colimator.compositor import Frames, Move, Shot, compose  # noqa: E402
from colimator.style import CaptionStyle  # noqa: E402

SOURCE = Path(
    "/root/.claude/uploads/d319b216-0203-5f2b-8282-4960bf927c3d/"
    "1bfed9dd-_____________________________VEED_Export.mov"
)
OUT = ROOT / "out"
WORK = OUT / "work_agency"
FPS = 30

HEAD = 0.82         # с какой секунды исходника начинается ролик
CANVAS_IN = 7.62    # уход на холст
AUDIO_END = 13.48   # докуда идёт речь
END = 15.68         # с концовкой

CAPTIONS = CaptionStyle()
TITLE = "Что собака решает сама?"
# Текст концовки — заглушка: меняется этими двумя строками.
ENDCARD_TITLE = "Полный разбор"
ENDCARD_CTA = "на YouTube"


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip()[-3000:])


def canvas_scene() -> Scene:
    """«Чего она хочет»: три потребности выезжают ровно на своих словах."""
    return Scene(
        duration=AUDIO_END - CANVAS_IN,
        fps=FPS,
        nodes=[
            Node(-560, -380, "Прогулка", "ghost"),
            Node(500, -430, "Запахи", "ghost"),
            Node(-720, 160, "Поводок", "ghost"),
            Node(760, 120, "Расстояние", "ghost"),
            Node(-560, 620, "Свобода выбора", "ghost"),
            Node(600, 640, "Инициатива", "ghost"),
            Node(-100, -620, "Скорость", "ghost"),
            Node(180, 800, "Контакт", "ghost"),
            Node(0, -140, "Чего она хочет", "heading", appear=0.40),   # 8
            Node(-170, 20, "уходить дальше", "pill", appear=1.34),      # 9
            Node(170, 150, "нюхать", "pill", appear=2.76),              # 10
            Node(-60, 280, "идти быстрее", "pill", appear=3.76),        # 11
        ],
        links=[
            Link(8, 9, appear=1.24),
            Link(8, 10, appear=2.66),
            Link(8, 11, appear=3.66),
        ],
        # Камера едет вниз вслед за новыми узлами так, чтобы очередная
        # «таблетка» вставала около 600-й строки кадра — выше субтитров,
        # которые занимают полосу 770–830.
        camera=[
            CameraKey(t=0.0, x=0, y=-40, scale=0.55),
            CameraKey(t=1.2, x=0, y=-60, scale=0.95),
            CameraKey(t=1.9, x=-30, y=83, scale=0.95),
            CameraKey(t=3.0, x=30, y=172, scale=0.92),
            CameraKey(t=4.0, x=-20, y=280, scale=0.90),
            CameraKey(t=AUDIO_END - CANVAS_IN, x=0, y=300, scale=0.88),
        ],
    )


def endcard_scene() -> Scene:
    """Призыв уйти на YouTube. Зелёная таблетка — единственный акцент цветом."""
    return Scene(
        duration=END - AUDIO_END,
        fps=FPS,
        nodes=[
            Node(0, -60, ENDCARD_TITLE, "heading", appear=0.12),
            Node(0, 80, "*" + ENDCARD_CTA, "pill", appear=0.50),
        ],
        camera=[
            CameraKey(t=0.0, x=0, y=0, scale=1.00),
            CameraKey(t=END - AUDIO_END, x=0, y=-30, scale=1.05),
        ],
    )


def shots() -> list[Shot]:
    """Смены рамки посажены на границы фраз.

    Лицо стоит в кадре высоко, поэтому центр крупных планов — выше середины.
    """
    return [
        # Общий, еле заметный наезд под заголовок.
        Shot(0.00, 3.08, "video",
             Move(zoom=(1.00, 1.07), center=((0.48, 0.44), (0.49, 0.42))),
             offset=HEAD),
        # Крупный план на перечислении — читается как вторая камера.
        Shot(3.08, 6.78, "video",
             Move(zoom=(1.34, 1.26), center=((0.47, 0.33), (0.48, 0.35))),
             offset=3.90, transition="cut"),
        # «Для чего?» — наезд на паузе перед ответом.
        Shot(6.78, CANVAS_IN, "video",
             Move(zoom=(1.44, 1.50), center=((0.48, 0.31), (0.48, 0.31))),
             offset=7.60, transition="cut"),
        # Ответ уходит на графику.
        Shot(CANVAS_IN, AUDIO_END, "canvas", Move(),
             transition="blur", trans_dur=0.5),
        Shot(AUDIO_END, END, "end", Move(),
             transition="dissolve", trans_dur=0.45),
    ]


def build_subtitles(path: Path) -> None:
    raw = (ROOT / "assets" / "demo" / "agency_part1.srt").read_text(encoding="utf-8")
    ass = build(raw, CAPTIONS)
    ass = ass.replace(
        "[Events]",
        "Style: Title,Playfair Display,46,&H00F5F3EC,&H00F5F3EC,&H5A100E08,"
        "&H78000000,0,0,0,0,100,100,0,0,1,2,3,8,40,40,0,1\n\n[Events]",
    )
    ass += (
        "Dialogue: 0,0:00:00.25,0:00:03.00,Title,,0,0,0,,"
        f"{{\\pos(360,108)}}{TITLE}\n"
    )
    path.write_text(ass, encoding="utf-8")
    print(f"субтитры: {ass.count('Dialogue:')} событий")


def main() -> None:
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)

    video_dir = WORK / "video"
    video_dir.mkdir()
    run(["ffmpeg", "-y", "-v", "error", "-i", str(SOURCE),
         "-vf", f"fps={FPS}", "-q:v", "2", str(video_dir / "v_%05d.jpg")])

    canvas_dir, end_dir = WORK / "canvas", WORK / "end"
    print(f"холст: {render(canvas_scene(), canvas_dir)} кадров")
    print(f"концовка: {render(endcard_scene(), end_dir)} кадров")

    sources = {
        "video": Frames(video_dir, "v_%05d.jpg", FPS),
        "canvas": Frames(canvas_dir, "frame_%05d.png", FPS),
        "end": Frames(end_dir, "frame_%05d.png", FPS),
    }
    frames_dir = WORK / "out"
    print(f"сборка: {compose(shots(), sources, END, FPS, frames_dir)} кадров")

    subs = OUT / "agency_part1.ass"
    build_subtitles(subs)
    ass = subs.as_posix().replace(":", r"\:")
    fonts = (ROOT / "assets" / "fonts").as_posix().replace(":", r"\:")
    result = OUT / "agency_part1.mp4"
    run([
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-i", str(frames_dir / "f_%05d.jpg"),
        "-i", str(SOURCE),
        "-filter_complex",
        (
            f"[0:v]subtitles='{ass}':fontsdir='{fonts}'[vout];"
            f"[1:a]atrim={HEAD}:{HEAD + AUDIO_END},asetpts=PTS-STARTPTS,"
            # Громкость под площадки: EBU R128, как требуют TikTok и Reels.
            # Концовка идёт в тишине, поэтому хвост добивается apad.
            f"loudnorm=I=-14:TP=-1.5:LRA=11,apad[aout]"
        ),
        "-map", "[vout]", "-map", "[aout]", "-t", str(END),
        "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(result),
    ])
    print(result)


if __name__ == "__main__":
    main()
