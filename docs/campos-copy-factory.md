# Fase 4 — copy_factory (doc 01 §3.4, doc 02 §6)

Construido el 21/09/2026. Genera el texto de cada candidato a partir de la
fila gold con la API de Claude, y lo deja junto al gráfico en
`queue/<fecha>/candidates.json` (doc 03 §6) para revisión humana — este
repo no publica nada por sí solo (CLAUDE.md).

## Piezas

- `content/copy_factory/copy_factory.py`: el prompt (doc 02 §6, regla dura
  de "solo cifras de `values`, sin adjetivos, sin especulación, siempre
  fuente") y `generar_texto(serie, values, fuente_txt)`, que llama a la API
  y devuelve `{"x": ..., "instagram": ...}`.
- `content/copy_factory/cola.py`: `anadir_candidato()` escribe (o actualiza,
  por `registro`) una entrada en `queue/<fecha>/candidates.json`, con el
  esquema exacto de doc 03 §6.
- `content/copy_factory/candidatos.py`: orquesta las dos piezas anteriores
  — llama a `chart_factory` para generar el gráfico, pasa sus metadatos a
  `copy_factory`, y escribe el resultado en la cola.

## Modelo y coste

`claude-haiku-4-5-20251001` — el "modelo económico" que pide doc 01 §4
("el input es una fila de datos"), no el modelo de esta propia sesión de
Claude Code.

## Comprobaciones duras, no solo un prompt bien escrito

Doc 03 §4 (instrucciones del proyecto Cowork) es explícito: "si un texto
contiene un número que no está en los datos, lo marcas y no lo apruebas".
Confiar eso solo al prompt es frágil — el modelo puede redondear, sumar
dos cifras de `values`, o simplemente equivocarse. `generar_texto()`
verifica el texto generado después de recibirlo:

- Cada número que aparece en el texto de X debe estar en `values`, en
  alguna de sus formas razonables (con separador de miles, sin él). Si no,
  `ValueError` — el candidato no se genera, no se marca y se descarta en
  silencio.
- El texto de X no puede superar el límite real de X (280 caracteres, doc
  02 §8), aunque el objetivo del prompt sea 240 (doc 02 §6) — un texto que
  se pase de 240 pero quepa en 280 es aceptable; uno que no quepa en 280,
  no.
- Nombres de jugadores: `data/manual/alias_jugadores.csv` (hoy solo tiene
  la cabecera, sin filas) sustituye cualquier alias conocido por la grafía
  canónica **antes** de mandar los datos al modelo, no después — así el
  modelo nunca ve una grafía que no sea la oficial.

Un bug real que encontraron los tests nuevos (`tests/test_copy_factory.py`,
las partes que no dependen de la API): `_formatear_numero_es()` forzaba
siempre 2 decimales (`27.8` salía como `"27,80"` en vez de `"27,8"`), lo
que habría hecho que la comprobación de cifras rechazara un texto
correcto que citara `27,8` tal cual. Corregido antes de que dependiera de
una llamada real a la API para descubrirlo.

## Probado en vivo (21/09/2026) — dos bugs reales encontrados a la primera

El usuario añadió `ANTHROPIC_API_KEY` a `.env` y se hizo la primera
llamada real. Dos fallos que el prompt por sí solo no evitaba, cazados por
las comprobaciones posteriores a la respuesta en vez de dejarlos pasar a
la cola:

- **El modelo envolvió el JSON en una valla de código** (` ```json ... ``` `)
  pese a que el prompt pide "solo un JSON, sin texto fuera" — `json.loads()`
  fallaba con la valla incluida. Corregido con `_quitar_valla_markdown()`,
  que la quita antes de parsear en vez de confiar en que el modelo nunca
  la añada.
- **El texto de Instagram inventó una cifra que no estaba en los datos**
  ("salta desde el 114 al 99") — el `posicion` real de origen no se pasa
  (solo el `delta_puestos` y la `posicion` final), así que el modelo
  "reconstruyó" de dónde venía sin que ese dato estuviera en `values`. La
  comprobación de cifras solo se aplicaba al texto de X, no al de
  Instagram — corregido para comprobar los dos. La causa de fondo (que el
  modelo tenga la tentación de inventar la posición de origen) también
  apunta a que `values` podría incluir `posicion_anterior` en el futuro
  si esa cifra resulta útil para el texto — de momento se prefiere no
  dársela a que la invente.
- **Falso positivo al arreglar lo anterior**: la fecha de `fuente_txt`
  ("2026-09-16") se marcaba como cifra inventada, porque la comprobación
  solo miraba `values`, no la propia fuente que el texto cita tal cual.
  Corregido: los números válidos son los de `values` **y** los que ya
  aparecen en `fuente_txt`.

Con las tres correcciones, una llamada real completa (gráfico + texto +
cola) para #RankingLunes produjo un candidato válido en
`queue/<fecha>/candidates.json`, con el esquema exacto de doc 03 §6.

## Qué falta

- **Solo 2 series integradas**: `candidatos.py` genera candidatos para
  `#RankingLunes` y `Cierre de torneo` (ganancias) — las mismas dos que se
  migraron primero en `chart_factory`. Para el resto de series (perfil,
  forma reciente, parejas, h2h, sorpresas, pistas, licencias, mercado,
  trends) hace falta que sus `build()` devuelvan también los metadatos del
  candidato (`registro`, `serie`, `tabla_gold`, `fecha_dato`, `values`,
  `fuente_txt`, `png_16x9`, `png_4x5`) en vez de una lista de rutas —
  mismo patrón ya aplicado a `ranking_moves.py` y `ganancias.py`.
- **`png_16x9`/`png_4x5` como ruta de repo, no URL pública**: doc 03 §6
  describe `https://padeldb.es/cola/...`, que solo existe cuando haya web
  definitiva desplegada (Fase 4, migración a Astro). Hasta entonces, la
  cola se lee directamente del repo de GitHub.
- **Texto de Instagram sin usar todavía**: se genera (`borrador_ig`) pero
  la preview web y el propio repo no lo muestran en ningún sitio — es un
  campo a la espera de que exista el rito de revisión (doc 03 §5.1) que sí
  lo necesite.
