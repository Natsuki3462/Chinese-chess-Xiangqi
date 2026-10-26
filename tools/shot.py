from __future__ import annotations

import os
import sys
import time
from pathlib import Path

if os.environ.get("XQF_OFFSCREEN") == "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
OUT = Path(__file__).resolve().parent / "shots"
OUT.mkdir(exist_ok=True)

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

import config
from float_window import FloatWindow
from session import BLACK, RED

SIZE = (470, 620)
OK = 0
BAD = 0

def check(label: str, good: bool, detail: str = "") -> None:
    global OK, BAD
    if good:
        OK += 1
    else:
        BAD += 1
    extra = f"  {detail}" if detail else ""
    print(f"  [{'PASS' if good else 'FAIL'}] {label}{extra}")

def pump(app: QApplication, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)

def wait_for(app: QApplication, predicate, timeout: float = 10.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)
        if predicate():
            return True
    return False

def compose(window: FloatWindow, path: Path) -> None:
    pix = window.grab()
    canvas = QPixmap(pix.size())
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, canvas.width(), canvas.height())
    grad.setColorAt(0.0, QColor(38, 52, 78))
    grad.setColorAt(0.5, QColor(72, 92, 120))
    grad.setColorAt(1.0, QColor(146, 120, 96))
    painter.fillRect(canvas.rect(), grad)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 26))
    painter.drawEllipse(QPoint(90, 120), 120, 120)
    painter.setBrush(QColor(255, 210, 120, 40))
    painter.drawEllipse(QPoint(canvas.width() - 70, canvas.height() - 120), 150, 150)
    painter.setOpacity(max(0.05, window.windowOpacity()))
    painter.drawPixmap(0, 0, pix)
    painter.end()
    canvas.save(str(path))
    print(f"        截图 {path.name}  {pix.width()}x{pix.height()}")

def center(window: FloatWindow, pos: tuple[int, int]) -> QPoint:
    return window.board.point_xy(*pos).toPoint()

def click(window: FloatWindow, pos: tuple[int, int]) -> None:
    QTest.mouseClick(
        window.board, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier, center(window, pos),
    )

def _send_move(widget, pos: QPointF) -> None:
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        pos,
        QPointF(widget.mapToGlobal(pos.toPoint())),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, event)

def drag(window: FloatWindow, src: tuple[int, int], dst: tuple[int, int]) -> None:
    start = center(window, src)
    target = center(window, dst)
    QTest.mousePress(
        window.board, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start
    )
    mid = QPointF((start.x() + target.x()) / 2.0, (start.y() + target.y()) / 2.0)
    _send_move(window.board, mid)
    _send_move(window.board, QPointF(target))
    QTest.mouseRelease(
        window.board, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, target
    )

