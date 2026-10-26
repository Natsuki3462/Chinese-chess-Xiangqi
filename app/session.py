from __future__ import annotations

import cchess
from PyQt6.QtCore import QObject, pyqtSignal

RED = cchess.RED
BLACK = cchess.BLACK

START_FEN = cchess.FULL_INIT_FEN

PIECE_NAMES = {
    "King": ("帅", "将"),
    "Advisor": ("仕", "士"),
    "Bishop": ("相", "象"),
    "Knight": ("马", "马"),
    "Rook": ("车", "车"),
    "Cannon": ("炮", "炮"),
    "Pawn": ("兵", "卒"),
}

CHINESE_NUM = "一二三四五六七八九"
COLS = 9
DIAGONAL_PIECES = ("Knight", "Bishop", "Advisor")

Pos = tuple[int, int]
MoveTuple = tuple[Pos, Pos]

def pos_to_uci(pos: Pos) -> str:
    return f"{chr(ord('a') + pos[0])}{pos[1]}"

def uci_to_pos(text: str) -> Pos:
    return (ord(text[0]) - ord("a"), int(text[1]))

def move_to_uci(src: Pos, dst: Pos) -> str:
    return pos_to_uci(src) + pos_to_uci(dst)

class Session(QObject):
    positionChanged = pyqtSignal(int)
    historyChanged = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.board = cchess.ChessBoard(START_FEN)
        self.my_color: int = RED
        self.flipped = False
        self.version = 0
        self._stack: list[MoveTuple] = []
        self._texts: list[str] = []
        self._snaps: list[cchess.ChessBoard] = []
        self._redo: list[MoveTuple] = []
        self._legal: list[MoveTuple] = []
        self._legal_by_from: dict[Pos, list[Pos]] = {}
        self._last_move: MoveTuple | None = None
        self._refresh_legal()

    def _refresh_legal(self) -> None:

        try:
            raw = list(self.board.create_moves())
        except Exception:
            raw = []
        side = self.board.move_player.color
        legal: list[MoveTuple] = []
        for src, dst in raw:
            if self._keeps_king_safe(src, dst, side):
                legal.append((src, dst))
        self._legal = legal
        index: dict[Pos, list[Pos]] = {}
        for src, dst in legal:
            index.setdefault(src, []).append(dst)
        self._legal_by_from = index

    def _keeps_king_safe(self, src: Pos, dst: Pos, side: int) -> bool:

        trial = self.board.copy()
        try:
            trial._move_piece(src, dst)
        except AttributeError:
            trial.move(src, dst)
            trial.next_turn()
        return not self._in_check_on(trial, side)

    def _in_check_on(self, board, side: int) -> bool:
        try:
            king = board.get_king(side)
        except Exception:
            return False
        if king is None:
            return False
        target = (int(king.x), int(king.y))
        try:
            attackers = board.get_pieces(3 - side)
        except Exception:
            return False
        for piece in attackers:
            try:
                if piece.is_valid_move(target):
                    return True
            except Exception:
                continue
        return False

    @property
    def fen(self) -> str:
        return self.board.to_fen()

    @property
    def full_fen(self) -> str:
        return self.board.to_full_fen()

    @property
    def ply(self) -> int:
        return len(self._stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def turn(self) -> int:
        return self.board.move_player.color

    @property
    def is_my_turn(self) -> bool:
        return self.turn == self.my_color

    @property
    def turn_name(self) -> str:
        return "红方" if self.turn == RED else "黑方"

    @property
    def my_name(self) -> str:
        return "红方" if self.my_color == RED else "黑方"

    @property
    def last_move(self) -> MoveTuple | None:
        return self._last_move

    def legal_moves(self) -> list[MoveTuple]:
        return list(self._legal)

    def legal_targets(self, src: Pos) -> list[Pos]:
        return list(self._legal_by_from.get(src, ()))

    def can_move_from(self, src: Pos) -> bool:
        return src in self._legal_by_from

    def is_legal(self, src: Pos, dst: Pos) -> bool:
        return dst in self._legal_by_from.get(src, ())

    def piece_at(self, pos: Pos):
        return self.board.get_piece(pos)

    def piece_char(self, pos: Pos) -> str:
        piece = self.board.get_piece(pos)
        if piece is None:
            return ""
        names = PIECE_NAMES.get(type(piece).__name__)
        if names is None:
            return ""
        return names[0] if piece.color == RED else names[1]

    def is_in_check(self, color: int | None = None) -> bool:

        side = self.turn if color is None else color
        return self._in_check_on(self.board, side)

    def is_check(self) -> bool:

        return self.is_in_check()

    @property
    def winner(self) -> int | None:

        if self._legal:
            return None
        return 3 - self.turn

    def is_game_over(self) -> bool:
        return not self._legal

    def king_pos(self, color: int) -> Pos | None:

        try:
            king = self.board.get_king(color)
        except Exception:
            return None
        if king is None:
            return None
        try:
            return (int(king.x), int(king.y))
        except (AttributeError, TypeError, ValueError):
            return None

    def push(self, src: Pos, dst: Pos) -> bool:
        if not self.is_legal(src, dst):
            return False

        text = self.move_text(src, dst)
        self._snaps.append(self.board.copy())
        self.board.move(src, dst)
        self.board.next_turn()
        self._stack.append((src, dst))
        self._texts.append(text)
        self._redo.clear()
        self._last_move = (src, dst)
        self._bump()
        return True

    @property
    def move_texts(self) -> list[str]:
        return list(self._texts)

    def undo(self) -> bool:
        if not self._stack or not self._snaps:
            return False
        src, dst = self._stack.pop()
        if self._texts:
            self._texts.pop()
        self.board = self._snaps.pop()
        self._redo.append((src, dst))
        self._last_move = self._stack[-1] if self._stack else None
        self._bump()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        src, dst = self._redo.pop()
        text = self.move_text(src, dst)
        self._snaps.append(self.board.copy())
        self.board.move(src, dst)
        self.board.next_turn()
        self._stack.append((src, dst))
        self._texts.append(text)
        self._last_move = (src, dst)
        self._bump()
        return True

    def jump_to(self, ply: int) -> bool:
        target_ply = max(0, min(ply, self.ply + len(self._redo)))
        if target_ply == self.ply:
            return False
        if target_ply < self.ply:
            while self.ply > target_ply:
                src, dst = self._stack.pop()
                if self._texts:
                    self._texts.pop()
                self.board = self._snaps.pop()
                self._redo.append((src, dst))
        else:
            need = target_ply - self.ply

            pending = list(reversed(self._redo))
            self._redo = []
            replayed = 0
            for src, dst in pending:
                if replayed >= need:
                    self._redo.append((src, dst))
                    continue
                text = self.move_text(src, dst)
                self._snaps.append(self.board.copy())
                self.board.move(src, dst)
                self.board.next_turn()
                self._stack.append((src, dst))
                self._texts.append(text)
                replayed += 1
            self._redo = list(reversed(self._redo))
        self._last_move = self._stack[-1] if self._stack else None
        self._bump()
        return True

    def reset(self, my_color: int) -> None:
        self.my_color = my_color
        self.board = cchess.ChessBoard(START_FEN)
        self._stack.clear()
        self._texts.clear()
        self._snaps.clear()
        self._redo.clear()
        self._last_move = None
        self._bump()

    def load_fen(self, fen: str) -> bool:

        try:
            board = cchess.ChessBoard(fen)
        except Exception:
            return False
        try:
            if board.get_king(RED) is None or board.get_king(BLACK) is None:
                return False
        except Exception:
            return False
        self.board = board
        self._stack.clear()
        self._texts.clear()
        self._snaps.clear()
        self._redo.clear()
        self._last_move = None
        self._bump()
        return True

    def toggle_flip(self) -> None:
        self.flipped = not self.flipped
        self.historyChanged.emit()

    def eval_text(self, cp: int | None, mate: int | None) -> str:

        if mate is not None:
            value = mate if self.my_color == RED else -mate
            return f"{'+' if value > 0 else '-'}M{abs(value)}"
        if cp is None:
            return "—"
        value = cp / 100.0
        if self.my_color == BLACK:
            value = -value
        return f"{value:+.2f}"

    def move_text(self, src: Pos, dst: Pos) -> str:

        piece = self.board.get_piece(src)
        if piece is None:
            return pos_to_uci(src) + pos_to_uci(dst)
        names = PIECE_NAMES.get(type(piece).__name__)
        if names is None:
            return pos_to_uci(src) + pos_to_uci(dst)
        red = piece.color == RED
        name = names[0] if red else names[1]

        def file_no(x: int) -> int:
            return (COLS - x) if red else (x + 1)

        def file_label(x: int) -> str:
            n = file_no(x)
            return CHINESE_NUM[n - 1] if red else str(n)

        def step_label(steps: int) -> str:
            return CHINESE_NUM[steps - 1] if red else str(steps)

        prefix = ""
        peers = [p for p in self._same_pieces(src, piece) if p != src]
        if peers:
            same_file = [p for p in self._same_pieces(src, piece) if p[0] == src[0]]
            if len(same_file) > 1:
                ordered = sorted(same_file, key=lambda p: p[1], reverse=red)
                index = ordered.index(src)
                prefix = "前" if index == 0 else ("后" if index == len(ordered) - 1
                                                 else str(index + 1))

        if src[1] == dst[1]:
            action = "平"
            target = file_label(dst[0])
        else:
            forward = (dst[1] > src[1]) if red else (dst[1] < src[1])
            action = "进" if forward else "退"

            diagonal = type(piece).__name__ in DIAGONAL_PIECES
            target = file_label(dst[0]) if diagonal else step_label(abs(dst[1] - src[1]))

        if prefix:
            return f"{prefix}{name}{action}{target}"
        return f"{name}{file_label(src[0])}{action}{target}"

    def _same_pieces(self, src: Pos, piece) -> list[Pos]:
        result: list[Pos] = []
        name = type(piece).__name__
        for x in range(9):
            for y in range(10):
                other = self.board.get_piece((x, y))
                if other is None:
                    continue
                if type(other).__name__ == name and other.color == piece.color:
                    result.append((x, y))
        return result

    def _bump(self) -> None:
        self._refresh_legal()
        self.version += 1
        self.historyChanged.emit()
        self.positionChanged.emit(self.version)
