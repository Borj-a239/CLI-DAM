"""Extrae texto de un PDF SIN librerías externas (parser propio de fallback).

Cubre el subconjunto necesario para *detectar el tipo* de práctica (no es un
visor): objetos `N 0 obj`, flujos planos y FlateDecode, operadores BT/T*/ET,
Tj/'/" y arrays TJ, literales (..) y hex <..>, y ToUnicode (bfchar/bfrange).
Si algo es raro, se ignora ese trozo sin fallar nunca.
"""
from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

OBJ_RE = re.compile(rb"(\d+)\s+0\s+obj(.*?)endobj", re.DOTALL)
STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
REF_RE = re.compile(rb"(\d+)\s+0\s+R")
FONT_REF_RE = re.compile(rb"/Font\s*<<(.*?)>>", re.DOTALL)
FONT_PAIR_RE = re.compile(rb"/(\w+)\s+(\d+)\s+0\s+R")
BASE_FONT_RE = re.compile(rb"/BaseFont\s*/(\w+)")
BFCHAR_RE = re.compile(rb"beginbfchar(.*?)endbfchar", re.DOTALL)
BFRANGE_RE = re.compile(rb"beginbfrange(.*?)endbfrange", re.DOTALL)
CID_WIDTH_RE = re.compile(rb"\b(\d+)\s+(\d+)\s+put\b")
W_RE = re.compile(rb"\b(\d+)\s+(?:\[(.*?)\]|(\d+(?:\.\d+)?))\s+w\b", re.DOTALL)
BFHAT_PAIR_RE = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
BFHAT_TRIPLE_RE = re.compile(
    rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>"
)
# Operadors de text suportats. Els grups són:
#  g1: simple (Tf/Tj/TJ/BT/ET/T*)  g2,g3: par de coordenades (Td/TD o Tm)
#  g4: "Td|TD"  g5: "Tm" (amb sol el par e f, assumim matriu identitat)
OPERATOR_RE = re.compile(
    rb"(?<![\w])(Tf|Tj|TJ|BT|ET|T\*)(?![\w])"
    rb"|(-?[\d.]+)[ \t]+(-?[\d.]+)[ \t]+(Td|TD)(?![\w])"
    rb"|(-?[\d.]+)[ \t]+(-?[\d.]+)[ \t]+Tm(?![\w])"
)
LITERAL_RE = re.compile(rb"\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]*)>")


class PdfModel:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.objects: Dict[int, bytes] = {}
        self.streams: Dict[int, bytes] = {}
        for match in OBJ_RE.finditer(raw):
            obj_id = int(match.group(1))
            body = match.group(2)
            self.objects[obj_id] = body
            if b"stream" in body:
                self.streams[obj_id] = self._decode_stream(body)

    @staticmethod
    def _decode_stream(body: bytes) -> bytes:
        match = STREAM_RE.search(body)
        if not match:
            return b""
        data = match.group(1)
        if b"FlateDecode" in body:
            try:
                data = zlib.decompress(data)
            except zlib.error:
                try:
                    data = zlib.decompressobj().decompress(data)
                except zlib.error:
                    return b""
        return data

    def stream_of(self, obj_id: int) -> bytes:
        return self.streams.get(obj_id, b"")

    def extract_text(self) -> str:
        chunks: List[str] = []
        for body in self.objects.values():
            if not re.search(rb"/Type\s*/Page\b", body):
                continue
            fonts = _fonts_of_page(self, body)
            content_ids: List[int] = []
            single = re.search(rb"/Contents\s+(\d+)\s+0\s+R", body)
            if single:
                content_ids.append(int(single.group(1)))
            array = re.search(rb"/Contents\s*\[(.*?)\]", body, re.DOTALL)
            if array:
                content_ids.extend(int(r) for r in REF_RE.findall(array.group(1)))
            for content_id in content_ids:
                content = self.stream_of(content_id)
                if content:
                    chunks.append(_text_for_content(self, content, fonts))
        return "\n".join(chunk for chunk in chunks if chunk.strip())


def _squash(body: bytes) -> bytes:
    return re.sub(rb"\s+", b"", body)


def _fonts_of_page(model: PdfModel, page_body: bytes) -> Dict[str, FontInfo]:
    fonts: Dict[str, FontInfo] = {}
    blocks = FONT_REF_RE.findall(page_body)
    refs = re.findall(rb"/Font\s+(\d+)\s+0\s+R", page_body)
    for ref in refs:
        font_dict = model.objects.get(int(ref), b"")
        blocks += FONT_REF_RE.findall(font_dict)
        blocks.append(font_dict)
    for block in blocks:
        for alias, obj_id in FONT_PAIR_RE.findall(block):
            fonts[alias.decode(errors="ignore")] = _font_info(model, int(obj_id))
    return fonts


@dataclass
class FontInfo:
    cmap: Dict[int, str] = field(default_factory=dict)
    base_font: str = ""
    width_by_code: Dict[int, float] = field(default_factory=dict)
    default_width: float = 0.0


