"""Pruebas end-to-end del CLI `dam` sin dependencias externas.

Ejecutar desde la raíz del repo:
    python3 -m tests.test_dam          # o: python3 tests/test_dam.py
Usar HOME y roots temporales; genera los PDFs de prueba con el mini-generador
y comprueba los criterios de aceptación del proyecto.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dam.cli import main  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
import make_test_pdfs  # noqa: E402


def run_dam(argv: List[str]) -> Tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class DamTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.home.mkdir()
        self.root = base / "DAM"
        (self.root / "ASIX" / "UD03" / "herencia").mkdir(parents=True)
        (self.root / "DM" / "apuntes").mkdir(parents=True)
        (self.root / "lee.txt").write_text("hola\n")
        (self.root / "ASIX" / "UD03" / "herencia" / "Ejemplo.java").write_text("x\n")
        self.extra = base / "Descargas"
        self.extra.mkdir()
        (self.home / ".damrc").write_text(
            f"roots = {self.root}\nautor = Ada Lovelace\neditor = code\n"
        )
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.home)

        self.pdfs = base / "pdfs"
        make_test_pdfs.main([str(self.pdfs)])

    def tearDown(self) -> None:
        os.environ["HOME"] = self._old_home or "/home/tester"
        self.tmp.cleanup()

    # ------------------------------------------------------------- go / last
    def test_go_busca_en_roots(self) -> None:
        code, out, _ = run_dam(["go", "herencia", "--print-fast"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), str((self.root / "ASIX" / "UD03" / "herencia").resolve()))

    def test_go_sin_resultado_no_peta(self) -> None:
        code, out, err = run_dam(["go", "esto-no-existe-zzz", "--print-fast"])
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)
        self.assertEqual(out, "")

    def test_go_con_ruta_extra_ignora_roots(self) -> None:
        (self.extra / "apuntes-herencia").mkdir()
        code, out, _ = run_dam(
            ["go", "herencia", str(self.extra), "--print-fast"]
        )
        self.assertEqual(code, 0)
        self.assertTrue(out.strip().startswith(str(self.extra.resolve())))

    def test_go_punto_desde_cwd(self) -> None:
        old_cwd = os.getcwd()
        os.chdir(self.root / "ASIX")
        try:
            code, out, _ = run_dam(["go", ".", "--print-fast"])
            self.assertEqual(code, 0)
            self.assertTrue(Path(out.strip()).is_dir())
        finally:
            os.chdir(old_cwd)

    def test_go_tri_un_fitxer_torna_la_seva_carpete(self) -> None:
        code, out, _ = run_dam(["go", "Ejemplo.java", "--print-fast"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), str((self.root / "ASIX" / "UD03" / "herencia").resolve()))

    def test_last_imprimeix_historial(self) -> None:
        run_dam(["go", "herencia", "--print-fast"])
        run_dam(["go", "apuntes", "--print-fast"])
        code, out, _ = run_dam(["last"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), str((self.root / "ASIX" / "UD03" / "herencia").resolve()))
        code, out, _ = run_dam(["last", "0"])
        self.assertEqual(out.strip(), str((self.root / "DM" / "apuntes").resolve()))

    def test_last_buit_no_peta(self) -> None:
        code, out, err = run_dam(["last"])
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)

    # ------------------------------------------------------------------ ver
    def test_ver_oculta_brossa_i_ocultes(self) -> None:
        junk = self.root / "node_modules" / "paquet"
        junk.mkdir(parents=True)
        (self.root / ".gitignore").write_text("x\n")
        (self.root / "visible.txt").write_text("x\n")
        old_cwd = os.getcwd()
        os.chdir(self.root)
        try:
            code, out, _ = run_dam(["ver"])
            self.assertEqual(code, 0)
            self.assertNotIn("node_modules", out)
            self.assertNotIn(".gitignore", out)
            self.assertIn("visible.txt", out)

            code, out, _ = run_dam(["ver", "-a"])
            self.assertIn(".gitignore", out)

            code, out, _ = run_dam(["ver", "--build"])
            self.assertIn("node_modules", out)

            code, out, _ = run_dam(["ver", "--depth", "1"])
            self.assertNotIn("UD03", out)
        finally:
            os.chdir(old_cwd)

    # --------------------------------------------------------------- start
    def test_start_qüestionari_txt(self) -> None:
        code, out, err = run_dam(
            ["start", str(self.pdfs / "cuestionario_tema4.pdf"),
             "--dest", str(self.root / "ASIX" / "UD04" / "cuestionario")]
        )
        self.assertEqual(code, 0, msg=err)
        dest = self.root / "ASIX" / "UD04" / "cuestionario"
        readme = (dest / "README.md").read_text(encoding="utf-8")
        self.assertIn("Ada Lovelace", readme)
        txt = next(dest.glob("*.cuestionario.txt"), None)
        if txt is None:
            docx = next(dest.glob("*.docx"), None)
            self.assertIsNotNone(docx, "sin docx ni txt")
            return
        body = txt.read_text(encoding="utf-8")
        self.assertIn("1. Que es el polimorfismo?", body)
        self.assertIn("5. Que ventajas aporta una interface?", body)
        self.assertIn("Ada Lovelace", body)
        for line in body.splitlines():
            self.assertNotIn("TODO: resolver", line)

    def test_start_php_fallback(self) -> None:
        code, out, err = run_dam(
            ["start", str(self.pdfs / "php_formularios.pdf"),
             "--dest", str(self.root / "DM" / "p8")]
        )
        self.assertEqual(code, 0, msg=err)
        php = (self.root / "DM" / "p8" / "practica8.php").read_text(encoding="utf-8")
        self.assertIn("<?php", php)
        self.assertIn("Ada Lovelace", php)
        self.assertNotIn("echo", php)

    def test_start_web(self) -> None:
        code, out, err = run_dam(
            ["start", str(self.pdfs / "practica_web.pdf"),
             "--dest", str(self.root / "DM" / "web")]
        )
        self.assertEqual(code, 0, msg=err)
        web = self.root / "DM" / "web"
        html = (web / "index.html").read_text(encoding="utf-8")
        for tag in ("<header>", "<nav>", "<main>", "<footer>"):
            self.assertIn(tag, html)
        self.assertTrue((web / "css" / "estilos.css").is_file())

    def test_start_no_sobreescriveix_sense_forcar(self) -> None:
        dest = self.root / "DM" / "p8"
        dest.mkdir(parents=True)
        (dest / "practica8.php").write_text("MI CÓDIGO REAL\n")
        code, out, err = run_dam(
            ["start", str(self.pdfs / "php_formularios.pdf"), "--dest", str(dest)]
        )
        self.assertEqual(code, 0, msg=err)
        self.assertEqual((dest / "practica8.php").read_text(), "MI CÓDIGO REAL\n")

    def test_start_odb_via_base_de_dades(self) -> None:
        from dam.templates.data import write_odb

        odb_path = self.root / "odb" / "base.odb"
        write_odb(odb_path, {"Clientes": ["id", "nombre"]}, "Ada")
        with zipfile.ZipFile(odb_path) as archive:
            self.assertEqual(
                archive.read("mimetype"),
                b"application/vnd.oasis.opendocument.database",
            )
            content = archive.read("content.xml").decode("utf-8")
        self.assertIn("<office:database>", content)
        self.assertIn('table:name="Clientes"', content)

    # ------------------------------------------------------------------ conf
    def test_conf_i_help(self) -> None:
        code, out, _ = run_dam(["conf"])
        self.assertEqual(code, 0)
        self.assertIn("roots", out)
        code, out, _ = run_dam(["--help"])
        for command in ("go", "start", "ver", "last"):
            self.assertIn(command, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
