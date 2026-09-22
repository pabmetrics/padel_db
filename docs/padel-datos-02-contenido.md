# PadelDB — Estructura de creación de contenido

Versión 0.7 · 15 de septiembre de 2026 · Documento vivo

Documento hermano: `padel-datos-01-arquitectura.md`. Cada serie de contenido de este documento se alimenta de una tabla **gold** definida allí.

---

## 1. Posicionamiento e identidad

### 1.1 Marca

- **Nombre:** PadelDB. Se escribe PadelDB en texto corrido y `padelDB` en el wordmark; nunca "Padel DB" con espacio ni "PadelDb". Handle objetivo en todas las redes: @padeldb. **En X no estaba libre**: la cuenta real es **@padeldb_** (confirmado 22/09/2026) — el fallback que ya preveía la sección 12 de este documento. El resto de redes (Instagram, Threads, Bluesky, LinkedIn) siguen pendientes de confirmar con @padeldb.
- **Por qué:** DB es base de datos, la referencia técnica más directa que existe y la que cualquiera entiende sin explicación. Dice exactamente lo que hay detrás: una base de datos propia del pádel de la que sale un gráfico al día. Corto, igual en español y en inglés, y el handle más breve posible.
- **Concepto:** la base de datos abierta del pádel, y un gráfico al día que sale de ella. Lo que todo el mundo discute y nadie cuantifica.
- **Tagline:** "El pádel, en datos."
- **Promesa:** "Cada día, un dato del pádel que no vas a ver en ningún otro sitio. Y la base de datos para comprobarlo."
- **Diferencia frente a lo que ya existe:** PadelPedia se presenta como la mayor base de datos de pádel del mundo (estadísticas de jugadores, rankings, resultados, enfrentamientos) y va en inglés y en formato web. PadelDB no compite en exhaustividad: compite en el gráfico diario, en español, en los análisis derivados que nadie publica (parejas, puntos a defender, ganancias, pistas por municipio) y en las descargas abiertas. La base de datos es el respaldo del gráfico, no el producto principal.
- **Descartados (y por qué):** 20x10 (apodo genérico de la pista; podcast de Onda Cero, academias, clubes y canales); Deltapádel (negocios con el nombre Delta Padel); Padel X (clubes en Miami, Curaçao y Reino Unido); Nabla Pádel (libre, pero no convencía); la jerga de pista en general, porque x3, x4, Víbora, Golden Point, Sweet Spot, Glassbox, Off the Glass o Twenty by Ten ya son clubes, palas o ropa. El 20×10 se conserva como idea visual (ver 1.2), no como nombre.
- **Comprobado en la web abierta:** no aparece ninguna cuenta, app ni web con el nombre PadelDB. Vecinos a vigilar: PadelPedia (misma casilla conceptual) y la app Padel iD (en inglés suena parecido).
- **Riesgo asumido:** es un nombre descriptivo (pádel + base de datos), así que como marca denominativa es débil. Se registra la marca mixta (wordmark + icono), que es la forma defendible, y se construye la distintividad con la identidad visual y la constancia.
- **Comprobaciones hechas (14/09/2026):** GitHub: `padeldb` y `padel-db` libres (la página devuelve 404) y no hay repositorios con ese nombre. padeldb.com: registrado y aparcado, en venta en Spaceship por 25.000 $ (descartado comprarlo). padeldb.es, .net y .io: sin registros DNS, es decir, probablemente libres, pero hay que confirmarlo en el registrador. Handles @padeldb en X, Instagram, Threads y Bluesky: no aparece ningún perfil indexado con ese nombre, pero no se puede confirmar sin entrar en cada app.
- **Pendiente antes de registrar nada:** confirmar @padeldb a mano en X, Instagram, Threads, Bluesky y LinkedIn; registrar padeldb.es como dominio principal (y .io o .app como respaldo si están libres); consultar el localizador de la OEPM y eSearch de EUIPO. Poner una alerta de vigilancia sobre padeldb.com por si baja de precio o caduca.
- **Idioma:** texto en español; títulos y ejes de los gráficos en inglés cuando el dato sea internacional. Argentina, Italia, Suecia o EE. UU. leen gráficos, no hilos.
- **Tono:** preciso y cercano, con un punto de humor seco — cálido en la forma, nunca en el juicio: la cercanía va en el ritmo y la construcción de la frase, nunca en calificar el dato o a las personas (ajustado 22/09/2026; antes "sobrio"). Cuando el dato lo sostiene, el post cierra con una pregunta concreta que invite al debate (ver "Recursos de texto" más abajo y la plantilla "Pregunta con dato" en §7) — no una pregunta vacía tipo "¿qué opinas?", sino una anclada en la cifra. Nunca opinión sobre jugadores: los datos hablan y la comunidad discute.

