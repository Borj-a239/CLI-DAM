"""Lectura y escritura de la configuración en ~/.damrc (formato clave = valor)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .util import expand_home, home_dir



def config_path() -> Path:
    """Resuelto en cada llamada: ~/.damrc (respeta el HOME del momento)."""
    return home_dir() / ".damrc"



DEFAULT_ROOTS = ["~/DAM"]


@dataclass
class Config:
    roots: List[Path] = field(default_factory=list)
    autor: str = ""
    editor: str = ""

    def roots_or(self, fallback: List[Path]) -> List[Path]:
        return self.roots if self.roots else fallback


def _split_list(raw: str) -> List[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_config(path: Optional[Path] = None) -> Config:
    """Parseja ~/.damrc. Ignora silenciosament línies malformades."""
    cfg_path = path or config_path()
    raw_roots: List[str] = []
    autor = ""
    editor = ""
    if cfg_path.exists():
        try:
            for line in cfg_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip().lower()
                value = value.strip().strip("\"'")
                if key == "roots":
                    raw_roots.extend(_split_list(value))
                elif key == "autor":
                    autor = value
                elif key == "editor":
                    editor = value
        except OSError:
            pass

    roots: List[Path] = []
    for item in raw_roots:
        expanded = expand_home(item)
        if expanded.is_dir():
            roots.append(expanded.resolve())
    return Config(roots=roots, autor=autor, editor=editor or "xdg-open")


def ensure_config() -> Path:
    """Crea ~/.damrc con valores por defecto si no existe. Devuelve la ruta."""
    target = config_path()
    if target.exists():
        return target
    example_roots = ", ".join(DEFAULT_ROOTS)
    content = (
        "# Configuración de dam (formato: clave = valor)\n"
        f"# roots: lista de carpetas donde buscar, separadas por comas (sin límite)\n"
        f"roots = {example_roots}\n"
        "autor = Tu Nombre\n"
        "editor = code\n"
    )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError:
        pass
    return target
