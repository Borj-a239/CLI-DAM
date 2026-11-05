"""Detección de tipo de práctica a partir del texto de un PDF.

Dos capas:
  1. Diccionario de palabras clave editable (dam/detection/keywords.py).
  2. Fallback regex ``\\.\\w+`` : cualquier extensión mencionada en el PDF se
     genera como fichero vacío con cabecera de autor.

Devuelve un Detection con las señales suficientes para que los generadores
creen plantillas VACÍAS (nunca soluciones).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .keywords import KEYWORD_RULES, TYPE_PRIORITY

WORD_BOUNDARY_START = re.compile(r"[^A-Za-z0-9À-ɏ]")


def _count_needle(haystack: str, needle: str) -> int:
    """Cuenta coincidencias de palabra (sin hits parciales tipo formula⊂formulario).

    Si el termino empieza con caracter de puntuacion (p.ej. "(" o "?") se
    permite anidar dentro de palabras, porque ahi buscamos simbolos literales.
    """
    if not needle:
        return 0
    if not needle[0].isalnum():
        return haystack.count(needle)
    total = 0
    start = 0
    while True:
        pos = haystack.find(needle, start)
        if pos == -1:
            return total
        end = pos + len(needle)
        before_ok = pos == 0 or not haystack[pos - 1].isalnum()
        after_ok = end >= len(haystack) or not haystack[end].isalnum()
        if before_ok and after_ok:
            total += 1
        start = pos + 1

ACCENTS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")

# Pregunta: trozo "1." / "1)" / "1 -" ... "?" dentro de una misma línea.
# Sin DOTALL y con [^\n?] para que nunca se coma otra pregunta siguiente.
QUESTION_RE = re.compile(r"(?:^|\s)(\d{1,2})\s*[.)\-–]\s*([^\n?]{4,180}\?)")
# CREATE TABLE nombre ( ... )   — solo captura el nombre, jamás los campos
CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+[`\"\[]?(\w+)[`\"\]]?", re.IGNORECASE)
# SELECT ... FROM ... (para meterlo como comentario, no como query funcional)
SELECT_RE = re.compile(r"SELECT\s+.{0,120}?\s+FROM\s+[`\"\[]?(\w+)", re.IGNORECASE | re.DOTALL)
# function nombre(...) / nombre(...) {   — solo la firma, cuerpo vacío
FUNC_RE = re.compile(
    r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)", re.IGNORECASE
)
# Java-ish: class X, interface X (el nombre de clase siempre va en mayúscula)
CLASS_RE = re.compile(r"\b(?:class|interface)\s+([A-Z]\w*)")
# package det.ur (si el PDF lo declara explícitamente)
PACKAGE_RE = re.compile(r"\bpackage\s+([a-z][\w]*(?:\.[a-z][\w]*)+)\b")
# método Java-ish: tipo nombre( ) declarado en enumeraciones tipo "- método X()"
METHOD_RE = re.compile(r"(?:método|metodo|mètode)\s+([a-z]\w*)\s*\(", re.IGNORECASE)
# campos: "- campo nombre" o "campo: nombre"
FIELD_RE = re.compile(r"(?:campo|atr[íi]buto|camp)\s*[:\-]?\s+`?(\w+)`?", re.IGNORECASE)
# palabras vacías que nunca son nombres de campo ("el camp DE les bases")
FIELD_STOPWORDS = {
    "a", "al", "de", "del", "el", "la", "las", "les", "los", "lo", "y", "e", "o",
    "u", "i", "en", "es", "que", "se", "su", "sus", "un", "una", "unos", "unas",
    "the", "of", "l", "ho", "hi", "us", "nombre", "campo",
}
# ítems enumerados al inicio de línea: "1.", "2)", "Activitat 3." ...
ITEM_RE = re.compile(
    r"(?:^|\n)[ \t]*(?:[^\W\d]\w{0,14}\s+)?(\d{1,2})\s*[.)\-–]\s+"
)
# pies de página/folio que ensucian los enunciados (centros, webs, teléfonos)
FOOTER_RE = re.compile(
    r"(?m)^[^\n]*(?:\bwww\.\S+|\bTel\s*:|\bFax\s*:|@\S+)[^\n]*$"
    r"|(?m)^[ \t]*(?:IES\b|Avda?\.[ \t]|[Cc/]\s*[Pp]\.?\s*\d{4,5}\b)[^\n]*$"
)
# extensiones de fichero mencionadas en el texto
EXT_RE = re.compile(r"\.([A-Za-z][A-Za-z0-9]{0,6})\b")
# nombre de tabla para base de datos Access-ish (exige límite de palabra:
# "taules" no es "taula <nombre>", y evita capturar stopwords tipo "de")
TABLE_RE = re.compile(
    r"(?:tabla|asenyalador|taula)\b\s*[«\"'']?([^\W\d]\w{2,})", re.IGNORECASE
)


@dataclass
class Detection:
    scores: Dict[str, float] = field(default_factory=dict)
    question_hits: int = 0
    questions: List[str] = field(default_factory=list)
    sql_tables: List[str] = field(default_factory=list)
    sql_selects: List[str] = field(default_factory=list)
    js_functions: List[Tuple[str, str]] = field(default_factory=list)
    java_classes: List[str] = field(default_factory=list)
    java_package: str = ""
    calc_headers: List[str] = field(default_factory=list)
    db_tables: Dict[str, List[str]] = field(default_factory=dict)
    extensions: List[str] = field(default_factory=list)
    java_methods: List[str] = field(default_factory=list)

    @property
    def primary(self) -> str:
        """Tipo ganador (puntuación; empate → TYPE_PRIORITY). Vacío si nada."""
        if not self.scores:
            return ""
        best = max(self.scores.values())
        winners = [t for t, s in self.scores.items() if s >= best - 1e-9]
        for candidate in TYPE_PRIORITY:
            if candidate in winners:
                return candidate
        return winners[0]

    @property
    def wants_web(self) -> bool:
        return self.scores.get("html", 0) > 0 or self.scores.get("css", 0) > 0


ACCENT_TABLE = str.maketrans("ÀÈÌÒÙàèìòù", "AEIOUaeiou")


def normalize(text: str) -> str:
    return text.translate(ACCENTS).translate(ACCENT_TABLE).lower()


def score_keywords(text: str, question_hits: int = 0) -> Dict[str, float]:
    normalized = normalize(text)
    scores: Dict[str, float] = {}
    for ttype, hints in KEYWORD_RULES.items():
        total = 0.0
        distinct = 0
        for hint in hints:
            word, weight = hint if isinstance(hint, tuple) else (hint, 1.0)
            needle = normalize(word)
            if not needle:
                continue
            count = _count_needle(normalized, needle)
            if count:
                distinct += 1
                total += weight * min(count, 8)
        # una sola aparicion suelta no define el tipo (evita "Object"->java
        # por un solo golpe): hacen falta >=2 terminos distintos o mucha fuerza
        if distinct < 2 and total < 6.0:
            continue
        if ttype == "cuestionario":
            # refuerzo: numeracion tipo "1. ...?" detectada como preguntas
            total += question_hits * 2.0
            distinct += 1 if question_hits else 0
        if total > 0:
            scores[ttype] = total
    return scores


def extract_questions(text: str) -> List[str]:
    """Ítems numerados TAL CUAL (p.ej. "Activitat 5. ...") sin recortar en el
    primer "?": el cuerpo llega hasta el siguiente ítem, con las líneas unidas.

    Se queda con la racha más larga de numeración consecutiva (así los
    "CA1a." o "RA1. 1." de rúbricas no desplazan a las preguntas reales).
    """
    body = FOOTER_RE.sub("", text)
    matches = list(ITEM_RE.finditer(body))
    raw: List[Tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        chunk = re.sub(r"\s+", " ", body[match.end():end]).strip()
        if len(chunk) >= 4:
            raw.append((match.group(1), chunk[:500]))
    best: List[Tuple[str, str]] = []
    current: List[Tuple[str, str]] = []
    for item in raw:
        if current and int(item[0]) == int(current[-1][0]) + 1:
            current.append(item)
        else:
            current = [item]
        if len(current) > len(best):
            best = current
    return [f"{num}. {chunk}" for num, chunk in best][:60]


def extract_signals(text: str) -> Detection:
    det = Detection()
    det.question_hits = len(QUESTION_RE.findall(text))
    det.scores = score_keywords(text, det.question_hits)

    det.questions = extract_questions(text) or [
        f"{num}. {question.strip()}"
        for num, question in QUESTION_RE.findall(text)
    ][:60]

    seen: set = set()
    for table in CREATE_TABLE_RE.findall(text):
        if table.lower() not in seen:
            seen.add(table.lower())
            det.sql_tables.append(table)
    for match in SELECT_RE.finditer(text):
        snippet = re.sub(r"\s+", " ", match.group(0)).strip().rstrip(";.,")
        if snippet.lower() not in seen:
            seen.add(snippet.lower())
            det.sql_selects.append(snippet[:160])

    for name, params in FUNC_RE.findall(text):
        det.js_functions.append((name, params.strip()))
    det.js_functions = det.js_functions[:30]

    package_match = PACKAGE_RE.search(text)
    if package_match:
        det.java_package = package_match.group(1)
    classes = [c for c in CLASS_RE.findall(text) if c not in {"String", "System"}]
    det.java_classes = list(dict.fromkeys(classes))[:15]
    det.java_methods = list(dict.fromkeys(METHOD_RE.findall(text)))[:20]

    headers: List[str] = []
    for field_name in FIELD_RE.findall(text):
        if field_name.lower() not in FIELD_STOPWORDS:
            headers.append(field_name)
    det.calc_headers = list(dict.fromkeys(headers))[:20]

    for table in TABLE_RE.findall(text):
        if table.lower() in FIELD_STOPWORDS:
            continue
        det.db_tables.setdefault(table, [])
    if det.scores.get("base", 0) > 0 and not det.db_tables:
        det.db_tables["Tabla1"] = []
    for cols in det.db_tables.values():
        cols.extend(h for h in det.calc_headers if h not in cols)

    det.extensions = list(
        dict.fromkeys(e.lower() for e in EXT_RE.findall(text))
    )
    return det


def detect(text: str) -> Detection:
    return extract_signals(text)
