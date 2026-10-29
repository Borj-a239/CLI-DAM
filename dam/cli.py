"""Punto de entrada interno del CLI: `_dam` (el wrapper `dam` vive en dam.bash)."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .commands import nav, start, ver
from .config import Config, ensure_config, load_config
from .util import err

EPILOG = """\
Comandos disponibles:
  go        Busca un fichero/carpetas y (vía wrapper) hace cd real allí
  start     Lee un PDF de enunciado y crea la plantilla vacía que toca
  ver       Muestra el árbol de la carpeta actual (solo lectura, sin cd)
  last      Vuelve a una ruta del historial (cd real vía wrapper)

IMPORTANTE (el wrapper): un proceso hijo NO puede hacer cd al padre.
Por eso debes añadir a tu ~/.bashrc la función de dam.bash:
    dam() { if [ "$1" = "go" ] || [ "$1" = "last" ]; then
                local r; r=$(_dam "$@") && [ -n "$r" ] && cd "$r"
            else _dam "$@"; fi; }
El binario real es _dam (este); `dam go`/`dam last` imprimen SOLO la ruta
final por stdout y el wrapper hace el cd. En una TTY verás antes el árbol
interactivo (por stderr).

Config: ~/.damrc   (roots = ..., autor = ..., editor = ...)
Estado: ~/.dam/    (state.json con el historial, cache/ con los índices)
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dam",
        description=(
            "dam — asistente de navegación y plantilla de prácticas para 1º DAM.\n"
            "Solo navega y monta estructuras vacías; nunca resuelve nada."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"dam {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{go,start,ver,last}")
    nav.register(subparsers)
    start.register(subparsers)
    ver.register(subparsers)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    ensure_config()
    cfg: Config = load_config()
    try:
        return args.func(args, cfg)
    except KeyboardInterrupt:
        err("cancelado.", code=130)
        return 130


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dam.cli import main

    sys.exit(main())
