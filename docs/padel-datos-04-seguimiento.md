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
| Repo de código | Pendiente | No iniciado |
| Almacén de datos (Databricks Free Edition o Actions+DuckDB) | Pendiente | Decisión de stack aún abierta |
| Primer conector (F1 `pypadel`) | Pendiente | — |
| Bronze / silver / gold | Pendiente | — |
| Fábrica de contenido (`chart_factory`, `copy_factory`) | Pendiente | — |
| Web (Astro + Cloudflare Pages) | Pendiente | — |
| Proyecto Cowork "PadelDB" y tarea programada | Pendiente | Depende de que exista la cola (`queue/`) primero |

---

## 2. Próximo paso concreto

Fase 0 (semana 1 del plan de montaje, doc 01 §8):

1. Crear el repo `padel-datos` (GitHub).
2. Decidir stack: Databricks Free Edition vs GitHub Actions + DuckDB + Parquet (doc 01 §4).
3. Catálogo `padel` con esquemas `bronze`, `silver`, `gold`; secretos configurados.
4. Notebook exploratorio con `pypadel`: rankings M/F, calendario 2026, un torneo completo con cuadro y stats.
5. Primer snapshot de ranking a bronze; alta en padelapi (plan gratuito) y prueba de `/players/{id}/stats`.

**Hecho de la Fase 0**: ranking de la semana en bronze y en `fact_ranking_semanal`, y diccionario de campos de F1 documentado.

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
