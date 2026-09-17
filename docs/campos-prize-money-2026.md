# Prize money 2026 — fuentes y limitaciones

`data/manual/prize_money_2026.csv`, cargado el 17/09/2026 a partir de dos fuentes que aportó el usuario:

- **Premier Padel** (Major/P1/P2): [padelearnings.com/padel-prize-money](https://padelearnings.com/padel-prize-money). Extraído del HTML renderizado (no del resumen de la herramienta de lectura web, que en una primera pasada dio cifras dudosas para el FIP Tour — se verificó bajando el HTML crudo y comprobando los números literalmente en la página antes de usarlos). Cifras **fijas y exactas** por pareja y ronda: bolsa total 525.000 € (Major), 260.000 € (P1), 147.500 € (P2), reparto igual entre cuadro masculino y femenino. Solo cubre Winner/Final/Semifinal/Cuartos/R16 — la fuente no desglosa R32, R64 ni clasificación.
- **FIP Tour** (Platinum/Gold/Silver/Bronze): [padel-magazine.es](https://padel-magazine.es/Distribuci%C3%B3n-de-premios-en-met%C3%A1lico-del-FIP-Tour-y-montos-por-categor%C3%ADa-de-torneo/). Solo la **tabla** de la página es fiable (los porcentajes de cada fila suman 100%, comprobado); el texto del artículo debajo de la tabla tiene un error evidente de plantilla/traducción (repite el mismo rango de euros para todas las rondas) y se ha ignorado por completo.

## Por qué el FIP Tour no tiene una cifra fija por pareja

La tabla del FIP Tour da un **porcentaje de la bolsa total** para cada ronda (ej. Platino: Winner 20%, R32 19%), no un importe por pareja. Ese porcentaje se reparte entre **todas las parejas que llegaron a esa ronda**, y cuántas son depende del tamaño del cuadro de cada torneo concreto (que varía). Además, la bolsa total del FIP Tour se da como un rango (ej. Platino: 120.000–150.000 €), no una cifra fija por torneo como en Premier Padel.

Calcular un importe por pareja exigiría dos datos que no tenemos: la bolsa exacta de cada torneo concreto y el tamaño de su cuadro. Antes que inventar una cifra con supuestos no verificados, se ha dejado `prize_money_pareja_eur` vacío para estas filas — el porcentaje y el rango de bolsa quedan guardados por si en el futuro se consigue el dato exacto por torneo.

## Implicación para `gold.ganancias_temporada`

Con esta fuente, `ganancias_temporada` solo puede calcular cifras reales para resultados de **Premier Padel Major/P1/P2** en las rondas W/F/SF/QF/R16. Quedan sin importe (no en cero, en `NULL`, para no confundir "no cobró" con "no sabemos cuánto cobró"):

- Resultados de **Premier Padel Finals** (torneo de fin de temporada) — ninguna de las dos fuentes lo cubre.
- Resultados de **FIP Tour** (Platinum/Gold/Silver/Bronze) — bloqueado por lo explicado arriba.
- Rondas **R32, R64 y clasificación** de cualquier categoría — ninguna fuente las desglosa.

Es una tabla parcial pero honesta, no una tabla completa con huecos rellenados a ojo.
