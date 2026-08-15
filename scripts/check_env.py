"""Проверка окружения: всё ли на месте для сборки роликов.

    python scripts/check_env.py
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OK, FAIL, WARN = "  ok  ", " нет  ", " ! "


def check_python() -> bool:
    good = sys.version_info >= (3, 11)
    print(f"[{OK if good else FAIL}] Python {sys.version.split()[0]}"
          f"{'' if good else '  — нужен 3.11 или новее'}")
    return good


def check_module(name: str, why: str, required: bool = True) -> bool:
    try:
        importlib.import_module(name)
    except ImportError:
        mark = FAIL if required else WARN
        tail = "pip install -r requirements.txt" if required else "нужен только для расшифровки"
        print(f"[{mark}] {name} — {why}. {tail}")
        return not required
    print(f"[{OK}] {name} — {why}")
    return True


def check_binary(name: str) -> bool:
    path = shutil.which(name)
    if not path:
        print(f"[{FAIL}] {name} не найден в PATH")
        return False
    version = subprocess.run([name, "-version"], capture_output=True, text=True)
    first = version.stdout.splitlines()[0] if version.stdout else name
    print(f"[{OK}] {first[:60]}")
    return True


def check_fonts() -> bool:
    needed = ["PlayfairDisplay[wght].ttf", "PT_Serif-Web-Regular.ttf"]
    missing = [n for n in needed if not (ROOT / "assets" / "fonts" / n).exists()]
    if missing:
        print(f"[{FAIL}] нет шрифтов: {', '.join(missing)}")
        return False
    print(f"[{OK}] шрифты на месте")
    return True


def check_chromium() -> bool:
    """Рисует один кадр — это разом проверяет и браузер, и подключение шрифтов."""
    try:
        from colimator.canvas import CameraKey, Node, Scene, render
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            frames = render(
                Scene(duration=0.6, fps=5,
                      nodes=[Node(0, 0, "Проверка", "heading")],
                      camera=[CameraKey(t=0, x=0, y=0, scale=1.0)]),
                Path(tmp),
            )
        print(f"[{OK}] Chromium рисует кадры ({frames} шт.)")
        return True
    except Exception as error:
        print(f"[{FAIL}] Chromium не запустился: {str(error).splitlines()[0][:120]}")
        print("        поможет: playwright install chromium")
        return False


def main() -> None:
    print("Проверка окружения Colimator\n")
    results = [
        check_python(),
        check_module("PIL", "компоновка кадров"),
        check_module("numpy", "разбор звука"),
        check_module("cv2", "трекинг лица"),
        check_module("playwright", "рендер графики"),
        check_module("faster_whisper", "расшифровка речи", required=False),
        check_binary("ffmpeg"),
        check_binary("ffprobe"),
        check_fonts(),
        check_chromium(),
    ]
    print()
    if all(results):
        print("Всё готово. Можно собирать: python scripts/build_agency_part1.py")
    else:
        print("Есть чего не хватает — смотри строки выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()
