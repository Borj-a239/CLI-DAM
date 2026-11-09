"""Pruebas de la capa IA con proveedor simulado (nunca toca la red)."""
from __future__ import annotations

import urllib.error

import pytest

from dam import ia
from dam.errores import DamError, IaError


class ProveedorFalso:
    def __init__(self, respuesta: str):
        self.respuesta = respuesta
        self.llamadas = 0

    def preguntar(self, prompt: str, max_tokens: int = 1024) -> str:
        self.llamadas += 1
        return self.respuesta


@pytest.fixture
def falso(monkeypatch):
    def _instalar(respuesta: str) -> ProveedorFalso:
        p = ProveedorFalso(respuesta)
        ia.set_proveedor(p)
        return p

    yield _instalar
    ia.set_proveedor(None)


def test_resumir_crea_markdown(tmp_path, falso):
    doc = tmp_path / "apuntes.md"
    doc.write_text("contido " * 50, encoding="utf-8")
    p = falso("- punto uno\n- punto dos")
    r = ia.resumir_fichero(doc, None, 200, False)
    assert r.estado == "hecho"
    assert r.destino.name == "apuntes-resumen.md"
    assert "punto uno" in r.destino.read_text(encoding="utf-8")
    assert p.llamadas == 1


def test_resumir_simular_no_llama_ni_escribe(tmp_path, falso):
    doc = tmp_path / "apuntes.md"
    doc.write_text("contido", encoding="utf-8")
    p = falso("x")
    r = ia.resumir_fichero(doc, None, 200, True)
    assert r.estado == "simulado"
    assert p.llamadas == 0
    assert list(tmp_path.glob("*-resumen.md")) == []


def test_sin_clave_mensaje_humano(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for var in ("CENTRO_IA_URL", "CENTRO_IA_KEY"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(IaError) as e:
        ia.ProveedorIA(env={}).preguntar("hola")
    assert ".env" in str(e.value)


def test_sin_red_mensaje_humano(monkeypatch):
    def boom(*a, **k):
        raise urllib.error.URLError("sin red")

    monkeypatch.setattr(ia.urllib.request, "urlopen", boom)
    prov = ia.ProveedorIA(env={"CENTRO_IA_URL": "https://x/v1", "CENTRO_IA_KEY": "k"})
    with pytest.raises(IaError) as e:
        prov.preguntar("hola")
    assert "conexión" in str(e.value)


def test_propuestas_sucias_se_sanean(falso):
    p = falso("1. Práctica CSS!!\n`practica-css.md`\nMUY importante: menú\nbasura!!!")
    props = ia.proponer_nombres("texto", ".md", 3)
    assert p.llamadas == 1
    assert props == ["practica-css.md", "muy-importante-menu.md", "basura.md"]


def test_renombrar_elige_primera_y_evita_colision(tmp_path, falso):
    doc = tmp_path / "IMG.txt"
    doc.write_text("apuntes de css", encoding="utf-8")
    (tmp_path / "css-basico.txt").write_text("x", encoding="utf-8")
    falso("css-basico.txt\notro-nombre.txt")
    r = ia.renombrar_fichero(doc, None, False, 2)
    assert r.destino.name == "css-basico (1).txt"
    assert r.destino.is_file()


def test_renombrar_opcion_personalizada(tmp_path, falso):
    doc = tmp_path / "doc.txt"
    doc.write_text("contenido del documento", encoding="utf-8")
    falso("uno.txt\ndos.txt")
    r = ia.renombrar_fichero(doc, lambda props, f: "mi-nombre.txt", False, 2)
    assert r.destino.name == "mi-nombre.txt"


def test_renombrar_mantener_nombre(tmp_path, falso):
    doc = tmp_path / "doc.txt"
    doc.write_text("contenido del documento", encoding="utf-8")
    falso("uno.txt\ndos.txt")
    r = ia.renombrar_fichero(doc, lambda props, f: None, False, 2)
    assert r.estado == "saltado"
    assert doc.exists()


def test_renombrar_simular_no_toca(tmp_path, falso):
    doc = tmp_path / "doc.txt"
    doc.write_text("contenido del documento", encoding="utf-8")
    falso("uno.txt\ndos.txt")
    r = ia.renombrar_fichero(doc, None, True, 2)
    assert r.estado == "simulado"
    assert "uno.txt" in r.mensaje
    assert doc.name == "doc.txt"


def test_formato_no_soportado_en_resumen(tmp_path, falso):
    doc = tmp_path / "informe.docx"
    doc.write_text("x", encoding="utf-8")
    falso("x")
    with pytest.raises(DamError):
        ia.resumir_fichero(doc, None, 200, False)
