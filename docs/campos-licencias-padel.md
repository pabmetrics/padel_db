# Fase 3 — licencias federativas de pádel (F7 CSD)

Explorado y resuelto el 18/09/2026, tras un aviso del usuario: el intento
anterior (misma noche) había concluido que `csd.gob.es` estaba roto por un
error de certificado — era un falso positivo, ver más abajo.

## Fuente

El CSD publica en
`https://www.csd.gob.es/es/federaciones-y-asociaciones/federaciones-deportivas-espanolas/licencias`
un archivo de PDFs de la "Estadística de Deporte Federado". Para pádel hay
dos informes útiles:

- **"Histórico licencias (actualizado 2025)"**: tabla federación × año,
  1941-2025, en 5 páginas de ~20 años cada una.
- **"Licencias por sexo 2007-2025"**: hombres/mujeres/total por año.

`ingest/csd/licencias.py` localiza ambos PDFs buscando el enlace en la
propia página (no una URL fija) y extrae la fila "45 PÁDEL" de cada
informe con `pdfplumber`, sin persistir el PDF en el repo — solo el JSON
estructurado va a bronze (`bronze/csd/licencias/`).

## El error de certificado era del lado de Python, no del CSD

`httpx` (con el almacén de certificados de `certifi`) daba
`CERTIFICATE_VERIFY_FAILED: certificate signature failure` al pedir
`csd.gob.es`. El usuario confirmó que el sitio le funcionaba bien en su
navegador; `Invoke-WebRequest` de PowerShell (que usa el almacén de
certificados de Windows) también lo confirmó con un 200 OK. La causa: el
certificado del CSD está firmado por una cadena que el almacén de Mozilla
que trae `certifi` no reconoce, pero el almacén nativo de Windows sí. Se
resuelve con el paquete `truststore`
(`truststore.inject_into_ssl()` al principio del conector), que hace que
el módulo `ssl` de Python use el almacén de certificados del sistema
operativo en vez del de `certifi`. Tras aplicarlo, `httpx` accede sin
problema. Lección: un error de TLS en Python no implica que el sitio esté
roto — hay que comprobar con una herramienta que use el almacén del
sistema (navegador, `Invoke-WebRequest`) antes de concluirlo.

## Por qué nacional y no por CCAA (todavía)

El diseño original (doc 01 §3.2/§3.3) pide `fact_licencias` con
`(año, federación, ccaa, sexo)` y un gold `licencias_ccaa`. Los dos
informes de esta página del CSD son series **nacionales agregadas**: no
desglosan por comunidad autónoma. Un desglose por CCAA sí existe, pero en
los informes anuales "Licencias y Clubes `<año>`" (un PDF por año, con
tabla federación × CCAA), que habría que parsear uno a uno — ~13-20 PDFs
en vez de 2. Se ha preferido publicar primero la serie nacional, verificada
y consistente, que empezar un desglose por CCAA a medias. `fact_licencias`
usa `ambito="nacional"` en vez de una columna `ccaa` rellena a medias, para
que quede explícito en el propio dato. Pendiente para una sesión futura:
localizar y parsear los informes anuales por CCAA (mismo patrón de
`pdfplumber` que aquí).

## Verificación de los números

- La cifra de 2000 (6.137) y la tendencia hasta "más de 111.000" coinciden
  con el propio backlog del proyecto (`docs/padel-datos-02-contenido.md`
  #5), transcrito de otra fuente en una sesión anterior — confirma que es
  el informe correcto antes incluso de cruzar nada más.
- El informe "por sexo" se verifica solo: para cada año (excepto 2007, que
  tiene una columna adicional "sin especificar" de 253 licencias),
  hombres + mujeres = total, y ese total coincide exactamente con el de la
  tabla histórica del mismo año. Los 19 años de solape (2007-2025) cuadran
  sin excepción.
- El "P�DEL" que aparece en el texto crudo extraído del PDF es un
  artefacto de visualización (la tilde de "PÁDEL" mal decodificada en la
  consola), no corrupción real del dato — mismo patrón ya visto una vez
  esta sesión con un nombre de jugador.

## Un hueco real en la fuente, no un fallo de extracción

La tabla histórica no tiene fila de pádel en absoluto para 1941-1979 (el
deporte no estaba federado) ni para 1986-1999 (sin licencias registradas
en esos años en este informe concreto). El conector no rellena ese hueco:
`fact_licencias` simplemente no tiene filas para esos años, en vez de
interpolar o asumir un valor. La serie queda: 1980-1985 (6 años sueltos),
luego 2000-2025 continua.

## F8 (FEP, `padelfederacion.es`) — sí tenía una fuente estructurada, buena

El usuario señaló `https://www.padelfederacion.es/Datos_Federacion.asp?Id=0`,
la ficha de datos de la propia FEP (no la sección de noticias en texto
libre que se miró y descartó la sesión anterior). Es una página distinta y
mucho mejor: incrusta un bloque Highcharts con, según la propia página,
datos "actualizados online con la BBDD FEP" —

- Serie de licencias por año, 2012 hasta el **año en curso** (2026: 113.975
  a 18/09/2026, subiendo durante el año según la nota de la propia página:
  "al inicio de cada año se inicia el proceso de renovación y a lo largo
  del año van aumentando").
- Desglose por género del año en curso: Masculino 73.641, Femenino 40.334
  (suma exacta con el total).
- Desglose por edad del año en curso: Menores (<19) 12.868, Sub23 (19-23)
  6.408, Senior (24-39) 38.230, Veteranos (>39) 56.469 (suma exacta con el
  total; dato que no tiene el CSD).
- Además, cifras vivas de técnicos nacionales (1.461), jueces-árbitro
  nacionales (308) y clubes federados (1.506).

`ingest/fep/licencias.py` extrae estos bloques con expresiones regulares
sobre el JS embebido (no hay API ni tabla HTML clásica). **No se mezcla con
el CSD**: son dos fuentes independientes con series que no coinciden
exactamente incluso en años ya cerrados (p.ej. 2021: CSD 96.543 vs FEP
96.872, diferencia de 329 licencias; 2016-2019 difieren en un puñado de
licencias cada año) — mismo motivo que el doc de arquitectura ya da para
no mezclar F5 y F6 (doc 01 §6): el CSD es una foto fija anual del informe
oficial; la FEP es su propia base de datos en vivo, que puede seguir
corrigiéndose después de la foto del CSD. `fact_licencias` guarda ambas con
una columna `fuente` (`"csd"` / `"fep"`) y nunca las suma entre sí.
`docs/padel-datos-02-contenido.md` backlog #5 ("Licencias de pádel
2000-2025: de 6.137 a más de 111.000") puede publicarse con la fuente CSD;
el dato del año en curso solo lo tiene la FEP.
