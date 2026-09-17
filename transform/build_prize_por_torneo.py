"""silver/prize_por_torneo: une los snapshots reales de padelearnings.com
(Premier Padel) y padelfip.com (FIP Tour) en una sola tabla, keyed por
nombre de torneo normalizado + sexo + ronda.

Sustituye a dim_prize_categoria (basada en una tabla genérica por categoría
con cifras "aproximadas" que no coincidían con los datos reales de
padelearnings.com — ver docs/campos-prize-money-2026.md, hallazgo del
17/09/2026). Aquí cada fila es la cifra real de un torneo concreto.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = REPO_ROOT / "silver" / "prize_por_torneo" / "data.json"


def normalize_name(name: str) -> str:
    ascii_name = unidecode(name or "").lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()


def _latest_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def _load_snapshot(root: Path) -> list[dict[str, Any]]:
    dt_dir = _latest_dir(root)
    if dt_dir is None:
        return []
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    return payload["items"]


def build() -> Path:
    items = _load_snapshot(REPO_ROOT / "bronze" / "prizemoney" / "premierpadel")
    items += _load_snapshot(REPO_ROOT / "bronze" / "prizemoney" / "fip")

    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "torneo_nombre_norm": normalize_name(item["torneo_nombre_bronze"]),
                "torneo_nombre": item["torneo_nombre_bronze"],
                "sexo": item["sexo"],
                "ronda": item["ronda"],
                "prize_money_jugador_eur": item["jugador_eur"],
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    n_torneos = len({r["torneo_nombre"] for r in rows})
    print(f"prize_por_torneo: {len(rows)} filas de {n_torneos} torneos reales -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
