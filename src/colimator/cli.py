"""Командный интерфейс.

    python -m colimator captions in.srt out.ass
    python -m colimator burn in.mp4 out.ass out.mp4 [--from 12 --to 30]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .captions import build
from .style import FRAME_H, FRAME_W

FONTS_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"


def _run(cmd: list[str]) -> None:
    if not shutil.which(cmd[0]):
        sys.exit(f"не найден {cmd[0]}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip()[-2000:] or f"{cmd[0]} завершился с кодом {proc.returncode}")


def cmd_captions(args: argparse.Namespace) -> None:
    raw = Path(args.source).read_text(encoding="utf-8-sig")
    ass = build(raw)
    Path(args.output).write_text(ass, encoding="utf-8")
    print(f"{args.output}: {ass.count('Dialogue:')} строк")


def cmd_burn(args: argparse.Namespace) -> None:
    """Приводит кадр к 9:16 и вжигает субтитры."""
    ass = Path(args.subtitles).as_posix().replace(":", r"\:").replace("'", r"\'")
    fonts = FONTS_DIR.as_posix().replace(":", r"\:")
    vf = (
        f"scale={FRAME_W}:{FRAME_H}:force_original_aspect_ratio=increase,"
        f"crop={FRAME_W}:{FRAME_H},"
        f"subtitles='{ass}':fontsdir='{fonts}'"
    )
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if args.start is not None:
        cmd += ["-ss", str(args.start)]
    if args.end is not None:
        cmd += ["-to", str(args.end)]
    cmd += [
        "-i", args.video,
        "-vf", vf,
        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        args.output,
    ]
    _run(cmd)
    print(args.output)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="colimator")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("captions", help="SRT/VTT -> ASS в стиле референса")
    p.add_argument("source")
    p.add_argument("output")
    p.set_defaults(func=cmd_captions)

    p = sub.add_parser("burn", help="вжечь субтитры в видео, кадр 9:16")
    p.add_argument("video")
    p.add_argument("subtitles")
    p.add_argument("output")
    p.add_argument("--from", dest="start", type=float, default=None)
    p.add_argument("--to", dest="end", type=float, default=None)
    p.set_defaults(func=cmd_burn)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
