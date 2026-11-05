"""Pruebas pytest del núcleo del curso: camino feliz y casos feos.

Usan SIEMPRE carpetas temporales (tmp_path): nunca tocan ficheros reales.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dam import config as cfg
from dam.errores import AccionNoValida, ConfigError, DamError
from dam.motor import Motor


def _archivo(carpeta: Path, nombre: str, contenido: str = "x") -> Path:
    ruta = carpeta / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _acciones(carpeta: Path, acciones: list, tmp_path: Path) -> Path:
    ruta = tmp_path / "acciones.json"
    ruta.write_text(
        json.dumps({"version": 1, "acciones": acciones}, ensure_ascii=False),
        encoding="utf-8",
    )
    return ruta


# ---------- camino feliz ----------


def test_validar_ok_y_acciones(tmp_path):
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "ordenar",
                "descripcion": "mueve pdfs",
                "tipo": "mover",
                "destino": str(tmp_path / "destino"),
            }
        ],
        tmp_path,
    )
    assert len(cfg.cargar(ruta)) == 1


def test_mover_nunca_sobrescribe(tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    _archivo(origen, "factura.pdf")
    destino = tmp_path / "destino"
    destino.mkdir()
    _archivo(destino, "factura.pdf", "viejo")
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "ordenar",
                "descripcion": "d",
                "tipo": "mover",
                "filtro": {"extensiones": [".pdf"]},
                "destino": str(destino),
            }
        ],
        tmp_path,
    )
    motor = Motor(cfg.cargar(ruta))
    resultados = motor.ejecutar("ordenar", origen, False)
    assert resultados[0].estado == "hecho"
    assert resultados[0].destino.name == "factura (1).pdf"
    assert (destino / "factura.pdf").read_text(encoding="utf-8") == "viejo"


def test_simular_no_toca_el_disco(tmp_path):
    origen = tmp_path / "origen"
    origen.mkdir()
    _archivo(origen, "a.txt")
    destino = tmp_path / "destino"
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "ordenar",
                "descripcion": "d",
                "tipo": "mover",
                "destino": str(destino),
            }
        ],
        tmp_path,
    )
    Motor(cfg.cargar(ruta)).ejecutar("ordenar", origen, True)
    assert not destino.exists()
    assert (origen / "a.txt").exists()


def test_renombrar_usa_plantilla_y_fecha(tmp_path):
    _archivo(tmp_path, "IMG_1.jpg")
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "fotos",
                "descripcion": "d",
                "tipo": "renombrar",
                "filtro": {"extensiones": [".jpg"], "patron": "^IMG_"},
                "plantilla": "{fecha:%Y-%m-%d}_{n:03}{ext}",
            }
        ],
        tmp_path,
    )
    resultados = Motor(cfg.cargar(ruta)).ejecutar("fotos", tmp_path, False)
    assert resultados[0].estado == "hecho"
    assert resultados[0].destino.name.endswith("_001.jpg")


def test_revisar_avisade_inacabado(tmp_path):
    _archivo(tmp_path, "apuntes.md", "esto esta pendiente de terminar y")
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "revisar",
                "descripcion": "d",
                "tipo": "revisar",
                "min_palabras": 150,
                "filtro": {"extensiones": [".md"]},
            }
        ],
        tmp_path,
    )
    (resultado,) = Motor(cfg.cargar(ruta)).ejecutar("revisar", tmp_path, False)
    assert "inacabado" in resultado.mensaje
    assert "pendiente" in resultado.mensaje


def test_borrar_pide_accion_destructiva(tmp_path):
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "limpiar",
                "descripcion": "d",
                "tipo": "borrar",
                "confirmar": True,
            }
        ],
        tmp_path,
    )
    motor = Motor(cfg.cargar(ruta))
    assert motor.accion("limpiar").destructiva is True


# ---------- casos feos ----------


def test_json_roto_dice_linea_y_columna(tmp_path):
    ruta = tmp_path / "a.json"
    ruta.write_text('{"version": 1, "acciones": [ ] ,}', encoding="utf-8")
    with pytest.raises(ConfigError) as e:
        cfg.cargar(ruta)
    assert "línea" in str(e.value)


def test_tipo_inexistente(tmp_path):
    ruta = _acciones(
        tmp_path,
        [{"nombre": "x", "descripcion": "d", "tipo": "mober"}],
        tmp_path,
    )
    with pytest.raises(AccionNoValida) as e:
        cfg.cargar(ruta)
    assert "campo «tipo»" in str(e.value)


def test_nombre_repetido(tmp_path):
    accion = {"nombre": "x", "descripcion": "d", "tipo": "revisar"}
    ruta = _acciones(tmp_path, [accion, dict(accion)], tmp_path)
    with pytest.raises(AccionNoValida) as e:
        cfg.cargar(ruta)
    assert "repetido" in str(e.value)


def test_regex_rota(tmp_path):
    ruta = _acciones(
        tmp_path,
        [
            {
                "nombre": "x",
                "descripcion": "d",
                "tipo": "revisar",
                "filtro": {"patron": "*.tmp"},
            }
        ],
        tmp_path,
    )
    with pytest.raises(AccionNoValida) as e:
        cfg.cargar(ruta)
    assert "filtro.patron" in str(e.value)


def test_borrar_sin_confirmar_no_valida(tmp_path):
    ruta = _acciones(
        tmp_path,
        [{"nombre": "x", "descripcion": "d", "tipo": "borrar"}],
        tmp_path,
    )
    with pytest.raises(AccionNoValida) as e:
        cfg.cargar(ruta)
    assert "confirmar" in str(e.value)


def test_config_inexistente_es_config_error(tmp_path):
    with pytest.raises(ConfigError) as e:
        cfg.cargar(tmp_path / "nada.json")
    assert "No encuentro" in str(e.value)


def test_accion_o_carpeta_inexistentes(tmp_path):
    ruta = _acciones(
        tmp_path,
        [{"nombre": "x", "descripcion": "d", "tipo": "revisar"}],
        tmp_path,
    )
    motor = Motor(cfg.cargar(ruta))
    with pytest.raises(DamError):
        motor.ejecutar("no-existe", tmp_path, False)
    with pytest.raises(DamError):
        motor.ejecutar("x", tmp_path / "sin-carpeta", False)
