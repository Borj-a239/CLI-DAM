#!/usr/bin/env bash
# Revisa lo que vas a commitear con el subagente revisor (solo lectura), sin
# abrir la interfaz: el diff preparado le llega por la entrada estándar.
#
# Uso:  git add … && scripts/revisar.sh      (sale con 0 si el veredicto es OK)
#
# - El revisor no puede editar: si ve algo, lo cuenta y sale con 1 para que
#   el ARREGLO lo escribas tú a mano en la TUI (así el código sigue siendo tuyo).
# - timeout 180: si el servidor del centro no contesta, el script no se queda
#   colgado. Nunca uses --auto con esto.
set -euo pipefail

if git diff --staged --quiet; then
  echo "No hay nada preparado: haz git add primero." >&2
  exit 1
fi

revision=$(git diff --staged | timeout 180 opencode run --agent revisor \
  "Revisa este diff (te llega por la entrada estándar) con las normas del
proyecto. No escribas ni parchees nada: si algo está mal, di dónde y por qué.
Acaba con una línea exacta: VEREDICTO: OK o VEREDICTO: CAMBIAR")

echo "$revision"
grep -q "^VEREDICTO: OK" <<< "$revision"
