"""Plantillas de datos: .ods (hoja) y .odb (base de datos) vía odfpy."""
from __future__ import annotations

from pathlib import Path
from typing import List

from ..util import require


def write_ods(
    path: Path, sheet_name: str, headers: List[str], autor: str
) -> Path:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TableCellProperties
    from odf.table import Table, TableColumn, TableRow, TableCell

    require("odf", "odfpy")

    doc = OpenDocumentSpreadsheet()
    header_style = Style(name="HeaderCell", family="table-cell")
    header_style.addElement(TableCellProperties(fontweight="bold"))
    doc.styles.addElement(header_style)

    table = Table(name=sheet_name[:31] or "Hoja1")
    for _ in headers:
        table.addElement(TableColumn())

    if headers:
        from odf.text import P

        row = TableRow()
        for header in headers:
            cell = TableCell(valuetype="string", stylename="HeaderCell")
            cell.addElement(P(text=header))
            row.addElement(cell)
        table.addElement(row)

    for _ in range(10):  # filas vacías para rellenar
        row = TableRow()
        for _ in headers or [""]:
            row.addElement(TableCell())
        table.addElement(row)

    doc.spreadsheet.addElement(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    return path


def write_odb(path: Path, tables: dict, autor: str) -> Path:
    """Genera un .odb (OpenDocument Database) con tablas y campos detectados.

    Usa odfpy directamente escribiendo database:// en el almacén zip ODF.
    Estructura mínima: content.xml con table:table + table:table-column.
    """
    import zipfile

    require("odf", "odfpy")

    path.parent.mkdir(parents=True, exist_ok=True)
    content_parts = []
    for name, columns in tables.items():
        cols_xml = "".join(
            f'<table:table-column table:style-name="co1" '
            f'table:default-cell-style-name="Default"/>'
            for _ in columns
        ) or '<table:table-column table:style-name="co1" table:default-cell-style-name="Default"/>'
        header_cells = "".join(
            f'<table:table-cell office:value-type="string" calc:value="{col}" '
            f'text:string="{col}"/>'
            for col in columns
        )
        content_parts.append(
            f'<table:table table:name="{name}" table:style-name="ta1">'
            f'<table:table-column table:style-name="co1" table:number-columns-repeated="256"/>'
            f"<table:table-row>{header_cells}</table:table-row>"
            f"{cols_xml}"
            f"</table:table>"
        )
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'xmlns:calc="urn:oasis:names:tc:opendocument:xmlns:calc:1.0" '
        'office:version="1.2">'
        "<office:body><office:spreadsheet>"
        + "".join(content_parts)
        + "</office:spreadsheet></office:body></office:document-content>"
    )
    meta = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<office:document-meta '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" '
        'office:version="1.2">'
        f'<office:meta><meta:generator>dam start ({autor})</meta:generator>'
        "</office:meta></office:document-meta>"
    )
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest:manifest '
        'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.2">'
        '<manifest:file-entry manifest:full-path="/" '
        'manifest:media-type="application/vnd.oasis.opendocument.database"/>'
        '<manifest:file-entry manifest:full-path="content.xml" '
        'manifest:media-type="text/xml"/>'
        '<manifest:file-entry manifest:full-path="meta.xml" '
        'manifest:media-type="text/xml"/>'
        "</manifest:manifest>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.database")
        archive.writestr("META-INF/manifest.xml", manifest)
        archive.writestr("content.xml", content)
        archive.writestr("meta.xml", meta)
    return path
