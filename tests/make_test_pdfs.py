"""Genera PDFs de prueba SIN librerías (para validar dam start end-to-end).

Uso:
    python3 tests/make_test_pdfs.py out_dir/
Genera:
    cuestionario_tema4.pdf  -> tipo cuestionario
    practica_web.pdf        -> tipo html/css
    php_formularios.pdf     -> fallback regex .php
"""
from __future__ import annotations

import sys
import zlib
from pathlib import Path
from typing import List


def escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def page_stream(lines: List[str]) -> bytes:
    parts = ["BT", "/F1 12 Tf", "14 TL", "50 760 Td"]
    for line in lines:
        parts.append(f"({escape(line)}) Tj T*")
    parts.append("ET")
    return " ".join(parts).encode("latin-1", "replace")


def build_pdf(path: Path, pages: List[List[str]]) -> None:
    n_pages = len(pages)
    objects: List[bytes] = []
    page_ids = [4 + 2 * i for i in range(n_pages)]
    content_ids = [pid + 1 for pid in page_ids]

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, lines in enumerate(pages):
        page_id = page_ids[index]
        content_id = content_ids[index]
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode()
        )
        raw = page_stream(lines)
        compressed = zlib.compress(raw)
        objects.append(
            b"<< /Length "
            + str(len(compressed)).encode()
            + b" /Filter /FlateDecode >>\nstream\n"
            + compressed
            + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = []
    for obj_id, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{obj_id} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))


CUESTIONARIO = [
    [
        "CUESTIONARIO TEMA 4 - EL POLIMORFISMO",
        "Asignatura: Programacion. Responde en el documento adjunto.",
        "",
        "1. Que es el polimorfismo?",
        "2. Cual es la diferencia entre sobre carga y sobre escritura?",
        "3. Para que sirve la clase Object?",
        "4. Cuando usamos un metodo abstracto?",
        "5. Que ventajas aporta una interface?",
    ]
]

WEB = [
    [
        "PRÁCTICA 6 - PAGINA WEB CON HTML Y CSS",
        "Crea un index.html que tenga cabecera header, menu de navegacion nav,",
        "contenido main y pie de pagina footer. Añade una hoja de estilos",
        "css/estilos.css con colores, margenes y selectores por etiqueta.",
        "Usa etiquetas semanticas y enlaces hipervinculo entre dos paginas.",
    ]
]

PHP = [
    [
        "PRÁCTICA 8 - FORMULARIOS EN PHP",
        "Implementa la practica en el fichero practica8.php usando formularios",
        "GET y POST. Guarda el resultado en practica8.php y sube el ZIP.",
    ]
]


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)
    build_pdf(out_dir / "cuestionario_tema4.pdf", CUESTIONARIO)
    build_pdf(out_dir / "practica_web.pdf", WEB)
    build_pdf(out_dir / "php_formularios.pdf", PHP)
    print(f"PDFs de prueba escritos en {out_dir}")


if __name__ == "__main__":
    main()
