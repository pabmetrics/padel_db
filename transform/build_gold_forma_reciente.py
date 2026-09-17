"""Gold: forma_reciente (doc 01 §3.3): % victorias últimas 8 semanas y rachas.

Una fila = un jugador con partidos en la ventana. Fuente: fact_partido
(que a su vez sale de F2, /tournaments/{id}/matches — ver
transform/build_fact_partido.py).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
DIM_JUGADOR_ROOT = REPO_ROOT / "silver" / "dim_jugador"
GOLD_ROOT = REPO_ROOT / "gold" / "forma_reciente"

VENTANA_DIAS = 56  # 8 semanas

SLOTS_EQUIPO_1 = ("equipo_1_jugador_1", "equipo_1_jugador_2")
SLOTS_EQUIPO_2 = ("equipo_2_jugador_1", "equipo_2_jugador_2")


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def _load_sexo_por_jugador() -> dict[str, str]:
    dim_dir = _latest_dir(DIM_JUGADOR_ROOT)
    rows = json.loads((dim_dir / "data.json").read_text(encoding="utf-8"))
    return {r["jugador_id"]: r["sexo"] for r in rows}


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    sexo_por_jugador = _load_sexo_por_jugador()
    hoy = date.today()
    limite = hoy - timedelta(days=VENTANA_DIAS)

    # jugador_id -> lista de (fecha, resultado) ordenada cronológicamente
    historial: dict[str, list[tuple[date, str]]] = defaultdict(list)
    nombres: dict[str, str] = {}

    for partido in partidos:
        ganador = partido.get("ganador")
        if ganador not in ("team_1", "team_2"):
            continue
        fecha = date.fromisoformat(partido["fecha"])

        for slots, es_ganador in ((SLOTS_EQUIPO_1, ganador == "team_1"), (SLOTS_EQUIPO_2, ganador == "team_2")):
            for slot in slots:
                jugador = partido.get(slot)
                if not jugador or not jugador.get("jugador_id"):
                    continue
                jugador_id = jugador["jugador_id"]
                nombres[jugador_id] = jugador["nombre_padelapi"]
                historial[jugador_id].append((fecha, "V" if es_ganador else "D"))

    rows: list[dict[str, Any]] = []
    for jugador_id, partidos_jugador in historial.items():
        partidos_jugador.sort(key=lambda t: t[0])

        en_ventana = [r for f, r in partidos_jugador if f >= limite]
        if not en_ventana:
            continue
        victorias = en_ventana.count("V")

        racha_tipo = partidos_jugador[-1][1]
        racha_n = 0
        for _, resultado in reversed(partidos_jugador):
            if resultado != racha_tipo:
                break
            racha_n += 1

        rows.append(
            {
                "fecha_dato": hoy.isoformat(),
                "jugador_id": jugador_id,
                "jugador_nombre": nombres[jugador_id],
                "sexo": sexo_por_jugador.get(jugador_id),
                "partidos_8sem": len(en_ventana),
                "victorias_8sem": victorias,
                "pct_victorias_8sem": round(100 * victorias / len(en_ventana), 1),
                "racha_tipo": "victorias" if racha_tipo == "V" else "derrotas",
                "racha_n": racha_n,
                "fuente_txt": "padelapi.org · elaboración propia",
                "publicable": len(en_ventana) >= 3,
            }
        )

    rows.sort(key=lambda r: (-r["partidos_8sem"], -r["pct_victorias_8sem"]))

    out_dir = GOLD_ROOT / f"fecha_dato={hoy.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    mejor_racha = max((r for r in rows if r["racha_tipo"] == "victorias"), key=lambda r: r["racha_n"], default=None)
    print(f"forma_reciente: {len(rows)} jugadores con partidos en las últimas 8 semanas")
    if mejor_racha:
        print(f"  Mayor racha de victorias: {mejor_racha['jugador_nombre']} ({mejor_racha['racha_n']})")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
