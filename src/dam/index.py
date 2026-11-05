"""Índice perezoso del disco con caché en ~/.dam/cache/<hash>.json."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .util import home_dir



def cache_dir() -> Path:
    """Resolt a cada crida: ~/.dam/cache (respecta el HOME del moment)."""
    return home_dir() / ".dam" / "cache"

CACHE_TTL = 10 * 60  # segundos; si la raíz es más nueva que la caché, cae


@dataclass(frozen=True)
class Entry:
    path: str
    is_dir: bool

    @property
    def name(self) -> str:
        return os.path.basename(self.path)


def _cache_file(root: Path) -> Path:
    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:32]
    return cache_dir() / f"{digest}.json"


def _walk(root: Path) -> Iterator[Entry]:
    """Recorre sin petar nunca: los permisos denegados se ignoran en silencio."""
    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                children = list(it)
        except OSError:
            continue
        for child in children:
            try:
                is_dir = child.is_dir(follow_symlinks=False)
            except OSError:
                continue
            yield Entry(child.path, is_dir)
            if is_dir:
                stack.append(child.path)


def _load_cached(root: Path) -> Optional[List[Entry]]:
    cache = _cache_file(root)
    if not cache.exists():
        return None
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if time.time() - data.get("built_at", 0) > CACHE_TTL:
            return None
        try:
            if os.stat(root).st_mtime > data["built_at"]:
                return None
        except OSError:
            return None
        return [
            Entry(item["p"], item["d"]) for item in data.get("entries", [])
        ]
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def _save_cache(root: Path, entries: List[Entry]) -> None:
    try:
        cache_dir().mkdir(parents=True, exist_ok=True)
        payload = {
            "root": str(root),
            "built_at": time.time(),
            "entries": [{"p": e.path, "d": e.is_dir} for e in entries],
        }
        _cache_file(root).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def index_root(root: Path, reindex: bool = False) -> List[Entry]:
    """Índice completo de una raíz; reutiliza la caché si se puede."""
    root = root.resolve()
    if not root.is_dir():
        return []
    if not reindex:
        cached = _load_cached(root)
        if cached is not None:
            return cached
    entries = list(_walk(root))
    _save_cache(root, entries)
    return entries
