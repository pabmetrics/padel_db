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
  `@padeldb_` (handle real en X desde el 22/09/2026; `@padeldb` no estaba
  libre), y número de registro correlativo — los 6 elementos fijos de
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

## Marca de serie: de píldora a marcador minimal

La píldora rellena (fondo cristal, texto centrado) no acababa de convencer
al usuario. Se generaron 5 alternativas sobre el mismo gráfico
(#RankingLunes masculino 16:9) para comparar: píldora rellena (la
original), píldora con solo contorno, marcador minimal (cuadrado cristal +
texto en mayúsculas monoespaciado, sin caja), píldora invertida
(fondo Pista, texto Bola) y texto grande subrayado sin caja. Se eligió el
**marcador minimal**: un cuadrado cristal de acento fijo seguido del
nombre de la serie en mayúsculas con IBM Plex Mono (el mismo tipo de letra
que las cifras del gráfico, para que la marca de serie se lea como un
"tag" técnico, no como un titular), sin fondo ni caja alrededor. Se adapta
al tema oscuro con el texto en `texto_principal` (Arena) — el cuadrado de
acento se mantiene siempre en Cristal, en los dos temas.

De paso, al no depender ya de medir el ancho exacto del texto (necesario
solo para dimensionar una píldora), se eliminó `_ancho_texto_frac()` del
módulo — quedaba sin ningún uso.

## Series migradas a la plantilla completa

Las 10 tablas gold que existen a día de hoy tienen ya su gráfico:

