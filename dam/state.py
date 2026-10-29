"""Estat persistent a ~/.dam/state.json: historial per a `dam last`."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

STATE_DIR = Path.home() / ".dam"
STATE_PATH = STATE_DIR / "state.json"
MAX_HISTORY = 200


def _read_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _write_state(state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def history() -> List[str]:
    hist = _read_state().get("hist", [])
    return hist if isinstance(hist, list) else []


def record(path: str) -> None:
    """Afegeix una ruta a l'historial (més recent al final)."""
    state = _read_state()
    hist = state.get("hist", [])
    if not isinstance(hist, list):
        hist = []
    if hist and hist[-1] == path:
        return
    hist.append(path)
    state["hist"] = hist[-MAX_HISTORY:]
    _write_state(state)


def get(index: int) -> str:
    """Ruta N-èsima comatgem enrere des de l'actual.

    index=0 → la darrera visitada; index=1 → l'anterior a l'actual; etc.
    """
    hist = history()
    if not hist:
        raise IndexError("l'historial és buit; fes primer un 'dam go'")
    if index < 0 or index >= len(hist):
        raise IndexError(
            f"no hi ha {index + 1} entrades a l'historial (n'hi ha {len(hist)})"
        )
    return hist[-1 - index]
