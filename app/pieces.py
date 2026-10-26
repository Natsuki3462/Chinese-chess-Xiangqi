from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

import theme

_FONT_CACHE: dict[int, QFont] = {}

def piece_font(pixel_size: int, bold: bool = True) -> QFont:
    key = pixel_size * 10 + (1 if bold else 0)
    font = _FONT_CACHE.get(key)
    if font is None:
        font = QFont(theme.UI_FONT)
        font.setPixelSize(max(8, pixel_size))
        font.setBold(bold)
        _FONT_CACHE[key] = font
    return font

def draw_piece(
    painter: QPainter,
    center: QPointF,
    radius: float,
    char: str,
    is_red: bool,
    selected: bool = False,
    dim: bool = False,
) -> None:
    if radius <= 1.0:
        return

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    face = theme.PIECE_FACE if is_red else theme.PIECE_FACE_BLACK
    if dim:
        face = QColor(face)
        face.setAlpha(170)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(60, 45, 28, 70))
    painter.drawEllipse(
        QRectF(center.x() - radius, center.y() - radius + radius * 0.10,
               radius * 2, radius * 2)
    )

    outer = QRectF(
        center.x() - radius,
        center.y() - radius,
        radius * 2,
        radius * 2,
    )
    painter.setPen(QPen(theme.PIECE_EDGE, max(1.0, radius * 0.075)))
    painter.setBrush(face)
    painter.drawEllipse(outer)

    inset = radius * 0.70
    painter.setPen(QPen(theme.PIECE_EDGE_INNER, max(0.8, radius * 0.045)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(
        QRectF(center.x() - inset, center.y() - inset, inset * 2, inset * 2)
    )

    if char:
        font = piece_font(int(radius * 1.22))
        painter.setFont(font)
        painter.setPen(theme.RED_SIDE if is_red else theme.BLACK_SIDE)
        metrics = QFontMetricsF(font)
        baseline = center.y() + (metrics.ascent() - metrics.descent()) / 2.0
        width = metrics.horizontalAdvance(char)
        painter.drawText(QPointF(center.x() - width / 2.0, baseline), char)

    if selected:
        glow = QPen(theme.ACCENT, max(1.6, radius * 0.11))
        painter.setPen(glow)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(outer.adjusted(-1, -1, 1, 1))

    painter.restore()
