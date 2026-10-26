from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from PyQt6.QtWidgets import QApplication

import config
from float_window import FloatWindow
from session import RED

OK = 0
BAD = 0

BG = (238, 222, 190)

def check(label: str, good: bool, detail: str = "") -> None:
    global OK, BAD
    if good:
        OK += 1
    else:
        BAD += 1
    print(f"  [{'PASS' if good else 'FAIL'}] {label}{('  ' + detail) if detail else ''}")

def near(a, b, tol=30) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a[:3], b[:3]))

class Probe:
    def __init__(self, image) -> None:
        self.img = image

    def colors(self, x0, y0, x1, y1, step: int = 1):
        out = []
        for y in range(int(y0), int(y1), step):
            for x in range(int(x0), int(x1), step):
                if 0 <= x < self.img.width() and 0 <= y < self.img.height():
                    out.append(self.img.pixelColor(x, y).getRgb()[:3])
        return out

    def count(self, x0, y0, x1, y1, predicate, step: int = 1) -> int:
        return sum(1 for c in self.colors(x0, y0, x1, y1, step) if predicate(c))

    def modal(self, x0, y0, x1, y1, step: int = 1):
        colors = self.colors(x0, y0, x1, y1, step)
        if not colors:
            return (0, 0, 0), 0
        color, hits = Counter(colors).most_common(1)[0]
        return color, hits / len(colors)

