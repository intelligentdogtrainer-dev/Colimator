"""Визуальные константы, снятые с референсного ролика.

Все значения — в системе координат кадра 720x1280. См. docs/reference-breakdown.md.
"""

from dataclasses import dataclass

# Палитра референса.
CANVAS_BG = "#DFDDD0"
INK = "#070602"
GREEN = "#7A925E"
CAPTION_BOX = "#605F5C"
ENDCARD_BG = "#F9F8F4"

FRAME_W = 720
FRAME_H = 1280


@dataclass(frozen=True)
class CaptionStyle:
    """Стиль субтитров.

    Значения по умолчанию воспроизводят референс: белый serif на почти
    непрозрачной серой плашке, фиксированная позиция на 62.5% высоты кадра.
    """

    font: str = "PT Serif"
    size: int = 40
    text_color: str = "#FFFFFF"
    box_color: str = CAPTION_BOX
    box_opacity: float = 0.90
    # Внутренние поля плашки в пикселях кадра.
    padding: int = 10
    # Центр плашки по вертикали, доля высоты кадра.
    y_ratio: float = 0.625

    @property
    def y_px(self) -> int:
        return round(FRAME_H * self.y_ratio)


@dataclass(frozen=True)
class Cadence:
    """Ритм нарезки субтитров, снятый с референса.

    В референсе строка живёт 1.2–1.5 с и содержит 3–5 слов.
    """

    min_words: int = 3
    max_words: int = 5
    min_duration: float = 0.7
    max_duration: float = 2.0
    # Минимальный зазор между строками, чтобы смена читалась как смена.
    gap: float = 0.04
