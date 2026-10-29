"""Plantillas web vacías: index.html con header/nav/main/footer + css/estilos.css."""
from __future__ import annotations

from pathlib import Path
from typing import List


def write_web(dest: Path, autor: str, title: str) -> List[Path]:
    created: List[Path] = []

    html = dest / "index.html"
    html.write_text(
        f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- Autor: {autor} -->
    <link rel="stylesheet" href="css/estilos.css">
</head>
<body>
    <header>
        <!-- TODO: cabecera -->
    </header>
    <nav>
        <!-- TODO: menú -->
    </nav>
    <main>
        <!-- TODO: contenido -->
    </main>
    <footer>
        <!-- TODO: pie de página -->
    </footer>
</body>
</html>
""",
        encoding="utf-8",
    )
    created.append(html)

    css_dir = dest / "css"
    css_dir.mkdir(exist_ok=True)
    css = css_dir / "estilos.css"
    css.write_text(
        f"""/*
 * {title}
 * Autor: {autor}
 * Plantilla vacía generada por 'dam start'
 */

/* TODO: estilos */
""",
        encoding="utf-8",
    )
    created.append(css)
    return created
