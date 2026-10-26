from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from PyQt6.QtWidgets import QApplication

import cchess
import config
from float_window import FloatWindow
from session import BLACK, RED, Session

OK = 0
BAD = 0

def check(label: str, good: bool, detail: str = "") -> None:
    global OK, BAD
    if good:
        OK += 1
    else:
        BAD += 1
    print(f"  [{'PASS' if good else 'FAIL'}] {label}{('  ' + detail) if detail else ''}")

def main() -> int:
    app = QApplication(sys.argv)

    print("=" * 60)
    print("规则层校验")
    print("=" * 60)

    print("\n-- 1. king_pos 返回坐标而非棋子对象 --")
    s = Session()
    red_king = s.king_pos(RED)
    black_king = s.king_pos(BLACK)
    check("红帅返回元组", isinstance(red_king, tuple), str(red_king))
    check("黑将返回元组", isinstance(black_king, tuple), str(black_king))
    check("红帅在 (4,0)", red_king == (4, 0), str(red_king))
    check("黑将在 (4,9)", black_king == (4, 9), str(black_king))
    can_unpack = True
    try:
        x, y = s.king_pos(RED)
    except TypeError:
        can_unpack = False
    check("可直接解包（原先崩溃点）", can_unpack)

    print("\n-- 2. 将军判定（is_checking 语义相反）--")
    s.load_fen("4k4/9/9/9/9/4r4/9/9/9/4K4 w")
    check("红帅被黑车将军 → is_check 为真", s.is_check())
    check("黑方未被将军", not s.is_in_check(BLACK))
    raw_checking = s.board.is_checking()
    check("对照：cchess.is_checking() 为假（语义相反）", raw_checking is False,
          f"is_checking={raw_checking}")

    print("\n-- 3. 送将过滤（cchess 不过滤，我们自己过滤）--")
    s.load_fen("4k4/9/9/9/9/4r4/9/9/9/4K4 w")
    suicide = [m for m in s.board.create_moves() if not s.is_legal(*m)]
    check("存在被剔除的送将着法", len(suicide) > 0, f"{len(suicide)} 个 {suicide[:3]}")
    safe = True
    for src, dst in s.legal_moves():
        if s._in_check_on(_after(s, src, dst), RED):
            safe = False
            break
    check("保留的着法都不会让己方被将军", safe)
    check("非法 FEN（缺主将）被拒绝", not s.load_fen("9/9/9/9/4r4/9/9/9/9/4K4 w"))

    print("\n-- 4. 将死判定 --")
    s.load_fen("4k4/9/9/9/9/9/9/4r4/9/4K3r w")
    check("红方无合法着法", len(s.legal_moves()) == 0, str(len(s.legal_moves())))
    check("对局结束", s.is_game_over())
    check("黑方胜", s.winner == BLACK, str(s.winner))

    print("\n-- 5. 飞将（将帅照面）--")
    fen = "4k4/9/9/9/4P4/9/9/9/9/4K4 w"
    s.load_fen(fen)
    check("红兵在 (4,5)", s.piece_at((4, 5)) is not None)
    check("兵横走造成照面 → 被过滤", not s.is_legal((4, 5), (3, 5)))
    check("兵前进仍挡住 → 合法", s.is_legal((4, 5), (4, 6)))
    probe = cchess.ChessBoard(fen)
    probe._move_piece((4, 5), (3, 5))
    check("兵走开后黑将可飞吃红帅",
          probe.get_king(BLACK).is_valid_move((4, 0)))

    print("\n-- 6. 中文记谱 --")
    s = Session()
    cases = [
        ((7, 2), (4, 2), "炮二平五"),
        ((1, 2), (4, 2), "炮八平五"),
        ((7, 0), (6, 2), "马二进三"),
        ((7, 2), (7, 5), "炮二进三"),
        ((0, 0), (0, 1), "车九进一"),
        ((3, 0), (4, 1), "仕六进五"),
        ((2, 0), (4, 2), "相七进五"),
    ]
    for src, dst, expect in cases:
        got = s.move_text(src, dst)
        check(f"{src}->{dst} = {expect}", got == expect, got)

    print("\n-- 7. 将军局面下界面不崩溃（原报错路径）--")
    cfg = config.load_config()
    cfg["geometry"] = [40, 40, 470, 620]
    cfg["auto_accept"] = False
    cfg["strength"] = "custom"
    window = FloatWindow(cfg)
    window.resize(470, 620)
    window.show()

    def pump(seconds: float) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            app.processEvents()
            time.sleep(0.01)

    pump(1.0)
    window.choose_side(RED)
    pump(0.4)

    crashed: list[str] = []
    import traceback

    original_hook = sys.excepthook

    def hook(exc_type, exc, tb):
        crashed.append(f"{exc_type.__name__}: {exc}")
        original_hook(exc_type, exc, tb)

    sys.excepthook = hook

    for fen in (
        "9/9/9/9/4r4/9/9/9/9/4K4 w",
        "4k4/9/9/9/9/9/9/4r4/9/4K3r w",
        "4k4/9/9/9/4P4/9/9/9/9/4K4 w",
    ):
        window.session.load_fen(fen)
        window.session.flipped = False
        window.board.update()
        pump(0.25)
        window.board.grab()

    sys.excepthook = original_hook
    check("三种特殊局面渲染无异常", not crashed, "; ".join(crashed[:2]))

    invert = window.session.flipped
    window.session.flipped = True
    window.session.load_fen("4k4/9/9/9/9/4r4/9/9/9/4K4 w")
    window.board.grab()
    pump(0.2)
    check("翻转视角下将军渲染无异常", not crashed, "; ".join(crashed[:2]))
    window.session.flipped = invert

    window.close()
    pump(0.3)

    print(f"\n{'=' * 60}")
    print(f"规则校验: {OK} PASS / {BAD} FAIL")
    print("=" * 60)
    return 0 if BAD == 0 else 1

def _after(session, src, dst):
    trial = session.board.copy()
    trial._move_piece(src, dst)
    return trial

if __name__ == "__main__":
    sys.exit(main())
