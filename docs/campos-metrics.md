# Métricas de rendimiento — fuentes, conectores y hallazgos

`ingest_metrics` (doc 01 §3.4/§5) es la última pieza de Fase 4. Alimenta
`gold.rendimiento_posts`, que a su vez alimenta el rito del domingo (doc 03
§5.3: "leer impresiones e interacciones de los posts de la semana").

## Dos fuentes, dos grados de automatización

- **Web (Cloudflare Web Analytics)**: 100% automática. `ingest/webanalytics/cloudflare.py`
  consulta la API GraphQL de Cloudflare (dataset RUM,
  `rumPageloadEventsAdaptiveGroups`) y escribe un snapshot semanal a
  `bronze/webanalytics/pageviews/dt=<fecha>/data.json`. Requiere dos
  secretos que **todavía no están dados de alta**: `CLOUDFLARE_API_TOKEN`
  (token con permiso "Zone Analytics: Read" sobre la zona de padeldb.es) y
  `CLOUDFLARE_ZONE_TAG` (Cloudflare dashboard → padeldb.es → panel derecho,
  "Zone ID"). Sin ellos, el paso falla con un error claro
  (`CloudflareError`) y el workflow lo marca `continue-on-error` para no
  bloquear la parte de X.
- **X (analytics.x.com)**: manual por diseño, no por limitación de esta
  sesión — el propio doc 01 §3.4 lo especifica así ("export semanal de X
  analytics (CSV)"), porque X no da esa métrica por API gratis. El export
  se guarda en `data/manual/rendimiento_x/<fecha>.csv` (ver el README de
  esa carpeta) y se versiona en el repo como el resto de fuentes manuales
  (F4/F5/F6/F13).

## El cruce que hace falta para atribuir un post a una serie

`gold.rendimiento_posts` necesita saber qué `registro`/`serie` corresponde
a qué URL de X. Eso no está en ningún export automático — lo anota una
persona (o Cowork) en el momento de publicar, con:

```
python -m content.copy_factory.cola --registro "#0042" --url "https://x.com/padeldb/status/..." --fecha 2026-09-22 --hora 08:30
```

Esto pone `estado: "publicado"` y `url_x` en el candidato correspondiente
de `queue/<fecha>/candidates.json` (nueva función `marcar_publicado()` en
`content/copy_factory/cola.py`). Es la pieza que faltaba del ciclo de
estados que ya define doc 03 §6
(`candidato → aprobado → programado → publicado → medido`): hasta ahora
nada del repo escribía nunca el estado `publicado`.

`transform/build_fact_rendimiento_x.py` cruza el export de X con estos
candidatos por `Tweet permalink == url_x` (coincidencia exacta, nunca por
texto o fecha aproximada — mismo criterio de "un cruce dudoso es peor que
un hueco documentado" que ya se aplicó en prize money). Los posts del CSV
que no cruzan con ningún candidato publicado se listan en
`silver/_reconciliacion/rendimiento_x_sin_cruzar.json` en vez de
descartarse en silencio.

## Forma de `gold.rendimiento_posts`

Formato largo, no un cruce forzado entre X y web (no comparten grano — uno
es por post, el otro por página y día):

- `fuente="x"`: fila por (`registro`, `metrica`) — `impresiones`,
  `interacciones`, `retweets`, `respuestas`, `me_gusta`, `clics_url`.
- `fuente="web"`: fila por (`ruta`, `fecha_dato`, `metrica`) —
  `pageviews`, `visitas`.

No se exporta a `site/public/` (`export_web.py`): es rendimiento interno
de la cuenta y de la web, no un dato abierto del circuito de pádel.

## Qué falta para que corra en producción

1. Publicar de verdad un post y anotarlo con `marcar_publicado` (o el
   comando de arriba).
2. Exportar el primer CSV real de `analytics.x.com` a
   `data/manual/rendimiento_x/` — **bloqueado por ahora**: el usuario
   comprobó (22/09/2026) que `analytics.x.com` pide Premium para acceder,
   no solo para el programa de recompensas (doc 02 §8). Sin cuenta
   Premium activa (el disparador sigue siendo el de doc 02 §8: 60 días
   publicando sin fallar + 500 seguidores, o antes si la tracción lo
   justifica), esta pieza queda aparcada — el resto del pipeline funciona
   igual sin ella, simplemente `gold.rendimiento_posts` no tendrá filas
   `fuente="x"` hasta entonces.
3. ~~Dar de alta `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ZONE_TAG` como
   secretos de GitHub Actions~~ Hecho (22/09/2026, por el usuario). La
   parte web de `rendimiento_posts` ya puede correr en el próximo
   domingo programado, o antes con `workflow_dispatch`.

El workflow `ingest_metrics.yml` corre en domingo (06:30 UTC, antes del
rito del "lote del domingo" de doc 03 §5.3) y también se puede lanzar a
mano (`workflow_dispatch`).
