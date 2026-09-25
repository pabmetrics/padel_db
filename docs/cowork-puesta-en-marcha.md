# PadelDB — Puesta en marcha de Cowork (textos listos para pegar)

Versión 0.1 · 22 de septiembre de 2026. Desarrolla la sección 10 de
`padel-datos-03-operacion.md` con lo que el repo ofrece de verdad hoy. Si hay
discrepancia con doc 03 §4-§5.1, manda este documento: aquellos textos se
escribieron antes de que existiera la cola real.

Diferencias con doc 03:

- No existe `calendario_circuito.csv`. Qué series tocan cada día lo decide
  `content/copy_factory/calendario.py`, y el resultado se publica en
  `padeldb.es/cola/indice.json` (`series_previstas`). Cowork lee eso.
- La hora: el cron de GitHub Actions se dispara con hasta ~5 h de retraso
  (medido el 21 y el 22/09/2026: `content_candidates` programado a las 06:30
  UTC corrió a las 11:55 UTC). Una tarea de Cowork a las 07:45 leería casi
  siempre la cola vacía. Se programa por la tarde y se publica en la franja de
  19:30-21:30 (doc 02 §6).
- `registro` lleva almohadilla (`"#0083"`) y cada candidato trae `avisos`
  (lista de problemas que ya detectó la máquina).

---

## 1. Qué publica la máquina

| URL | Qué es |
|---|---|
| `https://padeldb.es/cola/indice.json` | `fecha` (UTC), `actualizado_utc`, `series_previstas`, `candidatos_hoy`, `publicables_hoy`, `dias` con cola |
| `https://padeldb.es/cola/hoy.json` | Candidatos de hoy, y solo de hoy (`[]` si no hay) |
| `https://padeldb.es/cola/<fecha>.json` | Cola de un día concreto (últimos 14 días) |
| `https://padeldb.es/cola/<fecha>/<fichero>.png` | Gráficos 16:9 y 4:5 enlazados desde cada candidato |

La cola no se bloquea en `robots.txt` (el fetcher de Cowork lo respeta y
devuelve `ROBOTS_DISALLOWED`, pasó el 25/09/2026); queda fuera de los
buscadores solo con la cabecera `X-Robots-Tag: noindex, nofollow` de
`site/public/_headers`.

Cadena diaria: `content_candidates` → (al terminar) `export_web` → commit →
Cloudflare Pages reconstruye la web (1-2 min). Nada de esto publica en X.

Cómo leer `indice.json`:

| Caso | Significado |
|---|---|
| `fecha` distinta de hoy | El export de hoy aún no ha corrido |
| `series_previstas` vacío | Hoy no toca ninguna serie (fin de semana, martes impar…) |
| `series_previstas` con series y `candidatos_hoy` = 0 | Tocaba y la cola no se ha generado, o ha fallado |
| `publicables_hoy` = 0 con candidatos | Hay candidatos, pero la máquina los marcó como no publicables (ver `avisos`) |

---

## 2. Proyecto "PadelDB" en Cowork

**Archivos del proyecto** (subir una vez y actualizar cuando cambien):

- `docs/padel-datos-02-contenido.md`
- `docs/padel-datos-03-operacion.md` y este documento
- `data/manual/alias_jugadores.csv`
- `brand/padeldb-favicon.svg` (para reconocer el icono del pie)

**Instrucciones del proyecto** (pegar tal cual):

