"""fact_pistas: cruce espacial real (point-in-polygon con shapely) de cada
elemento `sport=padel` de OSM con su provincia.

Doc 01 §6 ("trampas conocidas"): OSM mezcla pistas individuales
(`leisure=pitch`) y clubes enteros como un único punto (`leisure=sports_centre`,
`leisure=fitness_centre`, etc.). Este script cuenta ambos por separado en
vez de sumarlos sin más — `n_elementos_pitch` es lo más parecido a "número
de pistas" que da la fuente, pero infraestima allí donde solo se ha
mapeado el club; `n_ubicaciones` (agrupando por coordenadas redondeadas)
es una cota inferior más fiable de "número de clubes".
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_PISTAS = REPO_ROOT / "bronze" / "osm" / "pistas"
DIM_PROVINCIA = REPO_ROOT / "silver" / "dim_provincia" / "data.json"
OUT_PATH = REPO_ROOT / "silver" / "fact_pistas" / "data.json"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def _coords(el: dict[str, Any]) -> tuple[float, float] | None:
    if el["type"] == "node":
        return el.get("lat"), el.get("lon")
    center = el.get("center")
    return (center["lat"], center["lon"]) if center else None


def build() -> Path:
    dt_dir = _latest_dir(BRONZE_PISTAS)
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    provincias = json.loads(DIM_PROVINCIA.read_text(encoding="utf-8"))
    poligonos = [(p["provincia_id"], p["nombre"], wkt_loads(p["geometria_wkt"])) for p in provincias]

    por_provincia: dict[str, dict[str, Any]] = defaultdict(lambda: {"n_elementos": 0, "n_pitch": 0, "ubicaciones": set()})
    fuera_de_espana = 0

    for el in payload["items"]:
        coords = _coords(el)
        if not coords or coords[0] is None:
            continue
        lat, lon = coords
        punto = Point(lon, lat)

        provincia_id = provincia_nombre = None
        for pid, pnombre, poly in poligonos:
            if poly.contains(punto):
                provincia_id, provincia_nombre = pid, pnombre
                break
        if provincia_id is None:
            fuera_de_espana += 1
            continue

        entry = por_provincia[provincia_id]
        entry["nombre"] = provincia_nombre
        entry["n_elementos"] += 1
        if el.get("tags", {}).get("leisure") == "pitch":
            entry["n_pitch"] += 1
        # ubicación redondeada a ~100 m para deduplicar pistas del mismo club
        entry["ubicaciones"].add((round(lat, 3), round(lon, 3)))

    rows: list[dict[str, Any]] = []
    hoy = date.today().isoformat()
    for provincia_id, datos in por_provincia.items():
        rows.append(
            {
                "snapshot_fecha": hoy,
                "provincia_id": provincia_id,
                "provincia_nombre": datos["nombre"],
                "n_elementos_osm": datos["n_elementos"],
                "n_elementos_pitch": datos["n_pitch"],
                "n_ubicaciones": len(datos["ubicaciones"]),
                "fuente": "openstreetmap",
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    total = sum(r["n_elementos_osm"] for r in rows)
    print(f"fact_pistas: {len(rows)} provincias, {total} elementos asignados ({fuera_de_espana} sin provincia — islas/costa mal delimitada en OSM) -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
