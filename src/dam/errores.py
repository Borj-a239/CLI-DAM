"""Excepciones propias de dam: errores previsibles con código de salida."""
from __future__ import annotations


class DamError(Exception):
    """Base de todos los errores previsibles de la herramienta."""

    codigo_salida = 1


class ConfigError(DamError):
    """acciones.json no existe, no es JSON o no cumple el esquema."""

    codigo_salida = 3


class AccionNoValida(ConfigError):
    """Una acción concreta tiene un campo mal: dice cuál y por qué."""

    def __init__(self, accion: str, campo: str, motivo: str):
        super().__init__(f"Acción «{accion}», campo «{campo}»: {motivo}")
        self.accion = accion
        self.campo = campo


class IaError(DamError):
    """La IA no está configurada o no hay conexión: mensaje humano, código 1."""
