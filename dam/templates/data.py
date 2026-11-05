"""Plantillas de datos: .ods (hoja, via odfpy) y .odb (BD, zip ODF propio)."""
from __future__ import annotations

import html
import zipfile
from pathlib import Path
from typing import List

from ..util import try_import


def write_ods(
    path: Path, sheet_name: str, headers: List[str], autor: str
) -> Path:
    if try_import("odf") is None:
        raise LookupError("falta odfpy")
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.style import Style, TableCellProperties
    from odf.table import Table, TableColumn, TableRow, TableCell
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    header_style = Style(name="HeaderCell", family="table-cell")
    header_style.addElement(TableCellProperties(font_weight="bold"))
    doc.styles.addElement(header_style)

    table = Table(name=sheet_name[:31] or "Hoja1")
    for _ in headers:
        table.addElement(TableColumn())

    if headers:
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


ODB_CONTENT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
    office:version="1.2">
  <office:automatic-styles>
    <style:style style:name="co1" style:family="table-column">
      <style:table-column-properties fo:break-before="auto"
        style:column-width="2.258cm"/>
    </style:style>
    <style:style style:name="ta1" style:family="table">
      <style:table-properties table:display="true"
        style:writing-mode="lr-tb"/>
    </style:style>
  </office:automatic-styles>
  <office:body>
    <office:database>
      <office:database-data>
{tables}
      </office:database-data>
    </office:database>
  </office:body>
</office:document-content>
"""

ODB_TABLE_TEMPLATE = """        <table:table table:name="{name}" table:style-name="ta1">
          <table:table-column table:style-name="co1"
              table:number-columns-repeated="{ncols}"
              table:default-cell-style-name="Default"/>
          <table:table-row>
{header_cells}
          </table:table-row>
        </table:table>"""

ODB_HEADER_CELL = (
    '            <table:table-cell office:value-type="string" '
    'calc:value="{value}" text:string="{value}"/>'
)

ODB_META_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    office:version="1.2">
  <office:meta>
    <dc:creator>{autor}</dc:creator>
    <meta:generator>dam start</meta:generator>
  </office:meta>
</office:document-meta>
"""

ODB_MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
    xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
    manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/"
      manifest:media-type="application/vnd.oasis.opendocument.database"/>
  <manifest:file-entry manifest:full-path="content.xml"
      manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml"
      manifest:media-type="text/xml"/>
</manifest:manifest>
"""


def write_odb(path: Path, tables: dict, autor: str) -> Path:
    """Escribe un .odb real (ODF Database): tablas con cabeceras de campos.

    Sin dependencias: es un zip con content.xml + meta.xml + manifest.
    Solo estructura (cabeceras de campo), nunca datos de ejemplo.
    """
    tables_xml = []
    for name, columns in tables.items():
        cols = [str(col) for col in (columns or ["campo1", "campo2"])][:64]
        header_cells = "\n".join(
            ODB_HEADER_CELL.format(value=html.escape(col)) for col in cols
        )
        tables_xml.append(
            ODB_TABLE_TEMPLATE.format(
                name=html.escape(name), ncols=len(cols), header_cells=header_cells
            )
        )
    content = ODB_CONTENT_TEMPLATE.format(tables="\n".join(tables_xml))
    meta = ODB_META_TEMPLATE.format(autor=html.escape(autor or "sin-autor"))

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(
            info, "application/vnd.oasis.opendocument.database"
        )
        archive.writestr("META-INF/manifest.xml", ODB_MANIFEST_TEMPLATE)
        archive.writestr("content.xml", content)
        archive.writestr("meta.xml", meta)
    return path
