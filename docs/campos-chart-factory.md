# Fase 4 — chart_factory con plantilla de marca (doc 02 §1.2)

Construido el 21/09/2026. Sustituye a la versión mínima de `ranking_moves.py`
que solo cubría el "hecho" de Fase 1 (paleta básica, sin tipografía de marca
ni resto de elementos fijos de la plantilla).

## Qué hace `content/chart_factory/marca.py`

Módulo compartido por todas las series, con lo que el doc 02 §1.2 pide que
sea igual en todos los gráficos:

- **Paleta**: los 7 tokens de color exactos (Pista, Cristal, Bola, Coral,
  Arena, Gris pared, Texto secundario), más una variante de texto
  secundario para fondo oscuro no especificada en el doc pero necesaria
  para que el texto secundario tenga contraste legible sobre Pista.
- **Tipografía real**: Space Grotesk (títulos), IBM Plex Mono (cifras),
  IBM Plex Sans (texto) — no las tipografías por defecto de matplotlib. Los
  ficheros viven en `fonts/` (no en el repo de Google Fonts, para no
  depender de que esté disponible en cada máquina/runner).
- **Píldora de serie**, título+subtítulo, píldora "DB", pie con fuente y
  `@padeldb`, y número de registro correlativo — los 6 elementos fijos de
  la plantilla (doc 02 §1.2, puntos 1-3 y 6).
- **Dos variantes de tema** (claro/oscuro) y **dos tamaños de exportación**
  (16:9 para X, 4:5 para Instagram) — puntos 7 y 8 de la plantilla.

## Por qué las fuentes se referencian por fichero, no por nombre

Space Grotesk e IBM Plex Sans se distribuyen hoy como fuentes variables
(`[wght]` / `[wdth,wght]`), y `fontTools.varLib.instancer` (usado para
generar los TTF estáticos de `fonts/`) no reescribe limpiamente el nombre
de subfamilia de cada instancia — todas quedan como "Regular" en la tabla
`name`, aunque su `usWeightClass` sí sea distinto (500, 700...). Confiar en
que matplotlib elija el peso correcto por `family=`/`weight=` habría sido
frágil. En vez de eso, cada rol tipográfico (`Fuentes.titulo()`,
`Fuentes.cifra()`, etc.) carga su fichero exacto con
`FontProperties(fname=...)`, sin ambigüedad posible.

Para regenerar los TTF si hace falta (nueva versión de la fuente, otro
peso):

```
python -m fontTools.varLib.instancer <variable>.ttf wght=<peso> -o <salida>.ttf
```

Las tres familias son de Google Fonts bajo licencia SIL Open Font License
1.1 (gratuitas para este uso, redistribución incluida); los TTF se bajaron
del propio repositorio oficial `google/fonts` en GitHub.

## El icono real

El usuario añadió `brand/` con el icono y el logo (SVG + PNG) al ratito de
empezar esta fase. El pie de cada gráfico usa `brand/padeldb-icon.png`
(`icono_marca()` en `marca.py`) a 24 px de alto, como pide doc 02 §1.2
punto 6. No hay un `padeldb-icon-negative.png` suelto en `brand/` (solo el
logo vertical completo tiene versión negativa) — para el tema oscuro,
`_icono()` recolorea el PNG de Pista a Arena en memoria con Pillow/numpy
(sustituir los píxeles RGB conservando el canal alfa), aplicando la misma
regla de color que ya fija el doc para el icono en negativo, sin depender
de que exista un segundo fichero.

La píldora de texto "DB" (`pildora_db()`) se mantiene en el módulo para
su uso previsto por el propio doc: firma compacta en miniaturas donde el
icono no cabe — no se usa ya en el pie estándar de un gráfico a tamaño
completo.

## Número de registro

`content/chart_factory/registro.json` es un contador simple y persistente
(commiteado, no en `.gitignore`): cada llamada a `siguiente_registro()`
incrementa y guarda. En la Fase 4 completa, cuando exista de verdad la
cola (`queue/candidates.json`, doc 03 §6), el número de registro debería
vivir ahí en vez de en un fichero aparte — este contador es la versión
mínima mientras esa cola no se ha construido todavía.

## Series migradas a la plantilla completa

- `ranking_moves.py` (#RankingLunes) — ya existía en versión mínima,
  reescrita sobre `marca.py`.
- `ganancias.py` (Cierre de torneo / ganancias de temporada) — nueva.

Pendientes de migrar a la plantilla completa (documentado como trabajo
futuro, no bloqueante): perfil_top100, forma_reciente, parejas_duracion,
h2h, torneo_sorpresas, pistas_provincia, licencias_nacional, mercado_pais,
trends_geo. Todas tienen datos reales listos en `gold/`; falta solo
escribir el `_dibujar()` específico de cada formato siguiendo el mismo
patrón que `ranking_moves.py`/`ganancias.py`.

## Exportación a Plotly/JSON para la web

El doc 02 §1.2 punto 8 también pide "SVG/Plotly para la web" además de los
PNG de X/Instagram. No se ha construido todavía — la preview estática
actual (`site/`) sigue leyendo directamente el JSON de gold y dibujando
tablas HTML, no los gráficos de `chart_factory`. Es trabajo de la propia
Fase 4 (migración a la web definitiva de Astro), no de este cierre de
`chart_factory`.