def _font_info(model: PdfModel, obj_id: int) -> FontInfo:
    body = model.objects.get(obj_id, b"")
    info = FontInfo(cmap=_unicode_map(model, body) or {})
    base = BASE_FONT_RE.search(body)
    if base:
        info.base_font = base.group(1).decode(errors="ignore")
    desc_refs = re.findall(rb"/FontDescriptor\s+(\d+)\s+0\s+R", body)
    descriptor = b"".join(model.objects.get(int(r), b"") for r in desc_refs)
    width_match = re.search(rb"/MissingWidth\s+(\d+(?:\.\d+)?)", descriptor)
    if width_match:
        info.default_width = float(width_match.group(1))
    for descendant_match in re.finditer(rb"/(\d+)\s+(\d+)\s+0\s+R\s+D\b", body):
        cid, descendant_id = int(descendant_match.group(1)), int(descendant_match.group(2))
        desc_body = model.objects.get(descendant_id, b"")
        _collect_cid_widths(model, desc_body, cid, info)
    for array_match in re.finditer(rb"/(\d+)\s*\[(.*?)\]\s+D\b", body, re.DOTALL):
        cid = int(array_match.group(1))
        for number in re.findall(rb"\b(\d+)\s+0\s+R", array_match.group(2)):
            _collect_cid_widths(model, model.objects.get(int(number), b""), cid, info)
    if not info.width_by_code and descriptor:
        _collect_font_widths(descriptor, info)
    return info


def _collect_cid_widths(model: PdfModel, desc_body: bytes, cid: int, info: FontInfo) -> None:
    for match in CID_WIDTH_RE.finditer(desc_body):
        code, width = int(match.group(1)), float(match.group(2))
        info.width_by_code[(cid << 16) | code] = width
    for cid_match, width_match in re.findall(
        rb"/CID\s+(\d+).*?/MissingWidth\s+(\d+(?:\.\d+)?)", desc_body, re.DOTALL
    ):
        info.width_by_code.setdefault(int(cid_match) << 16, float(width_match))


def _collect_font_widths(descriptor: bytes, info: FontInfo) -> None:
    widths_match = re.search(rb"/Widths\s*\[(.*?)\]", descriptor, re.DOTALL)
    first_match = re.search(rb"/FirstChar\s+(\d+)", descriptor)
    if not widths_match or not first_match:
        return
    first = int(first_match.group(1))
    numbers = re.findall(rb"-?\d+(?:\.\d+)?", widths_match.group(1))
    for offset, number in enumerate(numbers):
        info.width_by_code[first + offset] = float(number)


def _unicode_map(model: PdfModel, font_body: bytes) -> Optional[Dict[int, str]]:
    match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", font_body)
    if not match:
        return None
    data = model.stream_of(int(match.group(1)))
    if not data:
        return None
    mapping: Dict[int, str] = {}
    try:
        for block in BFCHAR_RE.findall(data):
            for src, dst in BFHAT_PAIR_RE.findall(block):
                mapping[int(src, 16)] = _hex_to_str(dst)
        for block in BFRANGE_RE.findall(data):
            for line in block.split(b"\n"):
                triple = BFHAT_TRIPLE_RE.search(line)
                if triple:
                    lo = int(triple.group(1), 16)
                    hi = int(triple.group(2), 16)
                    start = _hex_to_str(triple.group(3))
                    if len(start) == 1 and hi - lo < 65535:
                        for offset in range(hi - lo + 1):
                            mapping[lo + offset] = chr(ord(start) + offset)
                    continue
                pair = BFHAT_PAIR_RE.search(line)
                if pair:
                    mapping[int(pair.group(1), 16)] = _hex_to_str(pair.group(2))
    except Exception:
        return mapping or None
    return mapping


def _text_for_content(
    model: PdfModel, content: bytes, fonts: Dict[str, FontInfo]
) -> str:
    """Reconstruye el texto rastreando la posición real (Td/TD/Tm) de cada trozo.

    Reglas:
      - T* fuerza salto de línea (así lo emiten la mayoría de generadores).
      - Td/TD/Tm: si cambiamos de coordenada Y => línea nueva; si en la misma
        línea el trozo empieza separado del último carácter emitido, insertamos
        un espacio (así se separan palabras cuando el PDF las pinta en Tj
        separados sin espacios literales).
    """
    fallback: Optional[FontInfo] = next(
        (f for f in fonts.values() if f.cmap), None
    )
    state = _TextState(fonts, fallback)
    in_text = False
    for match in OPERATOR_RE.finditer(content):
        simple = match.group(1)
        operands = content[max(0, match.start() - 4096) : match.start()]
        if simple == b"BT":
            in_text = True
        elif simple == b"ET":
            state.newline()
            in_text = False
        elif not in_text:
            continue
        elif simple == b"Tf":
            alias = re.search(rb"/(\w+)\s+[\d.]*$", operands)
            if alias:
                state.alias = alias.group(1).decode(errors="ignore")
        elif simple == b"Tj":
            literal = _last_literal(operands)
            if literal is not None:
                state.emit(_decode_literal(literal, state.font().cmap or None))
        elif simple == b"TJ":
            for literal in LITERAL_RE.finditer(_literal_region(operands)):
                state.emit(_decode_literal(literal.group(0), state.font().cmap or None))
        elif simple == b"T*":
            state.newline()
        elif match.group(4) in (b"Td", b"TD"):  # "x y Td" / "tx ty TD"
            state.move(float(match.group(2)), float(match.group(3)), absolute=False)
        elif match.group(5) is not None:
            # "... e f Tm": només ens cal l'origen (e, f) absolut
            state.move(float(match.group(5)), float(match.group(6)), absolute=True)
    return state.result()


