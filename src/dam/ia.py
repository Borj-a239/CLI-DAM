"""Proveedor de IA del centro (API compatible con OpenAI) + motor de las
acciones `resumir` y `renombrar-ia`.

Reglas: la clave NUNCA está en el repo (variable de entorno o .env ignorado);
si no hay clave o no hay red, IaError con mensaje humano y el resto de dam
sigue funcionando sin IA.
"""
from __future__ import annotations

import json
import re
import ssl
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .acciones import Resultado, destino_libre
from .errores import DamError, IaError

DOC_EXT = (".pdf", ".txt", ".md", ".docx", ".odt")
MAX_CARACTERES = 1500


def _archivos_env() -> List[Path]:
    return [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path.home() / ".config" / "dam" / ".env",
    ]


def cargar_env() -> Dict[str, str]:
    """Lee los .env (sin pisar las variables del entorno)."""
    datos: Dict[str, str] = {}
    for ruta in _archivos_env():
        if not ruta.is_file():
            continue
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            datos[clave.strip()] = valor.strip().strip("\"'")
    return datos


def _env(clave: str, env: Optional[Dict[str, str]] = None) -> str:
    import os

    directo = os.environ.get(clave, "").strip()
    if directo:
        return directo
    return (env if env is not None else cargar_env()).get(clave, "").strip()


class ProveedorIA:
    """Cliente mínimo de la API de chat del centro."""

    def __init__(self, env: Optional[Dict[str, str]] = None):
        self.url = _env("CENTRO_IA_URL", env).rstrip("/")
        self.clave = _env("CENTRO_IA_KEY", env)
        self.modelo = _env("CENTRO_IA_MODEL", env) or "qwen3.8-flash-next"
        try:
            self.timeout = int(_env("CENTRO_IA_TIMEOUT", env) or 180)
        except ValueError:
            self.timeout = 180
        ca = _env("CENTRO_IA_CA", env)
        self.ca = Path(ca).expanduser() if ca else None

    def preguntar(self, prompt: str, max_tokens: int = 1024) -> str:
        if not self.url or not self.clave:
            raise IaError(
                "La IA no está configurada: escribe CENTRO_IA_URL y "
                "CENTRO_IA_KEY en ~/CLI/.env (mira .env.example). Sin IA "
                "puedes seguir usando todo lo demás."
            )
        peticion = urllib.request.Request(
            self.url + "/chat/completions",
            data=json.dumps(
                {
                    "model": self.modelo,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.clave}",
            },
        )
        contexto = (
            ssl.create_default_context(cafile=str(self.ca)) if self.ca else None
        )
        try:
            with urllib.request.urlopen(
                peticion, timeout=self.timeout, context=contexto
            ) as r:
                datos = json.load(r)
            return datos["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            raise IaError(
                f"El servidor del modelo ha contestido {e.code}. Revisa "
                "CENTRO_IA_URL / CENTRO_IA_KEY."
            )
        except TimeoutError:
            raise IaError(
                f"El modelo del centro está tardando más de {self.timeout} s. "
                "Insiste o prueba con un modelo más rápido (CENTRO_IA_MODEL)."
            )
        except (urllib.error.URLError, OSError, KeyError, IndexError,
                json.JSONDecodeError, ValueError):
            raise IaError(
                "No hay conexión con el modelo del centro. Sin IA puedes "
                "seguir usando el resto de dam: validar, go, start, ver…"
            )


_proveedor: Optional[ProveedorIA] = None


def proveedor() -> ProveedorIA:
    global _proveedor
    if _proveedor is None:
        _proveedor = ProveedorIA()
    return _proveedor


def set_proveedor(p: Optional[ProveedorIA]) -> None:
    """Inyección para tests (None vuelve al proveedor real)."""
    global _proveedor
    _proveedor = p


