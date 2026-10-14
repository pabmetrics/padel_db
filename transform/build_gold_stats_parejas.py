"""Gold: stats_parejas — estadísticas de pista por pareja en la temporada
(F1, `silver/fact_partido_stats`).

Una fila = una pareja (dos `jugador_id`) y sexo, con sus partidos de cuadro
principal de la temporada que tienen estadísticas. Los porcentajes se
calculan sumando recuentos de todos los partidos (puntos ganados / puntos
jugados), no promediando el porcentaje de cada partido: un partido de tres
sets pesa lo que pesa.

Métricas: % de puntos ganados al resto, al saque, con el 2.º saque y en
total; racha máxima de puntos seguidos; duración media.

`publicable` exige los dos jugadores cruzados con `dim_jugador` y al menos
`MIN_PARTIDOS` partidos con stats: por debajo, un porcentaje dice más del
cuadro que le tocó a la pareja que de la pareja.

La previa (`fase = qualy`) queda fuera: los rivales no son comparables.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))  # se ejecuta como `python transform/build_gold_stats_parejas.py`

from content.copy_factory.nombres import cargar_alias  # noqa: E402

FACT = REPO_ROOT / "silver" / "fact_partido_stats" / "data.json"
DIM_JUGADOR_ROOT = REPO_ROOT / "silver" / "dim_jugador"
GOLD_ROOT = REPO_ROOT / "gold" / "stats_parejas"

MIN_PARTIDOS = 8
RATIOS = ("puntos_resto", "puntos_saque", "segundo_saque", "puntos_totales")
FUENTE_TXT = "Premier Padel · elaboración propia"


def _pct(ganados: int, jugados: int) -> float | None:
    return round(100 * ganados / jugados, 1) if jugados else None


def agregar(filas: list[dict[str, Any]], temporada: int, nombres: dict[str, str]) -> list[dict[str, Any]]:
    parejas: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}
    for f in filas:
        if f["bloque"] != "partido" or f["fase"] != "main" or f["stats_vacias"] or not str(f.get("fecha") or "").startswith(str(temporada)):
            continue
        ids = (f.get("jugador_1_id"), f.get("jugador_2_id"))
        cruzada = all(ids)
        clave_ids = tuple(sorted(ids)) if cruzada else (f"?{f['jugador_1_nombre_fuente']}", f"?{f['jugador_2_nombre_fuente']}")
        p = parejas.setdefault((f["sexo"], clave_ids), {
            "sexo": f["sexo"], "ids": clave_ids, "cruzada": cruzada, "partidos": 0, "victorias": 0,
            "racha_max": 0, "minutos": 0, "partidos_con_duracion": 0, "torneos": set(),
            **{f"{r}_{s}": 0 for r in RATIOS for s in ("ganados", "jugados")},
        })
        p["partidos"] += 1
        p["victorias"] += bool(f["gana"])
        p["racha_max"] = max(p["racha_max"], f.get("racha_max") or 0)
        p["torneos"].add(f["torneo_slug"])
        if f.get("duracion_min"):
            p["minutos"] += f["duracion_min"]
            p["partidos_con_duracion"] += 1
        for r in RATIOS:
            g, j = f.get(f"{r}_ganados"), f.get(f"{r}_jugados")
            if g is not None and j:
                p[f"{r}_ganados"] += g
                p[f"{r}_jugados"] += j

    salida = []
    for p in parejas.values():
        a, b = p["ids"]
        fila = {
            "temporada": temporada,
            "sexo": p["sexo"],
            "jugador_1_id": a if p["cruzada"] else None,
            "jugador_2_id": b if p["cruzada"] else None,
            "pareja": " / ".join(nombres.get(i, i.lstrip("?")) for i in (a, b)),
            "partidos": p["partidos"],
            "victorias": p["victorias"],
            "torneos": len(p["torneos"]),
            **{f"pct_{r}": _pct(p[f"{r}_ganados"], p[f"{r}_jugados"]) for r in RATIOS},
            **{f"{r}_{s}": p[f"{r}_{s}"] for r in RATIOS for s in ("ganados", "jugados")},
            "racha_max": p["racha_max"],
            "duracion_media_min": round(p["minutos"] / p["partidos_con_duracion"]) if p["partidos_con_duracion"] else None,
            "fuente_txt": FUENTE_TXT,
            "publicable": p["cruzada"] and p["partidos"] >= MIN_PARTIDOS,
        }
        salida.append(fila)
    salida.sort(key=lambda r: (r["sexo"], -(r["pct_puntos_resto"] or 0)))
    return salida


def build(hoy: date | None = None) -> Path:
    hoy = hoy or date.today()
    filas = json.loads(FACT.read_text(encoding="utf-8"))
    dim_dir = sorted(p for p in DIM_JUGADOR_ROOT.glob("dt=*") if p.is_dir())[-1]
    alias = cargar_alias()
    nombres = {
        r["jugador_id"]: alias.get(r["nombre_canonico"], r["nombre_canonico"])
        for r in json.loads((dim_dir / "data.json").read_text(encoding="utf-8"))
    }

    salida = agregar(filas, hoy.year, nombres)
    fecha_dato = max((f["fecha"] for f in filas if f.get("fecha")), default=hoy.isoformat())
    for r in salida:
        r["fecha_dato"] = fecha_dato

    out_dir = GOLD_ROOT / f"fecha_dato={fecha_dato}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    for sexo in ("M", "F"):
        pub = [r for r in salida if r["sexo"] == sexo and r["publicable"]]
        print(f"stats_parejas {hoy.year} {sexo}: {len(pub)} parejas publicables (>= {MIN_PARTIDOS} partidos)")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
