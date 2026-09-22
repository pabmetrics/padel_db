# PadelDB — Arquitectura de datos y plan de montaje

Versión 0.3 · septiembre 2026 · Documento vivo (actualizar en cada fase). Marca del proyecto: PadelDB (@padeldb_ en X; ver identidad completa en el documento hermano). La base de datos que describe este documento es, literalmente, el producto que da nombre a la marca: el export de gold es la sección pública de datos abiertos de la web.

Documento hermano: `padel-datos-02-contenido.md` (estructura de contenido, canales y calendario). Las tablas **gold** de aquí son las que alimentan las series de contenido de allí.

---

## 1. Objetivo del sistema

Producir, de forma automática y reproducible, los datos que alimentan una cuenta de X y una web sobre pádel con **un gráfico al día**. El sistema debe:

- Ingerir todas las fuentes sin intervención manual, salvo las curadas (lado de pista, reglamentos, informes anuales).
- Conservar el histórico desde el primer día (snapshots). La serie temporal propia es el activo que nadie más tendrá en español.
- Exponer tablas gold listas para gráfico: **una fila = un dato publicable**.
- Costar cerca de cero y sobrevivir a que cambie un endpoint.
- Servir de portfolio: Databricks, Delta Lake, medallón, calidad de datos, publicación automatizada.

Principios: bronze append-only; IDs canónicos propios; toda métrica trazable a su fuente; nada de datos personales de aficionados; atribución en cada salida.

---

## 2. Inventario de fuentes

| # | Fuente | Qué aporta | Método | Frecuencia | Coste | Riesgo |
|---|---|---|---|---|---|---|
| F1 | premierpadel.com (endpoints JSON públicos) vía SDK `pypadel` | Rankings, calendario, cuadros, resultados, marcadores en directo, estadísticas de partido, perfiles, noticias | SDK Python, sin clave | Semanal (ranking), diaria en torneo | 0 | Endpoints no documentados: pueden cambiar. Aislar en un conector |
| F2 | padelapi.org | Premier Padel (Major, P1, P2, Finals) + FIP Tour (Platinum→Bronze) + archivo WPT; resultados, punto a punto, rankings, stats por jugador; IDs consistentes entre circuitos | REST con Bearer token | Diaria/semanal | Free: 50.000 peticiones/mes, resultados de los últimos 6 meses, ranking actual. Histórico y evolución de rankings: de pago | Dependencia de un tercero; cuota |
| F3 | padelfip.com | Ranking oficial FIP, FIP Tour (Platinum→Promises), perfiles | Scraper propio (existe también un actor de Apify) | Semanal | 0 | HTML cambia; respetar robots.txt y ritmo |
| F4 | Reglamentos FIP / Premier Padel (PDF) | Tabla de puntos por ronda y categoría; prize money por torneo y reparto por ronda | Manual → CSV versionado por temporada | Anual + cambios | 0 | Cambios de normativa a mitad de año |
| F5 | Playtomic Global Padel Report (PDF anual, gratuito) | Pistas, clubes y jugadores por país; arquetipos de mercado; mercado de equipamiento | Manual → CSV | Anual (mayo) | 0 | Metodología cambia entre ediciones |
| F6 | FIP World Padel Report | Cifras oficiales FIP (jugadores, países) | Manual → CSV | Anual | 0 | Contradice a F5 (19,4 M vs 35 M jugadores): documentar, no mezclar |
| F7 | Estadística de Deporte Federado (CSD / Ministerio) | Licencias por federación, sexo y CCAA, serie anual desde 2013 | Excel descargable | Anual | 0 | Publicación con ~1 año de retraso |
| F8 | FEP (padelfederacion.es) | Licencias al día (noticias), rankings FEP, circuitos, campeonatos | Scraper | Mensual | 0 | HTML sin estructura |
| F9 | OpenStreetMap (Overpass API) | Pistas y clubes geolocalizados (`sport=padel`, `leisure=pitch`) | Query Overpass | Mensual | 0 | Cobertura incompleta y desigual por zonas |
| F10 | INE (Padrón municipal, API JSON) | Población por municipio | API | Anual | 0 | Cambios de códigos/municipios |
| F11 | Google Places API | Clubes por provincia (complemento a F9) | API | Trimestral | Cuota gratuita mensual (verificar) | Límites y ToS |
| F12 | Google Trends | Interés por país/provincia; pádel vs pickleball vs tenis | Export CSV manual o `pytrends` (no oficial) | Mensual | 0 | Bloqueos; índice relativo, no absoluto |
| F13 | Curación manual: lado de pista, parejas oficiales, alias de nombres | Variables que no existen en ninguna fuente | CSV en repo, con fecha y autor | Continua | Tiempo | Es el foso competitivo: mantenerlo |
| F14 | Playtomic / Matchi (disponibilidad, precios) | Precio medio de pista por ciudad | Scraper (zona gris de ToS) | Opcional | 0 | Legal/ToS. Solo agregados, muestreo pequeño, sin nombrar clubes, sin datos de usuarios |
| F15 | Padel Scientific Journal, dataset PADELVIC, toolkits de visión | Estudios y datasets académicos | Manual | Ocasional | 0 | Solo uso divulgativo |

