"""Lectura i escriptura de la configuració a ~/.damrc (format clau = valor)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

CONFIG_PATH = Path.home() / ".damrc"

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
    cfg_path = path or CONFIG_PATH
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
        expanded = Path(os.path.expandvars(item)).expanduser()
        if expanded.is_dir():
            roots.append(expanded.resolve())
    return Config(roots=roots, autor=autor, editor=editor or "xdg-open")


def ensure_config() -> Path:
    """Crea ~/.damrc amb valors per defecte si no existeix. Retorna el camí."""
    if CONFIG_PATH.exists():
        return CONFIG_PATH
    example_roots = ", ".join(DEFAULT_ROOTS)
    content = (
        "# Configuració de dam (format: clau = valor)\n"
        f"# roots: llista de carpetes on buscar, separades per comes (sense límit)\n"
        f"roots = {example_roots}\n"
        "autor = El teu Nom\n"
        "editor = code\n"
    )
    try:
        CONFIG_PATH.write_text(content, encoding="utf-8")
    except OSError:
        pass
    return CONFIG_PATH
