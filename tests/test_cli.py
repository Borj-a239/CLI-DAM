"""La CLI desde fuera (typer.testing.CliRunner): un código de salida por caso.

Estas pruebas no miran funciones sueltas: teclean la orden y comprueban lo
que ve una persona — el código que sale y que NUNCA aparece un Traceback.
La fixture `aislado` (autouse, en conftest.py) garantiza que no hay IA real.
"""
from __future__ import annotations

import io
import json

from typer.testing import CliRunner

from dam import ia
from dam.cli import app

runner = CliRunner()

SIN_TRACEBACK = "Traceback"


def test_la_ayuda_funciona(escribir_config):
    escribir_config([])  # cualquier config válida
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert SIN_TRACEBACK not in r.output


def test_json_roto_sale_con_3_y_sin_traza(escribir_config):
    ruta = escribir_config('{"version": 1, "acciones": [ }')
    r = runner.invoke(app, ["--config", ruta, "validar"])
    assert r.exit_code == 3
    assert "no es JSON válido" in r.output
    assert SIN_TRACEBACK not in r.output


def test_accion_que_no_existe_sale_con_1(escribir_config, descargas):
    ruta = escribir_config(
        [{"nombre": "a", "descripcion": "x", "tipo": "copiar", "destino": "d"}]
    )
    r = runner.invoke(app, ["--config", ruta, "ejecutar", "inventada", str(descargas)])
    assert r.exit_code == 1
    assert SIN_TRACEBACK not in r.output


def test_opcion_que_no_existe_sale_con_2():
    r = runner.invoke(app, ["listar", "--inventada"])
    assert r.exit_code == 2


def test_sin_clave_sale_con_4_y_explica_que_sigue(escribir_config, tmp_path):
    # sin CENTRO_IA_KEY (aislado), una acción con IA legible debe salir con 4
    # humano y decir que lo demás sigue funcionando; nada de traceback.
    docs = tmp_path / "Apuntes"
    docs.mkdir()
    (docs / "tema-1.txt").write_text("La CPU ejecuta instrucciones. " * 20, encoding="utf-8")
    ruta = escribir_config(
        [{"nombre": "res", "descripcion": "x", "tipo": "resumir"}]
    )
    r = runner.invoke(app, ["--config", ruta, "ejecutar", "res", str(docs)])
    assert r.exit_code == 4
    assert SIN_TRACEBACK not in r.output
    assert "IA" in r.output
    # y con la misma config rota… las acciones SIN IA siguen con código 0
    ruta2 = escribir_config(
        [{"nombre": "c", "descripcion": "x", "tipo": "copiar",
          "destino": str(tmp_path / "destino")}]
    )
    r2 = runner.invoke(app, ["--config", ruta2, "ejecutar", "c", str(docs), "--si"])
    assert r2.exit_code == 0


def test_comprobar_ia_sin_clave_sale_con_4():
    r = runner.invoke(app, ["comprobar-ia"])
    assert r.exit_code == 4
    assert isinstance(r.exception, SystemExit)  # salida limpia, no un fallo
    assert "definida" in r.output  # dice si la clave está o no, sin enseñarla


def test_comprobar_ia_con_servidor_ok(monkeypatch):
    cuerpo = json.dumps(
        {"choices": [{"message": {"content": "OK"}}]}
    ).encode("utf-8")

    class RespFalsa:
        def __enter__(self):
            return io.BytesIO(cuerpo)

        def __exit__(self, *exc):
            return False

    monkeypatch.setenv("CENTRO_IA_URL", "https://falso.test/v1")
    monkeypatch.setenv("CENTRO_IA_KEY", "clave-de-prueba")
    monkeypatch.setattr(ia.urllib.request, "urlopen", lambda *a, **k: RespFalsa())
    r = runner.invoke(app, ["comprobar-ia"])
    assert r.exit_code == 0
    assert "la IA responde" in r.output
    assert "OK" in r.output
