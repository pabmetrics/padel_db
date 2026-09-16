# PadelDB

La base de datos abierta del pádel, y un gráfico al día que sale de ella.

PadelDB ingiere resultados, rankings, mercado y territorio del pádel (Premier Padel, FIP, licencias federativas, pistas por municipio…), los modela en un pipeline bronze → silver → gold, y alimenta una fábrica de contenido que deja gráficos y textos listos para revisión humana antes de publicarse.

## Documentación

Este repo se construye siguiendo estos documentos (en `docs/`), que son la fuente de verdad del diseño:

- [`docs/padel-datos-01-arquitectura.md`](docs/padel-datos-01-arquitectura.md) — fuentes de datos, arquitectura bronze/silver/gold, stack, jobs y plan de montaje por fases.
- [`docs/padel-datos-02-contenido.md`](docs/padel-datos-02-contenido.md) — marca, identidad visual y estructura de contenido.
- [`docs/padel-datos-03-operacion.md`](docs/padel-datos-03-operacion.md) — cómo se opera el proyecto día a día una vez montado.
- [`docs/padel-datos-04-seguimiento.md`](docs/padel-datos-04-seguimiento.md) — estado actual y próximo paso concreto.

## Estado

**Fase 0 — Cimientos** (ver `docs/padel-datos-04-seguimiento.md` para el detalle actualizado). Repositorio recién creado; pendiente decidir stack de almacenamiento (Databricks Free Edition vs GitHub Actions + DuckDB), montar el primer conector (`pypadel`) y generar el primer snapshot de ranking en bronze.

## Estructura del repositorio

```
padel-datos/
├── ingest/            # un conector por fuente; cada uno escribe en bronze
├── transform/          # silver y gold (SQL + PySpark); tests de calidad
├── data/manual/         # CSV curados: alias de jugadores, puntos/prize money, informes anuales
├── content/            # chart_factory, copy_factory, plantillas, prompts
├── publish/            # flujos de publicación (siempre con aprobación humana)
├── site/               # web estática (Astro) que lee el export de gold
├── tests/
└── docs/               # documentos de diseño y seguimiento
```

## Principios

- Bronze es append-only, nunca se sobreescribe.
- Silver usa IDs propios (`jugador_id`, `pareja_id`, `torneo_id`…), nunca los IDs de las fuentes directamente.
- Gold: una fila = un dato publicable, siempre con `fecha_dato`, `fuente_txt` y `publicable`.
- Nada de secretos en el repo: van como secretos de GitHub Actions o de Databricks.
- Este repo no publica nada por sí solo. `content_candidates` deja candidatos en `queue/` para revisión y publicación humana.
