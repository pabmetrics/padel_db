"""dim_prize_categoria: carga data/manual/prize_money_2026.csv a silver.

Ver docs/campos-prize-money-2026.md para las fuentes y por qué el FIP Tour
no tiene una cifra fija por pareja (solo Premier Padel Major/P1/P2 la
tienen; el resto queda como porcentaje + rango de bolsa).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "manual" / "prize_money_2026.csv"
OUT_PATH = REPO_ROOT / "silver" / "dim_prize_categoria" / "data.json"


def _float_or_none(value: str) -> float | None:
    return float(value) if value else None


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
                    "pct_pool": float(row["pct_pool"]) if row["pct_pool"] else None,
                    "prize_money_pareja_eur": _float_or_none(row["prize_money_pareja_eur"]),
                    "pool_min_eur": _float_or_none(row["pool_min_eur"]),
                    "pool_max_eur": _float_or_none(row["pool_max_eur"]),
                    "moneda": row["moneda"],
                    "nota": row["nota"] or None,
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    con_cifra = sum(1 for r in rows if r["prize_money_pareja_eur"] is not None)
    print(f"dim_prize_categoria: {len(rows)} filas ({con_cifra} con cifra fija por pareja) -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
