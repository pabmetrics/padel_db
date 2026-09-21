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

## Qué falta para tenerlo funcionando de verdad

- **Clave de API de Anthropic**: pendiente de que el usuario la añada a
  `.env` en local (`ANTHROPIC_API_KEY=sk-ant-...`, ya en `.gitignore`) para
  poder probar `generar_texto()` con una llamada real, y como secreto de
  GitHub Actions (`ANTHROPIC_API_KEY`) para que corra `content_candidates.yml`
  en producción. Sin la clave, `_cliente()` falla con un `RuntimeError`
  explícito en vez de un error críptico — se ha comprobado que ese camino
  funciona, pero no se ha hecho todavía ninguna llamada real al modelo.
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
