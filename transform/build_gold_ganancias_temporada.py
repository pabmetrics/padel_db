"""Gold: ganancias_temporada (doc 01 §3.3 / doc 02 "Cierre de torneo").

Una fila = un jugador con ganancias conocidas en la temporada (ventana de
datos de fact_partido, 180 días). Solo cubre resultados de Premier Padel
Major/P1/P2 en rondas W/F/SF/QF/R16 — es lo único para lo que tenemos una
cifra fija por pareja. Ver docs/campos-prize-money-2026.md.

Deliberadamente NO se estima nada para FIP Tour, Premier Padel Finals, ni
R32/R64/clasificación: mejor una tabla incompleta y marcada que una completa
con números inventados (doc 03 §4, instrucción 5 del proyecto Cowork:
"Nunca inventes un dato para rellenar un hueco").
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_RESULTADO = REPO_ROOT / "silver" / "fact_resultado_torneo" / "data.json"
DIM_PRIZE = REPO_ROOT / "silver" / "dim_prize_categoria" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "ganancias_temporada"


def build() -> Path:
    resultados = json.loads(FACT_RESULTADO.read_text(encoding="utf-8"))
    prize_tabla = json.loads(DIM_PRIZE.read_text(encoding="utf-8"))
    prize_por_clave = {
        (p["circuito"], p["categoria"], p["ronda"]): p["prize_money_pareja_eur"]
        for p in prize_tabla
        if p["prize_money_pareja_eur"] is not None
    }

    dim_dir = REPO_ROOT / "silver" / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    nombres: dict[str, str] = {}
    sexo_por_jugador: dict[str, str] = {}
    if dt_dirs:
        filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        nombres = {r["jugador_id"]: r["nombre_canonico"] for r in filas}
        sexo_por_jugador = {r["jugador_id"]: r["sexo"] for r in filas}

    acumulado: dict[str, dict[str, Any]] = defaultdict(lambda: {"total_eur": 0.0, "torneos": set(), "detalle": []})

    for r in resultados:
        if not r["circuito"] or not r["categoria"]:
            continue
        premio = prize_por_clave.get((r["circuito"], r["categoria"], r["ronda_alcanzada"]))
        if premio is None:
            continue
        for jugador_id in (r["jugador_1_id"], r["jugador_2_id"]):
            entry = acumulado[jugador_id]
            entry["total_eur"] += premio
            entry["torneos"].add(r["torneo_id"])
            entry["detalle"].append(
                {
                    "torneo_nombre": r["torneo_nombre"],
                    "ronda_alcanzada": r["ronda_alcanzada"],
                    "premio_eur": premio,
                    "fecha": r["fecha"],
                }
            )

    rows: list[dict[str, Any]] = []
    for jugador_id, datos in acumulado.items():
        rows.append(
            {
                "fecha_dato": date.today().isoformat(),
                "jugador_id": jugador_id,
                "jugador_nombre": nombres.get(jugador_id),
                "sexo": sexo_por_jugador.get(jugador_id),
                "ganancias_conocidas_eur": round(datos["total_eur"], 2),
                "n_torneos_con_premio_conocido": len(datos["torneos"]),
                "detalle": sorted(datos["detalle"], key=lambda d: d["fecha"], reverse=True),
                "alcance": "Solo Premier Padel Major/P1/P2, rondas W/F/SF/QF/R16 (ver docs/campos-prize-money-2026.md)",
                "fuente_txt": "padelearnings.com + padelapi.org · elaboración propia",
                "publicable": datos["total_eur"] > 0,
            }
        )

    rows.sort(key=lambda r: -r["ganancias_conocidas_eur"])

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    if rows:
        top = rows[0]
        print(
            f"ganancias_temporada: {len(rows)} jugadores con ganancias conocidas. "
            f"Máximo: {top['jugador_nombre']} ({top['ganancias_conocidas_eur']:,.0f} €, "
            f"{top['n_torneos_con_premio_conocido']} torneos) — cifra parcial, ver 'alcance'"
        )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
