# torneo_previa — fuente, esquema y hallazgos

Última tabla gold que faltaba del diseño original de Fase 2 (doc 01 §8:
"previa automática del siguiente torneo con puntos a defender y h2h de
los cruces"). Construida el 22/09/2026, disparada por que Rotterdam P2
2026 empieza el 28/09 (6 días después) — el primer torneo próximo real
desde que existe el resto del pipeline.

## El hallazgo que hizo falta para diseñarla

`/tournaments/{id}/matches` de padelapi (F2) — el mismo endpoint que ya
usa `fact_partido` para resultados — también devuelve el cuadro **antes**
de jugarse: ronda, semillas y jugadores están ahí desde que se publica el
cuadro, con `score`/`winner` vacíos hasta que se juega. Comprobado en vivo
(22/09/2026) contra Rotterdam P2 2026 (id 745, `status: "pending"`): el
cuadro seguía vacío (0 partidos) a 6 días del inicio — los cuadros de P2
no se publican con tanta antelación. El pipeline se validó de punta a
punta con el cuadro ya completo de **Rotterdam P1 2025** (id 564,
terminado) como sustituto real, y los datos de esa prueba se borraron del
repo antes de comitear: no representan el torneo próximo de verdad.

Semántica de `round` (confirmada con datos reales): no es un número de
ronda jugada, es el número de partidos que quedan en esa ronda — 32 =
Round of 64, 16 = Round of 32, 8 = Round of 16, 4 = Quarter, 2 =
Semifinals, 1 = Finals. La "primera ronda real" de un cuadro es siempre
el valor de `round` más alto presente para `draw == "main"` en esa
categoría — no se puede asumir un valor fijo (P1 llega a Round of 64,
categorías más pequeñas no).

`status` de un cruce puede ser `pending` (sin jugar), `bye` (pasa sin
jugar: no es un cruce real, se descarta), y los ya conocidos de
`fact_partido` (`finished`, `walkover`, `retired`) una vez jugado.

## Conector: `ingest/padelapi/draw.py`

Deliberadamente separado de `ingest/padelapi/matches.py` (que solo mira
`status == "finished"`, ventana hacia atrás). Este mira `status ==
"pending"`, ventana hacia delante (`--days-forward`, default 10 — algo
más que la semana de margen que da doc 03 §5.4). Selecciona por
`/tournaments`, que viene ordenado por `end_date` descendente: los
`pending` (con `end_date` en el futuro) quedan agrupados al principio del
listado, así que basta con parar en cuanto se deja de ver `status ==
"pending"` — mismo tipo de asunción de orden que ya usaba
`fetch_recent_tournaments` en `matches.py` para el sentido contrario.

Snapshot a `bronze/padelapi/draw/tournament_id=<id>/dt=<fecha>/data.json`
— separado de `bronze/padelapi/matches/` para no mezclar cuadros sin
jugar con resultados, y para que `fact_partido` (que no filtra por
estado) no herede filas sin marcador ni fecha real y rompa el test "sin
fechas futuras".

## Silver: `fact_cuadro_previo`

`transform/build_fact_cuadro_previo.py`. Reutiliza la extracción de
jugador/torneo de `fact_partido` vía un módulo nuevo,
`transform/_padelapi_common.py` (`jugador_ref`, `load_map_padelapi`,
`torneo_id_for_padelapi`) — `build_fact_partido.py` se refactorizó para
usar el mismo módulo, sin cambiar su comportamiento (verificado: mismo
recuento de partidos antes/después). Mismo `torneo_id` que tendrá luego
en `fact_partido` (misma función hash sobre el id de padelapi), para que
cuando el torneo pase de "próximo" a "jugado" sus partidos encajen.

## Gold: `torneo_previa`

`transform/build_gold_torneo_previa.py`. Una fila = un cruce de la
primera ronda real del cuadro principal (`fase == "main"`, `ronda_num`
más alto de esa categoría, sin `bye`). Por cruce: los dos equipos, sus
semillas (si tienen), el h2h histórico entre ellos (calculado aquí mismo
desde `fact_partido`, no leído de `gold.h2h` — esa tabla indexa por
nombre de pareja, no por `jugador_id`, y reconstruir la clave a partir de
texto es más frágil que partir del mismo dato crudo con la misma lógica
de clave que usa `build_gold_h2h.py`), y los puntos a defender en las
próximas 8 semanas de cada equipo (suma de `gold.puntos_a_defender` de
sus dos jugadores — sale en 0 mientras esa tabla esté vacía por la
ventana de backfill corta, ver `docs/padel-datos-04-seguimiento.md`, no
es un fallo de esta tabla).

`publicable`: solo cruces con alguna cabeza de serie de por medio o con
historial (`h2h_total > 0`) — un cruce de primera ronda sin semilla ni
historia es un dato correcto pero sin ángulo publicable (mismo criterio
de "si dudas del dato, no sale").

## chart_factory + copy_factory

`content/chart_factory/torneo_previa.py`: un gráfico de barras horizontal
con los cruces más destacados (cristal = con cabeza de serie), siguiendo
la plantilla de `marca.py`. No es el hilo completo de 5-7 tuits que
describe doc 02 §7 ("Hilo de torneo") — es la pieza que abre esa previa;
el resto (puntos a defender con más detalle, pregunta de cierre) lo
cubre el texto de `copy_factory` con los mismos datos, no gráficos
adicionales.

`values` usa las claves `pareja_1`/`pareja_2` (no `equipo_1`/`equipo_2`)
a propósito: son las que ya reconoce `nombres.CLAVES_NOMBRE` para
verificar grafía/alias contra `map_jugador_fuente` — reutilizar la
convención de `h2h.py` en vez de añadir claves nuevas al verificador.

Integrado en `candidatos.py` (`GENERADORES_CON_PARAMETRO["torneo_previa"]`,
categorías `men`/`women`) y en `calendario.py`
(`empieza_torneo_pronto`, día antes de cada torneo — doc 02 §4 fija esa
cadencia; se probó primero con una ventana de 7 días pensando en el
"domingo anterior" de doc 03 §5.4, pero eso dispara la previa todos los
días de la semana anterior a cualquier torneo — se ajustó a 1 día justo
al ver fallar `test_lunes_sin_torneo_reciente_solo_ranking`, que por
coincidencia cae exactamente 7 días antes de Rotterdam P2 en el propio
fixture de test).

## Qué falta para tener datos reales

El cuadro de Rotterdam P2 (id 745) todavía no está publicado a
22/09/2026. `ingest_torneo_previa.yml` corre a diario (07:00 UTC, antes
de `content_candidates`); en cuanto padelapi publique el cuadro, la
siguiente ejecución lo recoge sin intervención manual.
