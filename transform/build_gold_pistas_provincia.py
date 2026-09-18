"""Gold: pistas_provincia (doc 01 §3.3 "pistas_municipio" / doc 02
#MapaDelPádel). Primera versión a nivel provincia, no municipio — ver
docs/campos-pistas-territorio.md sobre por qué.

Una fila = una provincia con pistas (OSM) por 10.000 habitantes (INE,
vintage 2021).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DIM_PROVINCIA = REPO_ROOT / "silver" / "dim_provincia" / "data.json"
FACT_PISTAS = REPO_ROOT / "silver" / "fact_pistas" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "pistas_provincia"


def build() -> Path:
    provincias = {p["provincia_id"]: p for p in json.loads(DIM_PROVINCIA.read_text(encoding="utf-8"))}
    pistas = json.loads(FACT_PISTAS.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    for p in pistas:
        prov = provincias.get(p["provincia_id"])
        if not prov or not prov.get("poblacion"):
            continue
        pistas_por_10k = round(p["n_elementos_osm"] / prov["poblacion"] * 10000, 2)
        rows.append(
            {
                "fecha_dato": p["snapshot_fecha"],
                "provincia_id": p["provincia_id"],
                "provincia_nombre": p["provincia_nombre"],
                "poblacion": prov["poblacion"],
                "anio_poblacion": prov["anio_poblacion"],
                "n_elementos_padel_osm": p["n_elementos_osm"],
                "n_ubicaciones_estimadas": p["n_ubicaciones"],
                "elementos_por_10000_hab": pistas_por_10k,
                "fuente_txt": "OpenStreetMap (colaborativo) + INE, Cifras de población · elaboración propia",
                "publicable": p["n_elementos_osm"] >= 3,
            }
        )

    rows.sort(key=lambda r: -r["elementos_por_10000_hab"])

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    if rows:
        top = rows[0]
        print(
            f"pistas_provincia: {len(rows)} provincias. Más pistas por 10.000 hab.: "
            f"{top['provincia_nombre']} ({top['elementos_por_10000_hab']})"
        )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
