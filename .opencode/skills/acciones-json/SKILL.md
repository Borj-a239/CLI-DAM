---
name: acciones-json
description: Reglas del fichero acciones.json de la CLI dam (campos, tipos, filtros, plantillas y validación). Úsala siempre que crees o cambies acciones o el código que las lee (config.py, acciones.py, motor.py).
---
# Esquema de acciones.json
- Raíz: {"version": 1, "acciones": [...]}. Cada acción: nombre (único, minúsculas-con-guiones), descripcion, tipo.
- Tipos: mover y copiar (requieren destino), renombrar (requiere plantilla), borrar (exige confirmar: true y pregunta salvo --si) y revisar (analiza documentos, nunca modifica; campo propio min_palabras).
- filtro opcional: extensiones (lista, en minúsculas), patron (regex válida), mas_antiguo_que_dias, mas_reciente_que_dias, mayor_que_mb, recursivo (true incluye subcarpetas).
- plantilla: huecos {fecha:%Y-%m-%d}, {n:03}, {ext}, {nombre}.

## Reglas al programar
- Valida el JSON en config.py ANTES de ejecutar; errores con AccionNoValida(accion, campo, motivo) y código de salida 3 (ConfigError).
- pathlib y shutil; encoding="utf-8"; nunca shell=True; nunca sobrescribir (destino_libre con sufijo « (n)»).
- Toda acción admite --simular y devuelve list[Resultado]; con simular=True no se toca NADA del disco (ni mkdir).
- Accion.desde_config es una fábrica por registro: un tipo nuevo = subclase con atributo tipo, sin if/elif.
- Si añades un campo o un tipo nuevo, documéntalo en el README y en esta skill.
