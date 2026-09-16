# Diccionario de campos — F3 (padelfip.com)

Explorado el 17/09/2026. `robots.txt` no bloquea `/ranking/` (redirige a `/es/fip-rankings/`). Scraper en `ingest/padelfip/ranking.py`.

## Página de ranking

Server-side rendered (HTML plano, sin necesidad de ejecutar JavaScript) para el **top 10 M/F únicamente**: el resto de posiciones se carga por un mecanismo de "cargar más" que no se ha identificado desde el HTML estático (probablemente una acción de `admin-ajax.php` de WordPress con un `nonce`; no investigado más a fondo porque el top 10 ya cubre el uso previsto en el documento de arquitectura: contrastar F1/F2, no sustituirlos).

| Campo (selector CSS) | Presente | Notas |
|---|---|---|
| `.player__rank` | Sí | Posición. **Con empates reales**: dos jugadores pueden compartir posición si tienen los mismos puntos (ver hallazgo abajo) |
| `.player__name` | Sí | Nombre tal cual lo escribe la FIP |
| `.player__country` | Sí | Código de país de 3 letras (ISO3, ej. `ESP`, `ARG`) — distinto del ISO2 de F2 |
| `.player__pointTNumber` | Sí | Puntos |
| `a.player__link` (href) | Sí | Slug de padelfip.com, otra clave de fuente más para `map_jugador_fuente` si algún día se amplía a más contenido de F3 |
| `.player__move` | Presente pero vacío | El HTML tiene el contenedor del indicador de movimiento semanal, pero viene sin contenido en la carga inicial (se rellena por JS) |

## Hallazgo importante: el ranking oficial tiene empates

Contrastando el top 10 de F3 con el snapshot de F2 del mismo día (17/09/2026): **Alejandro Galán y Federico Chingotto comparten la posición 3** con 18.331 puntos cada uno — no son 3º y 4º como asumía nuestro `fact_ranking_semanal` inicial (que tomaba el orden de la lista de F1, sin empates). F2 (padelapi) sí modela bien los empates en su campo `ranking`.

**Corrección aplicada** en `transform/build_fact_ranking_semanal.py`: la columna `posicion` ahora usa el `ranking` oficial de F2 cuando hay cruce (que respeta empates), y se guarda el orden de lista de F1 aparte como `posicion_lista_f1` (referencia/fallback, no la posición real). Se añadieron tests de calidad para esto (`tests/test_calidad_silver.py`): dos filas con la misma posición deben tener los mismos puntos, y los puntos no pueden crecer al empeorar la posición.

Esto es exactamente el tipo de "trampa conocida" que anticipa el documento de arquitectura (§6) y confirma por qué F1 sola no basta para una tabla de ranking correcta.
