"""Gold: remontadas (14/11/2026) — quién gana después de perder el primer set.

Una fila = una pareja (dos `jugador_id`) en la temporada, con los partidos
en los que perdió el primer set y cuántos de ellos acabó ganando. Cada fila
lleva también el % del circuito entero (todas las parejas, sin mínimo),
que es la referencia del gráfico: remontar es raro (≈11 % en 2026), y
eso es lo que hace noticia de la pareja que lo consigue a menudo.

Fuente: `fact_partido` (F2). Se excluyen los partidos sin marcador (oculto
en el plan gratuito), con marcador incoherente o con el primer set
empatado en el texto (no debería pasar, pero no se adivina quién lo ganó).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "remontadas"

MIN_PRIMER_SET_PERDIDO = 8  # por debajo, un 2 de 3 es ruido
FUENTE_TXT = "padelapi.org · elaboración propia"


def ganador_primer_set(marcador_txt: str | None) -> int | None:
    """1 o 2 según quién ganó el primer set ("6-4, 3-6, 7-5" -> 1)."""
    m = re.match(r"\s*(\d+)-(\d+)", marcador_txt or "")
    if not m or m[1] == m[2]:
        return None
    return 1 if int(m[1]) > int(m[2]) else 2


def _equipo(p: dict[str, Any], t: int) -> tuple[tuple[str, str], str] | None:
    j1, j2 = p.get(f"equipo_{t}_jugador_1") or {}, p.get(f"equipo_{t}_jugador_2") or {}
    if not j1.get("jugador_id") or not j2.get("jugador_id"):
        return None
    ids = tuple(sorted((j1["jugador_id"], j2["jugador_id"])))
    return ids, f"{j1['nombre_padelapi']} / {j2['nombre_padelapi']}"


def calcular(partidos: list[dict[str, Any]], temporada: int) -> list[dict[str, Any]]:
    por_pareja: dict[tuple, dict[str, Any]] = {}
    circuito: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # perdidos 1er set, remontados

    for p in partidos:
        if not str(p.get("fecha", "")).startswith(str(temporada)):
            continue
        if p.get("marcador_incoherente") or p.get("ganador") not in ("team_1", "team_2"):
            continue
        primero = ganador_primer_set(p.get("marcador_txt"))
        if primero is None:
            continue
        perdedor_primer_set = 2 if primero == 1 else 1
        equipo = _equipo(p, perdedor_primer_set)
        if equipo is None:
            continue
        ids, nombre = equipo
        remonta = p["ganador"] == f"team_{perdedor_primer_set}"

        fila = por_pareja.setdefault((p["categoria"], ids), {
            "categoria": p["categoria"], "jugador_1_id": ids[0], "jugador_2_id": ids[1],
            "pareja": nombre, "primer_set_perdido": 0, "remontadas": 0,
        })
        fila["primer_set_perdido"] += 1
        fila["remontadas"] += remonta
        circuito[p["categoria"]][0] += 1
        circuito[p["categoria"]][1] += remonta

    hoy = date.today().isoformat()
    filas = []
    for fila in por_pareja.values():
        total, remontadas = circuito[fila["categoria"]]
        filas.append({
            **fila,
            "temporada": temporada,
            "pct_remontada": round(100 * fila["remontadas"] / fila["primer_set_perdido"], 1),
            "pct_remontada_circuito": round(100 * remontadas / total, 1),
            "fecha_dato": hoy,
            "fuente_txt": FUENTE_TXT,
            "publicable": fila["primer_set_perdido"] >= MIN_PRIMER_SET_PERDIDO,
        })
    filas.sort(key=lambda r: (r["categoria"], -r["pct_remontada"], -r["primer_set_perdido"]))
    return filas


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    temporada = max(int(p["fecha"][:4]) for p in partidos if p.get("fecha"))
    filas = calcular(partidos, temporada)

    out_dir = GOLD_ROOT / f"fecha_dato={date.today().isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"remontadas: {len(filas)} parejas, {sum(r['publicable'] for r in filas)} publicables -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
