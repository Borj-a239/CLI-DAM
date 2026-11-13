# Cambios

Formato inspirado en *Keep a Changelog*; los números siguen
[SemVer](https://semver.org/lang/es/) (`mayor.menor.parche`).

## [Unreleased]

_Nada pendiente._

## [1.1.0] — 2026-11-13

### Añadido

- **Capa de IA** (`src/dam/ia.py`): acciones `resumir` y `renombrar-ia` que
  hablan con el modelo del centro (API compatible con OpenAI). Único punto de
  red del proyecto; con inyección de proveedor para los tests.
- **Comandos directos** `dam resumir ARCHIVO` y `dam renombrar ARCHIVO`, con
  propuesta de nombres (opciones `1/2/3`), `--simular`, `--si` y selector
  interactivo. Completado Tab para rutas (`--install-completion`).
- **Configuración de la IA** por variables de entorno o `.env` (ignorado en
  git): `CENTRO_IA_URL`, `CENTRO_IA_KEY`, `CENTRO_IA_MODEL`, `CENTRO_IA_CA` y
  `CENTRO_IA_TIMEOUT` (180 s por defecto, configurable).
- **Modo sin red**: si no hay clave o no hay conexión, `IaError` con mensaje
  humano (código de salida 1, sin traceback) y todo lo demás sigue funcionando.
- **Asserts de desarrollo**: invariantes en config, motor, acciones e IA
  (estados posibles, fábrica del registro, nombres sin rutas, acciones sin
  duplicados).
- Dos acciones más en `acciones.json`: `resumir-apuntes` y
  `renombrar-por-contenido`. Tests de IA con proveedor simulado.

### Arreglado

- `dam --version` funciona ya sin suborden (flag *eager* con su callback).

## [1.0.0] — 2026-11-06

- Base del proyecto: CLI con Typer + Rich, configuración externa validada
  (`acciones.json` + ADR 0001), motor en clases con fábrica por registro.
- Filtros (extensiones, patrón, antigüedad, tamaño, recursivo) y acciones
  `mover`, `copiar`, `renombrar`, `borrar`, `revisar`.
- Excepciones propias con códigos de salida 0/1/2/3; `--simular` que no toca
  disco; nunca sobrescribe (sufijo `(1)`).
- Navegación (`go`, `start`, `ver`, `last`, `edit`, `conf`) con wrapper
  `dam.bash` para el `cd` real.
- Instalación con una orden (`uv tool install`), suite de tests (pytest) y CI
  en las tres plataformas.