### 1.2 Identidad gráfica

**Logo (definitivo, 15/09/2026).** Ficheros en `brand/`. Los SVG son los ficheros maestros; los PNG originales se conservan como referencia del diseño.

- `padeldb-icon.svg` / `padeldb-icon-negative.svg` — icono solo (azul / arena para fondos oscuros).
- `padeldb-logo-vertical.svg` / `-negative.svg` — icono + wordmark apilados, lienzo 1254×1254.
- `padeldb-logo-horizontal.svg` / `-negative.svg` — icono a la izquierda, wordmark a la derecha, lienzo 2000×700 (cabeceras de X, LinkedIn y web).
- `padeldb-favicon.svg` + `favicon-16.png`, `favicon-32.png`, `favicon-180.png` — versión simplificada sin agujeros para tamaños pequeños (180 es el icono de iOS/Android).
- `build_logo.py` — genera todo lo anterior a partir de la geometría (un path para la P, 14 círculos, 3 rectángulos) y del wordmark convertido a trazados; cambiar un número y volver a ejecutar regenera el juego completo.
- `padeldb-logo-vertical.png`, `padeldb-icon.png` — los diseños originales en PNG.

![Logo PadelDB](brand/padeldb-logo-vertical.png)

El icono es una P cuyo ojo es la cabeza de una pala (con la rejilla de agujeros en 3-4-4-3) y cuyo asta se convierte en un gráfico de tres barras ascendentes: pádel arriba, datos abajo, una sola forma. El wordmark es "PadelDB" en una geométrica redondeada, con "DB" en negrita para que la referencia técnica se lea como marca y no como sigla. Todo en un solo color, azul marino, lo que lo hace versátil: funciona en una tinta, en negativo y en marca de agua. La idea anterior de las pistas apiladas queda descartada; el 20×10 sobrevive solo como proporción del área de dibujo de los gráficos.

**Notas sobre el vector.** El wordmark de los SVG está compuesto en Poppins (Medium para "Padel", Bold para "DB"), convertido a trazados para que el fichero no dependa de ninguna fuente instalada; no es exactamente la letra del PNG original, así que si se quiere calcar esa, se sustituye la fuente en `build_logo.py` (candidatas gratuitas con el mismo aire: Jost, Questrial, URW Gothic). El azul queda unificado en #0F3463 en todos los ficheros. Pendiente solo un retoque opcional del favicon de 16 px (engrosar el anillo de la P a mano en Inkscape si se ve borroso en la pestaña).

**Píldora DB.** Se conserva como firma compacta donde el icono no cabe (pie de gráficos pequeños, marca de agua en miniaturas, cabecera de tablas en la web): un rectángulo 2:1 de color cristal con "DB" en IBM Plex Mono negrita en color pista. No es el logo; es su abreviatura.

**Sistema de uso.** Icono solo: avatar, favicon, marca de agua, icono de descargas en la web. Logo vertical: portada de informes, cierre de vídeos, página "Sobre". Logo horizontal: cabeceras de X y LinkedIn, cabecera de la web. Píldora DB: pie de gráfico y firmas pequeñas. En texto corrido, siempre "PadelDB".

**Marco 20×10.** El área de dibujo de cada gráfico respeta la proporción 2:1 de la pista siempre que el dato lo permita, con rejilla solo horizontal, fina, como las líneas de la pista. Es el mismo rectángulo del icono, a escala de gráfico.

**Paleta y semántica**