Regla de precedencia: **F1** es la fuente primaria del circuito; **F2** valida y rellena (stats, histórico); **F3** es la referencia "oficial" para ranking cuando F1 y F2 discrepan.

---

## 3. Arquitectura lógica

```
Fuentes (F1..F15) ──► BRONZE  raw, snapshots, append-only
                         │
                         ▼
                      SILVER  entidades canónicas, calidad, SCD
                         │
                         ▼
                       GOLD   una fila = un dato publicable
                         │
              ┌──────────┴───────────┐
              ▼                      ▼
     Fábrica de gráficos      Export web (JSON/Parquet estáticos)
              │                      │
              ▼                      ▼
     Cola de publicación      Sitio estático (Astro / Cloudflare Pages)
     (Typefully / n8n → X)
              │
              ▼
     Métricas de rendimiento (X analytics, web) ──► bronze ──► gold.rendimiento_posts
```

### 3.1 Bronze

- Un directorio/tabla por fuente y tipo: `bronze/premierpadel/rankings/dt=2026-09-14/…json`.
- Cada fichero con metadatos: `source`, `endpoint`, `ingest_ts`, `sha256`, `params`.
- Nunca se sobreescribe. Un snapshot semanal de ranking durante 12 meses equivale a la serie histórica que padelapi cobra.
- Los CSV manuales (F4, F5, F6, F13) viven en el repo (`data/manual/`) y se cargan a bronze con número de versión.

### 3.2 Silver — modelo de datos

Tablas Delta. Claves propias; los IDs de fuente solo en la tabla de mapeo.