- `ranking_moves.py` (#RankingLunes) — movimientos del ranking.
- `ganancias.py` (Cierre de torneo) — ranking de ganancias de temporada.
- `perfil.py` (Perfil del top 100) — nacionalidades del top 100, con una
  tabla `NOMBRE_PAIS` que traduce los códigos ISO-3166-1 de F2 a nombre en
  español (mostrar "ES" en un gráfico público no vale).
- `forma_reciente.py` (Forma reciente) — % de victorias últimas 8 semanas,
  con un mínimo de 8 partidos para evitar que un 100% con 1 partido salga
  como líder.
- `parejas.py` (#ParejasEnDatos) — parejas activas más longevas.
- `h2h.py` (Cara a cara) — cruces más repetidos, barra apilada
  cristal/coral para mostrar el reparto de victorias dentro del total.
- `sorpresas.py` (El torneo en datos) — mayores sorpresas por diferencia
  de semilla.
- `pistas.py` (#MapaDelPádel) — pistas por 10.000 hab. por provincia.
- `licencias.py` (Pádel Mercado) — serie temporal 2000-2025 (CSD) con el
  dato en vivo de la FEP marcado aparte en Bola cuando hay un año
  posterior al último de la serie CSD. Solo se dibuja el tramo 2000+: el
  tramo suelto 1980-1985 (ver docs/campos-licencias-padel.md) se deja
  fuera para no unir con una línea recta un hueco de 14 años sin dato.
- `mercado.py` (Pádel Mercado) — comparación de dos cifras, FIP vs
  Playtomic, sin promediarlas (doc 01 §6). La cifra de Playtomic vive en
  `contexto_txt` (texto libre) porque el CSV manual no le dedicó una
  columna numérica propia; el script comprueba que el texto exacto siga
  ahí antes de usarla, para no hardcodear un número que deje de coincidir
  con la fuente sin que nadie se entere.
- `trends.py` (#MapaDelPádel) — variación trimestral del interés
  pádel/tenis en los países en expansión.

## Título largo en 4:5: se salía del lienzo, y hueco enorme antes del gráfico

Al revisar los primeros 4:5 (`torneo_sorpresas`), dos bugs reales en
`marca.py`, no en cada gráfico:

1. **El título se salía del lienzo.** `titulo_y_subtitulo()` dibujaba el
   título en una sola línea a tamaño fijo (23pt), sin comprobar si cabía.
   Con un título largo (nombres de jugadores incluidos) en el formato 4:5
   (10.8" de ancho frente a las 16" del 16:9), el texto se cortaba fuera
   del margen derecho. Arreglado con `_envolver_texto()`: mide el ancho
   real del título con el mismo TTF que se va a dibujar (`PIL.ImageFont`,
   no el estimador de `wrap=True` de matplotlib, que usa la fuente por
   defecto) y lo parte en hasta 2 líneas; si con la letra normal (23pt) no
   entra en 2 líneas, reintenta a 18pt.

2. **Demasiado hueco entre el subtítulo y el gráfico en 4:5.** Cada script
   fijaba `top=0.72` (16:9) / `top=0.62` (4:5) en `subplots_adjust` como
   fracción de la altura — pero 0.62 de una figura de 13.5" (4:5) deja casi
   2" de hueco en blanco, frente a las ~0.5" que deja 0.72 de una figura de
   9" (16:9): la misma fracción no da el mismo hueco en pulgadas cuando el
   alto del lienzo cambia tanto entre formatos. `titulo_y_subtitulo()`
   ahora calcula dónde termina el bloque de texto (que además varía si el
   título ocupa 1 o 2 líneas) y devuelve la fracción `top` que deja un hueco
   fijo de 0.45" en cualquier formato — los 10 scripts de gráfico reciben
   ese valor como `top_grafico` en vez de tener el número pegado a mano.

## Mismo problema, en el margen izquierdo: nombres de jugadoras cortados

Al revisar `h2h_women_4x5`, el margen izquierdo (donde van los nombres de
las parejas) también estaba fijado a ojo por gráfico (`left=0.3`, `left=0.34`...),
calculado mirando nombres de prueba concretos — con nombres de jugadoras
reales más largos, el texto se salía por el borde izquierdo del lienzo.
Mismo patrón de solución que el título: `margen_etiquetas_y()` en
`marca.py` mide el ancho real de la etiqueta más larga del eje Y (si es de
dos líneas, la línea más larga de cada una) con el mismo TTF que se va a
dibujar, y devuelve el margen izquierdo que hace falta — con un tope
(`max_frac=0.42`) para que un nombre absurdamente largo no deje el área de
dibujo reducida a nada. Aplicado a los 8 gráficos con etiquetas de texto en
el eje Y (`ranking_moves`, `ganancias`, `perfil`, `forma_reciente`,
`parejas`, `h2h`, `sorpresas`, `pistas`, `trends`); antes cada uno tenía su
propio par de números `left=` fijos para 16:9 y 4:5.

## Composición descentrada: margen izquierdo pegado al borde, derecho con aire

Con `margen_etiquetas_y()` ya funcionando (texto sin cortar), el usuario
notó que la composición no quedaba centrada: las etiquetas del eje Y
llegaban justo hasta el borde izquierdo del lienzo (el margen se calculaba
solo con el ancho del texto más un pequeño respiro, sin el margen exterior
que sí respetan el título, el subtítulo y el pie), mientras que a la
derecha quedaba el hueco fijo de `right=0.95`/`0.93` hasta el borde. Dos
cambios en `marca.py`:

- `margen_etiquetas_y()` ahora suma `MARGEN_IZQUIERDO` (0.06, la misma
  constante que ya usan título/subtítulo/pie) al ancho del texto, en vez de
  solo un respiro de 0.035 — la etiqueta más larga queda con el mismo aire
  a su izquierda que el título tiene sobre el suyo.
- Se añadió `MARGEN_DERECHO` (0.06) y se sustituyeron los `right=0.95`,
  `right=0.93`, `right=0.9`, `right=0.88`... (un número distinto por
  gráfico y formato) por `right=1 - MARGEN_DERECHO` en los 11 scripts, para
  que los dos lados respeten siempre el mismo margen exterior.

## Un glifo que no existe en IBM Plex Mono

El símbolo Δ (usado en el título de `ranking_moves.py`, con Space Grotesk,
donde sí existe) salió como un cuadrado vacío la primera vez que se probó
también en una etiqueta con IBM Plex Mono (`sorpresas.py`) — esa instancia
estática concreta no tiene ese glifo. Solución: no usar Δ fuera de Space
Grotesk; las etiquetas de barra de `sorpresas.py` dicen simplemente "N
puestos" en vez de "Δ N puestos".

## Exportación a Plotly/JSON para la web

El doc 02 §1.2 punto 8 también pide "SVG/Plotly para la web" además de los
PNG de X/Instagram. No se ha construido todavía — la preview estática
actual (`site/`) sigue leyendo directamente el JSON de gold y dibujando
tablas HTML, no los gráficos de `chart_factory`. Es trabajo de la propia
Fase 4 (migración a la web definitiva de Astro), no de este cierre de
`chart_factory`.
