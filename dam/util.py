"""Utilidades del entorno: importaciones suaves, salidas y rutas.

IMPORTANTE: todas las rutas con `~` se expanden con `expand_home()`, que usa
`$HOME` del proceso si está definido y si no `Path.home()`. Así el wrapper,
los tests y cualquier `HOME=... dam ...` se respetan siempre.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional


def try_import(name: str) -> Optional[Any]:
    """Importa un módulo o devuelve None si no está instalado."""
    try:
        return __import__(name)
    except ImportError:
        return None


def require(module_name: str, pip_name: Optional[str] = None) -> Any:
    """Devuelve el módulo o sale con un mensaje claro de instalación."""
    mod = try_import(module_name)
    if mod is None:
        pip = pip_name or module_name
        err(
            f"Falta la librería '{module_name}'. Instálala con:\n"
            f"    python3 -m pip install {pip}"
        )
    return mod


def err(message: str, code: int = 1) -> None:
    """Mensaje de error por stderr (stdout se reserva para las rutas)."""
    print(f"dam: {message}", file=sys.stderr)
    sys.exit(code)


def warn(message: str) -> None:
    print(f"dam: aviso: {message}", file=sys.stderr)


def info(message: str) -> None:
    print(message, file=sys.stderr)


def home_dir() -> Path:
    """HOME efectivo del proceso (respeta `HOME=... comando`)."""
    env = os.environ.get("HOME", "")
    return Path(env) if env else Path.home()


def expand_home(raw: str) -> Path:
    """Expande `$VARS` y `~` usando el HOME del entorno (no del pwd)."""
    expanded = Path(os.path.expandvars(raw))
    text = str(expanded)
    if text == "~":
        return home_dir()
    if text.startswith("~/"):
        return home_dir() / text[2:]
    if "~" not in text:
        return expanded
    return Path(os.path.expanduser(text))
