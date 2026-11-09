"""Motor: selecciona ficheros según el filtro y delega en la Accion."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from .acciones import Accion, Resultado
from .errores import DamError

DIA_SEGUNDOS = 86400


class Motor:
    def __init__(self, acciones: List[dict]):
        self.acciones: Dict[str, Accion] = {
            a["nombre"]: Accion.desde_config(a) for a in acciones
        }

    @staticmethod
    def seleccionar(carpeta: Path, filtro: dict) -> List[Path]:
        exts = {e.lower() for e in filtro.get("extensiones", [])}
        patron = re.compile(filtro["patron"]) if "patron" in filtro else None
        viejo = filtro.get("mas_antiguo_que_dias")
        nuevo = filtro.get("mas_reciente_que_dias")
        mb = filtro.get("mayor_que_mb")
        ahora = time.time()
        iterador = (
            carpeta.rglob("*") if filtro.get("recursivo") else carpeta.iterdir()
        )
        elegidos: List[Path] = []
        for f in sorted(iterador):
            try:
                if not f.is_file():
                    continue
                st = f.stat()
            except OSError:
                continue
            if exts and f.suffix.lower() not in exts:
                continue
            if patron and not patron.search(f.name):
                continue
            if viejo and ahora - st.st_mtime < viejo * DIA_SEGUNDOS:
                continue
            if nuevo and ahora - st.st_mtime > nuevo * DIA_SEGUNDOS:
                continue
            if mb and st.st_size < mb * 1024 * 1024:
                continue
            elegidos.append(f)
        return elegidos

    def accion(self, nombre: str) -> Accion:
        accion = self.acciones.get(nombre)
        if accion is None:
            raise DamError(
                f"No hay ninguna acción «{nombre}». Mira la lista con: dam acciones"
            )
        return accion

    def ejecutar(
        self,
        nombre: str,
        carpeta: Optional[Path],
        simular: bool,
        elegir=None,
    ) -> List[Resultado]:
        accion = self.accion(nombre)
        if elegir is not None:
            accion.elegir = elegir  # type: ignore[attr-defined]
        destino_carpeta = (
            Path(carpeta) if carpeta else Path(accion.config.get("origen", "."))
        ).expanduser()
        if not destino_carpeta.is_dir():
            raise DamError(f"La carpeta {destino_carpeta} no existe")
        ficheros = self.seleccionar(destino_carpeta, accion.config.get("filtro", {}))
        return accion.ejecutar(ficheros, simular)