def main() -> int:
    app = QApplication(sys.argv)
    cfg = config.load_config()
    cfg["geometry"] = [40, 40, 470, 620]
    cfg["analysis_ms"] = 400
    cfg["debounce_ms"] = 120
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
    pump(0.6)

    board = window.board
    rect = board.board_rect()
    cell = board.cell()
    r = board.piece_radius()
    print(f"\n棋盘控件 {board.width()}x{board.height()}  "
          f"网格 x={rect.x():.0f} y={rect.y():.0f} "
          f"宽={rect.width():.0f} 高={rect.height():.0f} 格距={cell:.1f}")

    probe = Probe(board.grab().toImage())

    print("\n-- 1. 棋盘底色 --")
    band_y = rect.y() + cell * 4.35
    color, ratio = probe.modal(rect.x() + cell * 0.2, band_y,
                               rect.right() - cell * 0.2, band_y + cell * 0.3, 2)
    check("河界带以木质底色为主", near(color, BG, 18) and ratio > 0.5,
          f"主色 {color} 占比 {ratio:.0%}")

    print("\n-- 2. 棋子 --")
    filled = 0
    total = 0
    for x, y in [(0, 0), (4, 0), (8, 0), (1, 2), (7, 2), (0, 3), (2, 3), (1, 9)]:
        center = board.point_xy(x, y)
        total += 1
        ring = probe.count(
            center.x() - r * 0.92, center.y() - r * 0.22,
            center.x() + r * 0.92, center.y() + r * 0.92,
            lambda c: near(c, (250, 242, 224), 34) or near(c, (244, 236, 218), 34),
            2,
        )
        if ring > 8:
            filled += 1
    check("交叉点上有棋子底面", filled >= total - 1, f"{filled}/{total}")

    hero = board.point_xy(4, 0)
    reds = probe.count(
        hero.x() - r * 0.60, hero.y() - r * 0.60,
        hero.x() + r * 0.60, hero.y() + r * 0.60,
        lambda c: c[0] > 110 and c[0] > c[1] + 45 and c[0] > c[2] + 45,
    )
    check("帅位有红色汉字", reds >= 4, f"红像素 {reds}")

    black_hero = board.point_xy(4, 9)
    darks = probe.count(
        black_hero.x() - r * 0.60, black_hero.y() - r * 0.60,
        black_hero.x() + r * 0.60, black_hero.y() + r * 0.60,
        lambda c: max(c) < 80,
    )
    check("将位有黑色汉字", darks >= 4, f"暗像素 {darks}")

    print("\n-- 3. 楚河汉界 --")
    river_y = rect.y() + cell * 4.5
    interior = probe.count(
        rect.x() + cell * 4 - cell * 0.06, river_y - cell * 0.22,
        rect.x() + cell * 4 + cell * 0.06, river_y + cell * 0.22,
        lambda c: not near(c, BG, 26),
    )
    check("河界内部竖线已断开", interior <= 2, f"非底色像素 {interior}")

    edge = probe.count(
        rect.x() - cell * 0.06, river_y - cell * 0.22,
        rect.x() + cell * 0.06, river_y + cell * 0.22,
        lambda c: not near(c, BG, 26),
    )
    check("河界最左竖线连续", edge >= 6, f"非底色像素 {edge}")

    text_pixels = probe.count(
        rect.x() + cell * 1.1, river_y - cell * 0.32,
        rect.right() - cell * 1.1, river_y + cell * 0.32,
        lambda c: not near(c, BG, 22),
    )
    check("河界写出「楚河 汉界」", text_pixels >= 30, f"文字像素 {text_pixels}")

    print("\n-- 4. 九宫斜线 --")
    for label, top in (("下方九宫", 0), ("上方九宫", 7)):
        hits = probe.count(
            rect.x() + cell * 3.2, rect.y() + cell * (top + 0.35),
            rect.x() + cell * 4.8, rect.y() + cell * (top + 1.65),
            lambda c: near(c, (96, 74, 48), 46),
        )
        check(f"{label}斜线存在", hits >= 25, f"线像素 {hits}")

    print("\n-- 5. 横竖线 --")
    top_line = probe.count(
        rect.x() + cell * 0.5, rect.y() - 1.5,
        rect.right() - cell * 0.5, rect.y() + 2.5,
        lambda c: not near(c, BG, 24),
    )
    check("顶部横线", top_line >= 60, f"像素 {top_line}")

    vline = probe.count(
        rect.x() + cell * 4 - 1.5, rect.y() + cell * 1.2,
        rect.x() + cell * 4 + 2.5, rect.y() + cell * 3.8,
        lambda c: not near(c, BG, 24),
    )
    check("中间竖线", vline >= 60, f"像素 {vline}")

    print("\n-- 6. 选中与提示 --")
    board._select((1, 2))
    pump(0.3)
    pr = Probe(board.grab().toImage())
    center = board.point_xy(1, 2)
    greens = pr.count(
        center.x() - r * 1.25, center.y() - r * 1.25,
        center.x() + r * 1.25, center.y() + r * 1.25,
        lambda c: c[1] > c[0] + 20 and c[1] > c[2] + 20,
    )
    check("选中后有绿色高亮", greens >= 20, f"绿像素 {greens}")

    targets = board.session.legal_targets((1, 2))
    dot_hit = 0
    for target in targets[:6]:
        tp = board.point_xy(*target)
        got = pr.count(tp.x() - r * 0.25, tp.y() - r * 0.25,
                       tp.x() + r * 0.25, tp.y() + r * 0.25,
                       lambda c: c[1] > c[0] + 12 and c[1] > 60)
        if got >= 3:
            dot_hit += 1
    check("可落点有提示标记", dot_hit >= min(3, len(targets)),
          f"{dot_hit}/{min(6, len(targets))}")

    print("\n-- 7. 建议箭头 --")
    board.clear_selection()
    board.set_suggestion(((7, 2), (4, 2)), stale=False)
    pump(0.35)
    pa = Probe(board.grab().toImage())
    a = board.point_xy(7, 2)
    b = board.point_xy(4, 2)
    green_arrow = pa.count(
        min(a.x(), b.x()) + cell * 0.6, a.y() - cell * 0.09,
        max(a.x(), b.x()) - cell * 0.6, a.y() + cell * 0.09,
        lambda c: c[1] > c[0] + 25 and c[1] > c[2] + 25,
    )
    check("新箭头为绿色", green_arrow >= 15, f"绿像素 {green_arrow}")

    board.set_suggestion(((7, 2), (4, 2)), stale=True)
    pump(0.35)
    ps = Probe(board.grab().toImage())
    gray = ps.count(
        min(a.x(), b.x()) + cell * 0.6, a.y() - cell * 0.09,
        max(a.x(), b.x()) - cell * 0.6, a.y() + cell * 0.09,
        lambda c: abs(c[0] - c[1]) < 26 and abs(c[1] - c[2]) < 26 and max(c) > 90,
    )
    check("陈旧箭头变灰", gray >= 10, f"灰像素 {gray}")

    window.close()
    pump(0.3)

    print(f"\n{'=' * 46}")
    print(f"像素校验: {OK} PASS / {BAD} FAIL")
    print("=" * 46)
    return 0 if BAD == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
