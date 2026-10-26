from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

RED = 1

@dataclass
class AnalysisResult:
    version: int
    uci: str = ""
    cp: int | None = None
    mate: int | None = None
    depth: int = 0
    pv: list[str] | None = None
    nodes: int = 0
    elapsed_ms: int = 0
    interrupted: bool = False

def _parse_info(line: str) -> dict:

    info: dict = {}
    tokens = line.split()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "depth" and i + 1 < len(tokens):
            try:
                info["depth"] = int(tokens[i + 1])
            except ValueError:
                pass
            i += 2
        elif token == "score" and i + 2 < len(tokens):
            kind = tokens[i + 1]
            try:
                value = int(tokens[i + 2])
            except ValueError:
                i += 3
                continue
            if kind == "cp":
                info["cp"] = value
            elif kind == "mate":
                info["mate"] = value
            i += 3
        elif token == "nodes" and i + 1 < len(tokens):
            try:
                info["nodes"] = int(tokens[i + 1])
            except ValueError:
                pass
            i += 2
        elif token == "time" and i + 1 < len(tokens):
            try:
                info["elapsed_ms"] = int(tokens[i + 1])
            except ValueError:
                pass
            i += 2
        elif token == "pv":
            info["pv"] = tokens[i + 1:]
            break
        else:
            i += 1
    return info

class EngineWorker(QThread):
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)
    progress = pyqtSignal(dict)
    analysisDone = pyqtSignal(object)

    def __init__(
        self,
        engine_path: str,
        nnue_path: str | None = None,
        threads: int = 4,
        hash_mb: int = 256,
        low_priority: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.engine_path = engine_path
        self.nnue_path = nnue_path
        self.threads = threads
        self.hash_mb = hash_mb
        self.low_priority = low_priority

        self._proc: subprocess.Popen | None = None
        self._lines: queue.Queue[str] = queue.Queue()
        self._reader: threading.Thread | None = None
        self._running = True

        self._lock = threading.Lock()
        self._pending: tuple[int, str, int] | None = None
        self._stop_current = False
        self._wake = threading.Event()

    def submit(self, version: int, fen: str, movetime_ms: int) -> None:
        with self._lock:
            self._pending = (version, fen, int(movetime_ms))
            self._stop_current = True
        self._wake.set()

    def cancel(self) -> None:
        with self._lock:
            self._pending = None
            self._stop_current = True
        self._wake.set()

    def shutdown(self) -> None:
        self._running = False
        with self._lock:
            self._pending = None
            self._stop_current = True
        self._wake.set()

    def run(self) -> None:
        if self.nnue_path and not os.path.isfile(self.nnue_path):
            self.failed.emit(
                "未找到 pikafish.nnue，请把神经网络权重与 pikafish.exe 放在同一目录"
            )
            return
        try:
            self._spawn()
        except Exception as exc:
            self.failed.emit(f"引擎启动失败：{exc}")
            self._teardown()
            return

        try:
            self._configure()
            name = self._engine_name or "Pikafish"
            self._lower_priority()
            self.ready.emit(name)
            self._loop()
        except Exception as exc:
            self.failed.emit(f"引擎异常：{exc}")
        finally:
            self._teardown()

    def _spawn(self) -> None:
        cwd = os.path.dirname(os.path.abspath(self.engine_path)) or None
        self._proc = subprocess.Popen(
            [self.engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=cwd,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            self._lines.put("<EOF>")
            return
        try:
            for line in proc.stdout:
                self._lines.put(line.rstrip("\n"))
        except Exception:
            pass
        self._lines.put("<EOF>")

    def _send(self, command: str) -> None:
        if self._proc is None or self._proc.stdin is None:
            return
        try:
            self._proc.stdin.write(command + "\n")
            self._proc.stdin.flush()
        except Exception:
            pass

    def _wait_for(self, prefix: str, timeout: float = 30.0) -> list[str]:
        collected: list[str] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                line = self._lines.get(timeout=0.1)
            except queue.Empty:
                continue
            if line == "<EOF>":
                break
            collected.append(line)
            if line.startswith(prefix):
                return collected
        return collected

    _engine_name = ""

    def _configure(self) -> None:

        self._send("uci")
        errors: list[str] = []
        for line in self._wait_for("uciok", timeout=20):
            if line.startswith("id name"):
                self._engine_name = line[len("id name "):]
            elif "ERROR" in line:
                errors.append(line)

        self._send(f"setoption name Threads value {self.threads}")
        self._send(f"setoption name Hash value {self.hash_mb}")
        self._send("isready")
        for line in self._wait_for("readyok", timeout=30):
            if "ERROR" in line:
                errors.append(line)

        if errors:
            raise RuntimeError("；".join(e.split("ERROR:", 1)[-1].strip() for e in errors))

    def _lower_priority(self) -> None:
        if not self.low_priority or os.name != "nt" or self._proc is None:
            return
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0200 | 0x0400, False, self._proc.pid)
            if handle:
                kernel32.SetPriorityClass(handle, 0x00004000)
                kernel32.CloseHandle(handle)
        except Exception:
            pass

    def _loop(self) -> None:
        while self._running:
            with self._lock:
                task = self._pending
                self._pending = None
                self._stop_current = False
            if task is None:
                self._wake.wait(0.05)
                self._wake.clear()
                continue
            version, fen, movetime = task
            self._analyse(version, fen, movetime)

    def _analyse(self, version: int, fen: str, movetime_ms: int) -> None:
        started = time.monotonic()
        best = ""
        info: dict = {}
        interrupted = False

        self._send(f"position fen {fen}")
        self._send(f"go movetime {int(movetime_ms)}")

        while True:
            if not self._running:
                self._send("stop")
                interrupted = True
                break
            with self._lock:
                should_stop = self._stop_current
                pending = self._pending
                self._stop_current = False
            if should_stop or pending is not None:
                self._send("stop")
                interrupted = True

            try:
                line = self._lines.get(timeout=0.05)
            except queue.Empty:
                continue

            if line == "<EOF>":
                break
            if line.startswith("info") and " pv " in line:
                info = _parse_info(line)
                self.progress.emit({**info, "version": version})
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) > 1 and parts[1] not in ("(none)", "0000"):
                    best = parts[1]
                break

        elapsed = (time.monotonic() - started) * 1000.0
        if not best:
            self.analysisDone.emit(
                AnalysisResult(version=version, interrupted=interrupted, elapsed_ms=int(elapsed))
            )
            return

        self.analysisDone.emit(
            AnalysisResult(
                version=version,
                uci=best,
                cp=info.get("cp"),
                mate=info.get("mate"),
                depth=info.get("depth", 0),
                pv=info.get("pv"),
                nodes=info.get("nodes", 0),
                elapsed_ms=int(elapsed),
                interrupted=interrupted,
            )
        )

    def _teardown(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdin is not None and not proc.stdin.closed:
                proc.stdin.write("quit\n")
                proc.stdin.flush()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream is not None and not stream.closed:
                    stream.close()
            except Exception:
                pass
