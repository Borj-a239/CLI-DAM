# ADR 0001 — Configuración externa (`acciones.json`) en lugar de acciones en el código

- Fecha: 05/11/2026
- Estado: Aceptado

## Contexto

`dam` mueve, copia, renombra, borra y revisa ficheros de clase. Mis carpetas y
necesidades cambian cada trimestre (nuevas asignaturas M07–M14, distintas
extensiones, otras rutas de copia). Si cada acción fuera una función escrita en
`src/dam/`, cada cambio de criterio («copia también los .sql», «ahora las fotos
caen en otra carpeta») obligaría a editar Python, probarlo y reinstalar el
paquete — con el riesgo de romper el motor que ya funciona.

## Decisión

Las acciones se describen en `acciones.json` (esquema versionado en el README) y
el código solo ofrece **tipos** genéricos (`mover`, `copiar`, `renombrar`,
`borrar`, `revisar`) implementados como subclases de `Accion` que se autorregistra.
El motor selecciona ficheros con `filtro` y aplica la acción; `config.py` valida
todo el JSON **antes** de tocar el disco y sale con código 3 diciendo qué acción
y qué campo fallan.

## Consecuencias

- Positivas: añadir o retocar una acción es cambiar una línea de JSON (con
  `/nueva-accion` como asistente); el alumno es dueño de la lógica de su
  herramienta sin tocar código; el código base se prueba una vez y se reutiliza;
  el esquema con `"version"` permite leer ficheros antiguos si cambia.
- Negativas: un tipo de acción nuevo **sí** exige escribir una subclase (coste
  puntual y documentado); el JSON no es tan expresivo como Python — lo
  compensamos documentando el esquema en README + skill `acciones-json`; hay que
  validar con más ganas, porque un JSON roto borra ficheros igual que un bug.
