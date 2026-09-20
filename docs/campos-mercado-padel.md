# Fase 3 — mercado del pádel (F5/F6 informes + F12 Trends)

Construido el 21/09/2026 a partir de dos PDF que pasó el usuario:

- **FIP World Padel Report 2025** (`https://www.padelfip.com/wp-content/uploads/2025/12/FIP-WPR-2025_DIGITAL.pdf`, F6, cifras oficiales de la federación).
- **Playtomic Global Padel Report 2026** (F5, informe de mercado con Strategy&/PwC).

## Qué se ha transcrito y qué no

Los dos informes son en gran parte infografías: texto narrativo con
cifras concretas intercalado con gráficos de barras cuyo texto, al
extraerlo con `pdfplumber`, pierde el orden fila↔etiqueta (los números y
los nombres de país salen todos juntos, sin garantía de que el orden de
lectura del PDF coincida con el de la barra en el gráfico). Siguiendo la
misma regla que ya se ha aplicado toda la sesión con datos financieros
("no adivinar"), **solo se han transcrito las cifras que aparecen en
frases de texto corrido**, no las de los gráficos de barras. Eso deja
fuera, por ejemplo, el desglose exacto del "Top 15 países por número de
pistas" del informe FIP (Fig. 4/6), porque el texto extraído no permite
emparejar con seguridad cada país con su cifra en esa tabla concreta.

- `data/manual/mercado_fip_2025.csv`: cifras globales, por continente y
  por país citadas explícitamente en prosa (pistas, clubes, jugadores,
  porcentajes de aficionados), con una columna `calificador`
  (`exacto`/`mas_de`/`aprox`) para no presentar un "más de 17.300" como si
  fuera una cifra exacta.
- `data/manual/mercado_playtomic_2026.csv`: el marco de 5 arquetipos de
  Playtomic (Padel Heartlands, The Sweet Spot, The Hotspot, Diamonds in
  the Rough, Post-Boom Adjustment), con los países representativos de cada
  uno y los rangos de pistas/jugadores por 100.000 habitantes que da el
  informe (rangos del arquetipo, no cifras por país individual — el
  informe no las da a ese nivel).

## Por qué FIP y Playtomic no se mezclan

Mismo criterio que el doc de arquitectura ya fija para F5/F6 (doc 01 §6) y
que este proyecto ya aplicó a licencias CSD/FEP: son dos fuentes
independientes con metodologías distintas, y sus cifras globales de pistas
no coinciden — 77.355 (FIP, dato de junio de 2025) frente a 58.334
(Playtomic, cierre de 2025). `fact_mercado_pais` guarda ambas con una
columna `fuente` (`fip`/`playtomic`) y nunca las suma ni las promedia.

## F12 — Google Trends, "países en expansión"

El usuario pidió centrar Trends en los países "en expansión", sin
concretar cuáles. En vez de decidirlo a ojo, `data/manual/paises_expansion.csv`
cruza la clasificación que ya hacen los dos informes:

- **Playtomic**: los dos arquetipos menos maduros — *The Hotspot* (Reino
  Unido, Alemania, Irlanda: crecimiento rápido) y *Diamonds in the Rough*
  (EE.UU., India, Australia, Indonesia, Brasil, Polonia: muy en fase
  inicial, alto potencial).
- **FIP**: países que el informe etiqueta explícitamente como "growing" o
  "emerging" en su repaso por continente, con un subconjunto curado (no
  los ~40 que cita el informe entero, para mantener el conector dentro de
  un ritmo de consulta razonable a Google Trends): Suiza, Portugal, México,
  Sudáfrica, Marruecos, Tailandia, Israel (growing); Colombia, Filipinas,
  China, Senegal (emerging).

20 países en total. `ingest/google_trends/interes_padel.py` usa
`pytrends` (librería no oficial, doc 01 §2, riesgo ya anticipado) para
consultar, por país, los términos **"padel" y "tenis" a la vez**: Google
Trends normaliza los términos de una misma consulta en la misma escala
0-100, así que el ratio padel/tenis dentro de una consulta sí es
comparable entre países, aunque el valor absoluto de cada término no lo
sea entre consultas distintas (cada país es una consulta aparte). Es el
mismo uso que le da la propia FIP en su informe, citado explícitamente
como fuente de contraste para Portugal, Argentina y Sudáfrica.

`gold.trends_geo` calcula el ratio padel/tenis del último trimestre y su
variación frente al trimestre anterior, para que "en expansión" se lea
como "el interés crece más rápido", no solo "tiene un índice alto" (que no
sería comparable entre países en la escala nativa de Trends).

## Riesgo conocido

`pytrends` no es una API oficial de Google: puede empezar a fallar o
bloquearse sin aviso (429, cambios de endpoint). El conector no reintenta
agresivamente ni sube el ritmo de consulta si falla — registra el error
por país en `errores` dentro del propio snapshot de bronze y sigue con el
resto, en vez de arriesgar un bloqueo por IP.
