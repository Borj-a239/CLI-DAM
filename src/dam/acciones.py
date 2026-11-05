"""Acciones del motor: cada tipo es una subclase de Accion (fábrica por registro).

Añadir un tipo nuevo = escribir una subclase; el registro se rellena solo.
"""
from __future__ import annotations

import re
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

from .errores import AccionNoValida

MARCAS_SIN_TERMINAR = re.compile(
    r"\b(pendiente|por terminar|por hacer|to do|todo|wip|borrador|incompleto)\b",
    re.IGNORECASE,
)


@dataclass
class Resultado:
    origen: Path
    destino: Optional[Path]
    estado: str  # hecho | simulado | saltado
    mensaje: str = ""


def destino_libre(destino: Path) -> Path:
    """Nunca sobrescribe: si existe, prueba «nombre (1).ext», « (2)»..."""
    libre, n = destino, 1
    while libre.exists():
        libre = destino.with_name(f"{destino.stem} ({n}){destino.suffix}")
        n += 1
    return libre


class Accion(ABC):
    tipo = ""
    destructiva = False
    _registro: Dict[str, Type["Accion"]] = {}

    def __init__(self, config: dict):
        self.nombre = config["nombre"]
        self.descripcion = config["descripcion"]
        self.config = config

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.tipo:
            Accion._registro[cls.tipo] = cls

    @staticmethod
    def desde_config(config: dict) -> "Accion":
        """Fábrica: del diccionario del JSON a la clase que toca."""
        clase = Accion._registro.get(config["tipo"])
        if clase is None:
            raise AccionNoValida(
                config.get("nombre", "?"), "tipo", "no hay ninguna clase para ese tipo"
            )
        return clase(config)

    def ejecutar(self, ficheros: List[Path], simular: bool) -> List[Resultado]:
        return [self.aplicar(f, n, simular) for n, f in enumerate(ficheros, start=1)]

    @abstractmethod
    def aplicar(self, fichero: Path, n: int, simular: bool) -> Resultado: ...


class Mover(Accion):
    tipo = "mover"

    def aplicar(self, fichero: Path, n: int, simular: bool) -> Resultado:
        carpeta = Path(self.config["destino"]).expanduser()
        destino = destino_libre(carpeta / fichero.name)
        if not simular:
            carpeta.mkdir(parents=True, exist_ok=True)
            shutil.move(str(fichero), str(destino))
        return Resultado(fichero, destino, "simulado" if simular else "hecho")


class Copiar(Accion):
    tipo = "copiar"

    def aplicar(self, fichero: Path, n: int, simular: bool) -> Resultado:
        carpeta = Path(self.config["destino"]).expanduser()
        destino = destino_libre(carpeta / fichero.name)
        if not simular:
            carpeta.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(fichero), str(destino))
        return Resultado(fichero, destino, "simulado" if simular else "hecho")


class Renombrar(Accion):
    tipo = "renombrar"

    def aplicar(self, fichero: Path, n: int, simular: bool) -> Resultado:
        fecha = datetime.fromtimestamp(fichero.stat().st_mtime)
        nuevo = str(self.config["plantilla"]).format(
            fecha=fecha, n=n, ext=fichero.suffix.lower(), nombre=fichero.stem
        )
        if nuevo == fichero.name:
            return Resultado(fichero, None, "saltado")
        destino = destino_libre(fichero.with_name(nuevo))
        if not simular:
            fichero.rename(destino)
        return Resultado(fichero, destino, "simulado" if simular else "hecho")


class Borrar(Accion):
    tipo = "borrar"
    destructiva = True

    def aplicar(self, fichero: Path, n: int, simular: bool) -> Resultado:
        if not simular:
            fichero.unlink()
        return Resultado(fichero, None, "simulado" if simular else "hecho")


class Revisar(Accion):
    """Analiza si un documento parece inacabado o con errores (nunca modifica)."""

    tipo = "revisar"

    def _texto(self, fichero: Path) -> str:
        sufijo = fichero.suffix.lower()
        if sufijo in (".txt", ".md"):
            return fichero.read_text(encoding="utf-8", errors="replace")
        if sufijo == ".pdf":
            from .pdf import read_pdf

            return read_pdf(fichero)
        return ""

    def aplicar(self, fichero: Path, n: int, simular: bool) -> Resultado:
        avisos: List[str] = []
        try:
            texto = self._texto(fichero)
        except Exception:
            texto = ""
            avisos.append("no se ha podido leer el contenido")
        minimo = int(self.config.get("min_palabras", 150))
        palabras = len(texto.split())
        if fichero.stat().st_size == 0:
            avisos.append("está vacío")
        elif texto and palabras < minimo:
            avisos.append(f"posiblemente inacabado: solo {palabras} palabras")
        if MARCAS_SIN_TERMINAR.search(texto):
            avisos.append("contiene marcas de trabajo pendiente")
        if texto.strip() and texto.strip()[-1] not in ".:;!?…\"')»]":
            avisos.append("el texto no acaba en signo de puntuación")
        return Resultado(
            fichero,
            None,
            "simulado" if simular else "hecho",
            "; ".join(avisos) or "pinta completo",
        )
