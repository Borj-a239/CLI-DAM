"""Comandaments `dam go` i `dam last`."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from .. import state
from ..config import Config
from ..index import Entry, index_root
from ..search import rank
from ..selector import select
from ..util import err, info

MAX_RESULTS = 300


class GoCommand:
    @staticmethod
    def subparser(subparsers):
        parser = subparsers.add_parser(
            "go",
            help="busca un fichero/carpeta y (vía wrapper) hace cd allí",
            description=(
                "Busca textos por todas tus raíces (config ~/.damrc) y por las "
                "rutas adicionales que pases. Muestra un selector interactivo "
                "(prompt_toolkit/fzf/lista) e imprime la ruta elegida por "
                "stdout. Si instalaste el wrapper de dam.bash, el shell hace "
                "el cd real (por eso un subproceso puede 'mover' tu terminal)."
            ),
            epilog=(
                "Ejemplos:\n"
                "  dam go herencia              # busca por las roots del config\n"
                "  dam go .                     # busca desde la carpeta actual\n"
                "  dam go herencia ~/Descargas  # incluye ~/Descargas aunque NO\n"
                "                               # esté en el config (sin límite)\n"
                "  dam go pdf --reindex         # fuerza a rehacer el índice\n"
                "\n"
                "Con --print-fast (o DAM_MODE=machine o salida no-TTY) no hay\n"
                "interactivo: se imprime directo el mejor resultado. El wrapper\n"
                "no necesita activarlo: dam detecta solo si es una TTY."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "text",
            help="texto a buscar; '.' o '' = carpeta actual (acepta acentos/mayúsculas)",
        )
        parser.add_argument(
            "paths",
            nargs="*",
            help="rutas extra donde buscar; se suman a las del config (si pasas "
                 "alguna, el config se ignora)",
        )
        parser.add_argument(
            "--reindex",
            action="store_true",
            help="descarta la caché (~/.dam/cache) y recorre el disco de nuevo",
        )
        parser.add_argument(
            "--print-fast",
            action="store_true",
            help="sin interactivo: imprime el mejor resultado directamente",
        )
        parser.set_defaults(func=GoCommand.run)
        return parser

    @staticmethod
    def run(args: argparse.Namespace, cfg: Config) -> int:
        roots = collect_roots(args.text, args.paths, cfg)
        if not roots:
            err(
                "no hay dónde buscar: añade 'roots' a ~/.damrc o pasa rutas "
                "como argumento."
            )

        query = "" if args.text in (".", "") else args.text
        entries: List[Entry] = []
        for root in roots:
            entries.extend(index_root(root, reindex=args.reindex))

        matches = rank(entries, query, limit=MAX_RESULTS)
        if not matches:
            err(
                f"ningún resultado para '{args.text}' (raíces: "
                + ", ".join(str(r) for r in roots)
                + ")"
            )

        chosen = choose(matches, args, query)
        if chosen is None:
            err("ninguna opción elegida.", code=2)

        final = final_dir(chosen)
        state.record(final)
        print(final)  # única sortida a stdout: la ruta final (mode wrapper)
        return 0


def collect_roots(text: str, extra: List[str], cfg: Config) -> List[Path]:
    roots: List[Path] = []
    if text == ".":
        roots.append(Path.cwd())
    for raw in extra:
        path = Path(os.path.expandvars(raw)).expanduser()
        if path.is_file():
            path = path.parent
        if path.is_dir():
            roots.append(path.resolve())
    if not extra:  # si l'usuari passa rutes, IGNORA el config
        roots.extend(cfg.roots)
    seen = set()
    unique: List[Path] = []
    for root in roots:
        if root not in seen:
            seen.add(root)
            unique.append(root)
    return unique


def choose(matches: List[Entry], args: argparse.Namespace, query: str) -> Optional[str]:
    machine = (
        args.print_fast
        or os.environ.get("DAM_MODE") == "machine"
        or not sys.stdin.isatty()
    )
    if machine:
        return matches[0].path
    if query:
        info(f"{len(matches)} coincidencias para '{query}':")
    return select(matches, prompt=f"dam ({query or '.'})> ")


def final_dir(path_str: str) -> str:
    """Si es tria un fitxer, la carpetna és la seva mare; si és carpeta, ella."""
    path = Path(path_str)
    if path.is_dir():
        return str(path)
    return str(path.parent)


class LastCommand:
    @staticmethod
    def subparser(subparsers):
        parser = subparsers.add_parser(
            "last",
            help="vuelve a una ruta del historial (~/.dam/state.json)",
            description=(
                "Imprime una ruta del historial de 'dam go'. La posición 0 es "
                "la última visita; sin argumentos se imprime la anterior a la "
                "actual (equivalente a 'last 1'). El wrapper de dam.bash hace "
                "el cd real a la ruta impresa."
            ),
            epilog=(
                "Ejemplos:\n"
                "  dam last      # la anterior a la carpeta actual\n"
                "  dam last 0    # la última carpeta visitada\n"
                "  dam last 2    # tres visitas hacia atrás\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "n",
            nargs="?",
            type=int,
            default=1,
            help="posición hacia atrás en el historial (0 = la última; por defecto 1)",
        )
        parser.set_defaults(func=LastCommand.run)
        return parser

    @staticmethod
    def run(args: argparse.Namespace, cfg: Config) -> int:
        try:
            path = state.get(args.n)
        except IndexError as exc:
            err(str(exc))
        print(path)
        return 0


def register(subparsers) -> None:
    GoCommand.subparser(subparsers)
    LastCommand.subparser(subparsers)