| Color | Hex | Uso |
|---|---|---|
| Pista | `#0F3463` | Azul del logo (tomado del fichero definitivo). Fondo de la versión oscura; texto y títulos en la versión clara |
| Cristal | `#1FB5A8` | Color de marca. Todo lo positivo: subidas, victorias, el elemento destacado en fondo claro |
| Bola | `#D6F000` | El único dato destacado en fondo oscuro. Nunca para texto ni sobre fondo claro |
| Coral | `#FF6B4A` | Bajadas, rupturas, negativos |
| Arena | `#F4F1EA` | Fondo de la versión clara |
| Gris pared | `#B8B5AD` | Rejilla, ejes y todas las barras que no son la protagonista |
| Texto secundario | `#6B6963` | Subtítulos y pies en la versión clara |

Regla de oro: un solo color de énfasis por gráfico; el resto en gris pared. Cristal para positivo y coral para negativo son fijos: nunca se intercambian.

**Tipografía** (gratuitas, disponibles en Google Fonts, valen para matplotlib y web)

- Títulos: Space Grotesk (peso medio).
- Cifras: IBM Plex Mono, con figuras tabulares. El monoespaciado es el guiño "datos crudos".
- Texto: IBM Plex Sans.
- Formato numérico español siempre: punto de miles, coma decimal.

**Plantilla de gráfico** (fija para todas las series)

