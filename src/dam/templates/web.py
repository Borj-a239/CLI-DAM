"""Plantillas web vacías: index.html con header/nav/main/footer + css/estilos.css."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional


def write_web_targets(dest: Path) -> List[Path]:
    """Rutas estándar donde irían index.html y css/estilos.css."""
    return [dest / "index.html", dest / "css" / "estilos.css"]


def write_web(dest: Path, autor: str, title: str, target: Optional[Path] = None) -> Path:
    """Escribe la plantilla web. `target` es la ruta final ya reservada.

    Sin `target` escribe solo index.html (el css se escribe en otra pasada
    con su propio target, para poder saltarse ficheros existentes 1 a 1).
    """
    if target is not None:
        if target.name == "estilos.css":
            return _write_css(target, autor, title)
        return _write_index(target, autor, title)
    return _write_index(dest / "index.html", autor, title)


def _write_index(html: Path, autor: str, title: str) -> Path:
    html.parent.mkdir(parents=True, exist_ok=True)
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
    return html


def _write_css(css: Path, autor: str, title: str) -> Path:
    css.parent.mkdir(parents=True, exist_ok=True)
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
    return css
