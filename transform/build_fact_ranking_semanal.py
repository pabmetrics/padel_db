"""Fase 1: fact_ranking_semanal definitivo, cruzando F1 (posición) y F2
(puntos, deltas) por jugador_id vía map_jugador_fuente — ya no por nombre.

Sustituye al build_silver.py provisional de Fase 0 (que solo tenía F1 y
`puntos = NULL`). Requiere haber corrido antes build_dim_jugador.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
F1_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "rankings"
F2_RANKINGS_ROOT = REPO_ROOT / "bronze" / "padelapi" / "rankings"
SILVER_ROOT = REPO_ROOT / "silver"

GENDER_TO_SEXO = {"Male": "M", "Female": "F", "men": "M", "women": "F"}


def _latest_dir(root: Path) -> Path:
    """Última subcarpeta particionada (dt=... o fecha_actualizacion=...), por nombre."""

    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def _load_map_by_fuente(fuente: str) -> dict[str, str]:
    map_dir = _latest_dir(SILVER_ROOT / "map_jugador_fuente")
    rows = json.loads((map_dir / "data.json").read_text(encoding="utf-8"))
    return {r["id_fuente"]: r["jugador_id"] for r in rows if r["fuente"] == fuente}


def _load_dim_jugador() -> dict[str, str]:
    dim_dir = _latest_dir(SILVER_ROOT / "dim_jugador")
    rows = json.loads((dim_dir / "data.json").read_text(encoding="utf-8"))
    return {r["jugador_id"]: r["nombre_canonico"] for r in rows}


def build() -> Path:
    f1_dir = _latest_dir(F1_ROOT)
    fecha_ranking = f1_dir.name.removeprefix("dt=")

    map_premierpadel = _load_map_by_fuente("premierpadel")
    map_padelapi = _load_map_by_fuente("padelapi")
    nombres = _load_dim_jugador()

    f2_dir = _latest_dir(F2_RANKINGS_ROOT)
    f2_payload = json.loads((f2_dir / "data.json").read_text(encoding="utf-8"))
    f2_by_jugador_id: dict[str, dict[str, Any]] = {}
    for item in f2_payload["items"]:
        jugador_id = map_padelapi.get(str(item["id"]))
        if jugador_id:
            f2_by_jugador_id[jugador_id] = item

    rows: list[dict[str, Any]] = []
    for filename in ("male.json", "female.json"):
        path = f1_dir / filename
        if not path.exists():
            continue
        f1_payload = json.loads(path.read_text(encoding="utf-8"))
        for item in f1_payload["items"]:
            jugador_id = map_premierpadel.get(str(item["id"]))
            if not jugador_id:
                continue
            f2_match = f2_by_jugador_id.get(jugador_id)
            # El ranking oficial tiene empates: parejas con los mismos puntos
            # comparten posición (ej. Galán y Chingotto, ambos #3, 17-18/09/2026,
            # verificado también contra F3/padelfip). El orden de lista de F1
            # (posicion_lista) rompe esos empates en 1,2,3,4... — no es la
            # posición real. F2 sí trae el ranking oficial con empates, así que
            # se usa como fuente de la posición cuando hay cruce; posicion_lista
            # de F1 queda solo de referencia/fallback.
            posicion_oficial = f2_match["ranking"] if f2_match and f2_match.get("ranking") is not None else item["posicion_lista"]
            rows.append(
                {
                    "fecha_ranking": fecha_ranking,
                    "circuito": "Premier Padel",
                    "sexo": GENDER_TO_SEXO.get(item.get("gender"), "?"),
                    "jugador_id": jugador_id,
                    "jugador_nombre": nombres.get(jugador_id, item["full_name"]),
                    "posicion": posicion_oficial,
                    "posicion_lista_f1": item["posicion_lista"],
                    "puntos": f2_match["points"] if f2_match else None,
                    "puntos_diff_semana": f2_match["points_diff"] if f2_match else None,
                    # padelapi da ranking_diff = ranking_actual - ranking_anterior (positivo
                    # = ha empeorado). Verificado con casos reales (17/09/2026): jugadores
                    # que ganan puntos tienen ranking_diff negativo. Lo invertimos para que
                    # positivo = ha subido N puestos, como "Δ +14 puestos" en doc 02.
                    "posicion_diff_semana": (
                        -f2_match["ranking_diff"] if f2_match and f2_match.get("ranking_diff") is not None else None
                    ),
                    "fuente_txt": "FIP / Premier Padel · elaboración propia",
                }
            )

    ndjson_path = SILVER_ROOT / "_tmp_fact_ranking_semanal.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    out_dir = SILVER_ROOT / "fact_ranking_semanal" / f"fecha_ranking={fecha_ranking}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.parquet"

    con = duckdb.connect()
    con.execute(
        f"COPY (SELECT * FROM read_json_auto('{ndjson_path.as_posix()}')) "
        f"TO '{out_file.as_posix()}' (FORMAT PARQUET)"
    )
    ndjson_path.unlink()

    n_con_puntos = sum(1 for r in rows if r["puntos"] is not None)
    print(
        f"fact_ranking_semanal {fecha_ranking}: {len(rows)} filas "
        f"({n_con_puntos} con puntos de F2) -> {out_file.relative_to(REPO_ROOT)}"
    )
    return out_file


if __name__ == "__main__":
    build()
