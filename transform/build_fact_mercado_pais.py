"""Silver: fact_mercado_pais (doc 01 §3.2) — mercado del pádel por país.

Dos fuentes independientes, **nunca mezcladas** (doc 01 §6: "F5 y F6 no se
mezclan"; mismo criterio ya aplicado a licencias CSD/FEP):

- F6 (FIP World Padel Report 2025, `padelfip.com`): cifras y porcentajes
  citados en prosa dentro del informe — pistas, clubes, jugadores,
  porcentajes de aficionados por continente. Transcritos a
  `data/manual/mercado_fip_2025.csv`.
- F5 (Playtomic Global Padel Report 2026): marco de 5 arquetipos que
  clasifica países por madurez de ecosistema y calidad de demanda (Padel
  Heartlands, The Sweet Spot, The Hotspot, Diamonds in the Rough,
  Post-Boom Adjustment), con rangos de pistas/jugadores por 100.000
  habitantes por arquetipo (no cifras exactas por país). Transcrito a
  `data/manual/mercado_playtomic_2026.csv`.

Ambos informes dan números de pistas/jugadores mundiales que **no
coinciden** (FIP: 77.355 pistas a junio 2025; Playtomic: 58.334 pistas a
cierre de 2025) — es exactamente el tipo de discrepancia entre fuentes que
el doc de arquitectura ya avisa que hay que documentar, no reconciliar.
Solo se transcriben aquí las cifras explícitas en el texto de cada
informe (nunca las de gráficos/figuras donde el orden de barras y las
cifras no se pueden emparejar con seguridad al extraer el PDF).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_FIP = REPO_ROOT / "data" / "manual" / "mercado_fip_2025.csv"
CSV_PLAYTOMIC = REPO_ROOT / "data" / "manual" / "mercado_playtomic_2026.csv"
OUT_PATH = REPO_ROOT / "silver" / "fact_mercado_pais" / "data.json"

FUENTE_TXT_FIP = "FIP World Padel Report 2025 · elaboración propia"
FUENTE_TXT_PLAYTOMIC = "Playtomic Global Padel Report 2026 (con Strategy&, PwC) · elaboración propia"


def _filas_fip() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with CSV_FIP.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "fuente": "fip",
                    "pais": row["pais"],
                    "continente": row["continente"] or None,
                    "categoria": row["categoria"],
                    "valor": float(row["valor"]),
                    "unidad": row["unidad"],
                    "calificador": row["calificador"],
                    "contexto_txt": row["contexto_txt"] or None,
                    "fuente_txt": FUENTE_TXT_FIP,
                }
            )
    return rows


def _filas_playtomic() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with CSV_PLAYTOMIC.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "fuente": "playtomic",
                    "pais": row["pais"],
                    "arquetipo": row["arquetipo"] or None,
                    "orden_arquetipo": int(row["orden_arquetipo"]) if row["orden_arquetipo"] else None,
                    "pistas_por_100k_min": float(row["pistas_por_100k_min"]) if row["pistas_por_100k_min"] else None,
                    "pistas_por_100k_max": float(row["pistas_por_100k_max"]) if row["pistas_por_100k_max"] else None,
                    "jugadores_por_100k_min": float(row["jugadores_por_100k_min"]) if row["jugadores_por_100k_min"] else None,
                    "jugadores_por_100k_max": float(row["jugadores_por_100k_max"]) if row["jugadores_por_100k_max"] else None,
                    "crecimiento_categoria": row["crecimiento_categoria"] or None,
                    "contexto_txt": row["contexto_txt"] or None,
                    "fuente_txt": FUENTE_TXT_PLAYTOMIC,
                }
            )
    return rows


def build() -> Path:
    rows = _filas_fip() + _filas_playtomic()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    n_fip = sum(1 for r in rows if r["fuente"] == "fip")
    n_playtomic = sum(1 for r in rows if r["fuente"] == "playtomic")
    print(f"fact_mercado_pais: {len(rows)} filas ({n_fip} FIP, {n_playtomic} Playtomic) -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
