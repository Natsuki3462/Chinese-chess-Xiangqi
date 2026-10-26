from __future__ import annotations

from PyQt6.QtGui import QColor

UI_FONT = "Microsoft YaHei"

CARD_BG = QColor(22, 24, 30, 246)
CARD_BORDER = QColor(255, 255, 255, 26)
HEADER_BG = QColor(31, 34, 42, 250)

BOARD_BG = QColor(238, 222, 190)
BOARD_LINE = QColor(96, 74, 48)
BOARD_EDGE = QColor(74, 55, 34)
RIVER_TEXT = QColor(120, 96, 66, 220)

RED_SIDE = QColor(178, 34, 34)
BLACK_SIDE = QColor(28, 28, 32)

PIECE_FACE = QColor(250, 242, 224)
PIECE_FACE_BLACK = QColor(244, 236, 218)
PIECE_EDGE = QColor(122, 92, 58)
PIECE_EDGE_INNER = QColor(186, 152, 108)

LAST_MOVE = QColor(72, 132, 232, 60)
SELECTED = QColor(74, 222, 128, 95)
HOVER = QColor(255, 255, 255, 46)
TARGET_DOT = QColor(58, 132, 96, 175)
CHECK_GLOW = QColor(226, 62, 62, 92)

ACCENT = QColor(74, 222, 128)
STALE = QColor(158, 168, 186)

TEXT = QColor(232, 236, 244)
TEXT_DIM = QColor(158, 168, 186)
TEXT_FAINT = QColor(108, 118, 136)
WARN = QColor(248, 113, 113)

QSS = """
QWidget {
    color: #e8ecf4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 12px;
}
QLabel#Title {
    color: #f2f5fa;
    font-size: 12px;
    font-weight: 600;
}
QLabel#Status {
    color: #9aa4b8;
    font-size: 11px;
}
QLabel#Eval {
    color: #cfd8e6;
    font-size: 12px;
    font-weight: 600;
    font-family: "Consolas", "Cascadia Mono", monospace;
}
QLabel#Pct {
    color: #7f8a9e;
    font-size: 10px;
    font-family: "Consolas", "Cascadia Mono", monospace;
}
QToolButton {
    color: #aab4c6;
    border: none;
    border-radius: 6px;
    background: transparent;
    font-size: 13px;
}
QToolButton:hover {
    background: rgba(255,255,255,0.09);
    color: #eef2f8;
}
QToolButton:pressed {
    background: rgba(255,255,255,0.14);
}
QToolButton:checked {
    background: rgba(74,222,128,0.20);
    color: #7ee2a8;
}
QToolButton:disabled {
    color: #4d5666;
}
QPushButton {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    padding: 3px 10px;
    color: #e4eaf4;
    font-size: 11px;
}
QPushButton:hover {
    background: rgba(255,255,255,0.17);
}
QPushButton:pressed {
    background: rgba(255,255,255,0.22);
}
QPushButton:disabled {
    background: rgba(255,255,255,0.04);
    color: #5b6474;
    border-color: rgba(255,255,255,0.05);
}
QPushButton#Primary {
    background: rgba(74,222,128,0.85);
    border: none;
    color: #10201a;
    font-weight: 600;
}
QPushButton#Primary:hover {
    background: rgba(96,235,146,0.95);
}
QPushButton#Primary:disabled {
    background: rgba(74,222,128,0.20);
    color: #5b6474;
}
QSlider::groove:horizontal {
    height: 5px;
    background: rgba(255,255,255,0.14);
    border-radius: 2.5px;
}
QSlider::sub-page:horizontal {
    background: rgba(74,222,128,0.55);
    border-radius: 2.5px;
}
QSlider::handle:horizontal {
    background: #dfe6f2;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QComboBox, QSpinBox, QLineEdit {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 5px;
    padding: 3px 6px;
    color: #e8ecf4;
    selection-background-color: rgba(74,222,128,0.55);
}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
    color: #6a7383;
    background: rgba(255,255,255,0.03);
}
QComboBox QAbstractItemView {
    background: #23262f;
    border: 1px solid rgba(255,255,255,0.14);
    selection-background-color: rgba(74,222,128,0.30);
    outline: none;
}
QCheckBox {
    color: #c8d2e2;
    font-size: 11px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid rgba(255,255,255,0.30);
    border-radius: 3px;
    background: rgba(255,255,255,0.05);
}
QCheckBox::indicator:checked {
    background: #4ade80;
    border-color: #4ade80;
}
QDialog {
    background: #1a1c23;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.18);
    border-radius: 4px;
}
"""