| Tabla | Clave | Columnas principales | Origen |
|---|---|---|---|
| `dim_jugador` | `jugador_id` | `nombre_canonico`, `sexo`, `nacionalidad`, `fecha_nac`, `altura_cm`, `mano`, `lado_pista` (drive/revés) + `lado_desde`, `activo` | F1, F2, F3 + F13 |
| `map_jugador_fuente` | (`fuente`, `id_fuente`) | `nombre_en_fuente`, `jugador_id`, `vigente` | Todas |
| `dim_pareja` | `pareja_id` | `jugador_1_id`, `jugador_2_id` (ordenados), `fecha_inicio`, `fecha_fin`, `n_torneos`, `activa` (SCD tipo 2) | Derivada de cuadros |
| `dim_torneo` | `torneo_id` | `nombre`, `circuito` (Premier Padel / FIP Tour / WPT), `categoria`, `sexo`, `ciudad`, `pais`, `fecha_ini`, `fecha_fin`, `temporada`, `prize_money_total`, `indoor` | F1, F2, F3 |
| `dim_puntos_categoria` | (`circuito`, `categoria`, `temporada`, `ronda`) | `puntos`, `prize_money_pareja` | F4 |
| `fact_partido` | `partido_id` | `torneo_id`, `fase` (qualy/main), `ronda`, `pareja_a_id`, `pareja_b_id`, `pareja_ganadora_id`, `sets_a/b`, `juegos_a/b`, `marcador_txt`, `duracion_min`, `walkover`, `abandono`, `fecha` | F1, F2 |
| `fact_partido_stats` | (`partido_id`, `pareja_id`, `set_num`) | Métricas disponibles: saque, winners, errores… (solo Majors/P1 suelen tener cobertura completa) | F1, F2 |
| `fact_ranking_semanal` | (`fecha_ranking`, `circuito`, `sexo`, `jugador_id`) | `posicion`, `puntos`, `torneos_computados` | F1, F3 |
| `fact_resultado_torneo` | (`torneo_id`, `pareja_id`) | `ronda_alcanzada`, `puntos_ganados`, `prize_money` | Derivada: última ronda × `dim_puntos_categoria` |
| `fact_licencias` | (`anio`, `federacion`, `ccaa`, `sexo`) | `licencias` | F7, F8 |
| `dim_municipio` | `codigo_ine` | `municipio`, `provincia`, `ccaa`, `poblacion`, `anio_padron`, `lat`, `lon` | F10 |
| `fact_pistas` | (`snapshot_fecha`, `codigo_ine`, `fuente`) | `n_pistas`, `n_clubes` | F9, F11 |
| `fact_mercado_pais` | (`anio`, `pais`, `fuente`) | `pistas`, `clubes`, `jugadores`, `arquetipo` (F5 y F6 nunca sumadas) | F5, F6 |
| `fact_trends` | (`mes`, `geo`, `termino`) | `indice` | F12 |

Reglas de derivación:

- **Parejas**: una pareja "nace" en el primer torneo que juegan juntos y "muere" cuando uno de los dos juega otro torneo con otro compañero. Se guarda historial completo (SCD2).
- **Resultados de torneo**: a partir de `fact_partido`, la última ronda ganada por cada pareja, cruzada con la tabla de puntos y prize money de esa temporada y categoría.
- **Fusiones de jugador**: padelapi devuelve una redirección 302 cuando fusiona dos fichas; el conector sigue la redirección y actualiza `map_jugador_fuente`.

### 3.3 Gold — una tabla por formato de contenido

| Tabla gold | Contenido que alimenta | Refresco |
|---|---|---|
| `ranking_movimientos_semana` | Subidas/bajadas en top 20/50/100, entradas y salidas, mayor salto | Lunes |
| `puntos_a_defender` | Puntos que caducan por jugador en las próximas 4/8 semanas (ranking rodante) | Lunes |
| `ganancias_temporada` | Prize money acumulado por jugador y pareja; ranking de ganancias | Tras cada torneo |
| `parejas_duracion` | Duración media, rupturas por temporada, pareja activa más longeva, "divorcios" del mes | Tras cada torneo |
| `torneo_previa` | Cuadro, cabezas de serie, puntos a defender de los favoritos, h2h de los cruces | Día antes del torneo |
| `torneo_sorpresas` | Derrotas por diferencia de ranking, favoritos eliminados por ronda | Diario en torneo |
| `h2h` | Historial entre parejas y entre jugadores | Tras cada torneo |
| `perfil_top100` | Edad, nacionalidad, altura, lado de pista: distribución y evolución | Mensual |
| `forma_reciente` | % victorias últimas 8 semanas, rachas | Semanal |
| `dominio_sets` | % sets y juegos ganados, % partidos a 3 sets, duración media | Tras cada torneo |
| `pistas_municipio` | Pistas por municipio/provincia y por 10.000 habitantes; datos para mapas | Mensual |
| `licencias_ccaa` | Serie de licencias por CCAA y sexo; pádel vs tenis | Anual |
| `mercado_pais` | Pistas/clubes/jugadores por país, arquetipos, crecimiento | Anual |
| `trends_geo` | Interés relativo por país/provincia, estacionalidad | Mensual |
| `archivo_eras` | Dominio histórico WPT→Premier: semanas como nº1, títulos por pareja | Trimestral |
| `rendimiento_posts` | Impresiones e interacciones por serie, día y hora (bucle de mejora) | Semanal |

