# PadelDB — Operación y automatización con Cowork

Versión 0.1 · 15 de septiembre de 2026 · Documento vivo

Documentos hermanos: `padel-datos-01-arquitectura.md` (la máquina de datos) y `padel-datos-02-contenido.md` (qué se publica y dónde). Este documento responde a una pregunta concreta: cómo se opera el proyecto cada día con el mínimo tiempo humano, usando Cowork donde aporta y sin usarlo donde no.

---

## 1. Principio: tres capas, y Claude solo donde hace falta juicio

| Capa | Quién | Qué hace | Cuándo |
|---|---|---|---|
| **Máquina** | Código determinista programado (GitHub Actions o jobs de Databricks) | Ingesta, silver, gold, gráficos, borradores de texto, export de la web, cola de candidatos | Solo, a su hora, sin nadie |
| **Agente** | Cowork (tareas programadas en la nube y sesiones a demanda) | Revisar la cola, elegir, corregir el texto, detectar errores, resumir métricas, redactar newsletter | Programado o cuando abras una sesión |
| **Persona** | Tú | Aprobar y publicar; decidir; hablar con marcas y medios | 5-10 minutos al día |

La regla que evita gastar tiempo y cuota: **nada que sea determinista pasa por Claude**. Bajar un ranking, calcular puntos a defender o pintar un gráfico es código y se ejecuta gratis y siempre igual. Claude entra donde hay juicio: si el dato es publicable, cómo contarlo, qué falla, qué ha funcionado esta semana. Y publicar es siempre de la persona, por dos razones: el programa de recompensas de X excluye lo "publicado por medios automatizados", y una cuenta que publica sola acaba diciendo algo que no querías.

---

## 2. Qué herramienta para qué

| Herramienta | Papel en PadelDB | Coste |
|---|---|---|
| **GitHub Actions** (cron) o **Databricks Jobs** | La máquina: todo lo programado del documento de arquitectura (`ingest_*`, `build_silver`, `build_gold`, `content_candidates`, `export_web`) | 0 € |
| **Claude Code** | Construir y mantener el repo: conectores, tests, `chart_factory`, la web. Es la herramienta de desarrollo; no la de operación diaria | Dentro del plan |
| **Cowork: proyecto "PadelDB"** | El espacio de trabajo persistente: instrucciones, archivos de referencia (marca, guía de estilo, alias de jugadores, calendario) y memoria propia | Dentro del plan |
| **Cowork: tareas programadas** | Los ritos que se repiten sin ti: revisión de la cola cada mañana, resumen semanal. Corren en la nube, sin el portátil encendido, y solo pueden usar conectores, URLs y archivos guardados en tu cuenta de Claude, no carpetas locales | Cuota de uso |
| **Cowork: sesiones a demanda** | Lo que necesita tu portátil o tu criterio en directo: programar el lote de la semana en X con el navegador, la semana de torneo, la newsletter del mes | Cuota de uso |
| **Navegador de Cowork / Claude in Chrome** | Rellenar el programador de X y de Instagram contigo delante; leer métricas de tus posts | Requiere la app de escritorio abierta |
| **App móvil de Claude** | Leer el parte de la mañana, contestar una pregunta de Cowork, aprobar. Las sesiones en la nube se abren desde cualquier superficie | 0 |
| **Chat normal** | Preguntas sueltas, ideas, redactar un texto puntual. Consume mucho menos que Cowork | Dentro del plan |

Cowork gasta más cuota que el chat, y el modo "Auto" (aprobación automática con revisión de seguridad) gasta más que el "Manual". En un plan Pro eso importa: las tareas programadas se diseñan cortas y con entradas ya masticadas por la máquina, y el chat se usa para todo lo que no necesite archivos ni ejecución larga.

---

## 3. ¿Un hilo por cuenta? No: un proyecto y una tarea por rito