> Eres el editor de PadelDB (@padeldb_ en X), una cuenta y web de datos de pádel en español. Tu trabajo es revisar, corregir y preparar; nunca publicar ni pulsar "Publicar" o "Programar" en ninguna red.
>
> Reglas:
> 1. Solo valen las cifras que estén en `values` o en `fuente_txt` del candidato. Si un texto contiene un número que no está ahí, lo marcas y no lo apruebas.
> 2. Solo se proponen candidatos con `publicable: true` y `estado: "candidato"`. Los que traen `avisos` se mencionan, pero no se proponen salvo que el aviso sea claramente menor, y en ese caso se dice por qué.
> 3. Texto de X: máximo 280 caracteres (sin Premium). Primera línea con la cifra más sorprendente, segunda con el contexto; cierra con una pregunta concreta anclada en el dato solo si el dato la sostiene. En los posts de movimiento (#RankingLunes, cierres) la primera línea empieza por "Δ +N" o "Δ −N". Formato numérico español (1.254 y 27,8). Como mucho un emoji, al inicio. Sin adjetivos sobre jugadores, sin especulación, sin pedir likes, RT, respuestas ni follows ("¿qué opinas?" tampoco).
> 4. La fuente va en el gráfico. En el texto de X, solo si cabe sin recortar el dato.
> 5. Nombres de jugadores exactamente como en `alias_jugadores.csv` (columna `nombre_canonico`).
> 6. Nunca inventes un dato para rellenar un hueco: si no hay dato, no hay post.
> 7. Responde siempre en español y breve. Termina cada revisión con un bloque "Para publicar" con los textos finales listos para copiar y los enlaces a las imágenes.

**Conectores y permisos**: la tarea diaria no necesita el conector de GitHub, porque lee la web pública. Si se conecta, que sea solo de lectura. Usa el modo "Manual" en cualquier sesión con navegador y nunca "Skip".

---

## 3. Tarea programada "Cola del día"

- **Proyecto:** PadelDB
- **Cadencia:** diaria, 17:30 (hora de Madrid). Hay margen de sobra sobre el retraso de GitHub, y el post sale en la franja de 19:30-21:30.
- **Prompt** (pegar en `/schedule`):

> Lee https://padeldb.es/cola/indice.json y https://padeldb.es/cola/hoy.json.
>
> 1. Si `indice.fecha` no es la fecha de hoy, responde solo: "Sin cola: el export de hoy no ha corrido (última actualización: <actualizado_utc>)". No propongas nada.
> 2. Si `series_previstas` está vacío, responde solo: "Hoy no toca serie." y, si en `dias` hay algún día de los últimos 6 con candidatos `publicable: true` y `estado: "candidato"` (léelo en https://padeldb.es/cola/<fecha>.json), menciónalo como posible reserva en una línea.
> 3. Si hay series previstas pero `hoy.json` está vacío, responde: "Sin cola: tocaban <series_previstas> y no se ha generado ningún candidato. Revisar el job content_candidates en GitHub Actions." No propongas nada.
> 4. Si hay candidatos, revisa cada uno siguiendo las reglas del proyecto: que las cifras de `borrador_x` y `borrador_ig` estén en `values`/`fuente_txt`, que `fuente_txt` no esté vacío, que los nombres coincidan con `alias_jugadores.csv`, y lee sus `avisos`. Descarta los que tengan `publicable: false` o un `estado` distinto de "candidato".
> 5. Elige el mejor candidato para X y, si lo hay, uno alternativo. Si hay torneo activo (serie "El torneo en datos" o "Previa en datos"), prioriza el de torneo. Reescribe el texto de X si hace falta (≤280 caracteres) y escribe el pie de Instagram (más largo, con 3-5 hashtags).
> 6. Devuelve el bloque "Para publicar" con: número de registro, serie, hora recomendada (entre las 19:30 y las 21:30), texto de X, pie de Instagram, enlace al PNG 16:9 (`png_16x9`) y al 4:5 (`png_4x5`), y una línea de avisos (cifras dudosas, avisos de la máquina, serie repetida esta semana). Si ningún candidato es publicable, dilo claramente y no propongas nada.

Antes de activarla, ejecútala una vez a demanda (doc 03 §10, paso 4) y
corrige el prompt hasta que el parte salga como quieres.

---

## 4. Cerrar el ciclo: marcar lo publicado

Cowork solo lee, así que no puede escribir en el repo. Tras publicar, anota el
post en el repo (es lo que alimenta `rendimiento_posts`):

```
python -m content.copy_factory.cola --registro "#0087" --url https://x.com/padeldb_/status/... --fecha 2026-09-24 --hora 20:15
```

Después, commit y push. Con eso el candidato pasa a `estado: "publicado"`,
el siguiente export lo refleja en la cola pública y Cowork deja de proponerlo.
Si un día no da tiempo, se puede anotar el domingo en el lote semanal.

---

## 5. Gráficos a medida (desde el chat de Cowork)

Para lo que no es una serie fija: una convocatoria, una noticia, una
«respuesta con datos» (doc 02 §7). Cowork **no dibuja**: escribe un pedido
JSON y lo lanza con el workflow `adhoc_chart` de GitHub Actions (input
`pedido`). La máquina lo valida contra gold (solo filas publicables), lo
dibuja con la plantilla de marca, le da número de registro y lo deja en la
cola de hoy con su borrador. En uno o dos minutos está en
`padeldb.es/cola/hoy.json` y se revisa como cualquier otro candidato.

Tipos disponibles (`content/chart_factory/adhoc.py`):

| Pedido | Qué dibuja |
|---|---|
| `{"tipo": "jugadores", "jugadores": ["Alejandro Galan", "Arturo Coello", …], "metrica": "forma_reciente"}` | Barras de % de victorias en 8 semanas (V/P) y posición en el ranking, de 2 a 12 jugadores. `"metrica": "ganancias"` para ganancias de la temporada |
| `{"tipo": "perfil_top100", "sexo": "M", "dimension": "altura_cm"}` | Posición de cada jugador del top 100 por tramo de altura (o `"edad"`), con la mediana de cada tramo |

Opcionales: `"titulo"` (máx. 10 palabras), `"subtitulo"`, `"serie"` (texto
de la marca de serie; por defecto «A medida») y `"contexto"`: una frase que
gold no trae y aporta quien pide («Convocatoria de España para el Mundial
2026»). El contexto permite que título y texto hablen del Mundial; queda en
el candidato como aviso para comprobarlo al revisar.

Reglas que aplica la máquina (el pedido se rechaza si no las cumple):

- Nombres: exactos, sin acentos o parte del nombre si solo encaja un
  jugador («Gemma Triay» → «Gemma Triay Pons»). Los apodos («Paquito
  Navarro») no valen: se rechazan con sugerencias, y si se repiten van a
  `alias_jugadores.csv`. Para acertar a la primera, Cowork puede mirar los
  nombres en `https://padeldb.es/datos/perfil_top100.json` o
  `forma_reciente.json`.
- Título y subtítulo: sin cifras que no salgan de los datos, sin
  valoraciones ni especulación (mismas listas que el texto de X).
- Un jugador sin fila publicable queda fuera del gráfico, con aviso.

Texto para el proyecto de Cowork (añadir a las instrucciones):

> Cuando te pida un gráfico que no es de una serie fija, no lo dibujes tú:
> escribe el pedido JSON según la sección 5 de `cowork-puesta-en-marcha.md`,
> enséñamelo y, cuando lo apruebe, lanza el workflow `adhoc_chart` del repo
> `pabmetrics/padel_db` en `main` con ese pedido. Si el workflow falla, el
> motivo está en su log («PEDIDO RECHAZADO: …»): corrige el pedido y
> vuelve a lanzarlo. Cuando termine, lee `https://padeldb.es/cola/hoy.json`
> y prepara el bloque "Para publicar" de ese candidato.

**Pendiente de comprobar:** que el conector de GitHub de Cowork pueda lanzar
un workflow (`workflow_dispatch`). Si no puede, las alternativas son una
sesión de Cowork en el portátil que ejecute
`python -m content.chart_factory.adhoc '<pedido>'` (con el `.env`), o
lanzarlo a mano desde la pestaña Actions de GitHub (Run workflow → pegar el
pedido). Para ver cómo queda sin gastar registro ni llamar a la API:
`python -m content.chart_factory.adhoc '<pedido>' --previa /tmp/previa`.

---

## 6. Comprobación rápida

- `https://padeldb.es/cola/indice.json` responde 200 y su `fecha` es la de hoy.
- `https://padeldb.es/robots.txt` no contiene `Disallow: /cola/`.
- En un día con serie (miércoles, jueves, lunes), `hoy.json` trae candidatos con `png_16x9` accesibles.
- La ejecución a demanda de la tarea devuelve el bloque "Para publicar", o una de las tres respuestas de "Sin cola"/"Hoy no toca serie".
