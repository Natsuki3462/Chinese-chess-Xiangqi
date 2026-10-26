import pathlib
import queue
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

import cchess

ENGINE = str(ROOT / "engine" / "pikafish.exe")
WORKDIR = str(ROOT / "engine")

class UciEngine:
    def __init__(self, path: str, cwd: str) -> None:
        self.proc = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=cwd,
        )
        self.lines: queue.Queue = queue.Queue()
        self.name = ""
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.lines.put(line.rstrip("\n"))

    def send(self, cmd: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def wait_for(self, prefix: str, timeout: float = 45.0) -> list:
        out = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = self.lines.get(timeout=0.2)
            except queue.Empty:
                continue
            out.append(line)
            if line.startswith(prefix):
                return out
        return out

    def handshake(self) -> None:
        self.send("uci")
        for ln in self.wait_for("uciok"):
            if ln.startswith("id name"):
                self.name = ln[8:]
        self.send("isready")
        self.wait_for("readyok")

    def go(self, fen: str, depth: int = 12):
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        best, info = None, ""
        for ln in self.wait_for("bestmove"):
            if ln.startswith("bestmove"):
                parts = ln.split()
                best = parts[1] if len(parts) > 1 else None
            elif ln.startswith("info") and " pv " in ln:
                info = ln
        return best, info

    def close(self) -> None:
        try:
            self.send("quit")
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

def to_uci(pos) -> str:
    return f"{chr(ord('a') + pos[0])}{pos[1]}"

def from_uci(text: str):
    return (ord(text[0]) - ord("a"), int(text[1]))

def check(label: str, good: bool, detail: str = "") -> bool:
    print(f"    [{'PASS' if good else 'FAIL'}] {label}{('  ' + detail) if detail else ''}")
    return good

def main() -> int:
    all_ok = True

    print("=" * 70)
    print("[1] 坐标映射  cchess (x, y)  <->  UCI (a-i / 0-9)")
    print("=" * 70)
    board = cchess.ChessBoard(cchess.FULL_INIT_FEN)
    for pos, expect in [((1, 2), "b2"), ((7, 2), "h2"), ((0, 0), "a0"), ((8, 9), "i9")]:
        all_ok &= check(f"{pos} <-> {expect}",
                        to_uci(pos) == expect and from_uci(expect) == pos,
                        f"实得 {to_uci(pos)}")
    piece = board.get_piece((1, 2))
    all_ok &= check("(1,2) 是炮(Cannon)", type(piece).__name__ == "Cannon",
                    type(piece).__name__)

    print()
    print("=" * 70)
    print("[2] cchess 合法着法可全部转成 UCI")
    print("=" * 70)
    moves = list(board.create_moves())
    all_ok &= check("开局合法着法数 = 44", len(moves) == 44, str(len(moves)))
    bad = [m for m in moves if len(to_uci(m[0]) + to_uci(m[1])) != 4]
    all_ok &= check("全部可转换", not bad, f"失败 {len(bad)}")

    print()
    print("=" * 70)
    print("[3] python-chess SimpleEngine 能否驱动 Pikafish")
    print("=" * 70)
    print("    结论（已实测，不再重复触发卡死）：不可复用")
    print("    原因：SimpleEngine.analyse(chess.Board()) 下发的是国际象棋 FEN")
    print("          rnbqkbnr/pppppppp/8/8/...，Pikafish 返回 b2e2 这类中国象棋着法，")
    print("          python-chess 的 push_uci 无法解析，抛 Exception parsing pv，")
    print("          且 info 流未终止导致 future 永不 resolve，进程会卡住。")
    print("    => engine_worker.py 必须改为自写 UCI 循环（下面第 4 步已验证可行）")
    print()
    print("=" * 70)
    print("[4] 闭环对练 12 步：引擎算 -> 落子 -> 再算")
    print("=" * 70)
    eng = UciEngine(ENGINE, WORKDIR)
    eng.handshake()
    print(f"    引擎: {eng.name}")

    played = 0
    for step in range(12):
        fen = board.to_fen()
        best, info = eng.go(fen, depth=12)
        if not best or best == "(none)":
            print(f"    第 {step + 1} 步: 无着法，对局可能结束")
            break
        src, dst = from_uci(best[:2]), from_uci(best[2:])
        legal = list(board.create_moves())
        if (src, dst) not in legal:
            all_ok &= check(f"第 {step + 1} 步着法合法", False, best)
            break
        board.move(src, dst)
        played += 1
        depth = ""
        if " depth " in info:
            depth = info.split(" depth ")[1].split()[0]
        print(f"    第 {step + 1:2d} 步  {best}  depth={depth:>3}  "
              f"{type(board.get_piece(dst)).__name__ if board.get_piece(dst) else '-':>8s}")

    all_ok &= check(f"成功走完 {played} 步", played >= 10, f"{played}/12")
    print(f"    末局面: {board.to_fen()}")
    eng.close()
    check("引擎正常退出", eng.proc.poll() is not None)

    print()
    print("=" * 70)
    verdict = "全链路通过" if all_ok else "存在失败项"
    print(f"总判定: {verdict}")
    print("engine_worker.py 复用性: 需改为自写 UCI 循环（分析结果解析要重写）")
    print("=" * 70)
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
