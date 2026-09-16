"""Gold: ranking_movimientos_semana (doc 01 §3.3 / doc 02 #RankingLunes).

Una fila = un jugador con movimiento de ranking esta semana. Requiere
fact_ranking_semanal con posicion_diff_semana ya resuelto (build_fact_ranking_semanal.py).

Limitación conocida hoy (17/09/2026): solo tenemos un snapshot propio, así
que posicion_diff_semana viene del ranking_diff que ya calcula padelapi (F2)
frente a su semana anterior, no de comparar dos snapshots nuestros. En cuanto
haya dos lunes de bronze propio, se puede recalcular en bruto y contrastar.

`publicable` se limita a posicion <= 100: por debajo de ahí los puntos están
tan apretados que perder 10-20 puntos puede mover a alguien 400 puestos —
matemáticamente real, pero es ruido para contenido (doc 02 habla de
"top 20/50/100", nadie conoce al puesto 300).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_ROOT = REPO_ROOT / "silver"
GOLD_ROOT = REPO_ROOT / "gold" / "ranking_movimientos_semana"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def build() -> Path:
    dt_dir = _latest_dir(SILVER_ROOT / "fact_ranking_semanal")
    fecha = dt_dir.name.removeprefix("fecha_ranking=")
    parquet_path = dt_dir / "data.parquet"

    con = duckdb.connect()
    rows = con.execute(
        f"""
        SELECT
            fecha_ranking AS fecha_dato,
            circuito,
            sexo,
            jugador_id,
            jugador_nombre,
            posicion,
            posicion_diff_semana,
            puntos,
            puntos_diff_semana,
            fuente_txt,
            (posicion_diff_semana IS NOT NULL AND posicion <= 100) AS publicable
        FROM read_parquet('{parquet_path.as_posix()}')
        WHERE posicion_diff_semana IS NOT NULL AND posicion_diff_semana != 0
        ORDER BY ABS(posicion_diff_semana) DESC
        """
    ).fetchall()
    columns = [d[0] for d in con.description]

    records: list[dict[str, Any]] = [dict(zip(columns, row)) for row in rows]
    for r in records:
        r["fecha_dato"] = str(r["fecha_dato"])

    out_dir = GOLD_ROOT / f"fecha_dato={fecha}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    if records:
        top = records[0]
        print(
            f"ranking_movimientos_semana {fecha}: {len(records)} movimientos. "
            f"Mayor: {top['jugador_nombre']} ({top['sexo']}) Δ {int(top['posicion_diff_semana']):+d} puestos "
            f"-> {out_file.relative_to(REPO_ROOT)}"
        )
    else:
        print(f"ranking_movimientos_semana {fecha}: sin movimientos -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
