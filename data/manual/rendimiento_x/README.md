# Export de analíticas de X (F: rendimiento de posts)

Carpeta para los CSV que exporta a mano `analytics.x.com` (Posts → Export
data). Es la única vía gratuita para impresiones e interacciones por post:
X no ofrece esa métrica por API sin un plan de pago, y el doc de
arquitectura (`padel-datos-01-arquitectura.md` §3.4) ya prevé esta fuente
como CSV manual, igual que los informes anuales F4/F5/F6.

## Cómo exportar

1. `analytics.x.com` → pestaña "Posts" → elegir el rango de fechas → botón
   "Export data" (esquina superior derecha). Descarga un CSV con una fila
   por post.
2. Guardar el fichero aquí sin modificar sus columnas, con el nombre
   `<fecha_export>.csv` (p. ej. `2026-09-28.csv`). No hace falta borrar
   los anteriores: `build_fact_rendimiento_x.py` lee todos los CSV de la
   carpeta y se queda con el valor más reciente de cada post (las
   impresiones solo crecen con el tiempo).
3. Commitear el CSV al repo — es la versión, igual que con los informes
   de mercado (doc 01 §3.1: "los CSV manuales viven en el repo y se
   cargan a bronze con número de versión").

## Requisito para que el post cruce con `gold.rendimiento_posts`

El post tiene que estar marcado como publicado en la cola, con la URL
exacta que aparece en la columna `Tweet permalink` del CSV:

```
python -m content.copy_factory.cola --registro "#0042" --url "https://x.com/padeldb/status/..." --fecha 2026-09-22 --hora 08:30
```

(o, desde código, `content.copy_factory.cola.marcar_publicado(...)`).
Sin esa anotación, el post aparece en el CSV pero no se puede atribuir a
ninguna serie ni registro — `build_fact_rendimiento_x.py` lo deja en
`silver/_reconciliacion/rendimiento_x_sin_cruzar.json` en vez de
inventarle una serie.

## Columnas que usa el conector

Del export estándar de X: `Tweet id`, `Tweet permalink`, `time`,
`impressions`, `engagements`, `retweets`, `replies`, `likes`,
`url clicks`. El resto de columnas del export se ignoran.
