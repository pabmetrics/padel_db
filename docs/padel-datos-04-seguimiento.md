# PadelDB — Seguimiento y hoja de ruta

Documento vivo · mantenido por el chat orquestador (Cowork) · última actualización: 17 de septiembre de 2026

---

## Cómo funciona este documento

Este chat es el orquestador del proyecto: no toca código ni configura redes (eso vive en otros chats dedicados, incluido Claude Code), pero lleva el mapa completo — cruza `padel-datos-01-arquitectura.md` (la máquina), `padel-datos-02-contenido.md` (marca y contenido) y `padel-datos-03-operacion.md` (el día a día con Cowork) — y dice en cada momento qué toca hacer y en qué orden.

---

## 1. Estado general

**Fase actual: Fase 1 — Núcleo del circuito** (sección 8 de `padel-datos-01-arquitectura.md`), en curso. Identidad y presencia resueltas; Fase 0 cerrada; Fase 1 tiene ya `dim_jugador`, `map_jugador_fuente`, `dim_torneo`, `fact_ranking_semanal` definitivo, tests de calidad y dos tablas gold reales, más el primer gráfico automático. Falta `fact_partido` (necesita una ingesta con el token de padelapi que solo puede lanzar una persona) y `forma_reciente`.

| Bloque | Estado | Detalle |
|---|---|---|
| Marca e identidad | Hecho | Nombre PadelDB, logo + juego vectorial, paleta y tipografía definidos |
| Dominio | Hecho | padeldb.es registrado (14/09/2026) |
| Cuenta de X | Parcial | Cuenta creada. Falta confirmar handle exacto y bio/avatar/cabecera/hilo fijado (checklist doc 02 §14) |
| Otras redes (Instagram, Threads, Bluesky, LinkedIn, GitHub) | Pendiente | Handle @padeldb por reservar aunque no se usen todavía |
| Repo de código | Hecho | Creado y subido a github.com/pabmetrics/padel_db |
| Almacén de datos (Databricks Free Edition o Actions+DuckDB) | Hecho | Decidido: GitHub Actions + DuckDB + Parquet (arranque inmediato, sin depender de límites de la Free Edition; Databricks queda como capa de escaparate opcional más adelante, sin cambiar el modelo de datos) |
| Primer conector (F1 `pypadel`) | Hecho | `ingest/premierpadel/rankings.py`; snapshot real de ranking M/F (top 500 cada uno) en bronze el 16/09/2026. Cron semanal en `.github/workflows/ingest_ranking.yml` |
| Conector F2 (`padelapi.org`) | Hecho | Alta en el plan gratuito hecha por el usuario (secreto `PADEL_API_TOKEN`). `ingest/padelapi/` con cliente que respeta el límite de 10 req/min; snapshots reales de `/rankings` (2.336 filas) y `/players` (2.634 fichas) el 16/09/2026. `/stats` confirmado de pago (402); `/matches` gratuito y prometedor para `fact_partido` en Fase 1 |
| Conector F3 (`padelfip.com`) | Hecho (parcial) | `ingest/padelfip/ranking.py`, scraper con BeautifulSoup. Solo top 10 M/F server-renderizado (el resto es AJAX no identificado); suficiente como referencia de contraste (doc 01 §2). Cron en `.github/workflows/ingest_padelfip.yml` |
| `dim_jugador` / `map_jugador_fuente` | Hecho | `transform/build_dim_jugador.py`: cruce F1+F2 por nombre normalizado (unidecode). 2.814 jugadores, 3.617 filas de mapeo. 180 solo en F1 y 1.831 solo en F2 sin cruzar (la mayoría, fuera del top 500 de F1, no un fallo de cruce) — ver `silver/_reconciliacion/` |
| `fact_ranking_semanal` definitivo | Hecho | `transform/build_fact_ranking_semanal.py`: **posición oficial de F2** (respeta empates) + puntos y delta semanal, unidos por `jugador_id`. 795/1.000 filas con puntos de F2. Corregido un bug real: la primera versión usaba el orden de lista de F1, que rompe empates (ej. Galán/Chingotto, ambos #3) en posiciones sucesivas — hallado contrastando con F3, ver `docs/campos-f3-padelfip.md` |
| `dim_torneo` | Parcial | `transform/build_dim_torneo.py` desde el calendario de F1 (13 torneos, ventana julio-diciembre 2026). Guarda `event_code` para cruzar con el historial de F2 en Fase 2 |
| `fact_partido` | Pendiente | F1 (`tournaments.draw`/`.results`) confirmado poco fiable: vacío para un Major ya acabado (ver `docs/campos-f1-premierpadel.md`). Hay que construirlo desde F2 (`/players/{id}/matches`, gratuito y probado), que necesita el token — pendiente de ejecutar con el usuario delante |
| Tests de calidad (doc 01 §6) | Hecho | `tests/test_calidad_silver.py`, 6 tests con pytest, corren en verde contra los datos reales del 16/09/2026 |
| Gold: `ranking_movimientos_semana` | Hecho | `transform/build_gold_ranking_movimientos.py`. Signo de `ranking_diff` de F2 verificado con casos reales antes de usarlo |
| Gold: `perfil_top100` | Hecho | `transform/build_gold_perfil_top100.py`. 100/100 con edad y **100/100 con lado de pista** en ambos géneros — F13 (curación manual) casi no hace falta para el top 100 |
| Gold: `forma_reciente` | Pendiente | Depende de `fact_partido` |
| Primer gráfico automático (#RankingLunes) | Hecho | `content/chart_factory/ranking_moves.py`, versión mínima (no es aún el `chart_factory` de marca completo de Fase 4) → `queue/<fecha>/ranking_movimientos_{m,f}_16x9.png` |
| Fábrica de contenido completa (`chart_factory`, `copy_factory`) | Pendiente | Fase 4 |
| Web (Astro + Cloudflare Pages) | Pendiente | — |
| Proyecto Cowork "PadelDB" y tarea programada | Pendiente | Depende de que exista la cola (`queue/`) de verdad (Fase 4) |

---

## 2. Próximo paso concreto

**Fase 0 — cerrada** (16-17/09/2026): repo, stack, conectores F1 y F2 dados de alta y probados contra la API real.

**Fase 1 — Núcleo del circuito** (semanas 2-3, doc 01 §8), en curso desde el 17/09/2026:

1. ~~`dim_jugador` + `map_jugador_fuente`~~ Hecho: cruce F1↔F2 por nombre normalizado.
2. ~~`fact_ranking_semanal` definitivo~~ Hecho: posición de F1 + puntos/delta de F2, unidos por `jugador_id`.
3. ~~`dim_torneo`~~ Hecho (parcial: solo calendario julio-diciembre 2026, no toda la temporada).
4. ~~Tests de calidad básicos~~ Hecho: 6 tests, en verde.
5. ~~Gold `ranking_movimientos_semana` y `perfil_top100`~~ Hecho.
6. ~~Primer gráfico automático~~ Hecho (versión mínima, no el chart_factory de marca completo).
7. **`fact_partido` y gold `forma_reciente`** — pendiente. F1 no sirve para esto (endpoint de resultados vacío, ver `docs/campos-f1-premierpadel.md`); hay que ingerir `/players/{id}/matches` de F2, que necesita el token y respeta 10 req/min (lento: cientos de jugadores × varias páginas cada uno). Requiere que el usuario esté delante para lanzarlo, como con el resto de llamadas a padelapi.
8. ~~Conector F3 (padelfip.com, scraper)~~ Hecho (parcial, top 10 M/F). Resultó necesario antes de lo previsto: sirvió para descubrir el bug de los empates en `fact_ranking_semanal` (punto 2).

**"Hecho" de la Fase 1** (doc 01 §8): "el lunes se genera solo el gráfico de movimientos del ranking" — conseguido de punta a punta (bronze → silver → gold → PNG en `queue/`), aunque con una versión de gráfico todavía sin la plantilla de marca completa de Fase 4. Lo que falta de la fase (partidos, forma reciente, F3) no bloquea pasar a pulir esto; se puede completar en paralelo con el arranque de Fase 2.

---

## 3. Pendientes sueltos de identidad/redes (checklist doc 02 §14)

- Confirmar handle @padeldb en X, Instagram, Threads, Bluesky y LinkedIn; si no está libre en alguna red, usar @padeldb_ o @padeldb_es
- Comprobar OEPM y EUIPO antes de plantearse registrar la marca
- Correo hola@padeldb.es operativo
- Avatar y cabecera de X exportados; bio y hilo fijado
- Lista pública en X con fuentes

---

## 4. Las cinco fases del montaje (doc 01 §8), de un vistazo

| Fase | Semana | Qué entrega | Estado |
|---|---|---|---|
| 0 — Cimientos | 1 | Repo, almacén, primer snapshot de ranking | Hecho |
| 1 — Núcleo del circuito | 2-3 | Conectores F1/F3, `ranking_movimientos_semana` autogenerado el lunes | En curso — "hecho" logrado, quedan `fact_partido`/F3 |
| 2 — Lo que nadie tiene | 4-5 | Puntos a defender, ganancias, parejas, previas de torneo | Siguiente |
| 3 — Mercado y territorio | 6-7 | Mapa de pistas, licencias, mercado | Pendiente |
| 4 — Fábrica y web | 8 | `chart_factory`, `copy_factory`, web Astro, pipeline completo | Pendiente |
| 5 — Operación | desde semana 9 | Backfill, modelo Elo, revisión mensual | Pendiente |

El proyecto Cowork y las tareas programadas de operación (doc 03 §10) solo tienen sentido a partir de la Fase 4, cuando ya existe una cola real que revisar.

---

## 5. Bitácora

- **16/09/2026** — Arranca el seguimiento. Estado de partida: marca, logo y dominio resueltos; cuenta de X creada (falta pulir bio/cabecera/handle en el resto de redes); nada del lado técnico empezado. Siguiente paso: Fase 0.
- **16/09/2026** — Fase 0 (cimientos técnicos): repo creado y subido a GitHub; stack decidido (Actions + DuckDB + Parquet, ver razonamiento en el chat de Claude Code); conector F1 (`ingest/premierpadel/rankings.py`) montado y probado contra la API real; primer snapshot de ranking M/F en bronze; `fact_ranking_semanal` provisional en silver; diccionario de campos de F1 documentado (`docs/campos-f1-premierpadel.md`), incluyendo el hallazgo de que el endpoint de ranking no trae puntos, solo posición. Cron semanal configurado en GitHub Actions. Pendiente para cerrar del todo Fase 0: alta manual en padelapi (F2) — tarea de persona, no de Claude Code.
- **17/09/2026** — Fase 0 cerrada: alta hecha en padelapi.org (plan gratuito), token guardado como secreto `PADEL_API_TOKEN` en GitHub Actions. Conector F2 (`ingest/padelapi/`) probado en vivo contra `/seasons`, `/players`, `/rankings`, `/players/{id}/matches` (todos gratuitos) y `/players/{id}/stats` (confirmado de pago, 402). Snapshots reales en bronze: 2.336 filas de `/rankings` y 2.634 fichas de `/players`. Diccionario de campos de F2 documentado (`docs/campos-f2-padelapi.md`), con dos hallazgos para el plan de montaje: (1) F2 ya trae puntos junto con la posición, cosa que F1 no hace; (2) F2 trae `side` (drive/revés) para el top del ranking, lo que reduce el alcance de la curación manual F13 prevista para Fase 2. Ajustado el cliente HTTP para respetar el límite de 10 peticiones/minuto del plan gratuito y reintentar timeouts/5xx transitorios.
- **17/09/2026** — Fase 1 (núcleo del circuito), sesión larga sin supervisión directa (usuario durmiendo, instrucción: seguir hasta acabar o hasta necesitar algo suyo): `dim_jugador` y `map_jugador_fuente` cruzando F1+F2 por nombre normalizado (2.814 jugadores); `fact_ranking_semanal` definitivo uniendo posición (F1) y puntos/delta (F2) por `jugador_id`, con el signo de `ranking_diff` de F2 verificado contra casos reales antes de usarlo (positivo = ha empeorado); `dim_torneo` desde el calendario de F1, con el hallazgo de que `event_code` (F1) y el `key_name` de F2 comparten numeración — clave de cruce para Fase 2; 6 tests de calidad (doc 01 §6) en verde; gold `ranking_movimientos_semana` (con el filtro de publicable acotado a top 100 tras ver que por debajo el ruido de puntos apretados genera saltos de cientos de puestos) y `perfil_top100` (100/100 jugadores del top 100 M y F con lado de pista conocido vía F2 — la curación manual F13 casi no hace falta ahí); primer gráfico automático de #RankingLunes con la paleta de marca. **Hallazgo importante que cambia el plan**: los endpoints de cuadro/resultados de F1 (`tournaments.draw`/`.results`) están vacíos para un Major recién acabado — no fiables para `fact_partido`; hay que construirlo desde F2 (`/players/{id}/matches`), que sí funciona pero necesita el token del usuario para ejecutarse (pendiente, pausado hasta que esté disponible). Corregido también un error de Fase 0: `.gitignore` excluía `queue/`, que el doc de operación dice explícitamente que debe vivir en el repo. Workflow `build_silver_gold.yml` añadido para automatizar todo esto cada lunes tras las dos ingestas. **"Hecho" de la Fase 1 alcanzado**: pipeline completo bronze→silver→gold→gráfico corriendo sin intervención manual salvo la ingesta de F2 (que necesita el token).
- **17/09/2026 (continuación)** — Añadido el conector F3 (`ingest/padelfip/ranking.py`, scraper con BeautifulSoup, solo top 10 M/F porque el resto se carga por AJAX no identificado). Contrastando F3 con F2 se encontró un bug real en `fact_ranking_semanal`: la posición se tomaba del orden de lista de F1, que no respeta empates del ranking oficial (Galán y Chingotto comparten el #3 con los mismos puntos; F1 los listaba como 3º y 4º). Corregido usando la posición oficial de F2 (que sí modela empates) y añadidos dos tests de calidad nuevos para esto (`test_ranking_empates_solo_con_mismos_puntos`, `test_ranking_puntos_no_crecen_con_la_posicion`), sustituyendo a los dos tests anteriores que asumían posiciones sin empates. Gold y gráfico regenerados con la corrección — los movimientos de ranking ahora son de magnitud realista (antes salían saltos de cientos de puestos en la cola de la tabla por el efecto de los empates rotos). Documentado en `docs/campos-f3-padelfip.md`.