class _TextState:
    def __init__(self, fonts: Dict[str, FontInfo], fallback: Optional[FontInfo]) -> None:
        self.fonts = fonts
        self.fallback = fallback
        self.alias = ""
        self.out: List[str] = []
        self.x = 0.0
        self.y = 0.0
        self.last_end: Optional[float] = None

    def font(self) -> FontInfo:
        return self.fonts.get(self.alias) or self.fallback or FontInfo()

    def emit(self, text: str) -> None:
        """Pinta text a la posició actual; si l'origen queda lluny del final
        del text anterior, insereix un espai (paraules pintades en Tj separats).
        """
        if not text:
            return
        font = self.font()
        if self.out and not self.out[-1].endswith("\n") and self.last_end is not None:
            if self.x - self.last_end > self.space_width(font) * 0.5:
                self.out.append(" ")
        width = _string_width(text, font)
        self.out.append(text)
        if width:
            self.last_end = self.x + width
        else:
            # font sense widths conegudes: aproximem per nombre de caràcters
            self.last_end = self.x + len(text) * self.space_width(font) * 0.5

    def move(self, dx: float, dy: float, absolute: bool) -> None:
        """Td/TD (relatiu) i Tm (absoluto):Y diferent => línia nova."""
        new_x = dx if absolute else self.x + dx
        new_y = dy if absolute else self.y + dy
        if new_y != self.y:
            self.newline()
            self.last_end = None
        self.x = new_x
        self.y = new_y

    def newline(self) -> None:
        if self.out and not self.out[-1].endswith("\n"):
            self.out.append("\n")

    def space_width(self, font: FontInfo) -> float:
        width = font.width_by_code.get(32)
        if width:
            return width
        return font.default_width or 250.0

    def result(self) -> str:
        text = "".join(self.out)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text


def _string_width(text: str, font: FontInfo) -> float:
    if not font.width_by_code:
        return 0.0
    total = 0.0
    for char in text:
        total += font.width_by_code.get(ord(char), font.default_width or 500.0)
    return total


def _last_literal(operands: bytes) -> Optional[bytes]:
    region = _literal_region(operands)
    matches = list(LITERAL_RE.finditer(region))
    if not matches:
        return None
    return matches[-1].group(0)


def _literal_region(operands: bytes) -> bytes:
    tail = operands[-4096:]
    start_paren = tail.rfind(b"(")
    start_angle = tail.rfind(b"<")
    start = max(start_paren, start_angle)
    if start <= 0:
        return tail
    opener = tail[start - 1 : start]
    closer = b")" if opener == b"(" else b">"
    end = tail.find(closer, start)
    if end == -1:
        return tail
    return tail[start - 1 : end + 1]


def _decode_literal(literal: bytes, cmap: Optional[Dict[int, str]]) -> str:
    if literal.startswith(b"<"):
        return _hex_to_str(literal[1:-1])
    inner = literal[1:-1]
    decoded = bytearray()
    escaped = False
    digits = 0
    for byte in inner:
        if escaped and 48 <= byte <= 55 and digits:
            continue
        if escaped:
            mapping = {
                ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8,
                ord("f"): 12, ord("("): 40, ord(")"): 41, ord("\\"): 92,
                ord("\r"): 0, ord("\n"): 0,
            }
            replacement = mapping.get(byte, byte)
            if replacement:
                decoded.append(replacement)
            escaped = False
        elif byte == 92:
            escaped = True
        else:
            decoded.append(byte)
    text = bytes(decoded)
    if cmap:
        chars = []
        for code in text.decode("latin-1"):
            chars.append(cmap.get(ord(code), ""))
        return "".join(chars)
    try:
        return text.decode("utf-8")
    except UnicodeDecodeError:
        return text.decode("latin-1")


def _hex_to_str(hex_bytes: bytes) -> str:
    clean = re.sub(rb"\s", b"", hex_bytes)
    if len(clean) % 2:
        clean += b"0"
    try:
        data = bytes.fromhex(clean.decode("ascii"))
    except ValueError:
        return ""
    if len(data) >= 2 and len(data) % 2 == 0:
        try:
            decoded = data.decode("utf-16-be")
            if all(31 < ord(ch) or ch in "\r\n\t" for ch in decoded):
                return decoded
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1")


def extract_pdf_text(path: Path) -> str:
    """API pública: texto del PDF o cadena vacía si no entendemos el PDF."""
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if not raw.startswith(b"%PDF"):
        return ""
    try:
        return PdfModel(raw).extract_text()
    except Exception:
        return ""
