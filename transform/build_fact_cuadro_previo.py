"""fact_cuadro_previo: el cuadro de un torneo próximo, desde los snapshots
de `ingest/padelapi/draw.py` (bronze/padelapi/draw/).

Separado de `fact_partido` a propósito: un cruce del cuadro antes de
jugarse no tiene ganador ni marcador, y mezclarlo en `fact_partido`
rompería los tests que asumen que toda fila ahí es un partido ya jugado
(p. ej. "sin fechas futuras" — un cruce sin jugar no tiene fecha real
todavía). Comparte la extracción de jugador/torneo con `fact_partido` vía
`_padelapi_common` para no duplicar esa lógica.

`torneo_id` usa la misma función que `fact_partido` (mismo id de padelapi
-> mismo torneo_id en las dos tablas), así que cuando el torneo pase de
"próximo" a "jugado" sus partidos aparecerán con el `torneo_id` que ya
tenía en el cuadro.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _padelapi_common import jugador_ref, load_map_padelapi, torneo_id_for_padelapi

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_DRAW_ROOT = REPO_ROOT / "bronze" / "padelapi" / "draw"
SILVER_ROOT = REPO_ROOT / "silver"


def _mostrar(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build() -> Path:
    jugador_por_id_fuente = load_map_padelapi()

    rows: list[dict[str, Any]] = []
    tournament_dirs = sorted(BRONZE_DRAW_ROOT.glob("tournament_id=*")) if BRONZE_DRAW_ROOT.exists() else []
    for tournament_dir in tournament_dirs:
        dt_dirs = sorted((p for p in tournament_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
        if not dt_dirs:
            continue
        payload = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        torneo_id = torneo_id_for_padelapi(payload["tournament"]["id"])

        for match in payload["items"]:
            team_1 = [jugador_ref(p, jugador_por_id_fuente) for p in match["players"]["team_1"]]
            team_2 = [jugador_ref(p, jugador_por_id_fuente) for p in match["players"]["team_2"]]
            seeds = match.get("seeds") or {}
            semilla_1 = int(seeds["team_1"]) if seeds.get("team_1") and str(seeds["team_1"]).isdigit() else None
            semilla_2 = int(seeds["team_2"]) if seeds.get("team_2") and str(seeds["team_2"]).isdigit() else None

            rows.append(
                {
                    "cruce_id": f"MC{match['id']}",
                    "torneo_id": torneo_id,
                    "torneo_nombre": payload["tournament"]["name"],
                    "torneo_nivel_padelapi": payload["tournament"].get("level"),
                    "fecha_inicio_torneo": payload["tournament"].get("start_date"),
                    "categoria": match.get("category"),
                    "fase": match.get("draw"),
                    "ronda_num": match.get("round"),
                    "ronda_nombre": match.get("round_name"),
                    "status": match.get("status"),
                    "equipo_1_jugador_1": team_1[0] if len(team_1) > 0 else None,
                    "equipo_1_jugador_2": team_1[1] if len(team_1) > 1 else None,
                    "equipo_2_jugador_1": team_2[0] if len(team_2) > 0 else None,
                    "equipo_2_jugador_2": team_2[1] if len(team_2) > 1 else None,
                    "semilla_equipo_1": semilla_1,
                    "semilla_equipo_2": semilla_2,
                    "fuente_txt": "padelapi.org · elaboración propia",
                }
            )

    out_dir = SILVER_ROOT / "fact_cuadro_previo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    torneos = {r["torneo_nombre"] for r in rows}
    print(f"fact_cuadro_previo: {len(rows)} cruces de {len(torneos)} torneo(s) -> {_mostrar(out_file)}")
    return out_file


if __name__ == "__main__":
    build()
