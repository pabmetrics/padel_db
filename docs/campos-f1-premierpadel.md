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

## Estadísticas de partido (investigado el 29/09/2026)

**Resumen:** F1 sí tiene estadísticas por partido, en dos APIs distintas.

### Por qué la API de `pypadel` dejó de tener partidos

premierpadel.com se ha rehecho como aplicación Next.js y ahora usa un
backend nuevo: `https://api-prod.premierpadel.com/api/` (sacado del
JavaScript de la web). La API antigua que usa `pypadel`
(`premierpadel.com/premierpadel/api`, la "fan app") dejó de recibir
partidos a mediados de 2026. Por eso los cuadros salían vacíos.

### API antigua (`pypadel`): histórico de abril de 2024 a mayo de 2026

- `gettournamentsmatchlistnew` y `gettournamentsmatchdraw` devuelven vacío
  para todo 2026 (también para torneos antiguos). Así no se consiguen ids.
- `gettournamentsmatchdetail` (`tournaments_match_id`) **sí funciona**, y los
  ids son correlativos. Un muestreo cada 60 ids dio:
  - datos entre el id ~60 (Bruselas P2, abril de 2024) y el **6589**;
  - por encima de 6600, nada;
  - los últimos torneos con stats son Buenos Aires P1 2026 (mayo), y después
    solo la previa del Málaga P1 (julio de 2026), ya sin stats;
  - hay un hueco de ids vacíos entre ~1380 y ~1620 (2024).
  - 100 de 104 partidos muestreados traían estadísticas: cuadro principal y
    previa, M y F.
  - En total son unos 6.500 partidos, cada uno una petición.
- El parser de `pypadel` (`parse_match_detail`) espera `match_state` como
  objeto, pero la API lo devuelve como **lista** (partido + un bloque por
  set). Hay que leer la respuesta en crudo (`client._transport.post_form`).

### API nueva (`api-prod.premierpadel.com`): temporada actual, en directo

Sin autenticación. Se usan tres llamadas:

- `GET tournament/getTournamentDetails?slug=<slug>`: ficha del torneo
  (`event_code`, `prize_money`, fechas UTC, categoría).
- `POST tournament/getTournamentMatches` (JSON) con
  `{"slug", "date", "matchStatus": "All"|"F"|"P"|"N"}`. Sin `date` devuelve
  la lista de fechas del torneo; con `date`, los partidos de ese día
  agrupados por pista. Cada partido trae `match_id` (espacio de ids nuevo:
  Paris Major 2026 ≈ 18.513-18.609), `draw_type`
  (MD/WD/MQ/WQ), `round_name`, **`duration`** (`"01:59:49"`), `winner_id`,
  y por equipo `seed_number`, marcador por set con tie-breaks y jugadores
  con `player_id`, `country_code` y `doubles_rank`.
- `POST tournament/getTournamentMatchDetailsByType` (form) con
  `match_id=<id>&type=Stats`. Otros `type` que usa la web: `MatchCenter`,
  `HeadToHead` y `Highlights`.

Probado con el Paris Major 2026 (110 partidos en 8 días, 10 muestreados:
10 de 10 con stats, previa incluida) y con Rotterdam P2 en juego
(29/09/2026).

### Qué estadísticas hay (las dos APIs, mismo formato)

`match_state` es una lista: un bloque `"Match"` y uno por set (`"set 1"`,
`"set 2"`…), cada uno con:

| Grupo | Métricas | Forma |
|---|---|---|
| `service` | Aces, Double Faults, Services Games Played | recuento en `title` |
| `service` | First Serve Points Won, Second Serve Points Won | `won`, `played`, `percentage` |
| `return` | First Return Points Won, Second Return Points Won | `won`, `played`, `percentage` |
| `return` | Return Games Played | recuento |
| `total_points` | Total Points Won, Total Serve Points Won, Total Return Points Won | `won`, `played`, `percentage` |
| `total_points` | Longest Points Won Streak | recuento |

