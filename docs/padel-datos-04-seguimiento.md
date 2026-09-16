# PadelDB — Seguimiento y hoja de ruta

Documento vivo · mantenido por el chat orquestador (Cowork) · última actualización: 16 de septiembre de 2026

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
| Bronze / silver | Parcial | Bronze: snapshot de ranking. Silver: `fact_ranking_semanal` provisional (posición sí, puntos no — ver `docs/campos-f1-premierpadel.md`), keyed por slug de la fuente hasta que exista `dim_jugador` en Fase 1 |
| Fábrica de contenido (`chart_factory`, `copy_factory`) | Pendiente | — |
| Web (Astro + Cloudflare Pages) | Pendiente | — |
| Proyecto Cowork "PadelDB" y tarea programada | Pendiente | Depende de que exista la cola (`queue/`) primero |

---

## 2. Próximo paso concreto

Fase 0 (semana 1 del plan de montaje, doc 01 §8) — lo que queda:

1. ~~Crear el repo `padel-datos` (GitHub).~~ Hecho.
2. ~~Decidir stack.~~ Hecho: Actions + DuckDB + Parquet.
3. ~~Primer snapshot de ranking a bronze y a `fact_ranking_semanal`.~~ Hecho (16/09/2026, top 500 M/F).
4. Explorar `pypadel` para calendario 2026 y un torneo completo con cuadro y stats (`dim_torneo`, `fact_partido`) — pendiente, es ya trabajo de Fase 1.
5. Alta en padelapi (F2, plan gratuito) y prueba de `/players/{id}/stats` — requiere que una persona cree la cuenta; no lo puede hacer Claude Code.

**Hecho de la Fase 0**: ranking de la semana en bronze y en `fact_ranking_semanal` ✅, diccionario de campos de F1 documentado ✅ (`docs/campos-f1-premierpadel.md`). Con esto la Fase 0 está sustancialmente cerrada; el hueco de puntos en el ranking (ver diccionario de campos) y el resto del inventario de F1 (torneos/partidos) se abordan ya dentro de la Fase 1.

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
| 0 — Cimientos | 1 | Repo, almacén, primer snapshot de ranking | Siguiente |
| 1 — Núcleo del circuito | 2-3 | Conectores F1/F3, `ranking_movimientos_semana` autogenerado el lunes | Pendiente |
| 2 — Lo que nadie tiene | 4-5 | Puntos a defender, ganancias, parejas, previas de torneo | Pendiente |
| 3 — Mercado y territorio | 6-7 | Mapa de pistas, licencias, mercado | Pendiente |
| 4 — Fábrica y web | 8 | `chart_factory`, `copy_factory`, web Astro, pipeline completo | Pendiente |
| 5 — Operación | desde semana 9 | Backfill, modelo Elo, revisión mensual | Pendiente |

El proyecto Cowork y las tareas programadas de operación (doc 03 §10) solo tienen sentido a partir de la Fase 4, cuando ya existe una cola real que revisar.

---

## 5. Bitácora

- **16/09/2026** — Arranca el seguimiento. Estado de partida: marca, logo y dominio resueltos; cuenta de X creada (falta pulir bio/cabecera/handle en el resto de redes); nada del lado técnico empezado. Siguiente paso: Fase 0.
- **16/09/2026** — Fase 0 (cimientos técnicos): repo creado y subido a GitHub; stack decidido (Actions + DuckDB + Parquet, ver razonamiento en el chat de Claude Code); conector F1 (`ingest/premierpadel/rankings.py`) montado y probado contra la API real; primer snapshot de ranking M/F en bronze; `fact_ranking_semanal` provisional en silver; diccionario de campos de F1 documentado (`docs/campos-f1-premierpadel.md`), incluyendo el hallazgo de que el endpoint de ranking no trae puntos, solo posición. Cron semanal configurado en GitHub Actions. Pendiente para cerrar del todo Fase 0: alta manual en padelapi (F2) — tarea de persona, no de Claude Code.
