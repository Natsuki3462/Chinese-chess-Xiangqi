from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
ENGINE_DIR = ROOT_DIR / "engine"
CONFIG_PATH = ROOT_DIR / "config.json"

APP_NAME = "XiangqiFloat"

WINDOW_MIN_WIDTH = 400
WINDOW_MIN_HEIGHT = 470
DEFAULT_GEOMETRY = [1090, 130, 470, 620]

MIN_OPACITY = 0.15
MAX_OPACITY = 1.0
DEFAULT_OPACITY = 0.95

STRENGTH_PRESETS: dict[str, tuple[str, int, int, int]] = {
    "fast": ("轻快", 300, 2, 128),
    "balanced": ("均衡", 800, 4, 256),
    "deep": ("深度", 1500, 6, 512),
    "max": ("极限", 3000, 8, 1024),
}
CUSTOM_STRENGTH = "custom"

DEFAULT_CONFIG: dict[str, Any] = {
    "engine_path": "",
    "strength": "balanced",
    "adaptive": True,
    "analysis_ms": 800,
    "debounce_ms": 220,
    "threads": 4,
    "hash_mb": 256,
    "opacity": 0.95,
    "geometry": list(DEFAULT_GEOMETRY),
    "show_coords": True,
    "auto_accept": False,
    "low_priority": True,
}

ENGINE_FILENAMES = ("pikafish.exe", "pikafish-windows-x86-64-universal.exe", "pikafish")
NNUE_FILENAME = "pikafish.nnue"

def find_engine(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
    for name in ENGINE_FILENAMES:
        candidate = ENGINE_DIR / name
        if candidate.is_file():
            return candidate
    return None

def nnue_path() -> Path:
    return ENGINE_DIR / NNUE_FILENAME

def apply_preset(cfg: dict[str, Any], name: str) -> None:
    if name in STRENGTH_PRESETS:
        _, ms, threads, hash_mb = STRENGTH_PRESETS[name]
        cfg["analysis_ms"] = ms
        cfg["threads"] = threads
        cfg["hash_mb"] = hash_mb
    cfg["strength"] = name

def _sanitize(cfg: dict[str, Any]) -> dict[str, Any]:
    out = dict(cfg)
    out["analysis_ms"] = int(max(50, min(30000, int(out.get("analysis_ms") or 800))))
    out["debounce_ms"] = int(max(0, min(1500, int(out.get("debounce_ms") or 220))))
    out["threads"] = int(max(1, min(32, int(out.get("threads") or 4))))
    out["hash_mb"] = int(max(16, min(4096, int(out.get("hash_mb") or 256))))
    try:
        opacity = float(out.get("opacity", DEFAULT_OPACITY))
    except (TypeError, ValueError):
        opacity = DEFAULT_OPACITY
    out["opacity"] = round(max(MIN_OPACITY, min(MAX_OPACITY, opacity)), 3)
    out["show_coords"] = bool(out.get("show_coords", True))
    out["auto_accept"] = bool(out.get("auto_accept", False))
    out["adaptive"] = bool(out.get("adaptive", True))
    out["low_priority"] = bool(out.get("low_priority", True))
    strength = out.get("strength")
    if strength not in STRENGTH_PRESETS and strength != CUSTOM_STRENGTH:
        strength = "balanced"
    out["strength"] = strength
    geo = out.get("geometry")
    if not (isinstance(geo, list) and len(geo) == 4):
        out["geometry"] = list(DEFAULT_GEOMETRY)
    else:
        out["geometry"] = [int(v) for v in geo]
    return out

def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    raw: dict[str, Any] = {}
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded
            cfg.update({k: v for k, v in raw.items() if k in DEFAULT_CONFIG})
    except (OSError, ValueError):
        pass
    if "strength" not in raw:
        apply_preset(cfg, "balanced")
    return _sanitize(cfg)

def save_config(cfg: dict[str, Any]) -> None:
    try:
        CONFIG_PATH.write_text(
            json.dumps(_sanitize(cfg), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