**Aces y dobles faltas salen a 0 en todos los partidos muestreados**: no se
registran y no deben publicarse. No hay winners, errores no forzados,
roturas ni puntos de oro. Las roturas **no** se pueden derivar del
marcador: con juegos al saque, juegos al resto y juegos ganados por cada
equipo, el sistema tiene dos incógnitas (juegos de saque ganados y roturas)
y una sola ecuación independiente. Haría falta saber quién sacó cada juego
(corregido el 29/09/2026; la primera versión de esta nota decía lo
contrario).

Winners y errores no forzados de profesionales solo los mide Padel
Intelligence (anotación manual, sin acceso programático); padelapi de pago
(plan Pro) da las mismas métricas que aquí más el % de bolas de break
convertidas. Investigado el 29/09/2026; se deja la puerta abierta a un
acuerdo con Padel Intelligence.

### Implicaciones

- Sirve para `fact_partido_stats` (doc 01 §3.2), que F2 no puede dar
  (`/stats` es de pago). Ejemplos de series: % de puntos ganados al resto
  por pareja, racha más larga, duración media por ronda o categoría, y
  cómo rinden en el 2.º saque.
- La previa también tiene stats en F1, y F2 no la trae.
- Los ids de partido y de jugador de F1 no son los de F2. Para cruzar con
  `fact_partido` hace falta: torneo por `event_code`, jugadores por
  `map_jugador_fuente` (nombre) y partido por ronda + pareja.
- Legal/ritmo (doc 01 §7): endpoints no documentados. Hay que ir despacio
  (1 petición/s), guardar caché en bronze y no redistribuir el crudo. El
  histórico de la API antigua son ~6.500 peticiones: mejor bajarlo por
  lotes y una sola vez.
- `POST tournament/getTournaments` con `{"type": "past", "year": 2026}`
  lista la temporada entera, con `status` F (terminado), P (en juego) o N
  (por jugar). La API nueva tiene **los 19 torneos de 2026**, de Riyadh
  (febrero) a Rotterdam (en juego), con estadísticas: cubre también el
  hueco de junio a agosto que la API antigua no tiene.

### Implementado (29/09/2026)

- `ingest/premierpadel/match_stats.py`: por cada torneo empezado de la
  temporada, partidos terminados + `type=Stats` → `bronze/premierpadel/
  match_stats/tournament=<slug>/dt=<fecha>/`. Append-only, solo partidos
  nuevos; un torneo cerrado y ya descargado (`torneo_status: "F"` en un
  snapshot) no se vuelve a consultar. 1 petición/s. Workflow diario
  `ingest_match_stats.yml`.
- `transform/build_fact_partido_stats.py` → `silver/fact_partido_stats`:
  (partido, equipo, bloque partido/set_N), en recuentos. Sin aces ni
  dobles faltas. Jugadores cruzados por nombre contra `dim_jugador`; lo
  que no cruza, a `silver/_reconciliacion/partido_stats_sin_cruzar.json`.
- `transform/build_gold_stats_parejas.py` → `gold/stats_parejas`: por
  pareja y temporada, solo cuadro principal, % sumando recuentos, mínimo
  8 partidos para publicar.
- `content/chart_factory/stats_resto.py`: serie #StatsDePista (martes de
  semanas impares), las 10 parejas que más puntos ganan al resto.
- El histórico de la API antigua (2024 - mayo de 2026, ids 1-6589) no se
  ha bajado todavía: no hace falta para la temporada actual.

## Pendiente de Fase 0

- Probar `padelapi.org` (F2): alta en el plan gratuito y una llamada a `/players/{id}/stats` — requiere una cuenta que solo puede crear una persona, no está hecho todavía.
- Explorar `tournaments`/`matches` de `pypadel` (calendario 2026, cuadro y stats de un torneo) para completar el diccionario de campos de F1 con `dim_torneo` y `fact_partido`. Se deja para el arranque de Fase 1, cuando toque construir esas tablas.
