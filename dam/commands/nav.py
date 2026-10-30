"""Comandaments `dam go` i `dam last`."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from .. import state
from ..config import Config, config_path, ensure_config, load_config
from ..index import Entry, index_root
from ..search import rank
from ..selector import select
from ..util import err, expand_home, info

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
        path = expand_home(raw)
        if not path.is_absolute() and cfg.roots:
            # ruta relativa: se resuelve dentro de la primera root del config
            path = cfg.roots[0] / path
        if path.is_file():
            path = path.parent
        if path.is_dir():
            roots.append(path.resolve())
    if not extra:  # si el usuario pasa rutas, IGNORA el config
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
    """Si se elige un fichero, la carpeta es su madre; si es carpeta, ella."""
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


class EditorCommand:
    @staticmethod
    def subparser(subparsers):
        parser = subparsers.add_parser(
            "edit",
            help="abre el editor (config `editor`) donde esté tu carpeta actual",
            description=(
                "Abre el editor configurado en ~/.damrc (por defecto `code`) "
                "en la carpeta que pases o en la actual. Se apoya en la "
                "navegación de `go`: primero `dam go herencia` (hace cd vía "
                "wrapper) y luego `dam edit` abre el editor ahí."
            ),
            epilog=(
                "Ejemplos:\n"
                "  dam edit            # abre el editor en .\n"
                "  dam edit ~/DAM/ASIX # abre el editor en esa carpeta\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "path", nargs="?", default=".",
            help="carpeta a abrir (por defecto, la actual)",
        )
        parser.set_defaults(func=EditorCommand.run)
        return parser

    @staticmethod
    def run(args: argparse.Namespace, cfg: Config) -> int:
        import shutil
        import subprocess

        target = expand_home(args.path)
        if not target.is_dir():
            err(f"'{args.path}' no es una carpeta.")
        editor = cfg.editor or os.environ.get("EDITOR") or "xdg-open"
        argv = editor.split() + [str(target)]
        binary = shutil.which(argv[0])
        if binary is None:
            err(f"no encuentro el editor '{argv[0]}' (cámbialo en ~/.damrc).")
        try:
            subprocess.run(argv, check=False)
        except OSError as exc:
            err(f"no puedo lanzar el editor: {exc}")
        return 0


class ConfigCommand:
    @staticmethod
    def subparser(subparsers):
        parser = subparsers.add_parser(
            "conf",
            help="muestra (o abre con el editor) la config ~/.damrc",
            description=(
                "Sin argumentos imprime ~/.damrc tal cual, para revisar qué "
                "roots/autor/editor estás usando. Con --editar lo abre con el "
                "editor configurado."
            ),
            epilog=(
                "Formato de ~/.damrc (una clave por línea):\n"
                "  roots = ~/DAM, ~/Uni, ~/Proyectos   # lista, sin límite\n"
                "  autor = Mi Nombre\n"
                "  editor = code\n"
                "\n"
                "Recuerda: si pasas rutas a `dam go`, el config se IGNORA para\n"
                "esa búsqueda (se usan solo las rutas que pases + la actual)."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "-e", "--editar", action="store_true",
            help="abre ~/.damrc con el editor del config",
        )
        parser.set_defaults(func=ConfigCommand.run)
        return parser

    @staticmethod
    def run(args: argparse.Namespace, cfg: Config) -> int:
        import shutil
        import subprocess

        path = ensure_config()
        if args.editar:
            editor = (cfg.editor or os.environ.get("EDITOR") or "xdg-open").split()
            if shutil.which(editor[0]) is None:
                err(f"no encuentro el editor '{editor[0]}'.")
            subprocess.run(editor + [str(path)], check=False)
            return 0
        try:
            print(path.read_text(encoding="utf-8"))
        except OSError as exc:
            err(f"no puedo leer {path}: {exc}")
        if cfg.roots:
            info("\nroots efectivas: " + ", ".join(str(r) for r in cfg.roots))
        else:
            info(
                "\nroots efectivas: (ninguna). Edita ~/.damrc (`dam conf --editar`)\n"
                "y pon, p. ej.:  roots = ~/DAM, ~/Uni  (solo cuentan carpetas que existan)."
            )
        return 0


def register(subparsers) -> None:
    GoCommand.subparser(subparsers)
    LastCommand.subparser(subparsers)
    EditorCommand.subparser(subparsers)
    ConfigCommand.subparser(subparsers)
