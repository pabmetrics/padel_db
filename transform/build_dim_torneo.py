"""Fase 1: dim_torneo a partir del calendario F1 (premierpadel.com).

torneo_id propio (hash del slug, estable), event_code guardado aparte para
cruzar con el historial de torneos de F2 en Fase 2 (ver nota en
ingest/premierpadel/tournaments.py).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "tournaments"
SILVER_ROOT = REPO_ROOT / "silver" / "dim_torneo"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def torneo_id_for(slug: str) -> str:
    return f"T{hashlib.sha1(slug.encode('utf-8')).hexdigest()[:10]}"


def build() -> Path:
    dt_dir = _latest_dir(BRONZE_ROOT)
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    for item in payload["items"]:
        rows.append(
            {
                "torneo_id": torneo_id_for(item["slug"]),
                "nombre": item.get("full_name") or item.get("name"),
                "circuito": "Premier Padel",
                "categoria": item.get("tournament_type"),
                "sexo": item.get("gender"),
                "ciudad": item.get("city"),
                "pais": item.get("country"),
                "fecha_ini": item.get("start_date"),
                "fecha_fin": item.get("end_date"),
                "temporada": item.get("year"),
                "indoor": None,
                "slug_premierpadel": item["slug"],
                "id_premierpadel": item["id"],
                "event_code_premierpadel": item.get("event_code"),
            }
        )

    fecha = dt_dir.name.removeprefix("dt=")
    out_dir = SILVER_ROOT / f"dt={fecha}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"dim_torneo: {len(rows)} torneos -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