Toda fila gold lleva: `fecha_dato`, `metrica`, `valor`, dimensiones, `fuente_txt` (para el pie del gráfico) y `publicable` (flag tras control de calidad).

### 3.4 Fábrica de contenido (capa de salida)

- `content/chart_factory/`: una función por formato (`ranking_moves`, `map_pistas`, `earnings_bar`, `pair_timeline`…) con plantilla de marca: paleta, tipografía, marca de agua con el handle, pie "Fuente: FIP / Premier Padel · elaboración propia". Salidas: PNG 1600×900 (X), PNG 1080×1350 (Instagram) y JSON de Plotly (web).
- `content/copy_factory/`: genera el texto del post con la API de Claude a partir de la fila gold + plantilla de la serie. Reglas duras en el prompt: solo cifras de la fila, sin adjetivos sobre personas, sin especulación, siempre fuente. Un humano aprueba en una cola (10 minutos al día).
- `publish/`: al arrancar, el programador nativo de X (gratuito, desde la web): la fábrica deja el gráfico y el texto en la cola y una persona los revisa y programa. Typefully o n8n con nodo de X solo si el volumen lo justifica, y siempre con aprobación humana (el programa de recompensas de X excluye lo publicado por medios automatizados). Espejos a Threads/Bluesky en fase 2.
- `metrics/`: export semanal de X analytics (CSV) y de la web (Umami / Cloudflare Web Analytics) a bronze → `gold.rendimiento_posts`.

---

## 4. Diseño físico y stack

**Opción recomendada:** Databricks Free Edition (Delta Lake, Unity Catalog, notebooks, jobs con serverless). Verificar los límites vigentes de cómputo y de jobs programados. Si no bastan, la alternativa completa es **GitHub Actions (cron) + Python + DuckDB + Parquet en Cloudflare R2**, sin cambiar el modelo de datos.

Estructura del repositorio:

```
padel-datos/
├── ingest/            # un conector por fuente (F1..F15); cada uno escribe en bronze
├── transform/         # silver y gold (SQL + PySpark); tests de calidad
├── data/manual/       # lados.csv, puntos_prize_2026.csv, playtomic_2026.csv,
│                      # fip_report_2025.csv, alias_jugadores.csv
├── content/           # chart_factory, copy_factory, plantillas, prompts
├── publish/           # flujos n8n, scripts de Typefully
├── site/              # web estática (Astro); lee el export de gold
├── tests/
└── docs/              # este documento, ADRs, diccionario de datos
```

- Secretos (padelapi, Places, Claude, Typefully): secretos de Databricks o de GitHub, nunca en el repo.
- Web: Astro + Cloudflare Pages (0 €); datos como JSON estáticos exportados de gold cada noche. Analítica sin cookies.
- Copy: API de Claude con un modelo económico (el input es una fila de datos).
- Gráficos: matplotlib/plotly con una plantilla única versionada.

Coste mensual objetivo: 0 €. Dominio ya pagado (~1 €/mes prorrateado) y 0 € de infraestructura. X Premium (~10 €/mes) solo cuando haya tracción (disparador en el documento de contenido); padelapi de pago y Places solo si aportan.

---

## 5. Jobs y calendario de ejecución