def leer_documento(fichero: Path) -> str:
    sufijo = fichero.suffix.lower()
    if sufijo == ".pdf":
        from .pdf import read_pdf

        return read_pdf(fichero)
    if sufijo in (".txt", ".md"):
        return fichero.read_text(encoding="utf-8", errors="replace")
    raise DamError(
        f"{fichero.name}: la IA solo lee .pdf, .txt y .md por ahora "
        f"(«{sufijo or 'sin ext'}» no)."
    )


def limpia_nombre(propuesta: str, ext: str) -> str:
    """Convierte la respuesta del modelo en un nombre de fichero seguro."""
    texto = propuesta.strip().strip("`\"'* ")
    texto = re.sub(r"^(?:\d+[\).\-\s]|[-—•·])+", "", texto)
    si_termina_en_ext = texto.lower().endswith(ext)
    if si_termina_en_ext:
        texto = texto[: -len(ext)]
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")[:60]
    if not texto:
        return ""
    return texto + ext


def resumir_texto(texto: str, max_palabras: int) -> str:
    return proveedor().preguntar(
        "Resume el siguiente documento en menos de "
        f"{max_palabras} palabras, en español, en viñetas claras. "
        "Devuelve SOLO el resumen, sin preámbulos.\n\n---\n"
        + texto[:4000]
    )


def proponer_nombres(texto: str, ext: str, opciones: int = 3) -> List[str]:
    respuesta = proveedor().preguntar(
        f"Un fichero «{ext}» empieza así:\n\n{texto[:MAX_CARACTERES]}\n\n"
        f"Propón {opciones} nombres de fichero para él, uno por línea, "
        f"acabados en «{ext}», en minúsculas y con guiones, que digan qué "
        "contiene. Sin numeración, comillas ni explicaciones."
    )
    propuestas: List[str] = []
    for linea in respuesta.splitlines():
        limpio = limpia_nombre(linea, ext)
        if limpio and limpio not in propuestas:
            propuestas.append(limpio)
    return propuestas[:opciones]


def resumir_fichero(
    fichero: Path,
    dest: Optional[Path],
    max_palabras: int = 200,
    simular: bool = False,
) -> Resultado:
    if not fichero.is_file():
        raise DamError(f"No encuentro {fichero}.")
    carpeta = (dest or fichero.parent).expanduser()
    destino = destino_libre(carpeta / f"{fichero.stem}-resumen.md")
    if simular:
        return Resultado(
            fichero,
            destino,
            "simulado",
            f"resumen de «{fichero.name}» (no se ha llamado al modelo)",
        )
    texto = leer_documento(fichero)
    if not texto.strip():
        raise DamError(f"«{fichero.name}» está vacío, no hay nada que resumir.")
    resumen = resumir_texto(texto, max_palabras)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        f"# Resumen de {fichero.name}\n\n{resumen}\n", encoding="utf-8"
    )
    return Resultado(
        fichero, destino, "hecho", f"{len(resumen.split())} palabras"
    )


def renombrar_fichero(
    fichero: Path,
    elegir: Optional[Callable[[List[str], Path], Optional[str]]] = None,
    simular: bool = False,
    opciones: int = 3,
) -> Resultado:
    if not fichero.is_file():
        raise DamError(f"No encuentro {fichero}.")
    texto = ""
    try:
        texto = leer_documento(fichero)
    except DamError:
        pass
    if not texto.strip():
        return Resultado(fichero, None, "saltado", "sin texto legible que leer")
    propuestas = proponer_nombres(texto, fichero.suffix.lower(), opciones)
    propuestas = [p for p in propuestas if p != fichero.name]
    if not propuestas:
        return Resultado(
            fichero, None, "saltado", "el modelo no ha propuesto nombres válidos"
        )
    if simular:
        return Resultado(
            fichero, Path(propuestas[0]), "simulado",
            "propuestas: " + " | ".join(propuestas),
        )
    elegido = elegir(propuestas, fichero) if elegir else propuestas[0]
    if elegido is None:
        return Resultado(fichero, None, "saltado", "mantienes el nombre")
    destino = destino_libre(fichero.with_name(elegido))
    fichero.rename(destino)
    return Resultado(fichero, destino, "hecho", f"nombre elegido: {elegido}")