Organizar Cowork por cuenta (un hilo para X, otro para Instagram, otro para LinkedIn) es la forma natural de pensarlo y la peor de operarlo: el contenido es el mismo gráfico contado tres veces, así que tres hilos significan tres veces el contexto, tres decisiones sobre el mismo dato y tres sitios donde mirar. El canal es el último paso de cada rito, no un hilo aparte.

La organización que funciona:

- **Un proyecto de Cowork, "PadelDB"**, con las instrucciones permanentes, los archivos de referencia y la memoria. Todo lo demás vive dentro.
- **Una tarea programada por rito recurrente** (cola del día, resumen del domingo). Cada ejecución es una sesión nueva que lee el proyecto y la cola; no arrastra basura de días anteriores.
- **Una sesión a demanda por evento** (cada torneo, cada cierre de mes), que se abre con un prompt fijo y se cierra cuando termina el evento. El torneo es la unidad natural de trabajo en pádel, no la red social.
- **Cero sesiones "eternas"**: un hilo con tres meses de historia es lento, caro y acaba mezclando contextos.

Los canales se resuelven dentro del rito con una tabla de salida: el mismo dato produce un texto de X (≤280 caracteres, sin Premium), un pie de Instagram (más largo, con hashtags) y, si toca, la nota de LinkedIn. Cowork los genera de golpe y tú publicas cada uno donde corresponde.

---

## 4. El proyecto "PadelDB" en Cowork

**Archivos del proyecto** (se suben una vez, se actualizan cuando cambien):

- `padel-datos-02-contenido.md` (secciones 1, 4, 5, 7 y 12 son la guía de estilo: marca, series, calendario, plantillas, ética).
- `brand/` con el logo y los tokens (los usa para comprobar que los gráficos llevan pie y píldora).
- `data/manual/alias_jugadores.csv` (grafías correctas de nombres; evita el error más frecuente).
- `calendario_circuito.csv` (fechas de torneos; decide qué rito toca cada día).
- Este documento.

**Instrucciones del proyecto** (texto para pegar tal cual):

> Eres el editor de PadelDB, una cuenta y web de datos de pádel en español. Tu trabajo es revisar, corregir y preparar; nunca publicar. Reglas: (1) Solo se publican cifras que estén en el JSON de la cola o en gold; si un texto contiene un número que no está en los datos, lo marcas y no lo apruebas. (2) Cada gráfico lleva fuente y píldora DB; si falta, lo marcas. (3) Texto de X: máximo 280 caracteres, primera línea con la cifra más sorprendente, segunda con el contexto, tercera con la fuente; formato numérico español (1.254 y 27,8); sin adjetivos sobre jugadores, sin especulación, sin pedir likes, respuestas ni follows; una pregunta a la comunidad es válida. (4) Nombres de jugadores exactamente como en alias_jugadores.csv. (5) Nunca inventes un dato para rellenar un hueco: si no hay dato, el post no sale. (6) Responde siempre en español, breve, y termina cada revisión con un bloque "Para publicar" con los textos finales listos para copiar y los enlaces a las imágenes.

**Memoria del proyecto**: Cowork la actualiza sola con lo que aprende (qué series funcionan, correcciones repetidas). Una vez al mes se lee y se poda.

**Conectores y permisos**: conector de GitHub en modo "Siempre permitir" solo para lectura (la tarea programada necesita leer la cola sin que nadie apruebe cada paso); navegador en modo "Manual" siempre que haya publicación por medio. Modo "Skip" nunca en este proyecto.

---

## 5. Los ritos y cómo se implementa cada uno

