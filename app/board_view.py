from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

import pieces
import theme
from session import Session

COLS = 9
ROWS = 10
RIVER_ROW = 4

FILE_LABELS = "abcdefghi"

class BoardView(QWidget):
    movePlayed = pyqtSignal(tuple, tuple)
    illegalMove = pyqtSignal(str)
    selectionChanged = pyqtSignal()

    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self._selected: tuple[int, int] | None = None
        self._hover: tuple[int, int] | None = None
        self._flash: tuple[int, int] | None = None
        self._suggestion: tuple[tuple[int, int], tuple[int, int]] | None = None
        self._suggestion_stale = False
        self._interactive = True
        self.show_coords = True

        self._press_pos: QPointF | None = None
        self._press_was_selected = False
        self._dragging = False

        self.setMinimumSize(300, 340)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_flash)

    def set_suggestion(self, move, stale: bool = False) -> None:
        self._suggestion = move
        self._suggestion_stale = stale
        self.update()

    @property
    def suggestion_move(self):
        return self._suggestion

    @property
    def suggestion_stale(self) -> bool:
        return self._suggestion_stale

    def clear_selection(self) -> None:
        if self._selected is not None:
            self._selected = None
            self.selectionChanged.emit()
            self.update()

    def is_interacting(self) -> bool:
        return self._dragging or self._selected is not None

    def set_interactive(self, enabled: bool) -> None:
        self._interactive = enabled
        if not enabled:
            self.clear_selection()

    def _clear_flash(self) -> None:
        self._flash = None
        self.update()

    def board_rect(self) -> QRectF:

        side_w = max(40.0, self.width() - 2 * self.margin())
        side_h = max(40.0, self.height() - 2 * self.margin())
        cell = min(side_w / (COLS - 1), side_h / (ROWS - 1))
        width = cell * (COLS - 1)
        height = cell * (ROWS - 1)
        return QRectF(
            (self.width() - width) / 2.0,
            (self.height() - height) / 2.0,
            width,
            height,
        )

    def margin(self) -> float:
        side = min(self.width(), self.height())
        return max(14.0, side * 0.055)

    def cell(self) -> float:
        return self.board_rect().width() / (COLS - 1)

    def piece_radius(self) -> float:
        return self.cell() * 0.44

    def point_xy(self, x: int, y: int) -> QPointF:
        rect = self.board_rect()
        cell = self.cell()
        col = (COLS - 1 - x) if self.session.flipped else x
        row = y if self.session.flipped else (ROWS - 1 - y)
        return QPointF(rect.x() + col * cell, rect.y() + row * cell)

    def point_rect(self, x: int, y: int) -> QRectF:
        center = self.point_xy(x, y)
        r = self.piece_radius()
        return QRectF(center.x() - r, center.y() - r, r * 2, r * 2)

    def square_at(self, pos: QPointF) -> tuple[int, int] | None:
        rect = self.board_rect()
        cell = self.cell()
        col = round((pos.x() - rect.x()) / cell)
        row = round((pos.y() - rect.y()) / cell)
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return None
        center = QPointF(rect.x() + col * cell, rect.y() + row * cell)
        if (pos - center).manhattanLength() > cell * 0.62:
            return None
        x = (COLS - 1 - col) if self.session.flipped else col
        y = row if self.session.flipped else (ROWS - 1 - row)
        return (x, y)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        self._paint_board(painter)
        self._paint_marks(painter)
        self._paint_pieces(painter)
        self._paint_drag_piece(painter)
        self._paint_arrow(painter)
        self._paint_coords(painter)

    def _paint_board(self, painter: QPainter) -> None:

        rect = self.board_rect()
        cell = self.cell()
        margin = self.margin()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.BOARD_BG)
        painter.drawRoundedRect(
            rect.adjusted(-margin * 0.56, -margin * 0.56,
                          margin * 0.56, margin * 0.56),
            7, 7,
        )

        line_w = max(1.0, cell * 0.022)
        pen = QPen(theme.BOARD_LINE, line_w)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for rank in range(ROWS):
            py = rect.y() + rank * cell
            painter.drawLine(QPointF(rect.x(), py), QPointF(rect.right(), py))

        river_top = rect.y() + RIVER_ROW * cell
        river_bottom = rect.y() + (RIVER_ROW + 1) * cell
        for file in range(COLS):
            px = rect.x() + file * cell
            if file in (0, COLS - 1):
                painter.drawLine(QPointF(px, rect.y()), QPointF(px, rect.bottom()))
            else:
                painter.drawLine(QPointF(px, rect.y()), QPointF(px, river_top))
                painter.drawLine(QPointF(px, river_bottom), QPointF(px, rect.bottom()))

        self._paint_river_text(painter, rect, cell)

        painter.setPen(QPen(theme.BOARD_EDGE, max(1.7, cell * 0.048)))
        painter.drawRect(rect)
        pad = cell * 0.14
        painter.setPen(QPen(theme.BOARD_EDGE, max(1.0, cell * 0.022)))
        painter.drawRect(rect.adjusted(-pad, -pad, pad, pad))

        self._paint_palaces(painter, rect, cell)

    def _paint_river_text(self, painter: QPainter, rect: QRectF, cell: float) -> None:

        mid_y = rect.y() + RIVER_ROW * cell + cell / 2.0
        font = QFont(theme.UI_FONT)
        font.setPixelSize(max(9, int(cell * 0.36)))
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, cell * 0.16)
        painter.setFont(font)
        painter.setPen(theme.RIVER_TEXT)

        band_h = cell * 0.80
        painter.drawText(
            QRectF(rect.x() + cell * 1.15, mid_y - band_h / 2.0, cell * 2.7, band_h),
            Qt.AlignmentFlag.AlignCenter,
            "楚河",
        )
        painter.drawText(
            QRectF(rect.right() - cell * 3.85, mid_y - band_h / 2.0, cell * 2.7, band_h),
            Qt.AlignmentFlag.AlignCenter,
            "汉界",
        )

    def _paint_palaces(self, painter: QPainter, r: QRectF, cell: float) -> None:
        pen = QPen(theme.BOARD_LINE, max(1.0, cell * 0.020))
        painter.setPen(pen)
        for top, bottom in ((0, 2), (7, 9)):
            x1, x2 = 3, 5
            p1 = QPointF(r.x() + x1 * cell, r.y() + top * cell)
            p2 = QPointF(r.x() + x2 * cell, r.y() + bottom * cell)
            painter.drawLine(p1, p2)
            p3 = QPointF(r.x() + x2 * cell, r.y() + top * cell)
            p4 = QPointF(r.x() + x1 * cell, r.y() + bottom * cell)
            painter.drawLine(p3, p4)

    def _paint_marks(self, painter: QPainter) -> None:
        last = self.session.last_move
        if last is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.LAST_MOVE)
            for pos in last:
                rect = self.point_rect(*pos)
                grow = rect.width() * 0.16
                painter.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow), 5, 5)

        if self._selected is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.SELECTED)
            rect = self.point_rect(*self._selected)
            grow = rect.width() * 0.18
            painter.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow), 6, 6)

        if self._selected is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.TARGET_DOT)
            radius = max(2.4, self.cell() * 0.085)
            for target in self.session.legal_targets(self._selected):
                center = self.point_xy(*target)
                occupied = self.session.piece_at(target) is not None
                if occupied:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(theme.TARGET_DOT, max(1.6, self.cell() * 0.055)))
                    r = self.piece_radius() * 1.02
                    painter.drawEllipse(QRectF(center.x() - r, center.y() - r, r * 2, r * 2))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(theme.TARGET_DOT)
                else:
                    painter.drawEllipse(center, radius, radius)

        if self._flash is not None:
            center = self.point_xy(*self._flash)
            r = self.piece_radius() * 1.05
            painter.setPen(QPen(theme.WARN, max(1.8, self.cell() * 0.06)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center.x() - r, center.y() - r, r * 2, r * 2))

        if self._hover is not None and self._hover != self._selected:
            piece = self.session.piece_at(self._hover)
            if piece is not None:
                center = self.point_xy(*self._hover)
                r = self.piece_radius()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(theme.HOVER)
                painter.drawEllipse(QRectF(center.x() - r, center.y() - r, r * 2, r * 2))

        if self.session.is_check():
            king = self.session.king_pos(self.session.turn)
            if king is not None:
                center = self.point_xy(*king)
                r = self.piece_radius() * 1.16
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(theme.CHECK_GLOW)
                painter.drawEllipse(QRectF(center.x() - r, center.y() - r, r * 2, r * 2))

    def _paint_pieces(self, painter: QPainter) -> None:
        radius = self.piece_radius()
        for x in range(COLS):
            for y in range(ROWS):
                piece = self.session.piece_at((x, y))
                if piece is None:
                    continue
                if self._dragging and self._selected == (x, y):
                    continue
                center = self.point_xy(x, y)
                pieces.draw_piece(
                    painter,
                    center,
                    radius,
                    self.session.piece_char((x, y)),
                    piece.color == 1,
                    selected=False,
                )

    def _paint_drag_piece(self, painter: QPainter) -> None:
        if not self._dragging or self._selected is None:
            return
        cursor = self.mapFromGlobal(self.cursor().pos())
        piece = self.session.piece_at(self._selected)
        if piece is None:
            return
        pieces.draw_piece(
            painter,
            QPointF(cursor),
            self.piece_radius() * 1.05,
            self.session.piece_char(self._selected),
            piece.color == 1,
        )
        if self._hover is not None and self.session.is_legal(self._selected, self._hover):
            center = self.point_xy(*self._hover)
            r = self.piece_radius() * 1.10
            painter.setPen(QPen(theme.ACCENT, max(1.8, self.cell() * 0.055)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(center.x() - r, center.y() - r, r * 2, r * 2))

    def _paint_arrow(self, painter: QPainter) -> None:
        if self._suggestion is None:
            return
        src, dst = self._suggestion
        start = self.point_xy(*src)
        end = self.point_xy(*dst)
        base = theme.STALE if self._suggestion_stale else theme.ACCENT
        color = QColor(base)
        color.setAlpha(120 if self._suggestion_stale else 205)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(color, max(2.0, self.cell() * 0.085))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)

        head = max(4.0, self.cell() * 0.20)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1.0:
            return
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        tip = end
        left = QPointF(tip.x() - ux * head + px * head * 0.62,
                       tip.y() - uy * head + py * head * 0.62)
        right = QPointF(tip.x() - ux * head - px * head * 0.62,
                        tip.y() - uy * head - py * head * 0.62)
        path = QPainterPath(tip)
        path.lineTo(left)
        path.lineTo(right)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)

    def _paint_coords(self, painter: QPainter) -> None:
        if not self.show_coords:
            return
        rect = self.board_rect()
        cell = self.cell()
        margin = self.margin()
        font = QFont(theme.UI_FONT)
        font.setPixelSize(max(7, int(margin * 0.42)))
        painter.setFont(font)
        painter.setPen(theme.TEXT_FAINT)
        metrics = QFontMetricsF(font)

        for col in range(COLS):
            x = (COLS - 1 - col) if self.session.flipped else col
            label = FILE_LABELS[x]
            px = rect.x() + col * cell
            painter.drawText(
                QPointF(px - metrics.horizontalAdvance(label) / 2.0,
                        rect.bottom() + margin * 0.72),
                label,
            )
        for row in range(ROWS):
            y = row if self.session.flipped else (ROWS - 1 - row)
            label = str(y)
            py = rect.y() + row * cell
            painter.drawText(
                QPointF(rect.left() - margin * 0.72 - metrics.horizontalAdvance(label),
                        py + metrics.ascent() * 0.36),
                label,
            )

    def _reject(self, pos: tuple[int, int], reason: str) -> None:
        self._flash = pos
        self._flash_timer.start(420)
        self.illegalMove.emit(reason)
        self.update()

    def _why_not(self, pos: tuple[int, int]) -> str:
        piece = self.session.piece_at(pos)
        if piece is None:
            return "这里没有棋子"
        side = "红方" if piece.color == 1 else "黑方"
        if piece.color != self.session.turn:
            return f"现在轮到{self.session.turn_name}走，{side}棋子暂时不能动"
        return "这枚棋子现在没有可走的着法"

    def _commit(self, src: tuple[int, int], dst: tuple[int, int]) -> None:
        self._selected = None
        self.selectionChanged.emit()
        self.update()
        self.movePlayed.emit(src, dst)

    def _select(self, pos: tuple[int, int]) -> None:
        if self._selected != pos:
            self._selected = pos
            self.selectionChanged.emit()
        self.update()

    def mousePressEvent(self, event) -> None:
        if not self._interactive or event.button() != Qt.MouseButton.LeftButton:
            return
        pos = self.square_at(event.position())
        if pos is None:
            self.clear_selection()
            return

        piece = self.session.piece_at(pos)

        if self._selected is not None and pos != self._selected:
            if self.session.is_legal(self._selected, pos):
                self._commit(self._selected, pos)
                return
            if piece is not None and self.session.can_move_from(pos):
                self._select(pos)
                return
            if piece is not None:
                self._reject(pos, self._why_not(pos))
                return
            self._reject(self._selected, "这一步走不了")
            return

        if piece is None:
            if self._selected is not None:
                self.clear_selection()
            return

        if not self.session.can_move_from(pos):
            self._reject(pos, self._why_not(pos))
            return

        self._press_pos = event.position()
        self._press_was_selected = self._selected == pos
        self._dragging = False
        self._select(pos)

    def mouseMoveEvent(self, event) -> None:
        pos_now = event.position()

        if (
            self._press_pos is not None
            and not self._dragging
            and event.buttons() & Qt.MouseButton.LeftButton
            and (pos_now - self._press_pos).manhattanLength() > 4
        ):
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            return

        pos = self.square_at(pos_now)
        if pos != self._hover:
            self._hover = pos
            self.update()
        if self._dragging:
            self.update()
            return
        piece = self.session.piece_at(pos) if pos is not None else None
        if self._interactive and piece is not None and self.session.can_move_from(pos):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        was_dragging = self._dragging
        self._dragging = False
        self._press_pos = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

        if was_dragging:
            target = self.square_at(event.position())
            origin = self._selected
            if target is not None and origin is not None and target != origin:
                if self.session.is_legal(origin, target):
                    self._commit(origin, target)
                    return
            self.update()
            return

        pos = self.square_at(event.position())
        if pos is None:
            return
        if pos == self._selected and self._press_was_selected:
            self.clear_selection()
        self._press_was_selected = False

    def leaveEvent(self, event) -> None:
        if self._hover is not None:
            self._hover = None
            self.update()
