# Fase 3 — pistas y territorio: fuentes y limitaciones

Explorado el 18/09/2026 (sesión nocturna sin supervisión directa). Primera versión de `pistas_municipio` del doc de arquitectura, aunque a nivel **provincia**, no municipio.

## Fuentes

- **F9 (OpenStreetMap, Overpass API)**: `ingest/osm/pistas.py` — todos los elementos con `sport=padel` en España (nodos y ways), 7.628 elementos reales el 18/09/2026. `ingest/osm/provincias.py` — límites administrativos de las 50 provincias (`admin_level=6`), con geometría completa para el cruce espacial.
- **F10 (INE, API JSON wstempus)**: `ingest/ine/poblacion_provincia.py` — tabla 2852, población por provincia. **Vintage real: 2021**, el último año publicado en esta tabla concreta. Requiere un `User-Agent` de navegador: con el de `httpx` por defecto, la API de INE devuelve 403.

## Por qué provincia y no municipio (todavía)

El doc de arquitectura pide `dim_municipio` con `codigo_ine`. Se intentó la tabla de INE "Población por sexo, municipios y país de nacimiento" (identificador API 33791), pero solo devolvió datos de la provincia de Girona en la consulta de prueba — no da confianza suficiente como para asumir que cubre toda España sin verificarlo caso por caso, y equivocarse aquí sería servir un mapa con provincias enteras vacías. Se ha preferido una tabla provincial verificada (2852, cobertura confirmada de las 52 provincias) a una municipal sin confirmar. Pasar a municipio es la mejora natural de la próxima sesión: hace falta localizar la tabla de INE correcta (o usar el fichero de Padrón municipal descargable en Excel, que si cubre todos los municipios) y límites de OSM a nivel de municipio (`admin_level=8`), más pesados de consultar.

## Cruce espacial

`transform/build_dim_provincia.py` reconstruye los polígonos de provincia con `shapely.ops.polygonize` a partir de los tramos de `way` de cada relación de límite administrativo de OSM — el método estándar para esto, no una aproximación con centroides o cajas delimitadoras.

`transform/build_fact_pistas.py` hace el `point-in-polygon` real (no una asignación por cercanía ni por nombre de dirección) de cada elemento de pádel a su provincia. 7.617 de 7.628 elementos (99,9%) caen dentro de alguna de las 50 provincias; los 11 restantes quedan sin asignar, probablemente en la costa o en islas pequeñas mal delimitadas en OSM.

## Cruce de nombres INE ↔ OSM

INE y OSM no siempre escriben igual el nombre de una provincia ("Alicante/Alacant" vs "Alacant / Alicante"; "Rioja, La" vs "La Rioja"). Se resuelve comparando **conjuntos de palabras** normalizadas (sin acentos, sin mayúsculas) en vez de la cadena exacta — así el orden de las palabras no importa. Dos casos no se resuelven así porque OSM usa un nombre descriptivo que INE no usa ("Comunidad de Madrid" en vez de "Madrid", "Región de Murcia" en vez de "Murcia") y necesitan un alias explícito en el código. Las 50 provincias quedan cruzadas.

## "Pistas" vs "clubes": lo que OSM no distingue de forma fiable

OSM mezcla dos formas de mapear lo mismo: unos usuarios etiquetan cada pista individual (`leisure=pitch`, un `way` por pista), otros etiquetan el club entero como un único punto (`leisure=sports_centre`). Contar elementos en bruto sobrestima en las zonas mapeadas pista a pista e infraestima en las mapeadas solo como club. `fact_pistas` guarda tres cifras por separado en vez de mezclarlas en una sola "verdad":

- `n_elementos_osm`: todo lo etiquetado `sport=padel`, la cifra más completa pero mezclando pistas y clubes.
- `n_elementos_pitch`: solo lo etiquetado como pista individual — infraestima donde solo se mapeó el club.
- `n_ubicaciones`: coordenadas agrupadas a ~100 m, una cota inferior razonable de "número de clubes" distintos.

`elementos_por_10000_hab` en el gold usa `n_elementos_osm` porque es la métrica más completa de las tres, con esta salvedad documentada. La cobertura de OSM además es desigual por zona (doc 01 §6, riesgo ya anticipado) — más completa en ciudades grandes, más floja en zonas rurales.

## F7 (CSD, licencias) — bloqueado por un problema real del propio sitio

Probado el 18/09/2026: `www.csd.gob.es` da error de certificado TLS (`certificate signature failure`) tanto con `httpx` como con la herramienta de lectura web — no es un problema de este proyecto, el sitio del CSD tiene un certificado mal encadenado ahora mismo. No se ha forzado sin verificar el certificado (no es buena práctica dejarlo así en un conector que corre solo). Pendiente de reintentar más adelante, por si es un fallo temporal de su lado.

## F8 (FEP, padelfederacion.es) — explorado, aparcado por baja confianza

El sitio funciona (es una web antigua tipo ASP.NET con redirección por meta-refresh, no HTTP — hay que pedir `/Home` directamente, no la raíz). Pero el doc de arquitectura ya avisaba de que esta fuente son "licencias al día (noticias)" — datos mencionados en artículos de prensa de la propia federación, sin una tabla ni endpoint estructurado. Montar un scraper que interprete cifras de licencias dentro de texto libre de noticias tiene mucha más probabilidad de arrastrar un número mal leído que las fuentes tabulares que sí se han usado esta sesión. Se ha preferido no montarlo esta noche a arriesgar un dato de licencias mal extraído.
