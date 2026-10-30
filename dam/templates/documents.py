"""Plantillas de documentos: .docx (python-docx) y .odt (odfpy).

Solo estructura: portada, preguntas numeradas TAL CUAL y párrafo vacío bajo
cada una. Jamás respuestas.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..util import require, try_import


def _header_lines(autor: str, title: str, subject: str) -> List[str]:
    lines = [title]
    if subject and subject != "-":
        lines.append(f"Asignatura: {subject}")
    if autor:
        lines.append(f"Autor: {autor}")
    lines.append("Plantilla vacía generada por 'dam start'")
    return lines


def write_docx_questions(
    path: Path, title: str, autor: str, subject: str, questions: List[str]
) -> Path:
    docx = try_import("docx")
    if docx is None:
        raise LookupError("falta python-docx")

    document = docx.Document()
    document.add_heading(title, level=0)
    for line in _header_lines(autor, title, subject)[1:]:
        document.add_paragraph(line)
    document.add_paragraph("")
    if not questions:
        document.add_paragraph("1. (añade aquí las preguntas del enunciado)")
        document.add_paragraph("")
    for question in questions:
        paragraph = document.add_paragraph()
        run = paragraph.add_run(question)
        run.bold = True
        document.add_paragraph("")  # hueco para responder
    _add_author_field(document, autor)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))
    return path


def _add_author_field(document, autor: str) -> None:
    """Pone el autor en la propiedad core del docx (si la lib la expone)."""
    try:
        if autor:
            document.core_properties.author = autor
    except Exception:
        pass


def write_odt_questions(
    path: Path, title: str, autor: str, subject: str, questions: List[str]
) -> Path:
    if try_import("odf") is None:
        raise LookupError("falta odfpy")
    from odf.opendocument import OpenDocumentText
    from odf.style import Style, TextProperties, ParagraphProperties
    from odf.text import H, P

    doc = OpenDocumentText()
    heading_style = Style(name="Heading2", family="paragraph")
    heading_style.addElement(TextProperties(fontweight="bold"))
    doc.styles.addElement(heading_style)

    doc.text.addElement(H(outlinelevel=1, stylename=heading_style, text=title))
    for line in _header_lines(autor, title, subject)[1:]:
        doc.text.addElement(P(text=line))
    if not questions:
        doc.text.addElement(P(text="1. (añade aquí las preguntas del enunciado)"))
        doc.text.addElement(P(text=""))
    for question in questions:
        doc.text.addElement(H(outlinelevel=2, stylename=heading_style, text=question))
        doc.text.addElement(P(text=""))  # hueco para responder
    _set_meta(doc, autor)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    return path


def _set_meta(doc, autor: str) -> None:
    """Autor en las propiedades del documento ODF (si odfpy las expone)."""
    try:
        if autor:
            from odf.dc import Creator

            doc.meta.addElement(Creator(text=autor))
    except Exception:
        pass


def _missing_library() -> bool:
    """True si ni python-docx ni odfpy están instalados."""
    from ..util import try_import

    return try_import("docx") is None and try_import("odf") is None


def write_questions(
    dest_dir: Path, base: str, autor: str, subject: str, questions: List[str], prefer_odt: bool = False
) -> Optional[Path]:
    """Crea el cuestionario en .docx (o .odt si se prefiere / falta docx).

    Devuelve None si ni python-docx ni odfpy están instalados: el caller
    degrada a un .txt y avisa cómo instalar las libs.
    """
    if prefer_odt:
        try:
            return write_odt_questions(
                dest_dir / f"{base}.odt", base, autor, subject, questions
            )
        except LookupError:
            pass
    try:
        return write_docx_questions(
            dest_dir / f"{base}.docx", base, autor, subject, questions
        )
    except LookupError:
        try:
            return write_odt_questions(
                dest_dir / f"{base}.odt", base, autor, subject, questions
            )
        except LookupError:
            return None


def write_questions_txt(
    path: Path, title: str, autor: str, subject: str, questions: List[str]
) -> Path:
    """Cuestionario de reserva en text pla (sense dependencias): preguntes +
    buit sota cadascuna. Cap respuesta."""
    lines = [title]
    if subject and subject != "-":
        lines.append(f"Asignatura: {subject}")
    if autor:
        lines.append(f"Autor: {autor}")
    lines.append("Plantilla vacía generada por 'dam start'")
    lines.append("")
    if not questions:
        lines.append("1. (añade aquí las preguntas del enunciado)")
        lines.append("")
    for question in questions:
        lines.append(question)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