1. Píldora de serie arriba a la izquierda (#RankingLunes, #MapaDelPádel…), siempre en el mismo sitio, fondo cristal y texto pista.
2. Título de máximo ocho palabras que dice la conclusión, no la descripción ("Mayor subida de la semana", no "Movimientos del ranking").
3. Subtítulo con contexto y unidad.
4. Área de dibujo en proporción 2:1 cuando sea posible; rejilla horizontal fina; sin leyenda con una o dos series (etiquetas directas sobre el dato).
5. Un solo elemento destacado (cristal en claro, bola en oscuro).
6. Pie fijo: fuente a la izquierda ("Fuente: FIP / Premier Padel · elaboración propia"), icono a 24 px y @padeldb_ a la derecha (píldora DB si el gráfico es pequeño).
7. Dos versiones: clara (arena) para el día y oscura (pista) para "El torneo en datos" por la noche.
8. Tamaños: 1600×900 para X, 1080×1350 para Instagram, SVG/Plotly para la web.

**Aplicaciones.** Avatar: icono en negativo (arena) sobre fondo pista, con margen generoso para que la P no toque el círculo. Cabecera de X: un gráfico real de la semana con el logo horizontal en la esquina, se cambia cada mes. Favicon: versión simplificada de 16/32 px. Web: mismos tokens de color y tipografía; el icono como icono de las descargas. Miniaturas de Instagram: fondo pista con el icono pequeño en la esquina.

**Recursos de texto.** Cada gráfico lleva número de registro correlativo en monoespaciada, arriba a la derecha ("#0042"): la base de datos crece a la vista y el número convierte los posts en serie coleccionable ("el #0100 lo celebramos con…"). El Δ, como notación matemática de variación, abre los posts de movimiento: en #RankingLunes y en los cierres de torneo la primera línea empieza con "Δ +14 puestos" o "Δ −3".

---

## 2. Audiencias

| Audiencia | Qué quiere | Formatos | Canal principal |
|---|---|---|---|
| Aficionados al circuito (España, Argentina, Italia, Francia, Suecia, Países Bajos…) | Ranking, torneos, parejas, sorpresas | Gráfico rápido, hilo de torneo | X, Instagram |
| Jugadores amateur | Pistas cerca, precios, tendencias, "cuánto crece mi ciudad" | Mapas, comparativas | Instagram, web |
| Industria (clubes, marcas, inversores, plataformas) | Mercado, pistas, licencias, crecimiento por país | Informes, gráficos de mercado | LinkedIn, web, newsletter |
| Periodistas y medios de pádel | Datos citables con fuente | Gráficos embebibles, datos abiertos | X, web |

La primera audiencia da alcance; la tercera y la cuarta dan dinero y legitimidad. Las dos últimas son además las que más usuarios Premium tienen en X, que es lo único que cuenta para el programa de recompensas de X (ver sección 8).

---

## 3. Análisis de canales

| Canal | Encaje con pádel | Esfuerzo | Papel | Cuándo |
|---|---|---|---|---|
| **X** | La conversación en directo de los torneos está aquí: periodistas, jugadores, federaciones. El algoritmo premia gráficos y hilos | Bajo (automatizable) | Motor de alcance y conversación | Día 1 |
| **Web** | Hub, SEO evergreen, archivo, datos abiertos, captación de newsletter, embeds para medios | Medio al montar, bajo después | Activo propio; no depende de ningún algoritmo | Día 1 (mínima), crece cada mes |
| **Newsletter** | Retención y monetización futura; resumen mensual con lo mejor | Bajo (reutiliza la semana) | Relación directa | Mes 2 |
| **LinkedIn** | Industria, inversores, clubes; refuerza tu marca profesional de datos | Bajo (1 post/semana) | Leads B2B | Mes 2 |
| **Instagram** | La audiencia amateur de pádel vive en IG; los carruseles de gráficos funcionan; las marcas de pádel invierten ahí. Con la monetización de X fuera del horizonte cercano, es el canal que más acerca a las marcas | Bajo si se reutilizan los gráficos (formato 4:5) | Alcance amateur y marcas | Mes 2 |
| **Threads / Bluesky** | Espejo automático de X; poco pádel todavía | Nulo (automatizado) | Presencia | Mes 3 |
| **TikTok / Reels / Shorts** | Bar chart races y mapas animados; audiencia joven | Medio (vídeo) | Descubrimiento | Mes 6 |
| **Canal de Telegram / WhatsApp** | Alertas de torneo y comunidad | Bajo | Fidelización | Mes 6 |
| **YouTube largo** | Análisis de temporada; requiere producción | Alto | Autoridad | Año 2 |

**Decisión:** X + web en la fase 1; newsletter y LinkedIn en el mes 2; Instagram en el mes 3 con los mismos gráficos reformateados; vídeo corto cuando la fábrica de gráficos ya esté rodada.

---

## 4. Pilares y series con nombre

| Serie | Frecuencia | Tabla gold | Ejemplo |
|---|---|---|---|
| **#RankingLunes** | Lunes | `ranking_movimientos_semana`, `puntos_a_defender` | "Mayor subida de la semana: +14 puestos. Y estos cinco jugadores defienden más de 500 puntos en las próximas cuatro semanas." |
| **Previa en datos** | Día antes de cada torneo | `torneo_previa`, `h2h` | Cuadro con cabezas de serie, h2h de los cruces de primera ronda, quién se juega el nº 1 |
| **El torneo en datos** | Diario durante el torneo | `torneo_sorpresas`, `dominio_sets` | "Tres cabezas de serie fuera en primera ronda: la mayor criba de la temporada" |
| **Cierre de torneo** | Lunes siguiente | `ganancias_temporada`, `parejas_duracion` | Ranking de ganancias; parejas que se separan |
| **#ParejasEnDatos** | Miércoles | `parejas_duracion`, `h2h` | Duración media de una pareja del top 20; la pareja activa más longeva |
| **Perfil del top 100** | Mensual | `perfil_top100` | Edad media, España vs Argentina, altura, drive vs revés |
| **#MapaDelPádel** | Jueves | `pistas_municipio`, `trends_geo` | Pistas por 10.000 habitantes por provincia; el municipio con más pistas per cápita |
| **Pádel Mercado** | Martes (quincenal) | `mercado_pais`, `licencias_ccaa` | 58.300 pistas y 19,4 millones de jugadores… o 35 millones según a quién preguntes |
| **Archivo** | Viernes | `archivo_eras` | Semanas como nº 1 desde la era WPT; títulos por pareja |
| **Hilos explicativos** | Quincenal | varias | Cómo funciona el ranking FIP; cómo se reparte el prize money; por qué Playtomic y la FIP no coinciden |

Cada serie tiene un formato visual fijo (mismo tipo de gráfico, misma posición del título). Eso hace posible automatizarla y que la audiencia la reconozca.

---

## 5. Calendario editorial

**Semana tipo (sin torneo)**

- Lunes: #RankingLunes (dos gráficos: movimientos + puntos a defender).
- Martes: Pádel Mercado, o previa del torneo si empieza el miércoles.
- Miércoles: #ParejasEnDatos.
- Jueves: #MapaDelPádel.
- Viernes: Archivo o hilo explicativo.
- Sábado y domingo: descanso, o reposición de lo mejor de la semana con un ángulo nuevo.

**Semana con torneo** (Premier Padel suele ocupar la semana entera, con qualy al inicio y final el domingo)

- Domingo o lunes: previa en datos.
- Cada día de partidos: un post de sorpresas o dominio a última hora, cuando la conversación está viva, más respuestas con datos a cuentas grandes.
- Lunes siguiente: cierre (ganancias, parejas, ranking).
- El calendario oficial del circuito vive en `dim_torneo`; la fábrica decide qué serie toca cada día.

**Mensual:** newsletter "El mes en datos" (cinco gráficos, una lectura), perfil del top 100, post de mercado en LinkedIn.

**Anual:** informe propio "El pádel en España en datos" (licencias, pistas, mercado) en web y PDF. Es la pieza pensada para prensa.

---

## 6. Sistema de producción

1. `content_candidates` genera cada mañana los gráficos y textos candidatos según el calendario.
2. Revisión humana (10 minutos): aprobar, corregir una cifra o descartar. Regla: si dudas del dato, no sale.
3. Programación con el programador nativo de X (gratuito, desde la web) o Typefully a la hora objetivo (X: 8:30-9:30 y 19:30-21:30 hora española; en torneo, tras la última sesión). Ajustar con `rendimiento_posts`. Regla de originalidad: el gráfico es obra propia y el texto final lo escribe o corrige una persona; el borrador automático es un punto de partida, no lo que se publica. El programa de recompensas de X excluye el contenido "creado o publicado por medios automatizados", así que nada de bots que publiquen solos: la fábrica prepara, una persona aprueba y programa.
4. Espejo automático a Threads y Bluesky (fase 2); reformato 4:5 a Instagram (fase 3).
5. Domingo: 20 minutos de métricas. Qué series funcionan, a qué horas, qué gráficos. Ajustar el calendario.
6. Producción en lote: lo que no depende del ranking (mapas, mercado, archivo) se genera el domingo para toda la semana.

Prompt del `copy_factory` (resumen, actualizado 22/09/2026): *"Con estos datos [fila gold], escribe un post para X en español de máximo 240 caracteres, tono cercano: primera línea con la cifra más sorprendente, segunda con el contexto en una frase, y si cabe una pregunta concreta anclada en el dato que invite al debate; la fuente la añade otro paso. Sin adjetivos sobre personas, sin especulación, sin emojis salvo uno al inicio, sin pedir interacción genérica ('¿qué opinas?', 'comenta', 'dale like')."* La salida siempre pasa por revisión.

---

## 7. Plantillas de post (X)

**Dato único**

```
[Cifra gancho]. [Qué significa, en una frase].
[Gráfico]
Fuente: FIP / Premier Padel · elaboración propia
```

Ejemplo: "El top 100 masculino tiene 27,8 años de media. El femenino, 26,1. Y los diez primeros de cada uno son más jóvenes que hace tres años."

**Movimiento (#RankingLunes y cierres de torneo)**

```
Δ [+/−N] [qué se ha movido]. [Contexto en una frase].
[Gráfico]
Fuente: FIP · elaboración propia
```

Ejemplo: "Δ +14 puestos. La mayor subida de la semana la firma un jugador que hace un mes no estaba en el top 100."

**Hilo de torneo (5-7 tuits)**

1. Gancho: la cifra más llamativa del torneo.
2. Cuadro y cabezas de serie (gráfico).
3. Puntos a defender de los tres favoritos.
4. h2h de los cruces más igualados.
5. Cierre con pregunta a la comunidad: "¿Qué pareja rompe el cuadro?"

**Respuesta con datos** (crecimiento inicial)

Cuando una cuenta grande (medio, jugador, federación, periodista) publica una afirmación cuantificable, reaccionar en menos de 30 minutos con el gráfico. Es la vía más rápida a los primeros 500 seguidores: el algoritmo muestra la reacción a la audiencia del post original. Sin Premium, las respuestas de cuentas no verificadas quedan por debajo de las verificadas en el hilo, así que la forma preferente es la cita (quote) con el gráfico, que es un post propio y no se entierra; la respuesta directa se reserva para hilos con poca competencia.

**Dato contradictorio**

Dos fuentes, dos cifras, y explicar por qué (Playtomic 19,4 M vs FIP 35 M de jugadores).

**Pregunta con dato**

"¿Cuál es la pareja con más victorias seguidas de 2026? Pista: no es la nº 1." El gráfico va en la respuesta.

---

## 8. Estrategia de crecimiento en X

**0 → 500 seguidores (meses 1-2)**

- Sin Premium al arrancar. Es un side project y se prueba a coste cero: el dominio ya está pagado, la infraestructura es gratuita y el programador de X también. Lo que se pierde sin Premium es concreto y asumible: las respuestas se ven menos (se compensa citando en vez de responder), el texto se limita a 280 caracteres (los posts del formato ya caben), no se pueden editar posts (revisar dos veces antes de publicar) y parte de la analítica avanzada. Los gráficos como imagen alcanzan igual. Disparador para activar Premium (unos 10 €/mes, el estándar, no Basic): 60 días publicando sin fallar y más de 500 seguidores, o antes si la tracción llega y las citas y respuestas empiezan a quedarse cortas. El programa de recompensas exige Premium, pero sus umbrales quedan mucho más lejos que ese disparador.
- Publicar durante los torneos: es cuando la audiencia de pádel está en X.
- Un post propio al día + 3-5 respuestas con datos a cuentas grandes.
- Lista pública "Pádel: fuentes" con periodistas, jugadores, clubes, marcas y federaciones; seguirlos y responderles con datos.
- Nombre de perfil "PadelDB", handle @padeldb_, avatar con el icono. Bio: "El pádel, en datos. Un gráfico al día y la base de datos abierta detrás. Fuentes: FIP, Premier Padel, CSD, Playtomic." con el enlace a la web.
- Pin: el hilo "cómo funciona el ranking FIP".

**500 → 5.000 (meses 3-6)**

- Las series con nombre crean hábito; hilos quincenales.
- Colaboraciones: gráficos exclusivos para un medio de pádel a cambio de mención y enlace.
- Newsletter activa; LinkedIn semanal con el ángulo de mercado.

**5.000+ (meses 6-12)**

- "Data partner" de un medio o de un torneo.
- Informe anual como pieza de prensa.
- Jugadores compartiendo sus propios datos (etiquetarlos solo cuando el dato les favorezca o sea neutro).
- Spaces tras las finales de los Majors si ya hay comunidad.

**Monetización en X: estado a 15/09/2026.** El reparto de ingresos publicitarios (Creator Revenue Sharing) ha terminado: sin altas nuevas desde el 7 de agosto y cerrado del todo el 7 de septiembre de 2026. Lo sustituye el Original Content Rewards Program, que sí está disponible en España (figura en la lista oficial de países del Help Center). Requisitos para entrar y para seguir cobrando:

- Suscripción Premium, Premium+ o Premium Business (Premium Basic no vale).
- Al menos 500 seguidores verificados.
- Al menos 500.000 impresiones en el Home Timeline procedentes de usuarios verificados en los últimos 90 días; las impresiones en respuestas no cuentan.
- Contenido original: gráficos, análisis y comentario propios sí; contenido copiado, mínimamente modificado, agregado o "creado o publicado por medios automatizados", no. Un post con Community Note deja de cobrar.
- Prohibido pedir interacción ("dale like", "RT si…", "sígueme"); las preguntas a la comunidad sí valen.
- Se cobra por impresiones únicas de usuarios Premium en el Home Timeline, cada dos semanas, con un mínimo de 30 $, vía Stripe fuera de EE. UU. La aceptación no es automática: hay solicitud y revisión.

Lectura para PadelDB: 500.000 impresiones solo de usuarios de pago en 90 días es un listón alto para una cuenta nueva en español; es un objetivo de segundo año, no un plan de negocio. X sigue siendo el canal de crecimiento (es donde está la conversación del circuito y los medios), pero el dinero se planifica fuera de X: marcas, web, newsletter e informes. Dos reglas prácticas que salen de las condiciones: (1) las respuestas con datos sirven para ganar seguidores, pero no suman para el programa, así que el volumen de posts propios debe mantenerse; (2) publicar siempre con persona en el bucle, sin automatizaciones que puedan leerse como bot. Antecedente a vigilar: en marzo de 2026 X anunció, y pausó en 24 horas, dar más peso a las impresiones de la región del creador; si vuelve, favorece a una cuenta española con audiencia española.

---

## 9. Web

**Estructura**

- Home: el gráfico de hoy y acceso a las series.
- Ranking: tabla semanal con movimientos y puntos a defender (interactiva).
- Torneos: ficha por torneo (cuadro, sorpresas, ganancias).
- Parejas: duraciones, h2h.
- Mapa de pistas: por provincia y municipio, con descarga.
- Mercado: pistas, clubes, jugadores, licencias, con serie histórica.
- Datos abiertos: CSV/JSON derivados con licencia CC BY y metodología.
- Metodología y fuentes · Sobre · Contacto y prensa.

**Stack:** Astro + Cloudflare Pages; gráficos en PNG (rápidos, compartibles) con versión interactiva (Plotly) donde aporte; analítica sin cookies; formulario de newsletter en todas las páginas.

**SEO evergreen (10 páginas iniciales)**

1. Cómo funciona el ranking FIP.
2. Prize money de Premier Padel 2026 y cómo se reparte.
3. Cuántas pistas de pádel hay en España (y por provincia).
4. Licencias de pádel en España: evolución 2000-2025.
5. Pádel vs tenis: quién tiene más licencias.
6. Calendario Premier Padel 2026 en datos.
7. Los jugadores más jóvenes del top 100.
8. Las parejas más longevas de la historia reciente.
9. Playtomic vs FIP: cuántos jugadores de pádel hay de verdad.
10. Pádel en el mundo: pistas por país.

**Embeds:** cada gráfico con botón "Insertar" (iframe o PNG con atribución). Los medios que lo usen enlazan: SEO y credibilidad.

---

## 10. Métricas y objetivos

**Objetivos de proceso** (los únicos que dependen solo de ti): 5 posts por semana durante 90 días sin fallar; 3 respuestas con datos al día en semana de torneo; newsletter mensual desde el mes 2; 10 páginas evergreen a los 3 meses.

**Indicadores de resultado** (revisión de los domingos): impresiones semanales; interacciones por post y por serie; seguidores nuevos por semana; % de posts por encima de la mediana; menciones y citas en medios; visitas y suscriptores de la web; y, como termómetro del programa de recompensas, seguidores verificados e impresiones de verificados en 90 días (Creator Studio → Original Content Rewards muestra el estado de elegibilidad).

**Hitos orientativos:** primera cita en un medio → preparar media kit; 2.000 seguidores y 300 suscriptores → primera propuesta a marcas; 500 seguidores verificados y 500.000 impresiones de verificados en 90 días → solicitar el programa de recompensas de X (previsiblemente en el segundo año).

---

## 11. Monetización (hoja de ruta)

| Etapa | Vía | Nota |
|---|---|---|
| 0-6 meses | Ninguna. Construir el activo | Lo que se monetiza después es la serie histórica y la marca |
| 6-12 meses | Patrocinio de una serie ("#RankingLunes con [marca]"); media kit; contenido para marcas en Instagram y X | Marcas de palas y zapatillas, plataformas de reserva, clubes premium. El programa de recompensas de X solo si se alcanzan sus umbrales; no se cuenta con él |
| 12+ meses | Informe anual de pago para clubes e inversores; dashboard o API de datos derivados para medios; consultoría de datos deportivos; suscripción premium de X o de la newsletter | El perfil de ingeniero de datos es la credencial |

Reglas: todo contenido patrocinado se marca como tal; nunca contenido de apuestas (regulación de la publicidad del juego en España y reputación); no vender datos crudos de terceros, solo elaboración propia.

---

## 12. Legal y ética de contenido

- Fuente en cada gráfico y enlace a la metodología en la web.
- Sin fotos de jugadores; sin datos personales de amateurs.
- Los jugadores son figuras públicas y los datos son deportivos: nada de vida personal, lesiones no confirmadas ni especulación.
- Errores: corregir en público citando el post original. La credibilidad es el producto.
- Marca: registrar padeldb.es (el .com está aparcado y en venta a 25.000 $; no compensa) y el handle @padeldb en X, Instagram, Threads, Bluesky, LinkedIn y GitHub desde el primer día, aunque no se usen todavía. Si el handle exacto no está libre en alguna red, usar @padeldb_ o @padeldb_es, nunca una variante del nombre. **En X ya se ha dado este caso**: @padeldb no estaba libre, la cuenta real es @padeldb_ (confirmado 22/09/2026).

---

## 13. Backlog de 30 posts para arrancar

1. Edad media del top 100 masculino y femenino, y evolución en tres años.
2. Nacionalidades del top 100: España vs Argentina vs resto.
3. Pistas por 10.000 habitantes por provincia.
4. El municipio con más pistas per cápita de España.
5. Licencias de pádel 2000-2025: de 6.137 a más de 111.000.
6. Pádel supera al tenis en licencias: cuándo y por cuánto.
7. Licencias por comunidad autónoma y sexo.
8. 19,4 millones vs 35 millones: Playtomic contra FIP.
9. 58.300 pistas en el mundo y 91.000 previstas en 2028.
10. Los cinco arquetipos de mercado y dónde está España.
11. Mercado de equipamiento: 34% anual desde 2019.
12. Puntos a defender del nº 1 en las próximas ocho semanas.
13. Mayor subida y mayor caída del ranking de la semana.
14. Duración media de una pareja del top 20.
15. La pareja activa más longeva.
16. Rupturas de parejas por temporada.
17. Prize money por ronda de un Major, explicado.
18. Ranking de ganancias de 2026.
19. Diferencia de prize money entre categorías.
20. Porcentaje de partidos a tres sets por categoría.
21. Duración media de partido por categoría (si hay dato).
22. Mayores sorpresas de la temporada por diferencia de ranking.
23. El h2h más repetido del año.
24. Drive vs revés: distribución del top 50.
25. Altura media del top 100 y relación con el ranking (con cautela).
26. Interés en Google: pádel vs pickleball por país.
27. Estacionalidad del interés por el pádel en España.
28. Semanas como nº 1 desde la era WPT.
29. Títulos por pareja en la historia reciente.
30. Cómo funciona el ranking FIP (hilo).

---

## 14. Checklist de lanzamiento

- [x] GitHub `padeldb` libre; padeldb.com aparcado (en venta, descartado); padeldb.es sin DNS (confirmar en registrador).
- [x] Confirmar handle en X: @padeldb no estaba libre, cuenta real @padeldb_ (22/09/2026). [ ] Instagram, Threads, Bluesky y LinkedIn (con @padeldb si está libre); sin coincidencias en OEPM y EUIPO.
- [x] Dominio padeldb.es registrado (14/09/2026).
- [x] Handle registrado en X (@padeldb_, 22/09/2026). [ ] Instagram, Threads, Bluesky, LinkedIn y GitHub; correo hola@padeldb.es operativo.
- [x] Logo diseñado: icono + wordmark (PNG en `brand/`, 15/09/2026).
- [x] Juego vectorial generado: icono, vertical, horizontal, negativos, favicon 16/32/180, azul unificado a #0F3463 (`brand/`, 15/09/2026).
- [ ] Avatar y cabecera exportados a los tamaños de cada red; retoque opcional del favicon de 16 px.
- [ ] Cuenta de X lista sin Premium: bio, cabecera con un gráfico, hilo fijado "cómo funciona el ranking". Premium solo cuando salte el disparador de la sección 8.
- [ ] Plantilla de gráfico implementada en `chart_factory` con los tokens de 1.2 (paleta, Space Grotesk / IBM Plex, píldora de serie, pie con fuente y monograma), en versión clara y oscura.
- [ ] 10 posts del backlog generados y programados.
- [ ] Web mínima: home, metodología, tres páginas evergreen, formulario de newsletter.
- [ ] Lista pública en X con las fuentes (medios, jugadores, federaciones, marcas).
- [ ] Analítica activa (X y web) y tabla `rendimiento_posts`.
- [ ] Política de corrección escrita y publicada en la web.

---

## 15. Riesgos

| Riesgo | Mitigación |
|---|---|
| Quemarse a los dos meses | Fábrica automática; la única tarea diaria es aprobar; producción en lote el domingo |
| Cambios de algoritmo en X | Web y newsletter como activos propios; espejos en otras redes |
| Alguien copia el formato | El foso son los datos manuales (lados, parejas) y la serie histórica; publicar más rápido y siempre con fuente |
| Torneos sin cobertura de estadísticas | Series que no dependen de stats: ranking, parejas, mercado, mapas |
| Reacción negativa de un jugador o federación | Solo datos deportivos públicos, tono neutro, corrección inmediata si hay error |
