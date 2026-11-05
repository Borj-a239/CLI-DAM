# dam · CLI de ficheros para 1º DAM (proyecto 2 · CLI-DAM)

## Stack y órdenes

- Python 3.12 + Typer + Rich, gestionado con uv (src layout, paquete src/dam).
- Ejecutar: `uv run dam --help` · Validar config: `uv run dam validar` ·
  Acciones: `uv run dam acciones` · Pruebas: `uv run pytest`.

## Normas

- Mensajes y comentarios en español; código claro antes que listo.
- pathlib siempre, encoding="utf-8", nada de os.system ni shell=True: tiene que
  funcionar en Linux, Windows y macOS.
- Nunca ejecutes acciones sobre carpetas reales: solo en ~/pruebas-tareas y con
  --simular. Los comandos `dam ejecutar` los lanza el alumno, nunca tú.
- No toques .env ni escribas claves en ningún fichero. No hagas git push ni
  commits: los hace el alumno.
- Antes de cambiar un fichero, explica en 2-3 líneas qué vas a hacer.
- Las acciones viven en acciones.json (esquema en el README y en la skill
  acciones-json); añadirlas no exige tocar el código salvo tipos nuevos.
