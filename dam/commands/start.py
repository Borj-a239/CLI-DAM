"""Comandament `dam start`: PDF → plantilla BUIDA al lloc correcte."""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..config import Config
from ..detection.detector import Detection, detect
from ..pdf import read_pdf
from ..templates.code import infer_package, write_java_project, write_js, write_sql
from ..templates.data import write_odb, write_ods
from ..templates.documents import write_questions
from ..templates.plain import write_plain, write_readme
from ..templates.web import write_web
from ..util import err, info, warn

SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")
PRACTICE_EXT_RE = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_]*\.(?:php|py|c|h|cpp|hpp|cs|rb|go|rs|kt|swift|sh|"
    r"bat|ps1|xml|json|html?|css|js|ts|sql|java|txt|csv))\b",
    re.IGNORECASE,
)


@dataclass
class Options:
    force: bool = False
    odt: bool = False


class StartCommand:
    @staticmethod
    def subparser(subparsers):
        parser = subparsers.add_parser(
            "start",
            help="lee un PDF de enunciado y crea la plantilla vacía que toca",
            description=(
                "Lee el PDF, detecta el tipo de práctica (diccionario de "
                "palabras clave editable en dam/detection/keywords.py + "
                "fallback regex \\.extension) y crea la estructura VACÍA en la "
                "ruta deducida de --dest o del nombre del PDF. NO resuelve "
                "nada: preguntas literales, firmas sin cuerpo, ficheros sin "
                "código."
            ),
            epilog=(
                "Ejemplos:\n"
                "  dam start ~/Descargas/herencia.pdf --dest DAM/ASIX/UD03/herencia\n"
                "  dam start cuestionario_tema4.pdf        # dest deducido del nombre\n"
                "  dam start practica.pdf --dest ~/Entregables/p5 --force\n"
                "\n"
                "La carpeta de destino se resuelve (en este orden):\n"
                "  1. --dest (relativa se resuelve dentro de la primera root del config)\n"
                "  2. carpeta del PDF / <nombre-del-pdf>\n"
                "  3. pregunta en la TTY (sin TTY usa la opción por defecto).\n"
                "NUNCA sobreescribe ficheros existentes sin preguntar (--force los salta).\n"
                "Crea siempre README.md con título y asignatura."
            ),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("pdf", help="ruta al PDF del enunciado")
        parser.add_argument(
            "--dest",
            default=None,
            metavar="ASIGNATURA/PRACTICA",
            help="destino (absoluto o relativo a la primera root del config)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="no pregunta: reescribe ficheros existentes (¡cuidado!)",
        )
        parser.add_argument(
            "--odt",
            action="store_true",
            help="fuerza .odt en lugar de .docx para los cuestionarios",
        )
        parser.set_defaults(func=StartCommand.run)
        return parser

    @staticmethod
    def run(args: argparse.Namespace, cfg: Config) -> int:
        pdf_path = Path(os.path.expandvars(args.pdf)).expanduser()
        text = read_pdf(pdf_path)
        if not text.strip():
            err("el PDF no té text llegible (escanejat?). No puc detectar el tipus.")

        detection = detect(text)
        dest = resolve_dest(pdf_path, args.dest, cfg)
        title = pdf_path.stem.replace("_", " ").replace("-", " ").strip() or "Práctica"
        subject = subject_from(dest, cfg)
        options = Options(force=args.force, odt=args.odt)

        info(f"PDF: {pdf_path}")
        info(f"Tipo detectado: {detection.primary or 'fallback por extensiones'}")
        created: List[Path] = []
        created += generate(detection, text, dest, title, subject, cfg.autor, options)
        created.append(write_readme(dest, title, subject, cfg.autor, [
            str(p.relative_to(dest)) for p in created
        ]))

        info(f"\nPlantilla vacía creada en: {dest}")
        for path in created:
            info(f"  + {path.relative_to(dest)}")
        print(dest)
        return 0


def resolve_dest(pdf_path: Path, dest_arg: Optional[str], cfg: Config) -> Path:
    if dest_arg:
        dest = Path(os.path.expandvars(dest_arg)).expanduser()
        if not dest.is_absolute() and cfg.roots:
            dest = cfg.roots[0] / dest
        return dest.resolve()

    default = pdf_path.parent / slugify(pdf_path.stem)
    if not sys.stdin.isatty():
        info(f"Sin --dest y sin TTY: uso {default}")
        return default

    info(f"Cap --dest. Opció deduïda: {default}")
    try:
        raw = input("Carpetona on crear-la [Intro = deduïda]: ").strip()
    except (KeyboardInterrupt, EOFError):
        return default
    if not raw:
        return default
    chosen = Path(os.path.expandvars(raw)).expanduser()
    if not chosen.is_absolute() and cfg.roots:
        chosen = cfg.roots[0] / chosen
    return chosen.resolve()


def subject_from(dest: Path, cfg: Config) -> str:
    """Assignatura = primer tros de la ruta que coincideix amb una root filla."""
    for root in cfg.roots:
        try:
            relative = dest.relative_to(root)
            if relative.parts:
                return relative.parts[0]
        except ValueError:
            continue
    for part in reversed(dest.parts):
        if part in {Path.home().name, ""}:
            break
        if len(part) > 2 and not part.startswith("."):
            return part
    return "-"


def generate(
    det: Detection,
    text: str,
    dest: Path,
    title: str,
    subject: str,
    autor: str,
    opts: Options,
) -> List[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    ttype = det.primary

    if ttype == "cuestionario" and (det.questions or det.scores.get("cuestionario", 0) > 0):
        doc = write_questions(dest, slugify(title), autor, subject, det.questions, prefer_odt=opts.odt)
        if doc:
            created.append(doc)

    if det.wants_web:
        created += write_web(dest, autor, title)

    if ttype == "sql" or det.sql_tables or det.sql_selects:
        path = _alloc(dest / "practica.sql", opts)
        if path:
            created.append(write_sql(path, det.sql_tables, det.sql_selects, autor, title))

    if ttype == "js" or det.js_functions:
        path = _alloc(dest / "practica.js", opts)
        if path:
            created.append(write_js(path, det.js_functions, autor, title))

    if ttype == "java" and (det.java_classes or det.java_methods or det.java_package):
        package = det.java_package or infer_package(dest)
        created += write_java_project(
            dest, det.java_classes, det.java_methods, det.calc_headers, package, autor, title
        )

    if ttype == "calc" or (det.calc_headers and ttype not in {"java", "sql", "base"}):
        path = _alloc(dest / "practica.ods", opts)
        if path:
            try:
                created.append(write_ods(path, slugify(title)[:28] or "Hoja1", det.calc_headers, autor))
            except SystemExit:
                fallback = _alloc(dest / "practica_csv_headers.txt", opts)
                if fallback:
                    fallback.write_text(
                        ";".join(det.calc_headers) + "\n", encoding="utf-8"
                    )
                    created.append(fallback)
                    warn("falta odfpy: he deixat les capçaleres a un .txt")

    if ttype == "base" or det.db_tables:
        path = _alloc(dest / "base.odb", opts)
        if path:
            try:
                created.append(write_odb(path, det.db_tables, autor))
            except SystemExit:
                warn("falta odfpy: no puc generar el .odb (instal·la odfpy)")

    # Capa 2: fallback regex — qualsevol .extensio esmentada al PDF → fitxer buit
    skip = {"pdf", "doc", "docx", "odt", "ods", "odp", "png", "jpg", "jpeg", "gif",
            "zip", "rar", "7z", "exe", "msi", "iso", "deb", "mp4", "mp3", "svg",
            "usa", "r", "en", "la", "el", "com", "org", "es", "uk"}
    rich_owns = {"html", "htm", "css", "js", "sql", "java"}
    # Nombres explícitos del tipo "practica8.php" que aparecen en el enunciado
    named: dict = {}
    for full in PRACTICE_EXT_RE.findall(text):
        stem, _, ext = full.lower().rpartition(".")
        if ext not in skip and stem not in named:
            named[ext] = stem

    for ext in det.extensions:
        if ext in skip:
            continue
        if ext in rich_owns and not named.get(ext):
            if ext in {"html", "htm", "css"} and det.wants_web:
                continue
            if ext == "js" and (ttype == "js" or det.js_functions):
                continue
            if ext == "sql" and (ttype == "sql" or det.sql_tables):
                continue
            if ext == "java" and ttype == "java":
                continue
        base = named.get(ext) or (slugify(title[:20]) or "practica")
        path = _alloc(dest / f"{base}.{ext}", opts)
        if path:
            created.append(write_plain(path, autor, title))

    return created


def slugify(text: str) -> str:
    cleaned = SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return cleaned.replace("--", "-") or "practica"


def _alloc(path: Path, opts: Options) -> Optional[Path]:
    """Ruta on escriure, respectant 'no sobreescriure sense avisar'."""
    if path.exists():
        if opts.force:
            warn(f"reescriuré (--force): {path.name}")
            return path
        if sys.stdin.isatty():
            answer = input(f"YA existe {path} — ¿sobrescribir? [s/N]: ").strip().lower()
            return path if answer in {"s", "si", "sí", "y", "yes"} else None
        stem = path.stem
        parent = path.parent
        for i in range(2, 100):
            candidate = parent / f"{stem}-{i}{path.suffix}"
            if not candidate.exists():
                warn(f"existe {path.name}: crearé {candidate.name}")
                return candidate
        return None
    return path


def register(subparsers) -> None:
    StartCommand.subparser(subparsers)
