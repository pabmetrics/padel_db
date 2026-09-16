"""Gold: perfil_top100 (doc 01 §3.3 / doc 02 "Perfil del top 100").

Una fila = un jugador del top 100 (M o F) por ranking oficial, con edad,
nacionalidad, altura y lado de pista donde F2 lo tenga. Fuente: snapshot de
padelapi (F2), que es quien trae estos campos (F1 no los da en el ranking).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
F2_PLAYERS_ROOT = REPO_ROOT / "bronze" / "padelapi" / "players"
GOLD_ROOT = REPO_ROOT / "gold" / "perfil_top100"

CATEGORY_TO_SEXO = {"men": "M", "women": "F"}


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def _edad(birthdate: str | None, referencia: date) -> int | None:
    if not birthdate:
        return None
    nacimiento = datetime.strptime(birthdate, "%Y-%m-%d").date()
    años = referencia.year - nacimiento.year
    if (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day):
        años -= 1
    return años


def build() -> Path:
    dt_dir = _latest_dir(F2_PLAYERS_ROOT)
    fecha = dt_dir.name.removeprefix("dt=")
    referencia = date.fromisoformat(fecha)
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    for item in payload["items"]:
        sexo = CATEGORY_TO_SEXO.get(item.get("category"))
        ranking = item.get("ranking")
        if sexo is None or ranking is None or ranking > 100:
            continue
        rows.append(
            {
                "fecha_dato": fecha,
                "sexo": sexo,
                "ranking": ranking,
                "jugador_nombre": item["name"],
                "nacionalidad": item.get("nationality"),
                "edad": _edad(item.get("birthdate"), referencia),
                "altura_cm": int(item["height"]) if item.get("height") else None,
                "lado_pista": item.get("side"),
                "mano": item.get("hand"),
                "fuente_txt": "padelapi.org · elaboración propia",
                "publicable": item.get("birthdate") is not None,
            }
        )

    out_dir = GOLD_ROOT / f"fecha_dato={fecha}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    for sexo in ("M", "F"):
        edades = [r["edad"] for r in rows if r["sexo"] == sexo and r["edad"] is not None]
        con_lado = sum(1 for r in rows if r["sexo"] == sexo and r["lado_pista"])
        if edades:
            media = sum(edades) / len(edades)
            print(
                f"perfil_top100 {sexo}: {len(edades)}/100 con edad (media {media:.1f} años), "
                f"{con_lado}/100 con lado de pista conocido"
            )

    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