| Job | Qué hace | Cuándo |
|---|---|---|
| `ingest_ranking` | F1 + F3 rankings → bronze → `fact_ranking_semanal` | Lunes 07:00 |
| `ingest_torneo` | F1 (+F2) cuadros, resultados y stats del torneo activo | Diario 23:30 mientras hay torneo (según `dim_torneo`) |
| `ingest_torneo_previa` | F2: cuadro de torneos próximos (`status: pending`), antes de que se jueguen → `gold.torneo_previa` | Diario 07:00, antes de `content_candidates` |
| `ingest_fiptour` | F3 resultados del FIP Tour | Lunes 07:30 |
| `ingest_pistas` | F9 (+F11) → `fact_pistas` | Día 1 de mes |
| `ingest_trends` | F12 → `fact_trends` | Día 2 de mes |
| `ingest_anual` | F5, F6, F7, F8 (disparo manual al publicarse) | Anual |
| `build_silver` | Mapeo de IDs, parejas SCD, resultados derivados, tests | Tras cada ingesta |
| `build_gold` | Todas las tablas gold | Tras silver |
| `content_candidates` | Gráficos + copies candidatos → cola de revisión | Diario 07:30 |
| `export_web` | Gold → JSON/Parquet estáticos → despliegue | Diario 08:00 |
| `ingest_metrics` | X analytics + web → `rendimiento_posts` | Domingo |

Alertas: si un job falla dos veces seguidas, notificación (correo o Telegram). Si `ingest_ranking` falla, `content_candidates` no genera la serie del lunes (no se publica nada con datos viejos).

---

## 6. Calidad de datos y reconciliación

Tests obligatorios (el job falla si no pasan):

- `dim_jugador.jugador_id` único; ningún jugador activo sin entrada en `map_jugador_fuente`.
- Posiciones de `fact_ranking_semanal` contiguas por fecha/sexo/circuito, sin duplicados.
- Todo `fact_partido` referencia dos parejas cuya vigencia cubre la fecha del partido.
- Puntos recomputados (`fact_resultado_torneo`) vs puntos oficiales del ranking: desviación explicable (torneos no computados, penalizaciones) y registrada en una tabla de reconciliación.
- Sin fechas futuras en hechos; sin marcadores imposibles (sets > 3, juegos negativos).
- Snapshots bronze: hash distinto al anterior o marca explícita "sin cambios".

Trampas conocidas:

- Grafías de nombres (acentos, segundo apellido, apodos) entre F1/F2/F3 → `alias_jugadores.csv` + normalización (`unidecode`, minúsculas). Fuzzy matching solo como sugerencia, nunca automático.
- Qualy vs cuadro final; walkovers, abandonos y lucky losers.
- Torneos con el mismo nombre en distintos años y ciudades; categorías que cambian de nombre.
- Tablas de puntos y prize money cambian por temporada → `temporada` siempre en la clave.
- F5 y F6 no se mezclan; se publican como dos estimaciones distintas.
- OSM: deduplicar pistas dentro de un mismo club (relaciones y multipolígonos); marcar cobertura estimada por provincia.

---

## 7. Legal, ética y atribución

- Resultados, rankings y estadísticas son hechos; el valor añadido es la elaboración. Aun así: respetar `robots.txt`, ritmo bajo, caché local, y no revender datos crudos de F1/F2/F3.
- Pie de cada gráfico con fuente(s) y "elaboración propia". Los informes (F5/F6) se citan con nombre y año.
- Sin fotos de jugadores (derechos de imagen): gráficos, no imágenes.
- F14 (Playtomic/Matchi) solo si compensa: agregados, muestreo pequeño, baja frecuencia, sin nombrar clubes ni usuarios.
- Nada de datos de aficionados ni de jugadores amateur identificables.
- Datos abiertos derivados propios (pistas por municipio, series de licencias limpias): publicar en la web con licencia CC BY y atribución a las fuentes originales.

---

## 8. Plan de montaje

Diseñado en bloques de 2-4 horas. Cada fase termina con un "hecho" verificable.

### Fase 0 — Cimientos (semana 1)

