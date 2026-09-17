"""Gold: parejas_duracion (doc 01 §3.3 / doc 02 #ParejasEnDatos).

Una fila = un tramo de pareja (de dim_pareja) con su duración en días.

Limitación real (17/09/2026): fact_partido solo cubre 180 días hacia atrás
desde el primer backfill. Un tramo cuya fecha_inicio coincide con el primer
día de esa ventana probablemente empezó antes — está "censurado por la
izquierda", no es necesariamente el día real en que se formó la pareja. Se
marca `posible_inicio_anterior_a_datos` para no publicar una duración falsa
como si fuera exacta.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DIM_PAREJA = REPO_ROOT / "silver" / "dim_pareja" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "parejas_duracion"


def build() -> Path:
    parejas = json.loads(DIM_PAREJA.read_text(encoding="utf-8"))
    if not parejas:
        raise SystemExit("dim_pareja está vacío")

    primera_fecha_datos = min(p["fecha_inicio"] for p in parejas)
    hoy = date.today().isoformat()

    rows: list[dict[str, Any]] = []
    for p in parejas:
        inicio = date.fromisoformat(p["fecha_inicio"])
        fin = date.fromisoformat(p["fecha_fin"] if not p["activa"] else hoy)
        rows.append(
            {
                "pareja_id": p["pareja_id"],
                "jugador_1_nombre": p["jugador_1_nombre"],
                "jugador_2_nombre": p["jugador_2_nombre"],
                "categoria": p["categoria"],
                "fecha_inicio": p["fecha_inicio"],
                "fecha_fin": p["fecha_fin"],
                "activa": p["activa"],
                "duracion_dias": (fin - inicio).days,
                "n_torneos": p["n_torneos"],
                "n_partidos": p["n_partidos"],
                "posible_inicio_anterior_a_datos": p["fecha_inicio"] == primera_fecha_datos,
                "fuente_txt": "padelapi.org · elaboración propia",
                "publicable": p["n_torneos"] >= 2,
            }
        )

    rows.sort(key=lambda r: -r["duracion_dias"])

    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    activas_publicables = [r for r in rows if r["activa"] and r["publicable"]]
    if activas_publicables:
        mas_longeva = max(activas_publicables, key=lambda r: r["duracion_dias"])
        print(
            f"parejas_duracion: {len(rows)} tramos. Pareja activa más longeva en la ventana de "
            f"datos: {mas_longeva['jugador_1_nombre']}/{mas_longeva['jugador_2_nombre']} "
            f"({mas_longeva['duracion_dias']} días, {mas_longeva['n_torneos']} torneos)"
        )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
