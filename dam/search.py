"""Criterios de búsqueda: normalización, tokens y puntuación difusa simple."""
from __future__ import annotations

import os
import unicodedata
from typing import Iterable, List, Optional, Sequence, Tuple


def normalize(text: str) -> str:
    """Baixetes i sense accents, per comparar sense fricció."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def tokens(query: str) -> List[str]:
    return [t for t in normalize(query).split() if t]


def score_one(name: str, token: str) -> float:
    """Puntuació d'un sol token contra un nom (0 si no casa)."""
    nname = normalize(name)
    if not token:
        return 0.0
    if nname == token:
        return 100.0
    if nname.startswith(token):
        return 60.0
    if token in nname:
        return 40.0
    # subsequència de caràcters (difusa): "heren" troba "herencias"
    it = iter(nname)
    if all(ch in it for ch in token):
        return 15.0
    return 0.0


def score_entry(name: str, path: str, query_tokens: Sequence[str]) -> float:
    """Tots els tokens han de puntuar > 0 contra nom o ruta; suma + bonus."""
    if not query_tokens:
        return 1.0
    total = 0.0
    npath = normalize(path)
    for token in query_tokens:
        best = max(score_one(name, token), score_one(os.path.basename(path.rstrip("/")), token))
        if best == 0.0 and token in npath:
            best = 20.0
        if best == 0.0:
            return 0.0
        total += best
    # bonus per profunditat shallow i per ser directori (més navegable)
    depth = path.count(os.sep)
    total += max(0.0, 10.0 - depth * 0.1)
    return total


def rank(entries, query: str, limit: int = 400):
    """Ordena entries per puntuació descendent. entries: Iterable[Entry]."""
    qt = tokens(query)
    scored: List[Tuple[float, object]] = []
    seen = set()
    for entry in entries:
        if entry.path in seen:
            continue
        seen.add(entry.path)
        s = score_entry(entry.name, entry.path, qt)
        if s > 0:
            scored.append((s, entry))
    scored.sort(key=lambda pair: (-pair[0], pair[1].path))
    return [entry for _, entry in scored[:limit]]
