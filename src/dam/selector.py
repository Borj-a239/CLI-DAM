"""Selector interactivo de rutas: prompt_toolkit → fzf → lista numerada.

Todos imprimen por stderr y devuelven la ruta elegida (o None). stdout se
deja limpio para que solo salga la ruta final (modo wrapper).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import List, Optional

from .util import home_dir, info


def _glyph(is_dir: bool) -> str:
    return "📁" if is_dir else "📄"


def _label(entry) -> str:
    home = str(home_dir())
    path = entry.path
    if path.startswith(home + os.sep) or path == home:
        path = "~" + path[len(home):]
    return f"{_glyph(entry.is_dir)} {path}"


def select(entries: List, prompt: str = "dam> ") -> Optional[str]:
    """Abre el mejor selector disponible y devuelve la ruta elegida."""
    if not entries:
        return None
    if len(entries) == 1:
        info(f"único resultado: {entries[0].path}")
        return entries[0].path

    labels = [_label(e) for e in entries]

    choice = _select_prompt_toolkit(labels, prompt)
    if choice is None and shutil.which("fzf"):
        choice = _select_fzf(labels)
    if choice is None:
        choice = _select_numbered(labels)
    if choice is None:
        return None
    index = labels.index(choice)
    return entries[index].path


def _select_prompt_toolkit(labels: List[str], prompt: str) -> Optional[str]:
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import CompleteEvent, Completer, Completion
        from prompt_toolkit.document import Document
    except ImportError:
        return None
    if not sys.stdin.isatty():
        return None

    class TreeCompleter(Completer):
        def get_completions(self, document: Document, complete_event: CompleteEvent):
            if not complete_event.text_inserted:
                return
            text = normalize_local(document.text_before_cursor)
            for label in labels:
                if not text or text in normalize_local(label):
                    yield Completion(label, start_position=-len(document.text_before_cursor))

    def normalize_local(value: str) -> str:
        import unicodedata

        decomposed = unicodedata.normalize("NFD", value.lower())
        return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")

    completer = TreeCompleter()
    try:
        from prompt_toolkit.output import ColorDepth
        from prompt_toolkit.shortcuts import CompleteStyle

        session: PromptSession = PromptSession(
            completer=completer, complete_style=CompleteStyle.MULTI_COLUMN
        )
        while True:
            raw = session.prompt(prompt, complete_while_typing=True).strip()
            if not raw:
                return None
            if raw in labels:
                return raw
            needle = normalize_local(raw)
            matches = [label for label in labels if needle in normalize_local(label)]
            if len(matches) == 1:
                return matches[0]
            if matches:
                shown = "\n".join(f"  {m}" for m in matches[:15])
                info(f"Hay más de una coincidencia:\n{shown}\nEscribe algo más concreto.")
            else:
                info("Ninguna coincidencia; inténtalo otra vez o pulsa Enter para salir.")
    except (KeyboardInterrupt, EOFError):
        return None


def _select_fzf(labels: List[str]) -> Optional[str]:
    if not sys.stdin.isatty():
        return None
    try:
        proc = subprocess.run(
            ["fzf", "--height=60%", "--reverse", "--prompt=dam> "],
            input="\n".join(labels),
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    out = proc.stdout.strip()
    return out if out in labels else None


def _select_numbered(labels: List[str]) -> Optional[str]:
    """Fallback para TTY sin libs: lista numerada + elección por número."""
    for i, label in enumerate(labels[:60], start=1):
        info(f"[{i}] {label}")
    if len(labels) > 60:
        info(f"... y {len(labels) - 60} resultados más; acota la búsqueda.")
    try:
        raw = input("dam> número a elegir (Intro para salir): ").strip()
    except (KeyboardInterrupt, EOFError):
        return None
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= min(len(labels), 60):
            return labels[idx - 1]
        info("Número fuera de rango.")
    else:
        info("Debes escribir un número.")
    return None
