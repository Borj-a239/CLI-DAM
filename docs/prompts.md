# Prompts clave del proceso

Registro de los prompts que dirigieron el proyecto (resumen de sesiones de
OpenCode; el detalle está en el historial de git).

## Semana 1-2 · base del proyecto

1. **Spec y esqueleto** (plan): «Quiero una CLI `dam` que haga `cd` real a mis
   carpetas de estudio, que monte la plantilla vacía que toca desde un PDF de
   enunciado y que nunca resuelva nada. ¿Qué ficheros crearías?»
2. **Wrapper**: «Un hijo no puede hacer cd al padre: diseña un binario `_dam`
   que imprima la ruta elegida por stdout y una función de shell que haga el
   cd. Salida humana por stderr.»
3. **Detector**: «Del PDF salen SOLO estructuras vacías: preguntas literales con
   su hueco, firmas sin cuerpo, tablas por su nombre. Nada de soluciones.»

## Proyecto 2 · migración al esquema del curso (05/11/2026)

4. **Migración** (plan): «Migramos a uv + Typer + src/ conservando go/start/ver/
   last y el cd del wrapper. Códigos de salida 0/1/2/3. ¿Qué tocas?»
5. **Núcleo** (build): «Crea errores.py (DamError/1, ConfigError/3,
   AccionNoValida), config.py que valida acciones.json ANTES de tocar disco, y
   acciones.py con fábrica por registro sin ifs por tipo. --simular no toca
   NADA del disco. Nunca sobrescribir: sufijo « (n)».»
6. **Motor** (build): «Motor.seleccionar con extensiones, patron,
   mas_antiguo/reciente_que_dias, mayor_que_mb y recursivo; sin carpeta usa
   origen; acción o carpeta inexistente → DamError con mensaje humano.»
7. **Interfaz** (build): «Typer: version, listar [--json], acciones, validar,
   ejecutar --simular/--si y --config global ANTES de la orden. Una sola
   captura de DamError que sale con e.codigo_salida. Tabla Rich
   Fichero→Destino→Estado con escape de nombres.»
8. **Auditoría** (casos feos): carpetas inexistentes (1), JSON roto con línea y
   columna (3), tipo desconocido (3), nombre repetido (3), regex rota (3),
   `--config nada.json` (3), uso incorrecto (2). Ninguno en traceback.

## Reglas que nunca se negocian

- Pruebas siempre en carpetas temporales; `--simular` primero.
- Sin claves en código, ficheros ni historial (`.env` fuera de git desde el
  primer commit del curso).
- Los commits los hace el alumno con mensajes que cuentan el paso.
