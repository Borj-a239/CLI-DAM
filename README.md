# dam

Asistente de navegación y plantillas de prácticas para 1º DAM.
**No resuelve nada**: solo te mueve por el disco y monta la estructura vacía
que toca según el PDF del enunciado.

## Qué hace (y qué no)

| Comando | Para qué |
|---|---|
| `dam go <texto> [rutas…]` | Busca y (vía wrapper) **hace `cd` real** a la carpeta elegida |
| `dam start <pdf>` | Lee el PDF y crea la **plantilla vacía** del tipo detectado |
| `dam ver` | Árbol de la carpeta actual, ocultando basura de build |
| `dam last [N]` | `cd` real a una ruta del historial |
| `dam edit [ruta]` | Abre el editor del config donde estés |
| `dam conf` | Muestra/abre `~/.damrc` |

Prohibiciones que cumple: cero lógica de soluciones, cero borrar sin preguntar,
cero rutas hardcodeadas (todo desde `~/.damrc`).

## Instalación

```bash
cd dam-cli
python3 -m pip install -r requirements.txt   # pdfplumber, python-docx, odfpy, prompt_toolkit, pypdf
python3 -m pip install .                     # crea el binario interno `_dam`
```

Y **esto es lo importante**: un proceso hijo no puede hacer `cd` a tu shell,
así que añade a tu `~/.bashrc` la función wrapper (o `source` el fichero):

```bash
source /ruta/al/repo/dam.bash
```

Que por dentro es exactamente esto:

```bash
dam() {
    if [ "$1" = "go" ] || [ "$1" = "last" ]; then
        local r
        r=$(_dam "$@") && [ -n "$r" ] && cd "$r"
    else
        _dam "$@"
    fi
}
```

El binario real (`_dam`) solo imprime la ruta elegida por stdout; el wrapper
la lee y hace el `cd` **en tu terminal**. `go`/`last` imprimen solo la ruta;
el selector interactivo va por stderr, así que lo ves igual.

Sin pip a mano, puedes usarlo del repo directamente: `python3 dam.py …`.

## Configuración — `~/.damrc`

```ini
roots = ~/DAM, ~/Uni, ~/Proyectos   # lista, sin límite
autor = Mi Nombre
editor = code
```

- Si `dam go` recibe rutas como argumentos, **ignora el config** y busca solo
  en esas (más lo que se le añada con `.`).
- Estado en `~/.dam/`: `state.json` (historial) y `cache/<hash>.json`
  (índices perezosos; `--reindex` los refuerza).

## Comandos

### `dam go <texto> [rutas…]`

```bash
dam go herencia                # busca por las roots del config
dam go .                       # busca desde la carpeta actual
dam go herencia ~/Descargas    # busca en ~/Descargas aunque no esté en el config
dam go pdf --reindex           # fuerza a rehacer el índice
```

Selector interactivo: escribe y verás coincidencias (prompt_toolkit →
fzf → lista numerada). Acentos y mayúsculas dan igual. Si eliges un fichero,
el `cd` va a su carpeta. El historial alimenta `last`.

### `dam start <pdf> [--dest asignatura/practica]`

Detección en dos capas:

1. **Diccionario editable** (`dam/detection/keywords.py`) → plantilla rica:
   - cuestionario → `.docx`/`.odt` con las preguntas **tal cual** y hueco bajo
     cada una (sin respuestas);
   - html/css → `index.html` con `<header><nav><main><footer>` + `css/estilos.css`;
   - sql → `.sql` con `CREATE TABLE` detectados (cuerpo vacío) y los `SELECT`
     como **comentario**;
   - js → `.js` con firmas de funciones y cuerpo `// TODO`;
   - java → `src/main/java/<paquete>/` con clases, atributos `private` y
     métodos `// TODO` (package deducido de la ruta o del PDF);
   - calc → `.ods` con hoja y cabeceras detectadas;
   - base → `.odb` con tablas y columnas.
2. **Fallback regex `\.(\w+)`** sobre el texto: si el PDF menciona `.php`,
   `.py`, `.c`… se crea el fichero **vacío con cabecera de autor** (usa el
   nombre explícito del PDF si aparece, ej. `practica8.php`).

```bash
dam start ~/Descargas/practica8.pdf --dest DAM/DM/p8
dam start cuestionario_tema4.pdf          # destino deducido del nombre
```

Nunca sobreescribe sin preguntar (sin TTY conserva el existente). Crea siempre
`README.md` con título y asignatura, y mete `autor` en cada cabecera.

### `dam ver [--depth N] [-a|--all] [--build]`

```bash
dam ver                # árbol limpio
dam ver -a             # con ocultos (.gitignore, .git…)
dam ver --build        # con node_modules/, dist/, __pycache__/, target/…
dam ver --depth 2      # solo dos niveles
```

### `dam last [N]`

`dam last` → la anterior a la actual; `dam last 0` → la última; `dam last 3` →
cuatro visitas atrás.

## Estructura del repo

```
dam/                    paquete Python (el binario es _dam → dam.cli:main)
├── cli.py              argparse, ayuda en español
├── commands/nav.py     go / last / edit / conf
├── commands/start.py   start
├── commands/ver.py     ver
├── config.py           parser de ~/.damrc
├── state.py            historial ~/.dam/state.json
├── index.py            índice perezoso + caché ~/.dam/cache
├── search.py           ranking de coincidencias
├── selector.py         prompt_toolkit → fzf → lista numerada
├── pdf.py              lectura PDF: pdfplumber → pypdf → minipdf
├── minipdf.py          parser PDF propio (sin dependencias, solo detección)
├── detection/keywords.py   ← DICCIONARIO EDITABLE de palabras clave
├── detection/detector.py   señales (preguntas, tablas, funciones, clases…)
└── templates/          plain, web, documents, data, code
dam.bash                wrapper para tu ~/.bashrc
tests/make_test_pdfs.py generador de PDFs de prueba (sin librerías)
tests/test_dam.py       14 tests end-to-end
```

## Probar

```bash
python3 -m tests.test_dam          # todo verde sin instalar nada
python3 tests/make_test_pdfs.py /tmp/pdfs && _dam start /tmp/pdfs/practica_web.pdf --dest /tmp/web
```
