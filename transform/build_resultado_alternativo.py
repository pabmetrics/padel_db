"""silver/resultado_alternativo: ronda alcanzada por jugador y torneo, desde
la fuente de respaldo (padelearnings.com) para cuando padelapi oculta el
`winner` de un torneo entero.

Cruza jugador_slug de padelearnings con jugador_id vía nombre normalizado
contra dim_jugador (mismo patrón que build_dim_jugador.py: cruce
determinista por nombre, no fuzzy).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "matchresults" / "premierpadel"
OUT_PATH = REPO_ROOT / "silver" / "resultado_alternativo" / "data.json"


def normalize_name(name: str) -> str:
    ascii_name = unidecode(name or "").lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()


def _latest_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def build() -> Path:
    dt_dir = _latest_dir(BRONZE_ROOT)
    if dt_dir is None:
        raise SystemExit(f"No hay snapshots en {BRONZE_ROOT}")
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    dim_dir = REPO_ROOT / "silver" / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    jugador_id_por_nombre: dict[str, str] = {}
    if dt_dirs:
        filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        for r in filas:
            jugador_id_por_nombre[normalize_name(r["nombre_canonico"])] = r["jugador_id"]

    rows: list[dict[str, Any]] = []
    sin_cruzar: set[str] = set()
    for item in payload["items"]:
        jugador_id = jugador_id_por_nombre.get(normalize_name(item["jugador_nombre"]))
        compañero_id = jugador_id_por_nombre.get(normalize_name(item.get("compañero_nombre") or ""))
        if not jugador_id:
            sin_cruzar.add(item["jugador_nombre"])
            continue
        if not compañero_id:
            sin_cruzar.add(item.get("compañero_nombre") or "?")
        rows.append(
            {
                "torneo_nombre": item["torneo_nombre_bronze"],
                "jugador_id": jugador_id,
                "jugador_nombre": item["jugador_nombre"],
                "compañero_id": compañero_id,
                "compañero_nombre": item.get("compañero_nombre"),
                "ronda_alcanzada": item["ronda"],
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"resultado_alternativo: {len(rows)} filas ({len(sin_cruzar)} jugadores sin cruzar a jugador_id) -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
