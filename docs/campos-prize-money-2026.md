# Prize money 2026 — fuentes, conectores y hallazgos

Reescrito el 17/09/2026 tras encontrar que el primer enfoque (tabla genérica por categoría, ver historial de este documento en git) no coincidía con los datos reales de un jugador concreto (`padelearnings.com/players/agustin-tapia`), que el usuario señaló. El enfoque actual usa **cifras reales por torneo**, scrapeadas con dos conectores nuevos, en vez de una tabla aproximada por categoría.

## Conectores

- `ingest/prizemoney/premierpadel.py`: para Premier Padel (Major/P1/P2), lee `data/manual/prize_torneo_slugs_2026.csv` y descarga `https://padelearnings.com/tournaments/<slug>`, con la tabla "Prize money breakdown per round" de cada torneo. **Hallazgo real**: en Major el reparto es igual para M y F, pero en P1/P2 **no** — la página general de resumen decía que sí ("equal prize money at all events"), pero cada torneo concreto (ej. Madrid P1 2026: 26.000 €/jugador en categoría masculina, 17.000 €/jugador en femenina) lo contradice.
- `ingest/prizemoney/fip.py`: para FIP Tour (Platinum/Gold/Silver/Bronze), lee el mismo CSV y descarga `https://www.padelfip.com/events/<slug>/` (fuente oficial de la FIP, no un tercero), con su propia tabla "Prize distribution per tournament round" y bolsa total **fija** por torneo (no un rango como daba la tabla genérica de padel-magazine.es, que se ha dejado de usar). **Hallazgo real**: en FIP Silver, la ronda R32 no paga nada (0 €) en todos los torneos comprobados.

## El mapeo torneo → página de premios es curación manual

`data/manual/prize_torneo_slugs_2026.csv` asocia cada `torneo_nombre` (tal como aparece en nuestro propio `fact_partido`, vía padelapi) con el slug de su página de premios. El cruce automático por nombre normalizado (mismo método que `alias_jugadores.csv`) dio **falsos positivos peligrosos** entre categorías y ediciones distintas:

- "FIP Gold San Luis" casaba con la página de "FIP **Silver** San Luis" (categoría distinta, incluso el nombre visible en el listado).
- "FIP Silver Cyprus **I**" casaba con "FIP Silver Cyprus **II**" (edición distinta).
- "FIP Silver Oeiras" casaba con "FIP **Bronze** Oeiras" (categoría distinta).

Los tres se descartaron explícitamente en vez de arriesgar una cifra mal cruzada — con dinero real, un cruce dudoso es peor que un hueco documentado. El CSV final tiene 52 torneos verificados (16 Premier Padel, 36 FIP Tour) de los ~65 que hay en `fact_partido`; el resto (principalmente FIP Silver sin coincidencia clara, como "3f Elettronica Porto St'elpidio", "Betclic", "Hoganas") queda sin premio conocido.

## Bugs de formato de número encontrados y corregidos

La tabla de premios de padelfip.com mezcla, dentro de la misma tabla, tres formatos de número sin avisar:

- `421,88€` — coma decimal.
- `1.406€` — punto de millar.
- `337.50€` — punto **decimal** (no de millar, pese a tener el mismo aspecto que el caso anterior).

Un primer intento de parseo con una expresión regular ingenua leía "1.406€" como "1" y "337.50€" como "33.750" — ambos absurdos, detectados porque rompían la comprobación de que ganar una ronda posterior siempre paga más (`tests/test_calidad_silver.py::test_prize_por_torneo_positivo_y_monotono`). La función `_parse_euros` en `ingest/prizemoney/fip.py` distingue por la cantidad de dígitos tras el separador (2 → decimal, se descarta; 3 → millar, se une) en vez de asumir un convenio fijo.

## Cobertura de `gold.ganancias_temporada`

Con datos reales por torneo (no una estimación por categoría), la tabla cubre significativamente más que antes: 1.657 jugadores (frente a 143 con el enfoque anterior, que solo cubría Premier Padel Major/P1/P2). Sigue siendo parcial — los ~13-15 torneos sin cruce verificado no aportan ganancias — pero cada cifra que sí aparece es la real de ese torneo concreto, no una aproximación.
