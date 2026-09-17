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

Los tres se descartaron explícitamente en vez de arriesgar una cifra mal cruzada — con dinero real, un cruce dudoso es peor que un hueco documentado.

**Actualización (17/09/2026, misma sesión):** el usuario resolvió a mano los 13 torneos que habían quedado sin cruzar (los 9 sin coincidencia automática + los 3 descartados + 1 más), pasando el enlace exacto de cada uno. Dos de ellos confirman que la discrepancia de categoría no siempre es un error de cruce: "FIP Silver Oeiras" y "FIP Silver Westerbork" (nombres tal como los da padelapi) enlazan de verdad a páginas `fip-bronze-*` de la FIP, con bolsas de 8.500 € y 5.000 € — tamaño típico de Bronze, no de Silver. Es padelapi quien etiqueta mal la categoría de estos dos torneos concretos, no un fallo del cruce. Con esto, `data/manual/prize_torneo_slugs_2026.csv` cubre los **65 de 65** torneos de `fact_partido`.

## Bugs de formato de número encontrados y corregidos

La tabla de premios de padelfip.com mezcla, dentro de la misma tabla, tres formatos de número sin avisar:

- `421,88€` — coma decimal.
- `1.406€` — punto de millar.
- `337.50€` — punto **decimal** (no de millar, pese a tener el mismo aspecto que el caso anterior).

Un primer intento de parseo con una expresión regular ingenua leía "1.406€" como "1" y "337.50€" como "33.750" — ambos absurdos, detectados porque rompían la comprobación de que ganar una ronda posterior siempre paga más (`tests/test_calidad_silver.py::test_prize_por_torneo_positivo_y_monotono`). La función `_parse_euros` en `ingest/prizemoney/fip.py` distingue por la cantidad de dígitos tras el separador (2 → decimal, se descarta; 3 → millar, se une) en vez de asumir un convenio fijo.

## Cobertura de `gold.ganancias_temporada`

Con datos reales por torneo y los 74 torneos ya cubiertos (72 con premio + resultados de respaldo para Premier Padel y FIP Tour, ver `docs/campos-f2-padelapi.md`), la tabla pasó de 143 jugadores (enfoque genérico original) a 2.007.

**Resuelto (18/09/2026)**: dos ediciones distintas de "FIP Silver Damac Dubai" (febrero y junio de 2026) comparten el mismo nombre, y de verdad tienen bolsas distintas (20.000 € / Winner 1.600 € en febrero; 25.000 € / Winner 2.000 € en junio — confirmado en las dos páginas oficiales de padelfip.com). `data/manual/prize_torneo_slugs_2026.csv` admite una columna `mes_aprox` para estos casos: cuando el mismo nombre tiene más de una fila de premios, `build_gold_ganancias_temporada.py` elige la que corresponde al mes real del resultado en vez de una cualquiera. Es el único torneo del dataset con esta ambigüedad; si aparece otro caso igual, el mismo mecanismo lo cubre añadiendo una fila más al CSV.
