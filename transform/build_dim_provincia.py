"""dim_provincia: límites geográficos (OSM) + población (INE, tabla 2852,
vintage 2021 — ver ingest/ine/poblacion_provincia.py) por provincia.

La geometría se ensambla con shapely.ops.polygonize a partir de los tramos
de `way` que forman cada relación de límite administrativo — el método
estándar para reconstruir polígonos desde datos de OSM sin asumir un orden
concreto de los segmentos.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union
from shapely.wkt import dumps as wkt_dumps
from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_PROVINCIAS = REPO_ROOT / "bronze" / "osm" / "provincias"
BRONZE_POBLACION = REPO_ROOT / "bronze" / "ine" / "poblacion_provincia"
OUT_PATH = REPO_ROOT / "silver" / "dim_provincia" / "data.json"


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unidecode(name or "").lower()).strip()


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def build_polygon(rel: dict[str, Any]):
    lines = []
    for m in rel.get("members", []):
        if m.get("type") != "way" or "geometry" not in m:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in m["geometry"]]
        if len(coords) >= 2:
            lines.append(LineString(coords))
    if not lines:
        return None
    merged = unary_union(lines)
    polys = list(polygonize(merged))
    if not polys:
        return None
    return unary_union(polys)


def wordset(name: str) -> frozenset[str]:
    """Conjunto de palabras normalizadas — resuelve solo con esto la mayoría
    de las discrepancias INE/OSM: orden distinto ('Alacant / Alicante' vs
    'Alicante/Alacant') y formato 'Nombre, Artículo' vs 'Artículo Nombre'
    ('Rioja, La' vs 'La Rioja'), sin necesitar una lista de alias a mano."""

    return frozenset(w for w in normalize(name).split(" ") if w)


def load_poblacion() -> dict[frozenset[str], tuple[int, int]]:
    """conjunto de palabras del nombre -> (poblacion, año), con el dato
    'Total' (no desagregado por sexo) más reciente de cada provincia."""

    dt_dir = _latest_dir(BRONZE_POBLACION)
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    poblacion: dict[frozenset[str], tuple[int, int]] = {}
    for serie in payload["items"]:
        nombre = serie["Nombre"]
        if ". Total. Total habitantes." not in nombre:
            continue
        provincia = nombre.split(".")[0].strip()
        if not serie["Data"]:
            continue
        punto = max(serie["Data"], key=lambda d: d["Anyo"])
        poblacion[wordset(provincia)] = (int(punto["Valor"]), punto["Anyo"])
    return poblacion


# Solo para los nombres de OSM con palabras descriptivas que el INE no usa
# (p. ej. "Comunidad de Madrid" en vez de "Madrid") — el resto de casos los
# resuelve wordset() sin necesitar esto.
ALIAS_OSM_A_INE_WORDSET = {
    frozenset({"comunidad", "de", "madrid"}): frozenset({"madrid"}),
    frozenset({"region", "de", "murcia"}): frozenset({"murcia"}),
}


def _buscar_por_solape(clave: frozenset[str], poblacion: dict[frozenset[str], tuple[int, int]]):
    """Último recurso: si un conjunto de palabras es subconjunto del otro
    (ej. INE 'Asturias' ⊂ OSM 'Asturias Asturies', la forma bilingüe),
    se considera la misma provincia."""

    candidatos = [v for k, v in poblacion.items() if k <= clave or clave <= k]
    return candidatos[0] if len(candidatos) == 1 else None


def build() -> Path:
    dt_dir = _latest_dir(BRONZE_PROVINCIAS)
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    poblacion = load_poblacion()

    rows: list[dict[str, Any]] = []
    sin_poblacion: list[str] = []

    for rel in payload["items"]:
        nombre = rel["tags"].get("name")
        if not nombre:
            continue
        poly = build_polygon(rel)
        if poly is None:
            continue

        clave = wordset(nombre)
        dato = poblacion.get(clave)
        if dato is None and clave in ALIAS_OSM_A_INE_WORDSET:
            dato = poblacion.get(ALIAS_OSM_A_INE_WORDSET[clave])
        if dato is None:
            dato = _buscar_por_solape(clave, poblacion)
        if dato is None:
            sin_poblacion.append(nombre)

        centroide = poly.centroid
        rows.append(
            {
                "provincia_id": f"PR{rel['id']}",
                "nombre": nombre,
                "osm_relation_id": rel["id"],
                "poblacion": dato[0] if dato else None,
                "anio_poblacion": dato[1] if dato else None,
                "lat_centroide": round(centroide.y, 5),
                "lon_centroide": round(centroide.x, 5),
                "geometria_wkt": wkt_dumps(poly),
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    con_poblacion = sum(1 for r in rows if r["poblacion"] is not None)
    print(f"dim_provincia: {len(rows)} provincias ({con_poblacion} con población cruzada) -> {OUT_PATH.relative_to(REPO_ROOT)}")
    if sin_poblacion:
        print(f"  Sin población cruzada: {sin_poblacion}")
    return OUT_PATH


if __name__ == "__main__":
    build()