- Crear repo; Databricks Free Edition (o Actions + DuckDB); catálogo `padel` con esquemas `bronze`, `silver`, `gold`; secretos.
- Notebook exploratorio con `pypadel`: rankings M/F, calendario 2026, un torneo completo con cuadro y stats. Documentar qué campos existen de verdad y cuáles faltan.
- Primer snapshot de ranking a bronze. Alta en padelapi (plan gratuito) y prueba de `/players/{id}/stats`.
- **Hecho:** ranking de esta semana en bronze y en `fact_ranking_semanal`; diccionario de campos de F1 en `docs/`.

### Fase 1 — Núcleo del circuito (semanas 2-3)

- Conectores F1 y F3 programados; `dim_jugador`, `map_jugador_fuente`, `dim_torneo`, `fact_partido`, `fact_ranking_semanal`.
- Tests de calidad básicos.
- Tres gold: `ranking_movimientos_semana`, `perfil_top100`, `forma_reciente`.
- **Hecho:** el lunes se genera solo el gráfico de movimientos del ranking.

### Fase 2 — Lo que nadie tiene (semanas 4-5)

- `data/manual/puntos_prize_2026.csv` desde los reglamentos; `dim_puntos_categoria`; `fact_resultado_torneo`.
- Gold `puntos_a_defender` y `ganancias_temporada`.
- Derivar `dim_pareja` (SCD2) y gold `parejas_duracion`, `h2h`, `torneo_sorpresas`, `torneo_previa`.
- Etiquetado manual del lado de pista del top 50 M/F (`lados.csv`).
- **Hecho:** previa automática del siguiente torneo con puntos a defender y h2h de los cruces.

### Fase 3 — Mercado y territorio (semanas 6-7)

- F9 OSM + F10 INE → `fact_pistas`, `dim_municipio`, gold `pistas_municipio` y primer mapa.
- F7/F8 → `fact_licencias`, gold `licencias_ccaa`.
- F5/F6 → `fact_mercado_pais`, gold `mercado_pais`. F12 → `trends_geo`.
- **Hecho:** mapa de pistas por 10.000 habitantes y serie de licencias 2013-2025.

### Fase 4 — Fábrica y web (semana 8)

- `chart_factory` con plantilla de marca para 6 formatos; `copy_factory` con prompt y cola de revisión; Typefully conectado.
- `export_web` + sitio Astro con home, metodología, 3 páginas evergreen y descargas.
- `ingest_metrics` y `rendimiento_posts`.
- **Hecho:** pipeline completo dato → gráfico → cola → publicación sin tocar código.

### Fase 5 — Operación (desde la semana 9)

- Backfill: archivo WPT (F2 de pago o scraping histórico) para `archivo_eras`.
- Stats punto a punto (F2) → formatos nuevos (`dominio_sets` ampliado).
- Modelo propio: Elo/Glicko de parejas y probabilidad de victoria para las previas.
- Revisión mensual de fuentes rotas, tests y coste.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Cambian los endpoints de F1 | Conector aislado; F2/F3 como respaldo; alerta si el job falla dos veces |
| padelapi cambia el plan gratuito | Snapshots propios desde el día 1; F1 como primaria |
| Falta de tiempo | Todo programado; la única tarea humana diaria es aprobar la cola (10 min) |
| Error público en un dato | Tests + flag `publicable` + política de corrección visible en la web |
| Cobertura OSM pobre en algunas zonas | Publicar cobertura estimada; complementar con Places; invitar a la comunidad a completar OSM |
| ToS de plataformas privadas | No depender de F14; si se usa, agregados y baja frecuencia |
| Dependencia de X | Web + newsletter como activos propios (ver documento de contenido) |

---

## 10. Backlog de datos (para después)

- Elo de parejas y calibración con resultados reales.
- Kilómetros recorridos por jugador y temporada a partir de las sedes del calendario.
- Rankings amateur autonómicos (FMP, FCP…) para contenido regional.
- Audiencias o asistencia de torneos si algún organizador las publica.
- Cuotas de apuestas para "mercado vs resultado": descartado por ahora (regulación de la publicidad del juego en España y reputación de la marca).
