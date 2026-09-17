"""Gold: torneo_sorpresas (doc 01 §3.3 / doc 02 "El torneo en datos").

Una fila = una eliminación de una pareja mejor sembrada por una peor
sembrada (semilla más alta = cabeza de serie más baja). Usa las semillas
(`seeds`) que trae F2 directamente en cada partido — más fiable ahora mismo
que aproximar el ranking exacto de cada jugador en la fecha del partido, que
no tenemos (solo hay un snapshot propio de ranking, no histórico por fecha).

Solo partidos con semillas conocidas en ambos lados (no todos los cruces de
un cuadro llevan semilla) y con marcador coherente (se excluyen los
marcados `marcador_incoherente`, ver build_fact_partido.py).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "torneo_sorpresas"


def _nombre_equipo(a: dict[str, Any] | None, b: dict[str, Any] | None) -> str | None:
    if not a or not b:
        return None
    return f"{a['nombre_padelapi']} / {b['nombre_padelapi']}"


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    for p in partidos:
        if p.get("marcador_incoherente"):
            continue
        if p.get("ganador") not in ("team_1", "team_2"):
            continue
        s1, s2 = p.get("semilla_equipo_1"), p.get("semilla_equipo_2")
        if s1 is None or s2 is None:
            continue

        ganador_semilla = s1 if p["ganador"] == "team_1" else s2
        perdedor_semilla = s2 if p["ganador"] == "team_1" else s1
        if ganador_semilla <= perdedor_semilla:
            continue  # no es sorpresa: ganó la semilla mejor (o igual) situada

        equipo_ganador = _nombre_equipo(
            p["equipo_1_jugador_1"] if p["ganador"] == "team_1" else p["equipo_2_jugador_1"],
            p["equipo_1_jugador_2"] if p["ganador"] == "team_1" else p["equipo_2_jugador_2"],
        )
        equipo_perdedor = _nombre_equipo(
            p["equipo_2_jugador_1"] if p["ganador"] == "team_1" else p["equipo_1_jugador_1"],
            p["equipo_2_jugador_2"] if p["ganador"] == "team_1" else p["equipo_1_jugador_2"],
        )

        rows.append(
            {
                "fecha": p["fecha"],
                "torneo_nombre": p["torneo_nombre"],
                "categoria": p.get("categoria"),
                "ronda": p.get("ronda"),
                "equipo_ganador": equipo_ganador,
                "semilla_ganador": ganador_semilla,
                "equipo_perdedor": equipo_perdedor,
                "semilla_perdedor": perdedor_semilla,
                "diferencia_semillas": ganador_semilla - perdedor_semilla,
                "marcador_txt": p.get("marcador_txt"),
                "fuente_txt": "padelapi.org · elaboración propia",
                "publicable": ganador_semilla - perdedor_semilla >= 3,
            }
        )

    rows.sort(key=lambda r: -r["diferencia_semillas"])

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"torneo_sorpresas: {len(rows)} eliminaciones por sorpresa detectadas")
    if rows:
        top = rows[0]
        print(
            f"  Mayor sorpresa: {top['equipo_ganador']} (semilla {top['semilla_ganador']}) "
            f"elimina a {top['equipo_perdedor']} (semilla {top['semilla_perdedor']}) "
            f"en {top['torneo_nombre']}"
        )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
