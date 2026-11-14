"""Gold: tercer_set (14/11/2026) — quién gana los partidos que se deciden
en el tercer set.

Una fila = una pareja en la temporada, con los partidos que llegaron a un
tercer set y cuántos ganó. Fuente: `fact_partido` (F2), mismos filtros que
`build_gold_remontadas.py` (sin marcador oculto ni incoherente).
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "tercer_set"

MIN_TERCEROS_SETS = 8
FUENTE_TXT = "padelapi.org · elaboración propia"


def sets_jugados(marcador_txt: str | None) -> int:
    return len(re.findall(r"\d+-\d+", marcador_txt or ""))


def calcular(partidos: list[dict[str, Any]], temporada: int) -> list[dict[str, Any]]:
    por_pareja: dict[tuple, dict[str, Any]] = {}
    for p in partidos:
        if not str(p.get("fecha", "")).startswith(str(temporada)):
            continue
        if p.get("marcador_incoherente") or p.get("ganador") not in ("team_1", "team_2"):
            continue
        if sets_jugados(p.get("marcador_txt")) != 3:
            continue
        for t in (1, 2):
            j1, j2 = p.get(f"equipo_{t}_jugador_1") or {}, p.get(f"equipo_{t}_jugador_2") or {}
            if not j1.get("jugador_id") or not j2.get("jugador_id"):
                continue
            ids = tuple(sorted((j1["jugador_id"], j2["jugador_id"])))
            fila = por_pareja.setdefault((p["categoria"], ids), {
                "categoria": p["categoria"], "jugador_1_id": ids[0], "jugador_2_id": ids[1],
                "pareja": f"{j1['nombre_padelapi']} / {j2['nombre_padelapi']}",
                "terceros_sets": 0, "terceros_sets_ganados": 0,
            })
            fila["terceros_sets"] += 1
            fila["terceros_sets_ganados"] += p["ganador"] == f"team_{t}"

    hoy = date.today().isoformat()
    filas = [
        {
            **f,
            "temporada": temporada,
            "pct_tercer_set": round(100 * f["terceros_sets_ganados"] / f["terceros_sets"], 1),
            "fecha_dato": hoy,
            "fuente_txt": FUENTE_TXT,
            "publicable": f["terceros_sets"] >= MIN_TERCEROS_SETS,
        }
        for f in por_pareja.values()
    ]
    filas.sort(key=lambda r: (r["categoria"], -r["pct_tercer_set"], -r["terceros_sets"]))
    return filas


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    temporada = max(int(p["fecha"][:4]) for p in partidos if p.get("fecha"))
    filas = calcular(partidos, temporada)

    out_dir = GOLD_ROOT / f"fecha_dato={date.today().isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"tercer_set: {len(filas)} parejas, {sum(r['publicable'] for r in filas)} publicables -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