| Rito | Tipo | Cadencia | Entrada | Salida | Tiempo humano |
|---|---|---|---|---|---|
| **Cola del día** | Tarea programada en la nube | Diaria, 07:45 | `queue/<fecha>/candidates.json` + PNG (vía GitHub o la URL de la web) | "Parte del día": qué se publica hoy, textos finales por canal, avisos | 3-5 min (leer y aprobar en el móvil) |
| **Publicar** | Persona | Diaria | Parte del día | Post en X (y en Instagram desde el mes 2) | 2-3 min desde el móvil |
| **Lote del domingo** | Sesión en el portátil, con navegador | Semanal | Cola de la semana (mapas, mercado, archivo) + métricas de la semana | Posts de la semana programados en X con el programador nativo; `metrics/<semana>.csv` en el repo; resumen de qué funcionó | 20-30 min |
| **Semana de torneo** | Sesión a demanda | Por torneo (domingo a lunes siguiente) | `torneo_previa`, `torneo_sorpresas`, `ganancias`, `parejas` | Previa, un post por jornada, cierre | 5 min por jornada |
| **Cierre de mes** | Sesión a demanda | Mensual | Los 20-25 posts del mes y sus métricas | Borrador de newsletter, post de LinkedIn de mercado, lista de posts para reciclar | 30 min |
| **Mantenimiento** | Claude Code | Cuando falla algo o hay que añadir | Logs de los jobs, tests | Arreglos en el repo | Variable |

### 5.1 Cola del día (la tarea que hace que el proyecto no se caiga)

Prompt de la tarea programada (pegar en `/schedule`, cadencia diaria a las 07:45, proyecto PadelDB):

> Abre la cola de hoy en https://padeldb.es/cola/hoy.json (o en el repo, carpeta `queue/` con la fecha de hoy). Para cada candidato: comprueba que las cifras del texto coinciden con `values`, que `fuente_txt` no está vacío, que el nombre de la serie es correcto para el día de la semana según `calendario_circuito.csv`, y que los nombres de jugadores coinciden con `alias_jugadores.csv`. Elige el mejor candidato para X (y uno alternativo) según las reglas del proyecto; si hay torneo activo, prioriza la serie de torneo. Reescribe el texto de X si hace falta (≤280 caracteres) y genera la versión de Instagram. Si ningún candidato es publicable, dilo claramente y no propongas nada. Devuelve el bloque "Para publicar" con: hora recomendada, texto de X, pie de Instagram, enlace al PNG 16:9 y al 4:5, número de registro, y una línea de avisos (cifras dudosas, gráficos sin pie, series repetidas esta semana).

Por qué en la nube y no en el portátil: corre aunque el portátil esté cerrado y el parte te espera en el móvil. La condición es que la cola sea accesible sin archivos locales, de ahí que la máquina la deje en el repo y en una URL de la web (ver sección 6).

### 5.2 Publicar desde el móvil (2 minutos)

1. Abrir el parte en la app de Claude, leer "Para publicar".
2. Abrir el enlace al PNG, guardar la imagen.
3. En la app de X: nueva publicación, pegar el texto, adjuntar la imagen, programar a la hora recomendada (o publicar).
4. Marcar el candidato como publicado: contestar en la sesión "publicado #0042 a las 8:30" (Cowork lo anota en la memoria del proyecto y en la cola si tiene acceso de escritura al repo; si no, se reconcilia el domingo).

Sin Premium el texto cabe en 280 caracteres por diseño; los hilos se publican tuit a tuit.

### 5.3 Lote del domingo (con el portátil abierto)

Prompt de sesión (proyecto PadelDB, modo Manual):

> Lee `queue/semana-<n>/` con los candidatos de mapas, mercado y archivo para la semana que viene y las reglas del proyecto. Propón un post por día (lunes ranking se genera solo, no lo toques), con texto de X e Instagram. Cuando yo apruebe cada uno, ábreme el programador de X en el navegador y déjalo relleno (texto, imagen, fecha y hora) para que yo pulse "Programar". Después, entra en mi perfil de X, lee impresiones e interacciones de los posts de la semana pasada y escribe `metrics/<semana>.csv` en el repo con: fecha, número de registro, serie, hora, impresiones, interacciones. Termina con cinco líneas: qué serie funcionó mejor, qué hora, qué gráfico, qué no repetir, qué probar.

Claude rellena y tú pulsas: así la publicación sigue siendo tuya y el programador nativo de X hace el resto de la semana. Con Premium activo, este mismo rito lee la analítica completa; sin Premium, las impresiones por post se ven igual en el perfil.

