"""Сборка демо: 16 секунд из ролика про домашнюю собаку в стиле референса.

Говорящая голова до 12.9 с, дальше врезка холста с заголовком и «таблетками».
Субтитры идут поверх всего и стоят на 71 % высоты кадра — так они закрывают
подписи, вжатые в исходник экспортом VEED.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colimator.canvas import CameraKey, Node, Scene, render  # noqa: E402
from colimator.captions import build  # noqa: E402
from colimator.style import CaptionStyle  # noqa: E402

SOURCE = Path(
    "/root/.claude/uploads/d319b216-0203-5f2b-8282-4960bf927c3d/"
    "72a76446-______________________VEED_Export.mov"
)
OUT = ROOT / "out"
FPS = 30
CUT = 12.9      # переход с говорящей головы на холст
END = 15.90     # конец демо

# Субтитры закрывают вжатые подписи VEED (они занимают y=893..931, x=203..513),
# поэтому ниже референсных 62.5 % и без прозрачности: на 90 % белые буквы
# исходника просвечивают сквозь плашку.
CAPTIONS = CaptionStyle(y_ratio=0.7125, box_opacity=1.0)
# В кадре голова стоит высоко, места под двухстрочный заголовок нет,
# поэтому одна строка у самого верха.
TITLE = "Что значит быть собакой?"
# Цвет плашки в порядке BGR, как принято в ASS.
PLATE = "5C5F60"


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip()[-3000:])


def build_canvas(path: Path) -> None:
    """Врезка холста: заголовок и две «таблетки» под голос за кадром."""
    scene = Scene(
        duration=END - CUT,
        fps=FPS,
        nodes=[
            Node(0, 0, "Домашняя собака", "heading", appear=0.16),
            Node(-140, 190, "мотивации", "pill", appear=1.40),
            Node(170, 330, "потребности", "pill", appear=2.44),
            Node(-540, -330, "Благополучие", "ghost", appear=0.0),
            Node(620, 520, "Собака как вид", "ghost", appear=0.0),
        ],
        camera=[
            CameraKey(t=0.0, x=0, y=60, scale=1.05),
            CameraKey(t=END - CUT, x=40, y=200, scale=0.95),
        ],
    )
    frames = OUT / "canvas_frames"
    count = render(scene, frames)
    print(f"холст: {count} кадров")
    run([
        "ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
        "-i", str(frames / "frame_%05d.png"),
        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(path),
    ])


def build_subtitles(path: Path) -> None:
    raw = (ROOT / "assets" / "demo" / "demo_01.srt").read_text(encoding="utf-8")
    # Строки держатся до следующей: иначе в паузах видно вжатые подписи VEED.
    ass = build(raw, CAPTIONS, continuous=True, layer=1)
    # Заголовок первых секунд — как в референсе: serif по центру верхней трети.
    # В отличие от референса фон здесь светлый и пёстрый, поэтому под текст
    # добавлены тонкий контур и тень.
    ass = ass.replace(
        "[Events]",
        "Style: Title,Playfair Display,46,&H00F5F3EC,&H00F5F3EC,&H5A100E08,"
        "&H78000000,0,0,0,0,100,100,0,0,1,2,3,8,40,40,0,1\n"
        # Подложка под субтитрами: самые длинные подписи VEED шире короткой
        # строки и торчали бы по краям плашки.
        "Style: Plate,PT Serif,40,&H00" + PLATE + ",&H00" + PLATE + ",&H00" + PLATE
        + ",&H00" + PLATE + ",0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n[Events]",
    )
    ass += (
        f"Dialogue: 0,0:00:00.60,0:00:{CUT:05.2f},Plate,,0,0,0,,"
        "{\\p1\\pos(0,0)}m 190 881 l 530 881 l 530 943 l 190 943{\\p0}\n"
    )
    ass += (
        "Dialogue: 0,0:00:00.70,0:00:04.60,Title,,0,0,0,,"
        f"{{\\pos(360,108)}}{TITLE}\n"
    )
    path.write_text(ass, encoding="utf-8")
    print(f"субтитры: {ass.count('Dialogue:')} событий")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    canvas = OUT / "canvas.mp4"
    subs = OUT / "demo_01.ass"
    result = OUT / "demo_01.mp4"

    build_canvas(canvas)
    build_subtitles(subs)

    ass = subs.as_posix().replace(":", r"\:")
    fonts = (ROOT / "assets" / "fonts").as_posix().replace(":", r"\:")
    run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(SOURCE),
        "-i", str(canvas),
        "-filter_complex",
        (
            f"[0:v]trim=0:{CUT},setpts=PTS-STARTPTS,fps={FPS},"
            f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280[a];"
            f"[1:v]fps={FPS},scale=720:1280[b];"
            f"[a][b]concat=n=2:v=1:a=0[v];"
            f"[v]subtitles='{ass}':fontsdir='{fonts}'[vout];"
            f"[0:a]atrim=0:{END},asetpts=PTS-STARTPTS[aout]"
        ),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(result),
    ])
    print(result)


if __name__ == "__main__":
    main()
