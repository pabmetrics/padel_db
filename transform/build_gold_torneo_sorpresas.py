"""Gold: torneo_sorpresas (doc 01 §3.3 / doc 02 "El torneo en datos").

Una fila = una eliminación de una pareja mejor sembrada por una peor
sembrada (semilla más alta = cabeza de serie más baja). Usa las semillas
(`seeds`) que trae F2 directamente en cada partido — más fiable ahora mismo
que aproximar el ranking exacto de cada jugador en la fecha del partido, que
no tenemos (solo hay un snapshot propio de ranking, no histórico por fecha).

Solo partidos con semillas conocidas en ambos lados (no todos los cruces de
un cuadro llevan semilla) y con marcador coherente (se excluyen los
marcados `marcador_incoherente`, ver build_fact_partido.py).

Dos fuentes (14/11/2026): `fact_partido` (F2, se ingiere los lunes) y
`fact_partido_stats` (F1, Premier Padel, a diario y con el torneo en curso).
Sin la segunda, "El torneo en datos" no veía el torneo de la semana hasta
el lunes siguiente y repetía la sorpresa del último torneo ya ingerido
(Milano P1, del 9 al 13/11). Un partido que esté en las dos se cuenta una
vez (mismos 4 `jugador_id` y misma fecha), con la fila de F2.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
FACT_PARTIDO_STATS = REPO_ROOT / "silver" / "fact_partido_stats" / "data.json"
DIM_TORNEO_ROOT = REPO_ROOT / "silver" / "dim_torneo"
GOLD_ROOT = REPO_ROOT / "gold" / "torneo_sorpresas"


def _nombre_equipo(a: dict[str, Any] | None, b: dict[str, Any] | None) -> str | None:
    if not a or not b:
        return None
    return f"{a['nombre_padelapi']} / {b['nombre_padelapi']}"


RONDAS_F1 = {
    "R64": "Round of 64", "R32": "Round of 32", "R16": "Round of 16",
    "QF": "Quarter", "SF": "Semifinals", "F": "Finals",  # mismos nombres que F2
}


def nombre_torneo_f1(slug: str, nombres_calendario: dict[str, str]) -> str:
    """Nombre legible de un torneo de Premier Padel a partir de su slug: el
    del calendario (`dim_torneo`) si está, y si no, el propio slug sin el
    sufijo de edición ("dubai-p1-3" -> "Dubai P1")."""
    nombre = nombres_calendario.get(slug)
    if not nombre:
        nombre = re.sub(r"-\d+$", "", slug).replace("-", " ")
    palabras = [w.upper() if re.fullmatch(r"p\d", w, re.IGNORECASE) else w.capitalize() for w in nombre.split()]
    return " ".join(palabras)


def _nombres_calendario() -> dict[str, str]:
    dirs = sorted(p for p in DIM_TORNEO_ROOT.glob("dt=*") if p.is_dir())
    if not dirs:
        return {}
    torneos = json.loads((dirs[-1] / "data.json").read_text(encoding="utf-8"))
    return {t["slug_premierpadel"]: t["nombre"] for t in torneos if t.get("slug_premierpadel")}


def _marcador(ganador: dict[str, Any], perdedor: dict[str, Any]) -> str | None:
    a, b = ganador.get("juegos_por_set") or [], perdedor.get("juegos_por_set") or []
    if not a or len(a) != len(b):
        return None
    return ", ".join(f"{x}-{y}" for x, y in zip(a, b))


def sorpresas_f1(filas: list[dict[str, Any]], nombres_calendario: dict[str, str]) -> list[dict[str, Any]]:
    """Sorpresas del cuadro principal de Premier Padel (`fact_partido_stats`,
    bloque "partido": una fila por equipo). Misma regla que con F2: semillas
    conocidas en los dos lados y gana la peor situada."""
    por_partido: dict[str, dict[int, dict[str, Any]]] = {}
    for f in filas:
        if f.get("bloque") == "partido" and f.get("fase") == "main":
            por_partido.setdefault(f["partido_id"], {})[f["equipo"]] = f

    rows: list[dict[str, Any]] = []
    for equipos in por_partido.values():
        if set(equipos) != {1, 2}:
            continue
        ganadores = [e for e in equipos.values() if e.get("gana") is True]
        perdedores = [e for e in equipos.values() if e.get("gana") is False]
        if len(ganadores) != 1 or len(perdedores) != 1:
            continue
        g, p = ganadores[0], perdedores[0]
        if g.get("semilla") is None or p.get("semilla") is None or g["semilla"] <= p["semilla"]:
            continue
        rows.append(
            {
                "fecha": g["fecha"],
                # Con el año, como los nombra F2 ("Milano P1 2026"): el mismo
                # torneo se llama igual venga de una fuente o de la otra.
                "torneo_nombre": f"{nombre_torneo_f1(g['torneo_slug'], nombres_calendario)} {g['fecha'][:4]}",
                "categoria": "men" if g["sexo"] == "M" else "women",
                "ronda": RONDAS_F1.get(g.get("ronda"), g.get("ronda")),
                "equipo_ganador": f"{g['jugador_1_nombre_fuente']} / {g['jugador_2_nombre_fuente']}",
                "semilla_ganador": g["semilla"],
                "equipo_perdedor": f"{p['jugador_1_nombre_fuente']} / {p['jugador_2_nombre_fuente']}",
                "semilla_perdedor": p["semilla"],
                "diferencia_semillas": g["semilla"] - p["semilla"],
                "marcador_txt": _marcador(g, p),
                "fuente_txt": "Premier Padel · elaboración propia",
                "publicable": g["semilla"] - p["semilla"] >= 3,
                "_ids": frozenset(filter(None, (g.get("jugador_1_id"), g.get("jugador_2_id"),
                                                p.get("jugador_1_id"), p.get("jugador_2_id")))),
            }
        )
    return rows


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    ya_vistos: set[tuple[str, frozenset[str]]] = set()
    for p in partidos:
        ya_vistos.add((p["fecha"], frozenset(
            (p.get(k) or {}).get("jugador_id")
            for k in ("equipo_1_jugador_1", "equipo_1_jugador_2", "equipo_2_jugador_1", "equipo_2_jugador_2")
        )))
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

    if FACT_PARTIDO_STATS.exists():
        filas_f1 = json.loads(FACT_PARTIDO_STATS.read_text(encoding="utf-8"))
        for r in sorpresas_f1(filas_f1, _nombres_calendario()):
            ids = r.pop("_ids")
            if len(ids) == 4 and (r["fecha"], ids) in ya_vistos:
                continue  # ya está con la fila de F2
            rows.append(r)

    rows.sort(key=lambda r: (-r["diferencia_semillas"], r["fecha"]))

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