### 5.4 Semana de torneo

Sesión nueva el domingo anterior con el nombre del torneo. Prompt inicial:

> Empieza el <torneo> (<ciudad>, <fechas>, categoría <X>). Lee `gold/torneo_previa` y `gold/h2h` de la cola y prepara la previa en datos (post + hilo de 5). Cada noche del torneo te pasaré el enlace a `gold/torneo_sorpresas` del día: prepara un solo post con la cifra más llamativa. El lunes siguiente prepara el cierre con `ganancias_temporada` y `parejas_duracion`. Mismas reglas del proyecto; textos listos para copiar.

La sesión se cierra el lunes. El siguiente torneo abre otra. Es la unidad que de verdad tiene sentido para el pádel, y mantiene el contexto pequeño.

### 5.5 Cierre de mes

Sesión a demanda con acceso a `metrics/` y a los posts del mes: borrador de la newsletter "El mes en datos" (cinco gráficos, una lectura), post de LinkedIn con el ángulo de industria, y la lista de los tres posts que mejor funcionaron para reciclarlos con otro ángulo. Después, lectura y poda de la memoria del proyecto.

---

## 6. La cola: el contrato entre la máquina y el agente

La cola es una carpeta por día que escribe la máquina y lee el agente. Vive en el repo (`queue/`) y se publica también, sin enlazar desde ningún menú, en `padeldb.es/cola/<fecha>.json` y `padeldb.es/cola/hoy.json`, para que la tarea programada en la nube la lea sin conectores.

```
queue/2026-09-21/
├── candidates.json
├── 0042_ranking_movimientos_16x9.png
├── 0042_ranking_movimientos_4x5.png
├── 0043_puntos_a_defender_16x9.png
└── 0043_puntos_a_defender_4x5.png
```

`candidates.json` (un objeto por candidato):

```json
{
  "registro": "0042",
  "serie": "#RankingLunes",
  "tabla_gold": "ranking_movimientos_semana",
  "fecha_dato": "2026-09-21",
  "values": {"jugador": "Nombre Apellido", "delta": 14, "posicion": 37},
  "fuente_txt": "FIP · elaboración propia",
  "png_16x9": "https://padeldb.es/cola/2026-09-21/0042_ranking_movimientos_16x9.png",
  "png_4x5": "https://padeldb.es/cola/2026-09-21/0042_ranking_movimientos_4x5.png",
  "borrador_x": "Δ +14 puestos. ...",
  "borrador_ig": "...",
  "publicable": true,
  "estado": "candidato"
}
```

Estados: `candidato` → `aprobado` → `programado` → `publicado` → `medido`. La máquina crea en `candidato`; el agente propone; la persona publica; el lote del domingo escribe `medido` con las métricas. Si un estado no avanza en siete días, el candidato caduca y se archiva.

El número de registro (`registro`) lo asigna la máquina de forma correlativa y es el que aparece en el gráfico: nadie lo inventa ni lo reutiliza.

---

## 7. Publicación: reglas de seguridad

- Publicar es una acción de persona. Cowork prepara, rellena y espera; el clic final es tuyo. Modo "Manual" en cualquier sesión con navegador; "Skip" nunca.
- Nada de API no oficial ni bots que publiquen en X: riesgo de cuenta y exclusión del programa de recompensas.
- Sin Premium, el programador nativo de X desde la web cubre la semana entera; no hace falta ninguna herramienta de pago.
- Una sesión que se comporte raro se para y se pausa la tarea programada antes de investigar.
- Antes de programar en lote, un vistazo a cada gráfico: el error caro no es el texto, es un dato mal dibujado que se comparte cien veces.

---

## 8. Cuota y coste en un plan Pro

