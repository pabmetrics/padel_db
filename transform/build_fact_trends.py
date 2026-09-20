"""Silver: fact_trends (doc 01 §3.2) — interés de búsqueda de Google Trends
por país y término, agregado a mes natural (la fuente da datos semanales).

Fuente: F12 (`ingest/google_trends/interes_padel.py`). Los índices de
"padel" y "tenis" son comparables **entre sí dentro del mismo país** (misma
consulta, misma normalización 0-100 de Google Trends) pero **no entre
países** — cada país es una consulta distinta con su propia escala. Ver
docs/campos-mercado-padel.md.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "google_trends" / "interes_padel"
OUT_PATH = REPO_ROOT / "silver" / "fact_trends" / "data.json"

FUENTE_TXT = "Google Trends (pytrends, no oficial) · elaboración propia"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise FileNotFoundError(f"Sin snapshots en {root}")
    return dirs[-1]


def build() -> Path:
    snapshot = json.loads((_latest_dir(BRONZE_ROOT) / "data.json").read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    for codigo, info in snapshot["paises"].items():
        por_mes: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"padel": [], "tenis": []})
        for punto in info["serie_semanal"]:
            mes = punto["fecha"][:7]
            por_mes[mes]["padel"].append(punto["padel"])
            por_mes[mes]["tenis"].append(punto["tenis"])

        for mes, valores in sorted(por_mes.items()):
            for termino in ("padel", "tenis"):
                serie = valores[termino]
                rows.append(
                    {
                        "mes": mes,
                        "geo": codigo,
                        "pais": info["pais"],
                        "termino": termino,
                        "indice": round(sum(serie) / len(serie), 1),
                        "clasificacion": info["clasificacion"],
                        "fuente_txt": FUENTE_TXT,
                    }
                )

    rows.sort(key=lambda r: (r["geo"], r["mes"], r["termino"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    n_paises = len({r["geo"] for r in rows})
    print(f"fact_trends: {len(rows)} filas, {n_paises} países -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
