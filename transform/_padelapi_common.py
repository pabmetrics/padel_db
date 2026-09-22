"""Helpers compartidos entre build_fact_partido.py y
build_fact_cuadro_previo.py: los dos parten de la misma forma de partido
de F2 (padelapi), uno para partidos jugados y otro para el cuadro antes de
jugarse.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_ROOT = REPO_ROOT / "silver"


def latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def load_map_padelapi() -> dict[str, str]:
    map_dir = latest_dir(SILVER_ROOT / "map_jugador_fuente")
    rows = json.loads((map_dir / "data.json").read_text(encoding="utf-8"))
    return {r["id_fuente"]: r["jugador_id"] for r in rows if r["fuente"] == "padelapi"}


def torneo_id_for_padelapi(tournament_id: int) -> str:
    return f"T2{hashlib.sha1(f'padelapi:{tournament_id}'.encode()).hexdigest()[:9]}"


def jugador_ref(player: dict[str, Any], jugador_por_id_fuente: dict[str, str]) -> dict[str, Any]:
    id_fuente = str(player["id"])
    return {
        "jugador_id": jugador_por_id_fuente.get(id_fuente),
        "id_padelapi": player["id"],
        "nombre_padelapi": player["name"],
        "lado_pista": player.get("side"),
    }
