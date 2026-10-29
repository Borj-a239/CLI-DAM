"""Plantillas de código: .sql, .js y proyectos Java (solo firmas/huecos)."""
from __future__ import annotations

import keyword
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple

from .plain import write_plain

RESERVED_SQL = {
    "select", "from", "where", "table", "create", "insert", "into", "join",
    "inner", "left", "right", "outer", "group", "by", "order", "and", "or",
}


def _valid_table(name: str) -> bool:
    return name.lower() not in RESERVED_SQL and not keyword.iskeyword(name.lower())


def write_sql(
    path: Path,
    tables: List[str],
    selects: List[str],
    autor: str,
    title: str,
) -> Path:
    lines: List[str] = []
    real_tables = [t for t in tables if _valid_table(t)][:12]
    if not real_tables:
        real_tables = ["Tabla1"]
    for table in real_tables:
        lines.append(f"CREATE TABLE {table} (")
        lines.append("    -- TODO: define aquí los campos según el enunciado")
        lines.append(");")
        lines.append("")
    for snippet in selects[:6]:
        lines.append(f"-- Consulta propuesta por el enunciado (no la resuelvo):")
        lines.append(f"--   {snippet}")
    body = "\n".join(lines) + "\n"
    path.write_text(
        _sql_header(autor, title) + body + "\n-- TODO: completar\n", encoding="utf-8"
    )
    return path


def _sql_header(autor: str, title: str) -> str:
    return (
        f"-- Práctica: {title}\n"
        f"-- Autor: {autor}\n"
        "-- Plantilla vacía generada por 'dam start'\n\n"
    )


def write_js(
    path: Path,
    functions: List[Tuple[str, str]],
    autor: str,
    title: str,
) -> Path:
    lines = [
        f"// Práctica: {title}",
        f"// Autor: {autor}",
        "// Plantilla vacía generada por 'dam start'",
        "",
    ]
    seen = set()
    for name, params in functions:
        if name in seen:
            continue
        seen.add(name)
        lines.append(f"function {name}({params}) {{")
        lines.append("    // TODO: implementar")
        lines.append("}")
        lines.append("")
    if not seen:
        lines.append("// TODO: añade aquí las funciones del enunciado")
        lines.append("function ejercicio1() {")
        lines.append("    // TODO: implementar")
        lines.append("}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


SAFE_PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")


def _package_part(raw: str) -> str:
    part = raw.lower()
    part = unicodedata.normalize("NFD", part)
    part = "".join(ch for ch in part if unicodedata.category(ch) != "Mn")
    part = re.sub(r"[^a-z0-9_]", "", part)
    if not part:
        return ""
    if part[0].isdigit():
        part = "p" + part
    if keyword.iskeyword(part):
        part = part + "_"
    return part


def infer_package(dest: Path) -> str:
    """Paquete según la ruta: solo tramos con forma de id java válido.

    Se ignoran tramos absolutos típicos (home, tmp, carpetas de usuario) para
    no generar paquetes gigantes; si no queda nada, se usa `practica`.
    """
    ignored = {
        "home", "tmp", "users", "var", "root", "private", "documents",
        "descargas", "desktop", "escritorio",
    }
    parts: List[str] = []
    for part in dest.parts:
        candidate = _package_part(part)
        if not candidate or candidate in ignored:
            parts = []  # el contexto anterior ya no sirve: se reinicia
            continue
        parts.append(candidate)
    parts = parts[-3:]
    pieces = ["practica"] + [p for p in parts if p != "practica"]
    # dedupe preservando orden
    seen = set()
    unique = []
    for piece in pieces:
        if piece not in seen:
            seen.add(piece)
            unique.append(piece)
    pkg = ".".join(unique)
    return pkg if SAFE_PACKAGE_RE.match(pkg) else "practica"


def write_java_project(
    root: Path,
    classes: List[str],
    methods: List[str],
    fields: List[str],
    package: str,
    autor: str,
    title: str,
) -> List[Path]:
    created: List[Path] = []
    java_dir = root / "src" / "main" / "java"
    pkg_dir = java_dir / package.replace(".", "/")
    pkg_dir.mkdir(parents=True, exist_ok=True)

    if not classes:
        classes = ["Principal"]

    for i, class_name in enumerate(classes):
        body_lines = [f"package {package};", "", f"/**",
                      f" * Práctica: {title}",
                      f" * Autor: {autor}",
                      f" * Plantilla vacía generada por 'dam start'.",
                      f" */",
                      f"public class {class_name} {{"]
        if i == 0 and fields:
            for field in fields[:10]:
                body_lines.append(f"    private Object {field}; // TODO: tipo real")
            body_lines.append("")
        if i == 0:
            body_lines.append("    // TODO: constructores")
            body_lines.append("")
        for method in (methods[:8] if i == 0 else []):
            body_lines.append(f"    public void {method}() {{")
            body_lines.append("        // TODO: implementar")
            body_lines.append("    }")
            body_lines.append("")
        body_lines.append("}")
        file_path = pkg_dir / f"{class_name}.java"
        file_path.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
        created.append(file_path)

    main = pkg_dir / "Main.java"
    if "Main" not in classes and "Principal" not in classes and not main.exists():
        main.write_text(
            f"package {package};\n\n"
            f"// Autor: {autor}\n"
            "// Plantilla vacía generada por 'dam start'\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        // TODO: escribir el programa\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        created.append(main)
    return created
