"""Carga y validación de acciones.json ANTES de tocar el disco.

Esquema (v1): ver el README, sección «Esquema de acciones.json».
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, List

from .errores import AccionNoValida, ConfigError

TIPOS = {"mover", "copiar", "renombrar", "renombrar-ia", "borrar", "revisar", "resumir"}
OBLIGATORIOS = ["nombre", "descripcion", "tipo"]
POR_TIPO = {"mover": "destino", "copiar": "destino", "renombrar": "plantilla"}
NOMBRE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CAMPOS_FILTRO = {
    "extensiones",
    "patron",
    "mas_antiguo_que_dias",
    "mas_reciente_que_dias",
    "mayor_que_mb",
    "recursivo",
}


def _valida_filtro(acc: dict, nombre: str) -> None:
    filtro = acc.get("filtro")
    if filtro is None:
        return
    if not isinstance(filtro, dict):
        raise AccionNoValida(nombre, "filtro", "debe ser un objeto")
    desconocidos = set(filtro) - CAMPOS_FILTRO
    if desconocidos:
        raise AccionNoValida(
            nombre,
            "filtro",
            f"campos desconocidos: {', '.join(sorted(desconocidos))}",
        )
    if "extensiones" in filtro:
        exts = filtro["extensiones"]
        if not isinstance(exts, list) or not all(
            isinstance(e, str) and e.startswith(".") for e in exts
        ):
            raise AccionNoValida(
                nombre, "filtro.extensiones", "debe ser lista de extensiones con punto"
            )
    patron = filtro.get("patron")
    if patron is not None:
        try:
            re.compile(patron)
        except re.error as e:
            raise AccionNoValida(
                nombre, "filtro.patron", f"expresión regular rota: {e}"
            )
    for campo in ("mas_antiguo_que_dias", "mas_reciente_que_dias", "mayor_que_mb"):
        if campo in filtro and (
            not isinstance(filtro[campo], (int, float)) or isinstance(filtro[campo], bool)
            or filtro[campo] <= 0
        ):
            raise AccionNoValida(nombre, f"filtro.{campo}", "debe ser un número > 0")
    if "recursivo" in filtro and not isinstance(filtro["recursivo"], bool):
        raise AccionNoValida(nombre, "filtro.recursivo", "debe ser true/false")


def _valida_accion(a: Any, vistos: set) -> None:
    if not isinstance(a, dict):
        raise ConfigError("Cada acción debe ser un objeto JSON")
    nombre = str(a.get("nombre") or f"nº {len(vistos) + 1}")
    for campo in OBLIGATORIOS:
        if not a.get(campo):
            raise AccionNoValida(nombre, campo, "es obligatorio")
    if not NOMBRE_RE.match(nombre):
        raise AccionNoValida(
            nombre, "nombre", "solo minúsculas, dígitos y guiones, sin espacios"
        )
    if nombre in vistos:
        raise AccionNoValida(nombre, "nombre", "está repetido")
    vistos.add(nombre)
    tipo = a["tipo"]
    if tipo not in TIPOS:
        raise AccionNoValida(
            nombre, "tipo", f"«{tipo}» no existe; usa uno de: {', '.join(sorted(TIPOS))}"
        )
    extra = POR_TIPO.get(tipo)
    if extra and not a.get(extra):
        raise AccionNoValida(
            nombre, extra, f"es obligatorio en acciones de tipo {tipo}"
        )
    if tipo == "renombrar" and a.get("plantilla") is not None:
        plantilla = str(a["plantilla"])
        huecos = set(re.findall(r"\{(\w+)", plantilla))
        if not huecos <= {"fecha", "n", "ext", "nombre"}:
            raise AccionNoValida(
                nombre,
                "plantilla",
                "huecos válidos: fecha, n, ext, nombre",
            )
    if tipo == "borrar" and a.get("confirmar") is not True:
        raise AccionNoValida(
            nombre, "confirmar", "las acciones que borran exigen confirmar: true"
        )
    _valida_filtro(a, nombre)


def cargar(ruta: Path) -> List[dict]:
    """Devuelve la lista de acciones validadas; si algo falla, ConfigError."""
    ruta = ruta.expanduser()
    if not ruta.is_file():
        raise ConfigError(
            f"No encuentro {ruta}. Crea acciones.json o usa --config RUTA"
        )
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"{ruta.name} no es JSON válido: línea {e.lineno}, columna {e.colno} ({e.msg})"
        )
    if not isinstance(datos, dict):
        raise ConfigError("La raíz de acciones.json debe ser un objeto {...}")
    if datos.get("version") != 1:
        raise ConfigError(
            f"Versión de esquema «{datos.get('version')}» no soportada; la actual es 1"
        )
    acciones = datos.get("acciones")
    if not isinstance(acciones, list) or not acciones:
        raise ConfigError("Falta la lista «acciones» o está vacía")
    vistos: set = set()
    for a in acciones:
        _valida_accion(a, vistos)
    # Invariante de desarrollo: si la validación no grita, todo tiene nombre.
    assert all(a.get("nombre") for a in acciones), "acción sin nombre tras validar"
    return acciones
