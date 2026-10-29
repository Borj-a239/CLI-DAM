"""Utilitats de l'entorn: importacions suaus, sortides i errors."""
from __future__ import annotations

import sys
from typing import Any, Optional


def try_import(name: str) -> Optional[Any]:
    """Importa un mòdul o retorna None si no està instal·lat."""
    try:
        return __import__(name)
    except ImportError:
        return None


def require(module_name: str, pip_name: Optional[str] = None) -> Any:
    """Retorna el mòdul o surt amb un missatge clar d'instal·lació."""
    mod = try_import(module_name)
    if mod is None:
        pip = pip_name or module_name
        err(
            f"Falta la llibreria '{module_name}'. Installa-la amb:\n"
            f"    python3 -m pip install {pip}"
        )
    return mod


def err(message: str, code: int = 1) -> None:
    """Missatge d'error a stderr (stdout es reserva per a rutes)."""
    print(f"dam: {message}", file=sys.stderr)
    sys.exit(code)


def warn(message: str) -> None:
    print(f"dam: avís: {message}", file=sys.stderr)


def info(message: str) -> None:
    print(message, file=sys.stderr)
