"""Estado persistente en ~/.dam/state.json: historial para `dam last`."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from .util import home_dir



def state_dir() -> Path:
    return home_dir() / ".dam"


def state_path() -> Path:
    """Resolt a cada crida: ~/.dam/state.json (respecta el HOME del moment)."""
    return state_dir() / "state.json"
MAX_HISTORY = 200


def _read_state() -> dict:
    path = state_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _write_state(state: dict) -> None:
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        state_path().write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def history() -> List[str]:
    hist = _read_state().get("hist", [])
    return hist if isinstance(hist, list) else []


def record(path: str) -> None:
    """Añade una ruta al historial (la más reciente al final)."""
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
    """Ruta N-ésima hacia atrás desde la actual.

    index=0 → la última visitada; index=1 → la anterior a la actual; etc.
    """
    hist = history()
    if not hist:
        raise IndexError("el historial está vacío; haz primero un 'dam go'")
    if index < 0 or index >= len(hist):
        raise IndexError(
            f"no hay {index + 1} entradas en el historial (hay {len(hist)})"
        )
    return hist[-1 - index]
