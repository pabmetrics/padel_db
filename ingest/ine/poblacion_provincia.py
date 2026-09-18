"""Conector F10 (INE, API JSON wstempus) — población por provincia.

Tabla 2852 ("Cifras de población"). Cubre las 52 provincias + total
nacional. **Vintage real: 2021** — es el último año publicado en esta
tabla concreta a fecha de este conector (17/09/2026); el padrón municipal
tiene series más recientes en otras tablas de INEbase, pero requieren un
identificador de tabla distinto que no se ha localizado con la confianza
suficiente para no arriesgarse a coger la tabla equivocada — mejor una
cifra de 2021 verificada que una más reciente sin confirmar. Pendiente de
revisión en Fase 5.

Requiere un User-Agent de navegador: la API de INE devuelve 403 con el
User-Agent por defecto de httpx.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "ine" / "poblacion_provincia"
URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (padeldb.es research bot; contacto hola@padeldb.es)"


def fetch() -> list[dict[str, Any]]:
    response = httpx.get(URL, params={"nult": 3}, timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def write_snapshot(items: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    snapshot = {
        "source": "ine",
        "endpoint": f"{URL} (tabla 2852)",
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256,
        "n_items": len(items),
        "items": items,
    }
    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    items = fetch()
    out_file = write_snapshot(items)
    print(f"{len(items)} series -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
