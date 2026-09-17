# Diccionario de campos — F2 (padelapi.org)

Explorado el 16-17/09/2026 contra la API real (plan gratuito, token en el secreto `PADEL_API_TOKEN` de GitHub Actions). Base: `https://padelapi.org/api`, auth `Authorization: Bearer <token>`, paginación estilo Laravel (`data`/`links`/`meta`), límite del plan gratuito 10 peticiones/minuto y 50.000/mes.

## Endpoint `/rankings` (`type=official`)

Usado por `ingest/padelapi/snapshot.py fetch_rankings`. Snapshot real: **2.336 filas** (ambos géneros, ranking oficial vigente a `date: 2026-09-14`).

| Campo | Presente | Notas |
|---|---|---|
| `id` (player id de padelapi) | Sí | Id propio de padelapi, distinto del id de premierpadel.com — otra tabla de mapeo de fuente en Fase 1 |
| `ranking` | Sí | Posición, **explícita** (a diferencia de F1, que hay que derivarla del orden de la lista) |
| `points` | Sí | Puntos del ranking oficial — **F2 rellena el hueco que F1 dejaba** |
| `ranking_diff`, `points_diff` | Sí | Delta ya calculado frente a la semana anterior — útil directamente para `#RankingLunes` sin recalcular nosotros el movimiento |
| `category` | Sí | `men` / `women` |
| `date` | Sí | Fecha de la foto de ranking |
| `type` | Sí | Solo se pidió `official`; la documentación menciona también `race` y `elo` como variantes en `/players/{id}/rankings` (no probado aún) |

## Endpoint `/players` (ficha completa, paginado)

Usado por `fetch_players`. Snapshot real: **2.634 jugadores**.

| Campo | Presente | Notas |
|---|---|---|
| `ranking`, `points`, `elo` | Sí | Elo es propio de padelapi (no oficial FIP/Premier Padel); no mezclar con el ranking oficial sin etiquetarlo |
| `side` (drive/revés) | **Parcial** | Presente para jugadores con cobertura de partidos suficiente (ej. Agustín Tapia → `"backhand"`); `null` para jugadores de ranking bajo con poco historial (ej. Aaran Eastwood, ranking 1478 → `side: null`). **No sustituye a F13** (curación manual): cubre bien el top del ranking, no el conjunto completo |
| `hand` (diestro/zurdo) | Parcial | Mismo patrón que `side`: presente en jugadores con cobertura, `null` en el resto |
| `nationality` | Sí | Código ISO2 (`"AR"`, `"ES"`...) |
| `height`, `birthplace`, `birthdate`, `age` | Parcial | Huecos en jugadores de ranking bajo, igual que `side`/`hand` |
| `category` | Sí | `men` / `women` |

**Hallazgo relevante para el doc de arquitectura**: `side` (drive/revés) del top del ranking ya viene servido por F2, gratis. La curación manual F13 (`lados.csv`, Fase 2 del plan de montaje) se puede reducir a solo los jugadores donde `side` venga `null` en este snapshot, en vez de etiquetar el top 50 M/F entero a mano.

## Endpoint `/players/{id}/stats`

**402 Payment Required** con el plan gratuito, pese a que la documentación pública no lo marca como endpoint de pago. Confirmado en vivo (17/09/2026, jugador `agustin-tapia`, id 66). No usar en Fase 0/1; revisar si el plan de pago compensa cuando haya presupuesto (doc 01 §4: "padelapi de pago... solo si aportan").

## Endpoint `/players/{id}/matches`

**Gratuito y con buena cobertura**: probado con Agustín Tapia (id 66) → 456 partidos disponibles, paginados. Cada partido incluye marcador por set, ronda, jugadores con `side`, ganador y enlace al torneo. Campos ocultos en el plan gratuito: `started_time`, `duration` → `"hidden_free_plan"`. Es la fuente más prometedora para `fact_partido` en Fase 1, más rica que replicar cuadros de F1 partido a partido.

## Endpoints `/tournaments` y `/tournaments/{id}/matches` (17/09/2026)

Usados por `ingest/padelapi/matches.py` para construir `fact_partido`. Mucho mejor diseño que ir jugador a jugador: un torneo trae 100-130 partidos en 2-3 páginas de 50 y cubre a todos sus jugadores de golpe (frente a pedir el historial completo de cada uno, donde un mismo partido se repite 4 veces). `/tournaments` no expone un filtro de "torneo terminado" fiable (los futuros salen `status: "pending"`, no se ha visto qué valor toman los ya jugados) — el recorte de "reciente" se hace por `end_date`, aprovechando que la lista viene ordenada por fecha descendente.

Backfill real del 17/09/2026 (ventana de 180 días): 65 torneos, 3.291 partidos, **100% de los partidos con los 4 jugadores cruzados** a `jugador_id` vía `map_jugador_fuente`.

| Campo | Presente | Notas |
|---|---|---|
| `score` (por set) | **Parcial** | Oculto (`"hidden_free_plan"`, string en vez de lista) en un 2,5% de los partidos (82 de 3.291) aunque el partido esté `status: "finished"` — no es un fallo del conector, es una restricción real y algo inconsistente del plan gratuito |
| `winner` | Sí, pero con ruido | En 1 partido de 3.291 (0,03%) el ganador declarado no coincide con quién ganó más sets según el propio marcador de la fuente — error de datos de padelapi, no de cruce. Se guarda igualmente, marcado con `marcador_incoherente: true` en `fact_partido` |
| `started_time`, `duration` | No | Ocultos en el plan gratuito (`"hidden_free_plan"`) |
| `players[].side` | Parcial | Mismo patrón que en `/players`: presente para jugadores con cobertura suficiente |

## Regla de precedencia aplicada (doc 01 §2)

F1 (premierpadel.com) sigue siendo la fuente primaria de la posición de ranking; F2 (padelapi.org) valida y **rellena los puntos que F1 no da**. De momento (Fase 0) los snapshots de F1 y F2 se guardan por separado en bronze sin cruzarlos: reconciliarlos por jugador de forma segura (no por nombre, que es frágil — ver "Trampas conocidas" del doc de arquitectura) requiere `map_jugador_fuente`, que es trabajo de Fase 1.