def main() -> int:
    app = QApplication(sys.argv)
    cfg = config.load_config()
    cfg["geometry"] = [40, 40, *SIZE]
    cfg["opacity"] = 0.95
    cfg["analysis_ms"] = 500
    cfg["debounce_ms"] = 150
    cfg["strength"] = "custom"
    cfg["auto_accept"] = False
    cfg.pop("auto_accept", None) if False else None

    window = FloatWindow(cfg)
    window.resize(*SIZE)
    window.show()
    pump(app, 0.8)

    compose(window, OUT / "01_choose_side.png")

    print("\n-- 几何映射 --")
    board = window.board
    check("棋盘点位往返一致", all(
        board.square_at(board.point_xy(x, y)) == (x, y)
        for x in range(9) for y in range(10)
    ))
    check("交叉点在棋盘范围内", board.point_xy(0, 0).x() >= 0 and board.point_xy(8, 9).y() <= board.height())

    print("\n-- 执红流程 --")
    window.choose_side(RED)
    pump(app, 0.4)
    check("红方在下方、视角未翻转", not window.session.flipped)
    check("开局 44 个合法着法", len(window.session.legal_moves()) == 44,
          str(len(window.session.legal_moves())))

    got = wait_for(app, lambda: window._suggestion is not None, 15.0)
    check("执红开局给出建议", got,
          f"{window._history_texts() or '开局'} depth {window._suggestion.depth}"
          if got else "超时")
    compose(window, OUT / "03_suggestion.png")

    click(window, (7, 2))
    pump(app, 0.2)
    check("点炮位后选中", window.board._selected == (7, 2))
    compose(window, OUT / "02_selection.png")
    click(window, (7, 2))
    pump(app, 0.15)
    check("再点同一子取消选中", window.board._selected is None)

    click(window, (7, 2))
    pump(app, 0.15)
    click(window, (4, 2))
    pump(app, 0.3)
    check("点击走子成功", window.session.ply == 1, str(window.session.ply))
    check("记谱为「炮二平五」", window._history_texts()[:1] == ["1.炮二平五"],
          str(window._history_texts()[:1]))
    check("走子后轮到对手", not window.session.is_my_turn)

    kept = window.board.suggestion_move
    check("走子瞬间箭头不消失", kept is not None, str(kept))
    check("轮到对手时箭头转灰", window.board.suggestion_stale)
    compose(window, OUT / "04_stale.png")

    print("\n-- 对手回合 --")
    window._play_move((7, 7), (7, 4))
    pump(app, 0.2)
    check("对手回合不产出新建议", window._suggestion is None)
    check("轮回到自己", window.session.is_my_turn)
    if window.board.suggestion_move is not None:
        still_legal = window.session.is_legal(*window.board.suggestion_move)
        check("箭头仍在则要么合法要么已置灰",
              still_legal or window.board.suggestion_stale,
              f"legal={still_legal} stale={window.board.suggestion_stale}")

    print("\n-- 拖拽 --")
    window.new_game()
    pump(app, 0.3)
    window.choose_side(RED)
    pump(app, 0.3)
    drag(window, (1, 0), (2, 2))
    pump(app, 0.3)
    check("拖拽走子成功", window.session.ply == 1, str(window._history_texts()[:1]))
    drag(window, (2, 2), (8, 8))
    pump(app, 0.2)
    check("拖到非法位置回弹", window.session.ply == 1)

    print("\n-- 撤销 / 重做 --")
    ply = window.session.ply
    window.undo()
    pump(app, 0.2)
    check("撤销", window.session.ply == ply - 1)
    window.redo()
    pump(app, 0.2)
    check("重做", window.session.ply == ply)

    print("\n-- 视角翻转 --")
    window.flip()
    pump(app, 0.3)
    check("翻转后点位仍正确", all(
        board.square_at(board.point_xy(x, y)) == (x, y)
        for x in range(9) for y in range(10)
    ))
    compose(window, OUT / "05_flipped.png")
    window.flip()
    pump(app, 0.2)

    print("\n-- 执黑 --")
    window.new_game()
    pump(app, 0.3)
    window.choose_side(BLACK)
    pump(app, 0.4)
    check("执黑时视图翻转", window.session.flipped)
    check("执黑开局轮红方", window.session.turn == RED)
    click(window, (4, 6))
    pump(app, 0.25)
    check("点不该走的黑子给出提示", "轮到红方" in window.header.status.text(),
          window.header.status.text())
    click(window, (4, 3))
    pump(app, 0.2)
    check("执黑时点红子可复刻对手着法", window.board._selected == (4, 3),
          str(window.board._selected))
    window.board.clear_selection()
    compose(window, OUT / "06_black.png")

    print("\n-- 自动采纳 --")
    window.new_game()
    pump(app, 0.3)
    window.choose_side(RED)
    pump(app, 0.2)
    window.header.btn_auto.setChecked(True)
    auto = wait_for(app, lambda: window.session.ply >= 1, 12.0)
    check("自动采纳生效", auto, str(window._history_texts()[:1]))
    compose(window, OUT / "07_auto.png")
    ply_before = window.session.ply
    window.undo()
    pump(app, 0.8)
    check("撤销后自动暂停", not window.cfg["auto_accept"] and window.session.ply == ply_before - 1)

    print("\n-- 紧凑模式 --")
    window.toggle_compact()
    pump(app, 0.3)
    check("紧凑模式隐藏底栏", not window.footer.isVisible())
    compose(window, OUT / "08_compact.png")
    window.toggle_compact()
    pump(app, 0.2)

    print("\n-- 强度预设 --")
    window.set_strength("fast")
    pump(app, 0.8)
    check("切轻快档", (window.cfg["analysis_ms"], window.cfg["threads"]) == (300, 2),
          f"{window.cfg['analysis_ms']}ms/{window.cfg['threads']}T")
    window.set_strength("balanced")
    pump(app, 0.8)
    check("切均衡档", (window.cfg["analysis_ms"], window.cfg["threads"]) == (800, 4),
          f"{window.cfg['analysis_ms']}ms/{window.cfg['threads']}T")
    check("换档后引擎重新就绪", window._engine_ok)

    print("\n-- 引擎缺失 --")
    saved = config.find_engine
    saved_path = window.cfg.get("engine_path")
    window._stop_engine()
    window.cfg["engine_path"] = ""
    config.find_engine = lambda explicit=None: None
    window._start_engine()
    pump(app, 0.4)
    check("缺引擎时状态栏说明原因", "未找到" in window.header.status.text(),
          window.header.status.text())
    window.choose_side(RED)
    pump(app, 0.3)
    check("选先后手后提示仍在", "未找到" in window.header.status.text())
    config.find_engine = saved
    window.cfg["engine_path"] = saved_path or ""
    window._start_engine()
    pump(app, 1.5)
    check("恢复引擎后就绪", window._engine_ok and window._engine_error is None)

    window.close()
    pump(app, 0.5)

    print(f"\n{'=' * 50}")
    print(f"结果: {OK} PASS / {BAD} FAIL")
    print("=" * 50)
    return 0 if BAD == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
