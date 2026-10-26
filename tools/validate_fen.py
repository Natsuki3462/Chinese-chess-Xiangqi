import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

import cchess

ENGINE = str(ROOT / "engine" / "pikafish.exe")

def ask(cmds, timeout=25.0):

    proc = subprocess.Popen(
        [ENGINE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=str(ROOT / "engine"),
    )
    for cmd in cmds:
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()
        time.sleep(0.15)
    out = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        out.append(line.rstrip())
        if line.startswith("bestmove"):
            break
    try:
        proc.stdin.write("quit\n")
        proc.stdin.flush()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    return out

def first_bestmove(lines):
    for ln in lines:
        if ln.startswith("bestmove"):
            parts = ln.split()
            return parts[1] if len(parts) > 1 else None
    return None

def main() -> int:
    print("=" * 70)
    print("风险点：cchess 的 FEN 能否被 Pikafish 直接接受")
    print("=" * 70)

    board = cchess.ChessBoard(cchess.FULL_INIT_FEN)
    fen_short = board.to_fen()
    fen_full = board.to_full_fen()

    print("\n[1] cchess 输出的 FEN 形态")
    print(f"    to_fen()      : {fen_short}")
    print(f"    to_full_fen() : {fen_full}")

    cases = [
        ("A. 短 FEN（cchess 原生）", fen_short, ["position fen " + fen_short]),
        ("B. 完整 FEN（带 - - 0 1）", fen_full, ["position fen " + fen_full]),
        (
            "C. startpos 关键字",
            cchess.FULL_INIT_FEN,
            ["position startpos"],
        ),
    ]

    results = {}
    for label, fen, pos_cmd in cases:
        print(f"\n[2] {label}")
        print(f"    命令: {pos_cmd[0]}")
        lines = ask(["uci", "isready"] + pos_cmd + ["go depth 10"])
        best = first_bestmove(lines)
        errs = [ln for ln in lines if "Unknown" in ln or "error" in ln.lower()]
        if best and best != "(none)":
            print(f"    ✔ bestmove = {best}")
            results[label] = best
        else:
            print(f"    ✘ 无有效 bestmove")
            for ln in errs[:3]:
                print(f"      引擎报错: {ln}")
            results[label] = None

    print("\n" + "=" * 70)
    print("结论")
    print("=" * 70)
    for label, best in results.items():
        print(f"  {label:32s} {'可用 ✔  ' + str(best) if best else '不可用 ✘'}")

    short_ok = results.get("A. 短 FEN（cchess 原生）") is not None
    full_ok = results.get("B. 完整 FEN（带 - - 0 1）") is not None

    print()
    if short_ok:
        print("→ cchess 的短 FEN 可直接喂给 Pikafish，无需转换层。")
    elif full_ok:
        print("→ 需要给短 FEN 补 '- - 0 1' 后缀（to_full_fen），不需完整转换层。")
    else:
        print("→ 两种都不行，需要写 FEN 适配层。")

    return 0

if __name__ == "__main__":
    sys.exit(main())
