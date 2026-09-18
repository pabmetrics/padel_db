"""Conector F9 (OpenStreetMap, Overpass API) — pistas y clubes de pádel en
España. Fuente pública, sin autenticación.

Snapshot a bronze/osm/pistas/dt=<fecha>/data.json.

Nota (doc 01 §6, "trampas conocidas"): OSM no distingue de forma fiable
"pista individual" de "club completo" — algunos mapean cada pista como un
`way` (`leisure=pitch`), otros mapean el club entero como un único `node`
(`leisure=sports_centre`). Contar elementos en bruto sobrestima o
infraestima según la zona. Este conector guarda ambos tipos por separado
para que `transform/` decida cómo agregarlos, en vez de mezclar sin más.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "osm" / "pistas"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "padeldb.es research bot; contacto hola@padeldb.es"

QUERY = """
[out:json][timeout:180];
area["ISO3166-1"="ES"][admin_level=2]->.spain;
(
  node["sport"="padel"](area.spain);
  way["sport"="padel"](area.spain);
);
out center;
"""


def fetch() -> list[dict[str, Any]]:
    with httpx.Client(timeout=280, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}) as client:
        for intento in range(3):
            response = client.post(OVERPASS_URL, data={"data": QUERY})
            if response.status_code == 200:
                return response.json()["elements"]
            time.sleep(10 * (intento + 1))
        raise SystemExit(f"Overpass no respondió tras varios intentos: HTTP {response.status_code}")


def write_snapshot(elements: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(elements, sort_keys=True).encode()).hexdigest()
    snapshot = {
        "source": "openstreetmap",
        "endpoint": "https://overpass-api.de/api/interpreter (sport=padel, España)",
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256,
        "n_items": len(elements),
        "items": elements,
    }
    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    elements = fetch()
    out_file = write_snapshot(elements)
    print(f"{len(elements)} elementos con sport=padel -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
