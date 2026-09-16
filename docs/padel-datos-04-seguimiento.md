# PadelDB — Seguimiento y hoja de ruta

Documento vivo · mantenido por el chat orquestador (Cowork) · última actualización: 17 de septiembre de 2026

---

## Cómo funciona este documento

Este chat es el orquestador del proyecto: no toca código ni configura redes (eso vive en otros chats dedicados, incluido Claude Code), pero lleva el mapa completo — cruza `padel-datos-01-arquitectura.md` (la máquina), `padel-datos-02-contenido.md` (marca y contenido) y `padel-datos-03-operacion.md` (el día a día con Cowork) — y dice en cada momento qué toca hacer y en qué orden.

---

## 1. Estado general

**Fase actual: Fase 0 — Cimientos** (sección 8 de `padel-datos-01-arquitectura.md`). Lo de identidad y presencia (marca, dominio, cuenta de X) está resuelto; lo que falta es todo el lado técnico: repo, almacén de datos, primer conector, primera tabla.

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
| Bronze / silver | Parcial | Bronze: snapshots de ranking F1 y F2 (rankings + players). Silver: `fact_ranking_semanal` provisional a partir de F1 (posición sí, puntos no), keyed por slug de la fuente hasta que exista `dim_jugador` en Fase 1. F2 ya trae puntos y (parcialmente) lado de pista, pero cruzarlo con F1 de forma segura es trabajo de Fase 1 (`map_jugador_fuente`) |
| Fábrica de contenido (`chart_factory`, `copy_factory`) | Pendiente | — |
| Web (Astro + Cloudflare Pages) | Pendiente | — |
| Proyecto Cowork "PadelDB" y tarea programada | Pendiente | Depende de que exista la cola (`queue/`) primero |

---

## 2. Próximo paso concreto

Fase 0 (semana 1 del plan de montaje, doc 01 §8) — **cerrada**:

1. ~~Crear el repo `padel-datos` (GitHub).~~ Hecho.
2. ~~Decidir stack.~~ Hecho: Actions + DuckDB + Parquet.
3. ~~Primer snapshot de ranking a bronze y a `fact_ranking_semanal`.~~ Hecho (16/09/2026, top 500 M/F).
4. ~~Alta en padelapi (F2, plan gratuito) y prueba de un endpoint real.~~ Hecho (16-17/09/2026): `/players/{id}/stats` resultó de pago (402), pero `/rankings` y `/players` funcionan y aportan puntos y lado de pista que F1 no da.

**Hecho de la Fase 0**: ranking de la semana en bronze y en `fact_ranking_semanal` ✅; diccionario de campos de F1 documentado ✅ (`docs/campos-f1-premierpadel.md`); F2 dado de alta y documentado ✅ (`docs/campos-f2-padelapi.md`). Fase 0 completa.

**Siguiente: Fase 1 — Núcleo del circuito** (semanas 2-3, doc 01 §8): conectores F1 y F3 programados de verdad; `dim_jugador`, `map_jugador_fuente`, `dim_torneo`, `fact_partido`, `fact_ranking_semanal` definitivo (cruzando F1 + F2 por id de fuente, no por nombre); tests de calidad básicos; gold `ranking_movimientos_semana`, `perfil_top100`, `forma_reciente`. Explorar también calendario 2026 y cuadro/stats de un torneo con `pypadel` (parte de esta fase, no ya de Fase 0). "Hecho" de Fase 1: el lunes se genera solo el gráfico de movimientos del ranking.

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
| 1 — Núcleo del circuito | 2-3 | Conectores F1/F3, `ranking_movimientos_semana` autogenerado el lunes | Siguiente |
| 2 — Lo que nadie tiene | 4-5 | Puntos a defender, ganancias, parejas, previas de torneo | Pendiente |
| 3 — Mercado y territorio | 6-7 | Mapa de pistas, licencias, mercado | Pendiente |
| 4 — Fábrica y web | 8 | `chart_factory`, `copy_factory`, web Astro, pipeline completo | Pendiente |
| 5 — Operación | desde semana 9 | Backfill, modelo Elo, revisión mensual | Pendiente |

El proyecto Cowork y las tareas programadas de operación (doc 03 §10) solo tienen sentido a partir de la Fase 4, cuando ya existe una cola real que revisar.

---

## 5. Bitácora

- **16/09/2026** — Arranca el seguimiento. Estado de partida: marca, logo y dominio resueltos; cuenta de X creada (falta pulir bio/cabecera/handle en el resto de redes); nada del lado técnico empezado. Siguiente paso: Fase 0.
- **16/09/2026** — Fase 0 (cimientos técnicos): repo creado y subido a GitHub; stack decidido (Actions + DuckDB + Parquet, ver razonamiento en el chat de Claude Code); conector F1 (`ingest/premierpadel/rankings.py`) montado y probado contra la API real; primer snapshot de ranking M/F en bronze; `fact_ranking_semanal` provisional en silver; diccionario de campos de F1 documentado (`docs/campos-f1-premierpadel.md`), incluyendo el hallazgo de que el endpoint de ranking no trae puntos, solo posición. Cron semanal configurado en GitHub Actions. Pendiente para cerrar del todo Fase 0: alta manual en padelapi (F2) — tarea de persona, no de Claude Code.
- **17/09/2026** — Fase 0 cerrada: alta hecha en padelapi.org (plan gratuito), token guardado como secreto `PADEL_API_TOKEN` en GitHub Actions. Conector F2 (`ingest/padelapi/`) probado en vivo contra `/seasons`, `/players`, `/rankings`, `/players/{id}/matches` (todos gratuitos) y `/players/{id}/stats` (confirmado de pago, 402). Snapshots reales en bronze: 2.336 filas de `/rankings` y 2.634 fichas de `/players`. Diccionario de campos de F2 documentado (`docs/campos-f2-padelapi.md`), con dos hallazgos para el plan de montaje: (1) F2 ya trae puntos junto con la posición, cosa que F1 no hace; (2) F2 trae `side` (drive/revés) para el top del ranking, lo que reduce el alcance de la curación manual F13 prevista para Fase 2. Ajustado el cliente HTTP para respetar el límite de 10 peticiones/minuto del plan gratuito y reintentar timeouts/5xx transitorios. Siguiente: Fase 1.
