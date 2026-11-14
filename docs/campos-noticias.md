# La noticia en datos (14/11/2026)

Un gráfico al día conectado a lo que cuenta la prensa ese día. La noticia
da el "por qué hoy"; las cifras salen siempre de gold.

## Cadena

1. `ingest/noticias/rss.py` → `bronze/noticias/dt=<fecha>/`: titulares de
   las últimas 24 h de Google News por RSS (consultas "pádel",
   "Premier Padel", "pádel torneo"). Solo título, enlace, medio y fecha;
   nunca el cuerpo del artículo. Público, sin clave.
2. `transform/build_fact_noticia.py` → `silver/fact_noticia/dt=<fecha>/`:
   - **Jugadores**, sin modelo de lenguaje: el top 100 del último ranking
     (H y M), buscados por nombre completo, alias
     (`data/manual/alias_jugadores.csv`) o tramos de apellidos ("triay
     pons", "triay"). Fuera las claves que valen para dos jugadores
     ("Jensen": Claudia y Enzo), las partículas y los nombres de pila
     sueltos. Mejor no reconocer a nadie que atribuir mal la noticia.
   - **Tipo**, por palabras clave: parejas, eliminación, resultado,
     ranking, dinero. Si un titular con jugadores no casa con ninguna, se
     pregunta a Gemini en una sola llamada para todos (capa gratuita: los
     titulares son públicos). Sin Gemini, ese titular se queda sin usar.
   - **Salud y vida personal se descartan siempre** (doc 02 §12), también
     si el tipo lo decide Gemini.
3. `content/copy_factory/noticias.py`, desde `candidatos.py` (cada día,
   también en fin de semana; no con `--serie`):
   - Junta los titulares que comparten algún jugador (la misma historia en
     varios medios, o desde los dos lados) y ordena por tipo, número de
     titulares y ranking de los protagonistas.
   - Completa a cada jugador con su pareja actual, la de su último partido
     de Premier Padel (`fact_partido_stats`). No se usa `dim_pareja`: sus
     tramos "activos" salen de torneos sueltos y el 14/11 no tenía activa a
     Tapia/Coello.
   - No repite enlace ni jugadores de una noticia de los 3 días anteriores.
   - La historia más fuerte se convierte en un pedido de gráfico a medida
     (`adhoc.py`). Si los protagonistas son exactamente dos parejas, primero
     su **cara a cara** (tipo "h2h"); si nunca se han enfrentado, o no son
     dos parejas, la **forma al día** de los protagonistas (tipo
     "jugadores", métrica `forma_al_dia`), o sus ganancias de 2026 si la
     noticia va de premios. Serie "La noticia en datos", una al día
     (`MAX_POR_DIA`).
   - Las dos fuentes de partidos se juntan sin duplicar: padelapi
     (`fact_partido`, lunes) y Premier Padel (`fact_partido_stats`, a
     diario), así que en semana de torneo entra el partido de ayer.

## Qué lleva el candidato

- `noticia`: titular principal, enlace, medio, tipo, de dónde sale el tipo
  (`palabras`/`gemini`), otros titulares de la misma historia y
  `jugador_ids`. Es para quien revisa: comprobar que la noticia es la que
  parece antes de publicar.
- El borrador **no** recibe el titular, solo un contexto neutro ("Son
  noticia hoy por una eliminación"): los titulares de prensa valoran
  ("histórico", "arrollan") y eso no puede pasar al texto de PadelDB.

## Workflow

Dentro de `ingest_torneo_previa.yml` (diario, 07:00 UTC), que dispara
`content_candidates` al terminar. Los dos pasos llevan `continue-on-error`:
sin noticias, la cola sale igual.

## Límites conocidos

- Fuera de Premier Padel (FIP Tour), los partidos de la semana no entran
  hasta el lunes: solo Premier se ingiere a diario.
- `forma_al_dia` cuenta como mucho un partido por jugador y día (algún
  jugador viene sin identificar en Premier y el mismo partido no casaría
  por sus cuatro ids): dos partidos el mismo día cuentan como uno.
- Sin probar contra el RSS real desde el mini PC (sin permiso de red allí):
  la primera ejecución en Actions es la prueba.
