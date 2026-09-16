# Diccionario de campos — F1 (premierpadel.com vía `pypadel`)

Explorado el 16/09/2026 contra la API real (paquete `pypadel==0.1.0`, PyPI). Documenta qué campos existen de verdad en cada endpoint usado y cuáles faltan, tal como pide la Fase 0 del plan de montaje (`padel-datos-01-arquitectura.md` §8).

## Endpoint `getplayerrankingv2` (ranking, paginado de 20 en 20)

Usado por `client.players.list(gender, page)` / `ingest/premierpadel/rankings.py`.

| Campo | Presente | Notas |
|---|---|---|
| `player_id` | Sí | Id interno de premierpadel.com. Va a `map_jugador_fuente` en Fase 1, nunca directo a `jugador_id` |
| `slug` | Sí | Identificador estable en URL; usado como clave provisional en `fact_ranking_semanal` hasta que exista `dim_jugador` |
| `first_name`, `last_name`, `full_name` | Sí | Grafía de la fuente; contrastar con `alias_jugadores.csv` antes de publicar |
| `image`, `thumbnail_image` | Sí | URLs de imagen. No se usan (sin fotos de jugadores, doc 02 §12) |
| `countries_image` | Sí | URL de bandera, no el código de país (ese sí aparece en el detalle de jugador) |
| `status` | Sí | Ej. `"Active"` |
| `created_at`, `updated_at` | Sí | Timestamps de la ficha en la base de datos de premierpadel.com, no de la posición de ranking |
| **posición numérica** | **No** | El endpoint no devuelve una posición explícita. Se deriva del orden de la lista (`posicion_lista` = índice 1-based acumulado entre páginas) |
| **puntos** | **No** | Ausente en este endpoint. Sí aparece en el detalle de jugador (`getplayerdetails`, campo `points`), pero pedirlo jugador a jugador para todo el ranking no es viable a este volumen (ver más abajo) |

**Volumen real**: 435 páginas × 20 = ~8.700 fichas en el ranking masculino (y un número similar en femenino), la mayoría de jugadores inactivos o con una sola ficha histórica. El conector limita la ingesta a `--max-pages` (por defecto 25 páginas = top 500), que cubre de sobra el top 100/200 que alimenta las series de contenido. Pendiente de decidir en Fase 1 si vale la pena ampliarlo.

## Endpoint `getplayerdetails` (ficha de jugador)

Usado por `client.players.get(slug)`. Confirmado con datos reales (Agustín Tapia, 16/09/2026):

| Campo | Presente | Notas |
|---|---|---|
| `ranking`, `points` | Sí | Aquí sí hay posición y puntos, pero por jugador (no hay endpoint de "ranking con puntos" en bloque) |
| `birth_date`, `height`, `play_hand` | Sí | Alimentan `perfil_top100`. `play_hand` no es lo mismo que "lado de pista" (drive/revés): ese dato sigue siendo curación manual (F13) |
| `country_code`, `country_code_iso_2` | Sí | Código de país real (a diferencia del ranking, que solo trae la URL de la bandera) |
| `partner_player_id`, `partner_player_name` | Sí | Pareja actual declarada por la fuente — punto de partida útil para `dim_pareja`, pero no sustituye la derivación desde `fact_partido` (doc 01 §3.2: una pareja nace/muere por quién juega con quién, no por lo que diga el perfil) |
| `player_tournaments[]` | Sí | Historial completo de torneos jugados con `round_name` y `points` por torneo — es la fuente más directa para retro-poblar `fact_resultado_torneo` sin tener que reconstruirlo desde cuadros |
| `lado de pista` (drive/revés) | No | Confirmado ausente; sigue siendo F13 (curación manual) |

## Implicación para `fact_ranking_semanal` (Fase 0)

La tabla que genera `transform/build_silver.py` de momento tiene `posicion` (derivada del orden de lista) pero `puntos = NULL`, documentado explícitamente como hueco. Rellenar `puntos` en bloque para las primeras ~500 fichas de cada género requeriría 500 llamadas a `getplayerdetails` por género y por snapshot: se deja para Fase 1, evaluando entonces si compensa frente a padelapi (F2), que si ofrece rankings con puntos en su plan gratuito.

## Endpoint `getfanapptournaments` (calendario)

Usado por `ingest/premierpadel/tournaments.py` (Fase 1). Funciona bien: da `event_code`, `slug`, `name`/`full_name`, `city`, `country`, `tournament_type` (P1/P2/MAJOR/FINALS), `start_date`/`end_date`, `status`. `event_code` es la clave de cruce con el historial de torneos de F2 (ver `docs/campos-f2-padelapi.md`): el `key_name` de un torneo en el detalle de jugador de padelapi (`FIP-2025-3603`) lleva el mismo número que el `event_code` de F1 (`"3603"`).

## Endpoints de cuadro/resultados (`tournaments.draw`, `tournaments.results`) — no fiables

Probado en vivo el 17/09/2026 contra el Paris Major (id 270, 7-13 sept 2026, ya finalizado con Tapia/Coello campeones según F2). **Ambos endpoints devolvieron vacío** (`main_draw: []`, `matches: []`, solo la estructura de rondas sin partidos) pese a que el calendario lista el torneo correctamente. El campo `updated_at` del torneo se quedó en julio, antes de empezar — este endpoint de "fan app" no parece recibir los resultados reales una vez juega el torneo.

**Implicación para el plan de montaje**: `fact_partido` no se puede construir de forma fiable desde F1 con este SDK. La fuente que sí funciona para partidos es F2 (`/players/{id}/matches`, gratuito, probado con 456 partidos reales de un jugador — ver `docs/campos-f2-padelapi.md`). Fase 1/2 deberían construir `fact_partido` desde F2, no desde F1, invirtiendo la expectativa inicial del documento de arquitectura (que asumía F1 como fuente primaria también para partidos, no solo para ranking).

## Pendiente de Fase 0

- Probar `padelapi.org` (F2): alta en el plan gratuito y una llamada a `/players/{id}/stats` — requiere una cuenta que solo puede crear una persona, no está hecho todavía.
- Explorar `tournaments`/`matches` de `pypadel` (calendario 2026, cuadro y stats de un torneo) para completar el diccionario de campos de F1 con `dim_torneo` y `fact_partido`. Se deja para el arranque de Fase 1, cuando toque construir esas tablas.