- Cowork consume más que el chat. Presupuesto orientativo: una tarea programada corta al día, una sesión de 20-30 minutos el domingo, una por torneo (dos o tres al mes) y una de cierre de mes. Si se acerca al límite, la cola del día pasa a leerse en el chat normal (pegando el JSON) sin perder el rito.
- Las tareas programadas reciben la entrada ya procesada (JSON pequeño, PNG por enlace); no se les pide calcular nada.
- Modo "Auto" solo cuando de verdad ahorre tiempo; gasta más cuota que "Manual".
- La máquina (GitHub Actions o Databricks Free Edition) sigue costando 0 €. X Premium, cuando salte el disparador del documento de contenido.

---

## 9. Semana tipo

| Día | Máquina | Cowork | Tú |
|---|---|---|---|
| Lunes | 07:00 ranking; 07:30 candidatos | 07:45 cola del día | 08:15 aprobar y publicar #RankingLunes (5 min) |
| Martes a viernes | 07:30 candidatos | 07:45 cola del día | Publicar el post del día (3 min); en torneo, el post de la noche (5 min) |
| Sábado | Candidatos de reserva | Nada | Nada (o el post de torneo) |
| Domingo | Métricas de la semana en gold si hay export; candidatos de mapas, mercado y archivo | Lote del domingo (sesión) | 20-30 min: aprobar, programar la semana, leer el resumen |
| Torneo | `ingest_torneo` cada noche | Sesión del torneo | Previa el domingo, un post por noche, cierre el lunes |
| Fin de mes | Export del mes | Cierre de mes (sesión) | 30 min: newsletter y LinkedIn |

Total: unos 25 minutos en días normales de semana, 30 el domingo, algo más en semanas de torneo. Si una semana no hay tiempo, la máquina sigue llenando la cola y no pasa nada por publicar menos; lo que no se pierde es la serie histórica.

---

## 10. Puesta en marcha (una tarde)

> Textos definitivos para pegar (instrucciones, prompt de la tarea programada, hora y cómo marcar lo publicado), adaptados a la cola real: `cowork-puesta-en-marcha.md`. Sustituyen a los de 4 y 5.1 donde discrepen (no existe `calendario_circuito.csv`; la tarea va a las 17:30 por el retraso del cron de GitHub).

1. Crear el proyecto "PadelDB" en Cowork; pegar las instrucciones de la sección 4; subir los archivos de referencia.
2. Conectar GitHub (lectura) y comprobar que Cowork ve `queue/` en el repo. Si el conector no está disponible en tu plan, la vía es la URL de la web: `padeldb.es/cola/hoy.json`.
3. Hacer que la máquina genere una cola de prueba con dos candidatos reales (aunque sea a mano la primera vez).
4. Crear la tarea programada "Cola del día" con el prompt de 5.1; ejecutarla a demanda una vez y corregir el prompt hasta que el parte salga como quieres.
5. Publicar el primer post desde el móvil siguiendo 5.2. Con eso el ciclo entero está probado.
6. El primer domingo, abrir la sesión de lote con el navegador y programar la semana; guardar el prompt que haya funcionado como texto fijo en el proyecto.
7. Revisar la cuota en Ajustes → Uso al final de la primera semana y ajustar el tamaño de las tareas.

---

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| La tarea programada no puede leer la cola (conector caído, URL rota) | Doble vía: repo y URL; si ambas fallan, el parte dice "sin cola" y no propone nada |
| Cowork "mejora" un dato y lo cambia | Instrucción 1 y 5 del proyecto: cifras solo desde `values`; auditar el parte contra el JSON las dos primeras semanas |
| Publicación automática por descuido | Modo Manual con navegador; el programador de X se deja relleno, nunca enviado |
| Cuota del plan agotada a mitad de mes | Tareas cortas; entradas preprocesadas; chat para lo simple; revisar Uso semanalmente |
| Sesiones que se convierten en hilos eternos | Una tarea por rito, una sesión por torneo, cierre de mes; nada dura más de una semana |
| Dependencia de Cowork | El ciclo funciona sin él: la máquina deja la cola y los borradores; publicar a mano desde el JSON sigue costando cinco minutos |
