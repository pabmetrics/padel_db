"""dim_puntos_categoria: carga data/manual/puntos_prize_2026.csv a silver.

Fuente: tabla oficial de puntos FIP 2026 (imagen aportada por el usuario,
17/09/2026, "FIP Ranking Point Table Breakdown"). Los puntos son iguales
para M y F en todas las categorías de esta edición, así que no hay columna
de sexo. `prize_money_pareja` queda vacío: esta tabla solo trae puntos, el
reparto de prize money necesita otra fuente (pendiente).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "manual" / "puntos_prize_2026.csv"
OUT_PATH = REPO_ROOT / "silver" / "dim_puntos_categoria" / "data.json"


def build() -> Path:
    rows: list[dict[str, Any]] = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "circuito": row["circuito"],
                    "categoria": row["categoria"],
                    "temporada": int(row["temporada"]),
                    "ronda": row["ronda"],
                    "puntos": int(row["puntos"]),
                    "prize_money_pareja": float(row["prize_money_pareja"]) if row["prize_money_pareja"] else None,
                    "nota": row["nota"] or None,
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"dim_puntos_categoria: {len(rows)} filas -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
