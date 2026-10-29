#!/usr/bin/env bash
# ============================================================================
# Wrapper de `dam` para tu ~/.bashrc
# ----------------------------------------------------------------------------
# ¿Por qué? Un subproceso NO puede hacer `cd` al proceso padre. Por eso el
# binario real (`_dam`) solo IMPRIME la ruta elegida por stdout, y esta
# función envoltoria es la que hace el `cd` real en TU shell.
#
# Instalación:
#   1) Instala el paquete (te crea el binario _dam):
#        python3 -m pip install .
#   2) Pega (o sourcea) este fichero desde tu ~/.bashrc:
#        source /ruta/al/repo/dam.bash        # o copia el contenido dentro
#   3) Abre un terminal nuevo. Ya puedes usar `dam go ...` y `dam last`.
#
# Si algún día quieres desactivarlo:  unfunction dam  (o quita el source).
# ============================================================================

dam() {
    if [ "$1" = "go" ] || [ "$1" = "last" ]; then
        # Modo máquina: _dam imprime SOLO la ruta final por stdout.
        # El árbol interactivo va por stderr, así que lo ves igual.
        local r
        r=$(_dam "$@") && [ -n "$r" ] && cd "$r"
    else
        _dam "$@"
    fi
}

# Autocompletado opcional (requiere que _dam esté en el PATH):
if command -v _dam >/dev/null 2>&1; then
    complete -C _dam dam 2>/dev/null
fi
