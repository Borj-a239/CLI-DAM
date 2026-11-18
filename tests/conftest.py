"""Caja de arena: NINGUNA prueba toca carpetas reales ni el servidor del centro.

La fixture `aislado` (autouse) aplica a todas las pruebas con fixtures de
pytest; las de unittest (test_dam.py) ya aíslan HOME en su setUp.
"""
from __future__ import annotations

import pytest

from dam import ia

VARIABLES_IA = (
    "CENTRO_IA_URL",
    "CENTRO_IA_KEY",
    "CENTRO_IA_MODEL",
    "CENTRO_IA_CA",
    "CENTRO_IA_TIMEOUT",
)


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    """Cada prueba, en su carpeta temporal y sin credenciales de IA."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))  # ~ apunta aquí (Linux/macOS)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # y aquí en Windows
    for var in VARIABLES_IA:
        monkeypatch.delenv(var, raising=False)
    # ni siquiera el .env real del repo se deja leer desde las pruebas
    monkeypatch.setattr(ia, "_archivos_env", lambda: [])
    ia.set_proveedor(None)  # nada de proveedores cacheados entre pruebas
    yield


@pytest.fixture
def descargas(tmp_path):
    """Una carpeta con ficheros de prueba: tildes, espacios, mayúsculas, viejo."""
    import os
    import time

    carpeta = tmp_path / "Descargas"
    carpeta.mkdir()
    for nombre in ("factura.pdf", "apuntes de redes.docx", "FOTO1.JPG"):
        (carpeta / nombre).write_text("contenido de prueba", encoding="utf-8")
    (carpeta / "apuntes.txt").write_text("apuntes de prueba " * 40, encoding="utf-8")
    hace_40_dias = time.time() - 40 * 86400
    viejo = carpeta / "viejo.tmp"
    viejo.write_text("", encoding="utf-8")
    os.utime(viejo, (hace_40_dias, hace_40_dias))
    return carpeta


@pytest.fixture
def escribir_config(tmp_path):
    """Escribe un acciones.json (lista de acciones o texto tal cual)."""

    def escribir(acciones) -> str:
        import json

        ruta = tmp_path / "acciones.json"
        texto = (
            acciones
            if isinstance(acciones, str)
            else json.dumps({"version": 1, "acciones": acciones}, ensure_ascii=False)
        )
        ruta.write_text(texto, encoding="utf-8")
        return str(ruta)

    return escribir
