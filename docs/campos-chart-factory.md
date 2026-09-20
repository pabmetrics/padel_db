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

## El icono real, y por qué no es `padeldb-icon.png`

El usuario añadió `brand/` con el icono y el logo (SVG + PNG) al ratito de
empezar esta fase. El primer intento usó `brand/padeldb-icon.png` (el
icono completo, con la rejilla de 12 puntos de la pala) a 24 px de alto —
y a ese tamaño la rejilla se convertía en bloques en vez de círculos,
por mucho que se cuidara el reescalado (se probaron `OffsetImage`, ejes
insertados con `imshow`, y un resize de Pillow con LANCZOS compuesto
aparte con `paste()`; los tres dieron el mismo resultado, confirmado
comparando los píxeles exactos). La causa no era el método de
reescalado: a 24 px la rejilla de puntos simplemente no tiene resolución
suficiente para leerse como círculos, sea cual sea el filtro.

El propio sistema de marca ya preveía este problema: `brand/padeldb-favicon.svg`
es, según su propia descripción en doc 02 §1.2, la "versión simplificada
sin agujeros para tamaños pequeños" — un `<path>` de la P más 3 `<rect>`
de las barras, sin la rejilla de puntos. `_icono_favicon()` en `marca.py`
parsea ese SVG a mano (`svg.path`, puro Python, sin dependencias nativas
de sistema como libcairo — se descartó `cairosvg` por eso, no está
garantizado que el runner de CI tenga esa librería instalada) y lo dibuja
con matplotlib/Agg a alta resolución, para reducirlo después con Pillow
(LANCZOS) al tamaño final exacto. El resultado es nítido a 24 px. El icono
completo (`padeldb-icon.png`) queda disponible en `brand/` para usos a
tamaño grande (avatar, cabecera) que no son responsabilidad de
`chart_factory`.

Para el tema oscuro, la P se dibuja directamente en Arena en vez de Pista
(no hace falta recolorear un PNG a posteriori, al ser un dibujo vectorial
propio) — mismo criterio de "icono en negativo sobre fondo Pista" que fija
el doc.

La píldora de texto "DB" (`pildora_db()`) se mantiene en el módulo para
su uso previsto por el propio doc: firma compacta en miniaturas donde el
icono no cabe — no se usa ya en el pie estándar de un gráfico a tamaño
completo.

## Número de registro: en el pie, no arriba a la derecha

El doc 02 §1.2 pide el número de registro "arriba a la derecha". Se probó
así primero, pero quedaba como un elemento aislado que competía visualmente
con el título; a petición del usuario, se movió al pie, como prefijo de la
línea de fuente (`#0003 · Fuente: ...`) — mismo dato, correlativo y
visible, pero integrado en el bloque de atribución en vez de flotando
solo en una esquina.

`content/chart_factory/registro.json` es un contador simple y persistente
(commiteado, no en `.gitignore`): cada llamada a `siguiente_registro()`
incrementa y guarda. En la Fase 4 completa, cuando exista de verdad la
cola (`queue/candidates.json`, doc 03 §6), el número de registro debería
vivir ahí en vez de en un fichero aparte — este contador es la versión
mínima mientras esa cola no se ha construido todavía.

## Píldora de serie: ancho ajustado al texto real

La primera versión calculaba el ancho de la píldora a partir del número de
caracteres del texto (una estimación), lo que dejaba frases largas como
"Cierre de torneo" con demasiado aire a la derecha frente a series cortas
como "#RankingLunes". Se sustituyó por una medición real: `_ancho_texto_frac()`
carga el mismo TTF que se va a dibujar con `PIL.ImageFont` y mide el ancho
exacto en píxeles del texto a ese tamaño de letra, así que la píldora se
ajusta a cualquier frase con el mismo margen proporcional.

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
