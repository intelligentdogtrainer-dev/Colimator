"""Субтитры в стиле референса.

На вход — SRT или VTT с таймингами. На выход — файл .ass, в котором реплики
перерезаны на короткие строки по 3–5 слов и оформлены как в референсе.

Локальной расшифровки речи в этом окружении нет (модели Whisper недоступны:
huggingface.co и CDN OpenAI закрыты сетевой политикой), поэтому тайминги
приходят из готовых субтитров. Внутри реплики слова раскладываются
пропорционально своей длине — этого достаточно, чтобы строка менялась в такт
речи при длине реплики в несколько секунд.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .style import Cadence, CaptionStyle, FRAME_H, FRAME_W

_TIME_RE = re.compile(
    r"(\d+):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[.,](\d{1,3})"
)
# Знаки, после которых строку разорвать естественно.
_STRONG_BREAK = ".!?…:;"
_WEAK_BREAK = ",—–"


@dataclass
class Cue:
    start: float
    end: float
    text: str


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Line:
    start: float
    end: float
    text: str


def _hms(h: str, m: str, s: str, ms: str) -> float:
    # Некоторые экспортёры срезают ведущие нули в миллисекундах: "06,59" — это
    # 6.059, а не 6.590. Дополняем слева, иначе реплики наезжают друг на друга.
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.zfill(3)) / 1000


def parse_subtitles(raw: str) -> list[Cue]:
    """Разбирает SRT или VTT. Формат определяется по строке тайминга."""
    cues: list[Cue] = []
    start = end = None
    buf: list[str] = []

    def flush() -> None:
        if start is None:
            return
        text = " ".join(part.strip() for part in buf if part.strip())
        text = re.sub(r"<[^>]+>", "", text)  # инлайновая разметка VTT
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            cues.append(Cue(start, end, text))

    for raw_line in raw.replace("﻿", "").splitlines():
        line = raw_line.rstrip()
        match = _TIME_RE.search(line)
        if match:
            flush()
            buf = []
            start = _hms(*match.group(1, 2, 3, 4))
            end = _hms(*match.group(5, 6, 7, 8))
            continue
        if not line.strip():
            flush()
            start = end = None
            buf = []
            continue
        # Порядковый номер реплики SRT и заголовок WEBVTT содержания не несут.
        if not buf and (line.strip().isdigit() or line.strip().upper().startswith("WEBVTT")):
            continue
        buf.append(line)

    flush()
    if not cues:
        raise ValueError("не найдено ни одной реплики — ожидается SRT или VTT")
    return cues


def to_words(cues: list[Cue]) -> list[Word]:
    """Раскладывает реплики на слова, распределяя время по длине слов."""
    words: list[Word] = []
    for cue in cues:
        tokens = cue.text.split()
        if not tokens:
            continue
        span = max(cue.end - cue.start, 1e-3)
        weights = [len(t) + 1 for t in tokens]
        total = sum(weights)
        t = cue.start
        for token, weight in zip(tokens, weights):
            dt = span * weight / total
            words.append(Word(t, t + dt, token))
            t += dt
    return words


def _break_score(token: str) -> int:
    """Насколько естественно разорвать строку после этого слова."""
    tail = token.rstrip('"»)')
    if tail.endswith(tuple(_STRONG_BREAK)):
        return 2
    if tail.endswith(tuple(_WEAK_BREAK)):
        return 1
    return 0


def chunk(words: list[Word], cadence: Cadence | None = None) -> list[Line]:
    """Собирает слова в строки по ритму референса.

    Строка закрывается, когда набрано max_words слов, либо когда она уже
    достаточно длинная по времени, либо на знаке препинания — при условии, что
    слов набралось не меньше min_words.
    """
    cadence = cadence or Cadence()
    lines: list[Line] = []
    current: list[Word] = []

    def close() -> None:
        if not current:
            return
        lines.append(
            Line(current[0].start, current[-1].end, " ".join(w.text for w in current))
        )
        current.clear()

    for word in words:
        # Заметная пауза в речи — тоже граница строки.
        if current and word.start - current[-1].end > 0.6:
            close()
        current.append(word)
        count = len(current)
        duration = current[-1].end - current[0].start
        score = _break_score(word.text)
        # Конец предложения закрывает строку всегда: в референсе строка никогда
        # не перетекает через точку в следующую фразу.
        if score >= 2:
            close()
            continue
        if count >= cadence.max_words or duration >= cadence.max_duration:
            close()
            continue
        if count >= cadence.min_words and score > 0:
            close()

    close()
    return _enforce_min_duration(lines, cadence)


def _enforce_min_duration(lines: list[Line], cadence: Cadence) -> list[Line]:
    """Растягивает слишком короткие строки в паузу до следующей."""
    for i, line in enumerate(lines):
        if line.end - line.start >= cadence.min_duration:
            continue
        limit = lines[i + 1].start if i + 1 < len(lines) else line.start + cadence.max_duration
        line.end = min(line.start + cadence.min_duration, max(limit, line.end))
    for i in range(len(lines) - 1):
        lines[i].end = min(lines[i].end, lines[i + 1].start - cadence.gap)
    return [ln for ln in lines if ln.end > ln.start]


def _ass_time(t: float) -> str:
    t = max(t, 0.0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ass_color(hex_color: str, opacity: float = 1.0) -> str:
    """#RRGGBB -> &HAABBGGRR. В ASS альфа инвертирована: 00 — непрозрачно."""
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    alpha = round((1.0 - min(max(opacity, 0.0), 1.0)) * 255)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def to_ass(lines: list[Line], style: CaptionStyle | None = None,
           layer: int = 0) -> str:
    """Собирает .ass с плашкой и фиксированной позицией строки.

    layer задаёт порядок отрисовки: события с большим значением рисуются
    поверх. Пригодится, если под субтитры нужно подложить что-то ещё.
    """
    style = style or CaptionStyle()
    # BorderStyle=3 рисует непрозрачную плашку, её поля задаются Outline.
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {FRAME_W}
PlayResY: {FRAME_H}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{style.font},{style.size},{_ass_color(style.text_color)},{_ass_color(style.text_color)},{_ass_color(style.box_color, style.box_opacity)},{_ass_color(style.box_color, style.box_opacity)},0,0,0,0,100,100,0,0,3,{style.padding},0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(
        f"Dialogue: {layer},{_ass_time(ln.start)},{_ass_time(ln.end)},Caption,,0,0,0,,"
        f"{{\\pos({FRAME_W // 2},{style.y_px})}}{ln.text}\n"
        for ln in lines
    )
    return header + body


def hold_until_next(lines: list[Line], cadence: Cadence | None = None) -> list[Line]:
    """Держит строку на экране до появления следующей, убирая просветы.

    Нужно, когда субтитры обязаны закрывать что-то в кадре — например подписи,
    вжатые в исходник экспортом монтажки: в паузе между нашими строками эти
    подписи иначе видно.
    """
    cadence = cadence or Cadence()
    for current, following in zip(lines, lines[1:]):
        current.end = max(current.end, following.start - cadence.gap)
    return lines


def build(raw_subtitles: str, style: CaptionStyle | None = None,
          cadence: Cadence | None = None, continuous: bool = False,
          layer: int = 0) -> str:
    """SRT/VTT -> готовый .ass в стиле референса."""
    lines = chunk(to_words(parse_subtitles(raw_subtitles)), cadence)
    if continuous:
        lines = hold_until_next(lines, cadence)
    return to_ass(lines, style, layer)
