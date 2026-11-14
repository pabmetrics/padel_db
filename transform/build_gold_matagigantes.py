"""Gold: matagigantes (14/11/2026) — victorias ante cabezas de serie mejores.

Una fila = una pareja en la temporada, con los partidos que jugó contra una
pareja mejor sembrada que ella en ese torneo (la rival con semilla y la
pareja sin semilla, o con un número de semilla más alto) y cuántos ganó.
Mismo criterio de semillas que `torneo_sorpresas` (las `seeds` de F2 por
torneo), pero acumulado por pareja: no el golpe de un día, sino quién lo
hace a menudo.

Fuente: `fact_partido` (F2).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "matagigantes"

MIN_VICTORIAS = 3
FUENTE_TXT = "padelapi.org · elaboración propia"


def _equipo(p: dict[str, Any], t: int) -> tuple[tuple[str, str], str] | None:
    j1, j2 = p.get(f"equipo_{t}_jugador_1") or {}, p.get(f"equipo_{t}_jugador_2") or {}
    if not j1.get("jugador_id") or not j2.get("jugador_id"):
        return None
    return tuple(sorted((j1["jugador_id"], j2["jugador_id"]))), f"{j1['nombre_padelapi']} / {j2['nombre_padelapi']}"


def peor_sembrada(propia: int | None, rival: int | None) -> bool:
    """La pareja llega como peor sembrada que la rival."""
    if rival is None:
        return False
    return propia is None or propia > rival


def calcular(partidos: list[dict[str, Any]], temporada: int) -> list[dict[str, Any]]:
    por_pareja: dict[tuple, dict[str, Any]] = {}
    for p in partidos:
        if not str(p.get("fecha", "")).startswith(str(temporada)):
            continue
        if p.get("marcador_incoherente") or p.get("ganador") not in ("team_1", "team_2"):
            continue
        for t, o in ((1, 2), (2, 1)):
            if not peor_sembrada(p.get(f"semilla_equipo_{t}"), p.get(f"semilla_equipo_{o}")):
                continue
            equipo = _equipo(p, t)
            if equipo is None:
                continue
            ids, nombre = equipo
            fila = por_pareja.setdefault((p["categoria"], ids), {
                "categoria": p["categoria"], "jugador_1_id": ids[0], "jugador_2_id": ids[1],
                "pareja": nombre, "partidos_ante_mejor_semilla": 0, "victorias_ante_mejor_semilla": 0,
                "mejor_semilla_eliminada": None,
            })
            fila["partidos_ante_mejor_semilla"] += 1
            if p["ganador"] == f"team_{t}":
                fila["victorias_ante_mejor_semilla"] += 1
                rival = p[f"semilla_equipo_{o}"]
                if fila["mejor_semilla_eliminada"] is None or rival < fila["mejor_semilla_eliminada"]:
                    fila["mejor_semilla_eliminada"] = rival

    hoy = date.today().isoformat()
    filas = [
        {
            **f,
            "temporada": temporada,
            "fecha_dato": hoy,
            "fuente_txt": FUENTE_TXT,
            "publicable": f["victorias_ante_mejor_semilla"] >= MIN_VICTORIAS,
        }
        for f in por_pareja.values()
    ]
    filas.sort(key=lambda r: (r["categoria"], -r["victorias_ante_mejor_semilla"], r["partidos_ante_mejor_semilla"]))
    return filas


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    temporada = max(int(p["fecha"][:4]) for p in partidos if p.get("fecha"))
    filas = calcular(partidos, temporada)

    out_dir = GOLD_ROOT / f"fecha_dato={date.today().isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"matagigantes: {len(filas)} parejas, {sum(r['publicable'] for r in filas)} publicables -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
