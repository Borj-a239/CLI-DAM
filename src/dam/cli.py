"""Punto de entrada interno del CLI: `_dam` (el wrapper `dam` vive en dam.bash)."""
from __future__ import annotations

from datetime import datetime
from json import dumps
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

import typer
from rich import markup
from rich.console import Console
from rich.table import Table

from . import __version__
from . import config as acciones_loader
from .commands import nav as cmd_nav
from .commands import start as cmd_start
from .commands import ver as cmd_ver
from .damrc import ensure_config, load_config
from .errores import DamError
from .motor import Motor
from .util import err

app = typer.Typer(
    name="dam",
    help=(
        "dam — navegación, plantillas y acciones con ficheros para 1º DAM.\n"
        "Solo navega, monta estructuras vacías y aplica tus acciones; "
        "nunca resuelve nada."
    ),
    add_completion=False,
    no_args_is_help=True,
)

consola = Console()
consola_err = Console(stderr=True)


def _tamano(n: float) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.0f} B"


def _lanzar(comando, cfg, **kw) -> None:
    """Delega en el comando heredero (argparse) con su Namespace."""
    try:
        codigo = comando.run(SimpleNamespace(**kw), cfg)
    except KeyboardInterrupt:
        err("cancelado.", code=130)
        raise typer.Exit(130)
    raise typer.Exit(codigo)


def _motor(ctx: typer.Context) -> Motor:
    try:
        return Motor(acciones_loader.cargar(ctx.obj))
    except DamError as e:
        consola_err.print(f"[red]✘ {e}[/red]")
        raise typer.Exit(e.codigo_salida)


def _captura_dam(e: DamError) -> None:
    consola_err.print(f"[red]✘ {e}[/red]")
    raise typer.Exit(e.codigo_salida)


@app.callback()
def principal(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("acciones.json"),
        "--config",
        help="ruta del fichero de acciones (por defecto ./acciones.json)",
    ),
    version: bool = typer.Option(
        False, "--version", help="muestra la versión y sale", is_eager=True
    ),
) -> None:
    """dam: tus acciones se escriben en acciones.json, no en el código."""
    if version:
        consola.print(f"dam {__version__}")
        raise typer.Exit()
    ensure_config()
    ctx.obj = config.expanduser()


@app.command()
def version() -> None:
    """Muestra la versión instalada."""
    consola.print(f"dam {__version__}")


@app.command()
def go(
    texto: str = typer.Argument(
        ..., help="texto a buscar; '.' o '' = carpeta actual"
    ),
    rutas: Optional[List[str]] = typer.Argument(
        None, help="rutas extra donde buscar; si pasas alguna, el config se ignora"
    ),
    reindex: bool = typer.Option(
        False, "--reindex", help="descarta la caché y recorre el disco de nuevo"
    ),
    print_fast: bool = typer.Option(
        False, "--print-fast", help="sin interactivo: imprime el mejor resultado"
    ),
) -> None:
    """Busca un fichero o carpetas y (vía wrapper) hace cd real allí."""
    _lanzar(
        cmd_nav.GoCommand,
        load_config(),
        text=texto,
        paths=list(rutas or []),
        reindex=reindex,
        print_fast=print_fast,
    )


@app.command()
def last(n: int = typer.Argument(1, help="posiciones hacia atrás (0 = la última)")) -> None:
    """Vuelve a una ruta del historial (cd real vía wrapper)."""
    _lanzar(cmd_nav.LastCommand, load_config(), n=n)


@app.command()
def edit(path: str = typer.Argument(".", help="carpeta a abrir en el editor")) -> None:
    """Abre el editor del config en la carpeta actual (o la que digas)."""
    _lanzar(cmd_nav.EditorCommand, load_config(), path=path)


@app.command()
def conf(
    editar: bool = typer.Option(False, "-e", "--editar", help="abre ~/.damrc"),
) -> None:
    """Muestra (o abre) la configuración ~/.damrc."""
    _lanzar(cmd_nav.ConfigCommand, load_config(), editar=editar)


@app.command()
def ver(
    path: str = typer.Argument(".", help="carpeta a mostrar"),
    all: bool = typer.Option(False, "-a", "--all", help="ocultos y basura de build"),
    build: bool = typer.Option(False, "--build", help="incluye node_modules, dist…"),
    depth: Optional[int] = typer.Option(None, "--depth", help="límite de niveles"),
) -> None:
    """Muestra el árbol de la carpeta actual (solo lectura, sin cd)."""
    _lanzar(
        cmd_ver.VerCommand,
        load_config(),
        path=path,
        all=all,
        build=build,
        depth=depth,
    )


@app.command()
def start(
    pdf: str = typer.Argument(..., help="ruta al PDF del enunciado"),
    asignatura: Optional[str] = typer.Option(None, help="asignatura para el README"),
    dest: Optional[str] = typer.Option(
        None, help="destino ASIGNATURA/PRACTICA (o absoluto)"
    ),
    force: bool = typer.Option(
        False, "--force", help="no pregunta: reescribe ficheros existentes"
    ),
    odt: bool = typer.Option(False, "--odt", help="genera también el .odt"),
) -> None:
    """Lee un PDF de enunciado y crea la plantilla vacía que toca."""
    _lanzar(
        cmd_start.StartCommand,
        load_config(),
        pdf=pdf,
        asignatura=asignatura,
        dest=dest,
        force=force,
        odt=odt,
    )


