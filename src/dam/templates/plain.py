"""Cabeceras de autor, ficheros planos y README."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import List

COMMENT_BY_EXT = {
    "php": ("<?php\n", " */\n", "// "),
    "js": ("", "\n", "// "),
    "ts": ("", "\n", "// "),
    "py": ("", "\n", "# "),
    "sh": ("#!/usr/bin/env bash\n", "\n", "# "),
    "c": ("", "\n", "// "),
    "h": ("", "\n", "// "),
    "cpp": ("", "\n", "// "),
    "java": ("", "\n", "// "),
    "cs": ("", "\n", "// "),
    "sql": ("-- ", "\n", "-- "),
    "css": ("/* ", " */\n", "/* "),
    "html": ("<!-- ", " -->\n", "<!-- "),
    "xml": ("", "\n", "<!-- "),
}


def author_header_lines(autor: str, title: str) -> List[str]:
    today = datetime.date.today().isoformat()
    return [
        f"Práctica: {title}",
        f"Autor: {autor}" if autor else "Autor: (define 'autor' en ~/.damrc)",
        f"Creado: {today}",
        "Estado: plantilla vacía generada por 'dam start'",
    ]


def file_header(autor: str, title: str, ext: str) -> str:
    lines = author_header_lines(autor, title)
    opener, closer, prefix = COMMENT_BY_EXT.get(
        ext, ("", "\n", "# " if ext in {"py", "yml", "yaml", "ini", "toml"} else "// ")
    )
    if ext == "php":
        body = "".join(f"// {line}\n" for line in lines)
        return opener + "/**\n" + body + " */\n"
    if opener == "":
        body = "".join(f"{prefix}{line}\n" for line in lines)
        return body + (closer.lstrip("\n") if closer else "")
    if opener == "<!-- ":
        return "".join(f"<!-- {line} -->\n" for line in lines) + "\n"
    if opener == "/* ":
        return "/*\n" + "".join(f" * {line}\n" for line in lines) + " */\n"
    if opener == "-- ":
        return "".join(f"-- {line}\n" for line in lines)
    return "".join(f"{prefix}{line}\n" for line in lines)


HASH_COMMENT_EXTS = {"py", "sh", "yml", "yaml", "ini", "toml"}
SQL_EXTS = {"sql"}


def todo_line(ext: str) -> str:
    if ext in SQL_EXTS:
        return "-- TODO: implementar\n"
    if ext in HASH_COMMENT_EXTS or ext in {"md", "txt"}:
        return "# TODO: implementar\n" if ext in {"py", "yml", "yaml", "ini", "toml"} else ""
    return "// TODO: implementar\n"


def write_plain(path: Path, autor: str, title: str, extra: str = "") -> Path:
    """Fichero plano vacío: solo cabecera de autor + hueco. Nunca código resuelto."""
    ext = path.suffix.lstrip(".").lower()
    content = file_header(autor, title, ext)
    if extra:
        content += "\n" + extra
    content += "\n" + todo_line(ext)
    path.write_text(content, encoding="utf-8")
    return path


def write_readme(dest: Path, title: str, subject: str, autor: str, files: List[str]) -> Path:
    today = datetime.date.today().isoformat()
    listing = "\n".join(f"- `{name}`" for name in files) or "- (aún sin ficheros)"
    content = f"""# {title}

- **Asignatura:** {subject}
- **Alumno:** {autor or '(define autor en ~/.damrc)'}
- **Generada:** {today} con `dam start` (plantilla vacía, sin soluciones)

## Estructura creada

{listing}

## Pendiente

Rellena los huecos `TODO` de cada fichero según el enunciado del PDF.
"""
    readme = dest / "README.md"
    readme.write_text(content, encoding="utf-8")
    return readme
