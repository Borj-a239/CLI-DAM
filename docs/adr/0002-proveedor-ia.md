# ADR 0002 — La IA detrás de una interfaz (`ProveedorIA`)

- Fecha: 13/11/2026
- Estado: Aceptado

## Contexto

`dam` añade dos acciones con IA (`resumir` y `renombrar-ia`) que hablan con el
servidor del centro (API compatible con OpenAI). El proveedor puede cambiar:
hoy `ia.simarro` con certificado propio, mañana otro modelo u otro servidor; y
en los **tests** no se puede llamar al modelo real (no responde siempre igual,
cuesta tokens y falla sin red). Si cada acción construyera su petición HTTP, la
URL, la clave y el certificado quedarían repartidos por el código y las pruebas.

## Decisión

Toda la red vive detrás de una única clase, `ProveedorIA` en `src/dam/ia.py`,
con un método `preguntar(prompt) -> texto`. Las acciones (`resumir`,
`renombrar-ia`, `revisar`) solo la conocen a ella, nunca el HTTP. La instancia
se construye una vez (`proveedor()`, perezosa) leyendo `~/CLI/.env`
(`CENTRO_IA_URL/KEY/MODEL/CA/TIMEOUT`); para los tests existe `set_proveedor()`
que inyecta un proveedor simulado. El fallo (sin clave, sin red, sin
certificado) se traduce siempre a `IaError` (código 4) con mensaje humano, sin
traceback, y el resto de `dam` sigue funcionando sin IA.

## Alternativas

- **`httpx`/`requests` + librería del proveedor**: más dependencias para un solo
  `POST`; me quedo con `urllib` (ya disponible) y el modo sin red cubierto por
  `IaError`. Menos dependencias = instala igual en los tres sistemas.
- **Librería oficial OpenAI**: acopla a un proveedor concreto y trae su propia
  gestión de red/errores, que querría controlar yo.
- **Meter el HTTP dentro de cada acción**: prohibido por este ADR; duplicaría
  cabeceras y clave, y haría imposibles las pruebas sin red.

## Consecuencias

- Positivas: cambiar de modelo o URL es tocar el `.env`, no el código; probar
  el comportamiento ante respuestas buenas, raras o vacías no gasta un token
  (`set_proveedor(falso)`); la clave **nunca** se imprime ni viaja al contexto
  del agente.
- Negativas: la interfaz `preguntar()` es de una sola ronda (suficiente para
  resumir/renombrar; un chat multi-torno exigiría ampliarla); cada acción con
  IA depende de que el `.env` esté bien, que el usuario puede comprobar con
  `dam comprobar-ia`.
- Dónde vive la clave: solo en `~/CLI/.env` (ignorado por git) o en variables de
  entorno; jamás en el repositorio ni en su historial (comprobado con
  `git log --all -- .env` vacío).