@app.command()
def listar(
    carpeta: Optional[Path] = typer.Argument(None, help="por defecto, la actual"),
    json_salida: bool = typer.Option(False, "--json", help="salida para máquinas"),
) -> None:
    """Tabla con nombre, tipo, tamaño y fecha de cada fichero."""
    ruta = (carpeta or Path(".")).expanduser()
    if not ruta.is_dir():
        consola_err.print(f"[red]✘ {ruta} no es una carpeta[/red]")
        raise typer.Exit(1)
    try:
        entradas = sorted(
            ruta.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        )
    except OSError as e:
        consola_err.print(f"[red]✘ no se puede leer {ruta}: {e}[/red]")
        raise typer.Exit(1)
    if json_salida:
        datos = []
        for p in entradas:
            try:
                st = p.stat()
            except OSError:
                continue
            datos.append(
                {
                    "nombre": p.name,
                    "tipo": "carpeta" if p.is_dir() else p.suffix.lower().lstrip("."),
                    "tamano": None if p.is_dir() else st.st_size,
                    "modificado": datetime.fromtimestamp(st.st_mtime).isoformat(
                        timespec="minutes"
                    ),
                }
            )
        typer.echo(dumps(datos, ensure_ascii=False))
        return
    if not entradas:
        consola.print(f"[yellow]Aviso: {ruta} está vacía.[/yellow]")
        return
    tabla = Table(title=str(ruta), title_style="bold")
    for columna in ("Nombre", "Tipo", "Tamaño", "Modificado"):
        tabla.add_column(columna)
    for p in entradas:
        try:
            st = p.stat()
        except OSError:
            continue
        tipo = "carpeta" if p.is_dir() else (p.suffix.lower().lstrip(".") or "sin ext")
        tabla.add_row(
            markup.escape(p.name),
            tipo,
            "—" if p.is_dir() else _tamano(st.st_size),
            datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
        )
    consola.print(tabla)


@app.command()
def acciones(ctx: typer.Context) -> None:
    """Lista las acciones definidas en acciones.json."""
    motor = _motor(ctx)
    tabla = Table(title=str(ctx.obj), title_style="bold")
    for columna in ("Nombre", "Tipo", "Descripción"):
        tabla.add_column(columna)
    for a in motor.acciones.values():
        tabla.add_row(a.nombre, a.tipo, markup.escape(a.descripcion))
    consola.print(tabla)


@app.command()
def validar(ctx: typer.Context) -> None:
    """Comprueba acciones.json y dice exactamente qué campo falla."""
    try:
        n = len(acciones_loader.cargar(ctx.obj))
    except DamError as e:
        _captura_dam(e)
    consola.print(f"[green]✔ {n} acciones válidas[/green]")


@app.command()
def ejecutar(
    ctx: typer.Context,
    nombre: str = typer.Argument(..., help="nombre de la acción (ver: dam acciones)"),
    carpeta: Optional[Path] = typer.Argument(None, help="carpeta sobre la que actuar"),
    simular: bool = typer.Option(
        False, "--simular", help="enseña qué haría sin tocar nada"
    ),
    si: bool = typer.Option(False, "--si", help="no pedir confirmación"),
) -> None:
    """Aplica una acción de acciones.json sobre una carpeta."""
    motor = _motor(ctx)
    try:
        accion = motor.accion(nombre)
        if accion.destructiva and not simular and not si:
            typer.confirm(f"«{nombre}» borra ficheros. ¿Seguro?", abort=True)
        resultados = motor.ejecutar(nombre, carpeta, simular)
    except DamError as e:
        _captura_dam(e)
    except KeyboardInterrupt:
        err("cancelado.", code=130)
        raise typer.Exit(130)
    titulo = (
        f"{nombre} (SIMULACIÓN: no se ha tocado nada)"
        if simular
        else nombre
    )
    if not resultados:
        consola.print("[yellow]Ningún fichero cumple el filtro.[/yellow]")
        return
    tabla = Table(title=titulo, title_style="bold")
    for columna in ("Fichero", "Destino", "Estado", "Mensaje"):
        tabla.add_column(columna)
    for r in resultados:
        tabla.add_row(
            markup.escape(r.origen.name),
            markup.escape(str(r.destino)) if r.destino else "—",
            r.estado,
            markup.escape(r.mensaje) if r.mensaje else "",
        )
    consola.print(tabla)
    hechos = sum(1 for r in resultados if r.estado == "hecho")
    simulados = sum(1 for r in resultados if r.estado == "simulado")
    saltados = sum(1 for r in resultados if r.estado == "saltado")
    consola.print(
        f"{len(resultados)} ficheros · {hechos} hechos · {simulados} simulados "
        f"· {saltados} saltados"
    )
    if simular:
        consola.print("Para hacerlo de verdad, repite la orden sin --simular.")


def main(argv: Optional[List[str]] = None) -> int:
    """Modo programático (tests): SystemExit viaja al llamante, como antes."""
    app(args=argv, prog_name="dam", standalone_mode=True)
    return 0


if __name__ == "__main__":
    app()
