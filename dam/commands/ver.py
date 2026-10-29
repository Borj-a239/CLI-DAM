"""Comandament `dam ver`: pinta l'arbre de la carpeta actual sense cd."""
from __future__ import annotations

import argparse
import os
from typing import List

from ..config import Config
from ..util import err

BUILD_JUNK = {
    "target",
    "build",
    "node_modules",
    "__pycache__",
    "dist",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".gradle",
    ".next",
    "out",
}

UNHIDDEN_DEFAULT = False


class VerCommand:
    @staticmethod
    def subparser(subparsers):
        parser = subparsers.add_parser(
            "ver",
            help="muestra el árbol de la carpeta actual (solo lectura, sin cd)",
            description=(
                "Muestra el árbol de directorios de la carpeta actual (o de la "
                "ruta indicada) sin cambiar de directorio. Por defecte oculta "
                "los ocultos (.git, .gitignore...) y la basura de build "
                "(target/, build/, node_modules/, __pycache__/, dist/...)."
            ),
            epilog=(
                "Ejemplos:\n"
                "  dam ver                 # árbol limpio\n"
                "  dam ver -a              # incluye ocultos (.gitignore, .git...)\n"
                "  dam ver --build         # incluye también node_modules/, dist/...\n"
                "  dam ver --depth 2       # solo 2 niveles de profundidad\n"
                "  dam ver ~/DAM           # árbol de otra carpeta\n"
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "path",
            nargs="?",
            default=".",
            help="carpeta a mostrar (por defecto, la actual)",
        )
        parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            help="muestra ocultos (.gitignore, .git...) Y basura de build",
        )
        parser.add_argument(
            "--build",
            action="store_true",
            help="muestra también las carpetas de build (node_modules, dist...)",
        )
        parser.add_argument(
            "--depth",
            type=int,
            default=None,
            metavar="N",
            help="limita la profundidad del árbol (por defecto: sin límite)",
        )
        parser.set_defaults(func=VerCommand.run)
        return parser

    @staticmethod
    def run(args: argparse.Namespace, cfg: Config) -> int:
        root = os.path.abspath(os.path.expanduser(args.path))
        if not os.path.isdir(root):
            err(f"'{args.path}' no es una carpeta válida.")

        show_hidden = args.all
        show_build = args.all or args.build

        print(os.path.basename(root.rstrip(os.sep)) or root)
        walk_tree(root, depth=0, args=args, show_hidden=show_hidden, show_build=show_build)
        return 0


def _skip(name: str, show_hidden: bool, show_build: bool) -> bool:
    if not show_hidden and name.startswith("."):
        return True
    if not show_build and name in BUILD_JUNK:
        return True
    return False


def walk_tree(root: str, depth: int, args, show_hidden: bool, show_build: bool) -> None:
    """Pintada con os.walk manual y contador de profundidad (nunca peta)."""
    if args.depth is not None and depth >= args.depth:
        return
    try:
        with os.scandir(root) as it:
            children: List[os.DirEntry] = sorted(
                it, key=lambda e: (not e.name.startswith("."), e.name.lower())
            )
    except OSError:
        return

    dirs, files = [], []
    for child in children:
        if _skip(child.name, show_hidden, show_build):
            continue
        try:
            is_dir = child.is_dir(follow_symlinks=False)
        except OSError:
            continue
        (dirs if is_dir else files).append(child)

    total = len(dirs) + len(files)
    for i, child in enumerate(dirs + files):
        last = i == total - 1
        connector = "└── " if last else "├── "
        suffix = "/" if child in dirs else ""
        print("    " * depth + connector + child.name + suffix)
        if child in dirs:
            walk_tree(
                child.path,
                depth + 1,
                args,
                show_hidden=show_hidden,
                show_build=show_build,
            )


def register(subparsers) -> None:
    VerCommand.subparser(subparsers)
