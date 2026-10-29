"""Extracción de texto de PDFs con degradación suave.

Orden de capas (cada una solo se usa si la anterior falló/no hay librería):
  1. pdfplumber  (dependencia recomendada)
  2. pypdf / PyPDF2
  3. minipdf     (parser propio de este paquete, sin dependencias)

`read_pdf` nunca peta por un PDF raro: si nada extrae texto, sale con un
error claro por stderr (stdout se reserva para rutas).
"""
from __future__ import annotations

from pathlib import Path

from . import minipdf
from .util import err, warn


def _try_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return ""
    try:
        chunks = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                try:
                    chunks.append(page.extract_text() or "")
                except Exception:
                    chunks.append("")
        return "\n".join(chunks)
    except Exception as exc:
        warn(f"pdfplumber falló ({exc})")
        return ""


def _try_pypdf(path: Path) -> str:
    reader_cls = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_cls = PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_cls = PdfReader
        except ImportError:
            return ""
    try:
        reader = reader_cls(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        warn(f"pypdf falló ({exc})")
        return ""


def read_pdf(path: Path) -> str:
    if not path.is_file():
        err(f"no existe el PDF: {path}")

    for extractor in (_try_pdfplumber, _try_pypdf, minipdf.extract_pdf_text):
        try:
            text = extractor(path)
        except Exception:
            text = ""
        if text and text.strip():
            return text

    err(
        "no he podido extraer texto del PDF.\n"
        "  - Si es un PDF escaneado (imagen), necesitarás OCR.\n"
        "  - Si faltan librerías:  python3 -m pip install pdfplumber pypdf"
    )
    return ""
