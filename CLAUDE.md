# PadelDB — contexto para Claude Code

Este repo implementa el sistema descrito en los documentos de `docs/`. Léelos antes de tocar nada; son la fuente de verdad del diseño, no una referencia opcional.

- @docs/padel-datos-01-arquitectura.md — arquitectura de datos: fuentes, bronze/silver/gold, stack, jobs, fases del montaje. Es el documento que más vas a usar: define exactamente qué conector, qué tabla y qué job toca en cada fase.
- @docs/padel-datos-02-contenido.md — marca, identidad visual (paleta, tipografía, plantilla de gráfico) y estructura de contenido. Consúltalo al construir `chart_factory` y `copy_factory` para que la salida respete la marca.
- @docs/padel-datos-03-operacion.md — cómo se opera el proyecto día a día con Cowork una vez la máquina esté montada. No es tarea de Claude Code operarlo, pero conviene saber qué espera la capa de operación de la cola (`queue/`, `candidates.json`) para dejarla bien formada.
- @docs/padel-datos-04-seguimiento.md — estado actual del proyecto y próximo paso concreto. Consúltalo al empezar cualquier sesión para saber en qué fase estamos; actualízalo (o pide que se actualice) cuando cierres un hito.

## Cómo trabajar en este repo

- Seguimos el plan de montaje por fases del documento de arquitectura (sección 8): Fase 0 (cimientos) → Fase 1 (núcleo del circuito) → Fase 2 (lo que nadie tiene) → Fase 3 (mercado y territorio) → Fase 4 (fábrica y web) → Fase 5 (operación). No saltes de fase sin que la anterior tenga su "hecho" verificable cumplido.
- Estructura del repo (sección 4 del documento de arquitectura): `ingest/`, `transform/`, `data/manual/`, `content/`, `publish/`, `site/`, `tests/`, `docs/`.
- Bronze es append-only, nunca se sobreescribe. Silver usa IDs propios (`jugador_id`, `pareja_id`, `torneo_id`…), nunca los IDs de las fuentes directamente. Gold es "una fila = un dato publicable", siempre con `fecha_dato`, `fuente_txt` y `publicable`.
- Nombres de jugadores: usar siempre `data/manual/alias_jugadores.csv` como fuente de la grafía correcta.
- Nada de secretos en el repo (padelapi, Places, Claude, Typefully): van como secretos de GitHub Actions o de Databricks.
- Este repo no publica nada por sí solo: `content_candidates` deja gráficos y textos en `queue/` para que una persona (vía el proyecto de Cowork descrito en el documento de operación) los revise y publique. No construyas ningún flujo que publique en X sin aprobación humana — rompe las reglas del programa de recompensas de X y las reglas de seguridad del documento de operación (sección 7).

## Al terminar una sesión de trabajo

Si cierras una fase o un hito del plan de montaje, dilo explícitamente para poder actualizar `docs/padel-datos-04-seguimiento.md` (el seguimiento vive también, y de forma más actualizada, en el chat orquestador de Cowork — si hay discrepancia entre ambos, gana el de Cowork).
