# Cambios

Formato inspirado en *Keep a Changelog*; los números siguen
[SemVer](https://semver.org/lang/es/) (`mayor.menor.parche`).

## [1.2.0] — 2026-11-13

### Añadido

- **`dam comprobar-ia`**: dice de golpe si la IA del centro responde (servidor,
  modelo y si la clave está definida, sin enseñarla). Sale con 4 si no.
- **Caja de arena en las pruebas** (`tests/conftest.py`): la fixture `aislado`
  (autouse) encierra cada prueba en una carpeta temporal sin red ni IA, y
  `tests/test_cli.py` prueba la CLI desde fuera con `CliRunner` (un código de
  salida por caso, sin trazas).
- **`scripts/revisar.sh`**: el subagente revisor (`opencode run`) mira el
  `git add` antes de commitear, sin abrir la interfaz.
- **ADR-0002** sobre por qué la IA va detrás de una interfaz `ProveedorIA`.

### Cambiado

- Sin IA (falta de clave, sin red o servidor caído) ahora **sale con código 4**
  (antes 1), para distinguirlo de un fallo normal; las acciones sin IA siguen
  saliendo con 0.

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
