"""Gold: h2h (doc 01 §3.3 / doc 02 #ParejasEnDatos, previas de torneo).

Una fila = el cara a cara histórico entre dos combinaciones concretas de
jugadores (pareja A vs pareja B), agregado across todas las eras de esa
pareja — un head-to-head normalmente se lee "todo lo que se han enfrentado
estos dos dúos", no por tramo de dim_pareja.

Fuente: fact_partido, 3.291 partidos (ventana de 180 días desde el
17/09/2026). El h2h solo refleja esa ventana, no el historial completo de
las parejas — mismo aviso que en parejas_duracion.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "h2h"

SLOTS_EQUIPO_1 = ("equipo_1_jugador_1", "equipo_1_jugador_2")
SLOTS_EQUIPO_2 = ("equipo_2_jugador_1", "equipo_2_jugador_2")


def _pareja_key(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str] | None:
    if not a.get("jugador_id") or not b.get("jugador_id"):
        return None
    return tuple(sorted((a["jugador_id"], b["jugador_id"])))


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))

    stats: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, Any]] = {}

    for partido in partidos:
        if partido.get("ganador") not in ("team_1", "team_2"):
            continue
        pareja_1 = _pareja_key(partido["equipo_1_jugador_1"], partido["equipo_1_jugador_2"]) if partido.get("equipo_1_jugador_1") and partido.get("equipo_1_jugador_2") else None
        pareja_2 = _pareja_key(partido["equipo_2_jugador_1"], partido["equipo_2_jugador_2"]) if partido.get("equipo_2_jugador_1") and partido.get("equipo_2_jugador_2") else None
        if not pareja_1 or not pareja_2:
            continue

        # clave del enfrentamiento, con las dos parejas ordenadas de forma
        # estable para que "A vs B" y "B vs A" caigan en la misma fila
        if pareja_1 <= pareja_2:
            clave, gano_izquierda = (pareja_1, pareja_2), partido["ganador"] == "team_1"
        else:
            clave, gano_izquierda = (pareja_2, pareja_1), partido["ganador"] == "team_2"

        if clave not in stats:
            stats[clave] = {"victorias_izquierda": 0, "victorias_derecha": 0, "fechas": [], "categoria": partido.get("categoria")}
        if gano_izquierda:
            stats[clave]["victorias_izquierda"] += 1
        else:
            stats[clave]["victorias_derecha"] += 1
        stats[clave]["fechas"].append(partido["fecha"])

    dim_dir = REPO_ROOT / "silver" / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    nombres: dict[str, str] = {}
    if dt_dirs:
        filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        nombres = {r["jugador_id"]: r["nombre_canonico"] for r in filas}

    def nombre_pareja(clave: tuple[str, str]) -> str:
        return " / ".join(nombres.get(j, j) for j in clave)

    rows: list[dict[str, Any]] = []
    for (pareja_izq, pareja_der), datos in stats.items():
        total = datos["victorias_izquierda"] + datos["victorias_derecha"]
        rows.append(
            {
                "pareja_1": nombre_pareja(pareja_izq),
                "pareja_2": nombre_pareja(pareja_der),
                "categoria": datos["categoria"],
                "victorias_pareja_1": datos["victorias_izquierda"],
                "victorias_pareja_2": datos["victorias_derecha"],
                "total_enfrentamientos": total,
                "ultimo_enfrentamiento": max(datos["fechas"]),
                "fuente_txt": "padelapi.org · elaboración propia",
                "publicable": total >= 2,
            }
        )

    rows.sort(key=lambda r: -r["total_enfrentamientos"])

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    repetidos = [r for r in rows if r["publicable"]]
    if repetidos:
        top = repetidos[0]
        print(
            f"h2h: {len(rows)} enfrentamientos únicos, {len(repetidos)} con 2+ partidos. "
            f"El más repetido: {top['pareja_1']} vs {top['pareja_2']} ({top['total_enfrentamientos']})"
        )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
