"""Демо 02 — движение камеры и переходы.

Исходник снят одним планом без единой склейки. Второй ракурс делается наездом:
крупная рамка внутри того же кадра читается как отдельная камера, и между
такими планами можно резать. Плюс медленные проезды, кроссфейд, размытый
переход в холст и концовка.

Вжатые в исходник подписи VEED тут не маскируются — субтитры стоят на
референсных 62.5 % высоты с полупрозрачной плашкой.
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
    "72a76446-______________________VEED_Export.mov"
)
OUT = ROOT / "out"
WORK = OUT / "work02"
FPS = 30
CANVAS_IN = 11.0    # уход на холст
AUDIO_END = 15.90   # докуда есть звук исходника
END = 17.40         # с концовкой

CAPTIONS = CaptionStyle()   # ровно как в референсе
TITLE = "Что значит быть собакой?"
ENDCARD = "Понимаем свою собаку"


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip()[-3000:])


def canvas_scene() -> Scene:
    """Карта понятий: камера облетает её и подъезжает к нужному узлу."""
    return Scene(
        duration=AUDIO_END - CANVAS_IN,
        fps=FPS,
        nodes=[
            # Периферия карты: она читается на широком плане и задаёт масштаб.
            Node(-560, -430, "Благополучие", "ghost"),
            Node(430, -470, "Среда обитания", "ghost"),
            Node(-700, 120, "Обучение", "ghost"),
            Node(760, 180, "Собака как вид", "ghost"),
            Node(-540, 600, "Безопасность", "ghost"),
            Node(560, 640, "Общение", "ghost"),
            Node(-120, -560, "Порода", "ghost"),
            Node(140, 760, "Характер", "ghost"),
            Node(-780, -170, "Возраст", "ghost"),
            Node(820, -140, "Здоровье", "ghost"),
            Node(0, 0, "Домашняя собака", "heading", appear=2.06),      # 10
            Node(-160, 200, "мотивации", "pill", appear=3.30),          # 11
            Node(150, 330, "потребности", "pill", appear=4.34),         # 12
        ],
        links=[
            Link(10, 11, appear=3.20),
            Link(10, 12, appear=4.24),
        ],
        camera=[
            CameraKey(t=0.0, x=20, y=60, scale=0.52),
            CameraKey(t=2.0, x=0, y=-30, scale=0.92),
            CameraKey(t=3.3, x=-70, y=90, scale=0.96),
            CameraKey(t=AUDIO_END - CANVAS_IN, x=30, y=210, scale=0.88),
        ],
    )


def endcard_scene() -> Scene:
    return Scene(
        duration=END - AUDIO_END,
        fps=FPS,
        nodes=[
            Node(0, -40, ENDCARD, "heading", appear=0.12),
            Node(0, 60, "разбор языка тела", "ghost", appear=0.45),
        ],
        camera=[
            CameraKey(t=0.0, x=0, y=0, scale=1.00),
            CameraKey(t=END - AUDIO_END, x=0, y=-25, scale=1.04),
        ],
    )


def shots() -> list[Shot]:
    """Раскадровка. Наезды посажены на границы фраз, а не на ровные секунды."""
    return [
        # Общий план, еле заметный наезд — кадр «дышит».
        Shot(0.00, 3.10, "video",
             Move(zoom=(1.00, 1.09), center=((0.50, 0.46), (0.52, 0.44)))),
        # Резкий переход на крупную рамку: читается как вторая камера.
        Shot(3.10, 6.50, "video",
             Move(zoom=(1.36, 1.28), center=((0.50, 0.34), (0.49, 0.36))),
             transition="cut"),
        # Кроссфейд обратно на общий, камера отъезжает.
        Shot(6.50, 9.70, "video",
             Move(zoom=(1.14, 1.00), center=((0.50, 0.42), (0.50, 0.46))),
             transition="dissolve", trans_dur=0.45),
        # Ещё ближе — перед уходом на графику.
        Shot(9.70, CANVAS_IN, "video",
             Move(zoom=(1.42, 1.52), center=((0.50, 0.33), (0.50, 0.32))),
             transition="cut"),
        # Смаз на переходе в холст, дальше камера едет уже внутри сцены.
        Shot(CANVAS_IN, AUDIO_END, "canvas", Move(),
             transition="blur", trans_dur=0.55),
        Shot(AUDIO_END, END, "end", Move(),
             transition="dissolve", trans_dur=0.45),
    ]


def build_subtitles(path: Path) -> None:
    raw = (ROOT / "assets" / "demo" / "demo_01.srt").read_text(encoding="utf-8")
    ass = build(raw, CAPTIONS)
    # Фон в кадре светлый и пёстрый, поэтому под заголовком контур и тень.
    ass = ass.replace(
        "[Events]",
        "Style: Title,Playfair Display,46,&H00F5F3EC,&H00F5F3EC,&H5A100E08,"
        "&H78000000,0,0,0,0,100,100,0,0,1,2,3,8,40,40,0,1\n\n[Events]",
    )
    ass += (
        "Dialogue: 0,0:00:00.70,0:00:03.05,Title,,0,0,0,,"
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

    subs = OUT / "demo_02.ass"
    build_subtitles(subs)
    ass = subs.as_posix().replace(":", r"\:")
    fonts = (ROOT / "assets" / "fonts").as_posix().replace(":", r"\:")
    result = OUT / "demo_02.mp4"
    run([
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(FPS), "-i", str(frames_dir / "f_%05d.jpg"),
        "-i", str(SOURCE),
        "-filter_complex",
        (
            f"[0:v]subtitles='{ass}':fontsdir='{fonts}'[vout];"
            # Звук кончается раньше картинки — концовка идёт в тишине.
            f"[1:a]atrim=0:{AUDIO_END},asetpts=PTS-STARTPTS,apad[aout]"
        ),
        "-map", "[vout]", "-map", "[aout]", "-t", str(END),
        "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(result),
    ])
    print(result)


if __name__ == "__main__":
    main()
