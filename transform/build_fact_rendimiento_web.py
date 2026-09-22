"""fact_rendimiento_web: último snapshot de bronze/webanalytics/pageviews
(Cloudflare Web Analytics, `ingest/webanalytics/cloudflare.py`) a silver.

A diferencia de `fact_rendimiento_x`, esta fuente sí es 100% automática
(API de Cloudflare, sin export manual) — ver doc 01 §3.4.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "webanalytics" / "pageviews"
OUT_PATH = REPO_ROOT / "silver" / "fact_rendimiento_web" / "data.json"


def _mostrar(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _ultimo_snapshot() -> Path | None:
    snapshots = sorted(BRONZE_ROOT.glob("dt=*/data.json"))
    return snapshots[-1] if snapshots else None


def build() -> Path:
    snapshot = _ultimo_snapshot()
    rows: list[dict[str, Any]] = []

    if snapshot is not None:
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
        for grupo in payload.get("grupos", []):
            dims = grupo.get("dimensions", {})
            rows.append(
                {
                    "fecha": dims.get("date"),
                    "ruta": dims.get("requestPath"),
                    "pageviews": grupo.get("count"),
                    "visitas": (grupo.get("sum") or {}).get("visits"),
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    if snapshot is None:
        print("fact_rendimiento_web: sin snapshot en bronze todavía (falta ejecutar ingest/webanalytics/cloudflare.py)")
    else:
        print(f"fact_rendimiento_web: {len(rows)} filas día×ruta, desde {_mostrar(snapshot)}")
    print(f"-> {_mostrar(OUT_PATH)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
