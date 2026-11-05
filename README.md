# dam

[![pruebas](https://github.com/Borj-a239/CLI-DAM/actions/workflows/ci.yml/badge.svg)](https://github.com/Borj-a239/CLI-DAM/actions/workflows/ci.yml)

CLI de terminal para estudiantes de 1º DAM: **navega** por tus carpetas de estudio,
**monta la plantilla vacía** que toca a partir de un PDF de enunciado y **ejecuta
acciones sobre tus ficheros** que defines tú en `acciones.json`, sin tocar código.

Nunca resuelve nada: preguntas literales, firmas sin cuerpo, ficheros vacíos.

## Spec (versión 1 · 05/11/2026)

1. **Problema:** pierdo tiempo buscando apuntes entre carpetas, montando desde cero
   la estructura de cada práctica a partir del PDF y comprobando a ojo qué ficheros
   están sin acabar.
2. **Para quién:** para mí y para mi clase de DAM.
3. **Cómo se usa:** `dam ORDEN [CARPETA] [opciones]` desde cualquier terminal.
4. **Órdenes:** `--help`, `version`, `listar`, `acciones`, `validar`, `ejecutar`,
   más `go`, `start`, `ver`, `last`, `edit` y `conf`.
5. **Mis 3 acciones:** `copia-apuntes`, `renombrar-fotos`, `revisar-documentos`.
6. **Nunca hará:** borrar sin preguntar, sobrescribir ficheros, ni tocar rutas
   distintas de las que le indiques; y no genera soluciones, solo estructuras vacías.
7. **Plataformas:** Linux primero; también Windows y macOS (pathlib, utf-8, sin
   `os.system` ni `shell=True`).
8. **Códigos de salida:** 0 bien · 1 fallo al ejecutar · 2 error de uso (Typer) ·
   3 configuración inválida.
9. **Instalación:** `uv tool install git+https://github.com/Borj-a239/CLI-DAM`.
10. **Simulación:** toda acción se prueba antes con `--simular`.

## Instalación

Necesitas [uv](https://docs.astral.sh/uv/) (o `pipx` en su lugar).

```bash
uv tool install git+https://github.com/Borj-a239/CLI-DAM
dam --help && dam version
```

Modo desarrollo (cambios al instante, desde la carpeta del repo):

```bash
uv tool install --editable .
```

**Opcional Linux/macOS — `cd` real:** `dam go` y `dam last` imprimen la ruta por
stdout; añade a tu `~/.bashrc` la función de [`dam.bash`](dam.bash) para que el
shell haga el `cd` de verdad:

```bash
source /ruta/al/repo/dam.bash
```

Desinstalar: `uv tool uninstall dam`.

## Configuración

- `~/.damrc` — raíces de búsqueda, autor y editor (`roots = ~/DAM, ...`,
  `autor = ...`, `editor = code`). Se crea sola la primera vez.
- `acciones.json` — **tus acciones**, en la carpeta donde lanzas la orden (o donde
  diga `--config RUTA`, que va siempre antes de la orden).
- `~/.dam/` — historial (`state.json`) y caché de índices.

## Órdenes

| Orden | Qué hace |
|---|---|
| `dam --help` / `dam version` | ayuda y versión |
| `dam listar [CARPETA] [--json]` | tabla nombre/tipo/tamaño/fecha |
| `dam acciones` | lista las acciones de acciones.json |
| `dam validar` | comprueba acciones.json (sale con 3 si falla) |
| `dam ejecutar NOMBRE [CARPETA] --simular / --si` | aplica una acción |
| `dam go TEXTO [RUTAS…] [--reindex] [--print-fast]` | busca y (con wrapper) hace cd |
| `dam start PDF [--dest A/P] [--odt] [--force]` | plantilla vacía desde el enunciado |
| `dam ver [-a] [--build] [--depth N]` | árbol de la carpeta actual |
| `dam last [N]` · `dam edit [RUTA]` · `dam conf [-e]` | historial y editor |

```bash
dam --config ~/mis-acciones.json acciones       # opción global: antes de la orden
dam ejecutar copia-apuntes --simular            # enseña qué haría, sin tocar nada
dam ejecutar renombrar-fotos ~/Descargas        # pregunta si es destructiva
dam ejecutar revisar-documentos --si            # para scripts: sin preguntar
```

## Esquema de `acciones.json`

```json
{ "version": 1, "acciones": [ { "nombre": "…", "descripcion": "…", "tipo": "…" } ] }
```

| Campo | Obligatorio | Qué significa |
|---|---|---|
| `nombre` | sí | lo que tecleas en `dam ejecutar`; único, minúsculas y guiones |
| `descripcion` | sí | la que enseña `dam acciones` |
| `tipo` | sí | `mover` · `copiar` · `renombrar` · `borrar` · `revisar` |
| `origen` | no | carpeta por defecto; admite `~` |
| `destino` | mover/copiar | adónde van (se crea si no existe) |
| `plantilla` | renombrar | huecos: `{fecha:%Y-%m-%d}`, `{n:03}`, `{ext}`, `{nombre}` |
| `confirmar` | borrar: `true` | pregunta antes de borrar salvo `--si` |
| `min_palabras` | revisar (def. 150) | por debajo de eso, avisa «posiblemente inacabado» |

`filtro` (objeto, opcional — los ficheros deben cumplir **todos** lo que pongas):

| Filtro | Ejemplo |
|---|---|
| `extensiones` | `[".pdf", ".docx"]` (en minúsculas, `FOTO.JPG` también vale) |
| `patron` | `"^(IMG\|PXL)_"` (regex sobre el nombre; en JSON, `\\.`) |
| `mas_antiguo_que_dias` | `30` |
| `mas_reciente_que_dias` | `7` |
| `mayor_que_mb` | `100` |
| `recursivo` | `true` (incluye subcarpetas) |

La acción `revisar` lee el contenido (`.txt/.md/.pdf`), nunca modifica nada y
avisa de: fichero vacío, menos de `min_palabras` palabras, marcas como
«pendiente/TODO/borrador» o texto que no acaba en puntuación.

Añadir una acción **no exige tocar el código** (los tipos nuevos sí: una subclase
en `src/dam/acciones.py`, ver `docs/adr/0001-configuracion-externa.md`).

## Estructura

```
src/dam/
├─ cli.py          interfaz Typer (la única que habla contigo)
├─ errores.py      DamError (1) · ConfigError (3) · AccionNoValida
├─ config.py       carga y valida acciones.json ANTES de tocar disco
├─ motor.py        Motor: filtro de ficheros + delegación
├─ acciones.py     clases Accion (fábrica por registro, sin ifs por tipo)
├─ damrc.py        lectura de ~/.damrc
├─ commands/       go/last/edit/conf · start · ver
├─ detection/      detector del PDF + keywords.py editable
├─ templates/      generadores de plantillas vacías
└─ minipdf.py      generador PDF propio (sin dependencias)
```

## Probar

```bash
uv run pytest                      # pruebas completas, en carpetas temporales
uv run python -m tests.test_dam    # suite histórica
```

Prueba **siempre** en una carpeta de pruebas (`~/pruebas-tareas`) y con
`--simular` antes de dejar que una acción toque tus ficheros reales.
