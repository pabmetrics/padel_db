"""Prueba puntual (15/11/2026): ¿da padelapi el ranking "Race" (el de la
clasificación a las Premier Padel Finals)?

La documentación de padelapi menciona `type=race` (ver
`docs/campos-f2-padelapi.md`), pero nunca se ha probado. Este script no
guarda nada: pide la primera página de `/rankings?type=race` y, si no hay,
el ranking `race` de un jugador concreto, y escribe un resumen (campos que
trae, fecha y top 10 por categoría) en la salida y en el resumen del job de
GitHub Actions. Se lanza a mano con el workflow `probar_race`.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .client import PadelApiClient


def _resumen(items: list[dict[str, Any]]) -> list[str]:
    lineas = [f"Filas en la primera página: {len(items)}"]
    if not items:
        return lineas
    lineas.append(f"Campos: {', '.join(sorted(items[0]))}")
    lineas.append(f"Ejemplo: `{json.dumps(items[0], ensure_ascii=False)[:600]}`")
    for categoria in ("men", "women"):
        filas = sorted((i for i in items if i.get("category") == categoria), key=lambda i: i.get("ranking") or 9999)[:10]
        if filas:
            lineas.append(f"\n**Top 10 {categoria}** (fecha {filas[0].get('date')}):")
            for i in filas:
                jugador = i.get("player") or {}
                nombre = jugador.get("name") if isinstance(jugador, dict) else jugador
                lineas.append(f"- {i.get('ranking')}. {nombre or i.get('player_id')} · {i.get('points')} puntos")
    return lineas


def main() -> None:
    salida = ["## Prueba del ranking Race en padelapi"]
    with PadelApiClient() as cliente:
        for categoria in ("men", "women"):
            try:
                datos = cliente.get("/rankings", params={"type": "race", "category": categoria, "per_page": 50, "page": 1})
                items = datos.get("data") or datos.get("items") or []
                salida.append(f"\n### /rankings?type=race&category={categoria}")
                salida += _resumen(items)
            except Exception as e:  # noqa: BLE001 - es una prueba: que se vea el fallo, sin cortar
                salida.append(f"\n### /rankings?type=race&category={categoria}: ERROR {type(e).__name__}: {str(e)[:300]}")
        # Plan B: el ranking race de un jugador (la doc lo cita en /players/{id}/rankings).
        try:
            jugadores = cliente.get("/players", params={"search": "Tapia", "per_page": 5, "page": 1})
            lista = jugadores.get("data") or jugadores.get("items") or []
            if lista:
                pid = lista[0]["id"]
                datos = cliente.get(f"/players/{pid}/rankings", params={"type": "race"})
                items = datos.get("data") or datos.get("items") or []
                salida.append(f"\n### /players/{pid}/rankings?type=race ({lista[0].get('name')})")
                salida += _resumen(items if isinstance(items, list) else [items])
        except Exception as e:  # noqa: BLE001
            salida.append(f"\n### /players/{{id}}/rankings?type=race: ERROR {type(e).__name__}: {str(e)[:300]}")

    texto = "\n".join(salida)
    print(texto)
    if resumen := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(resumen, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


if __name__ == "__main__":
    main()
