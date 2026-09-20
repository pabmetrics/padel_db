"""Gold: trends_geo (doc 01 §3.3 / doc 02 #26-27 del backlog: "interés en
Google: pádel vs pickleball/tenis por país", estacionalidad).

Una fila = un país, con el ratio padel/tenis del trimestre más reciente y
su variación frente al trimestre anterior — así "en expansión" se lee como
"crece más rápido", no solo "tiene un índice alto" (que sería una cifra sin
poder compararse entre países en la escala nativa de Trends). Ver
docs/campos-mercado-padel.md.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_TRENDS = REPO_ROOT / "silver" / "fact_trends" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "trends_geo"

FUENTE_TXT = "Google Trends (pytrends, no oficial) · elaboración propia"


def _ratio_trimestre(meses_ordenados: list[str], por_mes: dict[str, dict[str, float]], meses: list[str]) -> float | None:
    ratios = []
    for mes in meses:
        valores = por_mes.get(mes)
        if not valores or not valores.get("tenis"):
            continue
        ratios.append(valores["padel"] / valores["tenis"])
    if not ratios:
        return None
    return round(sum(ratios) / len(ratios), 2)


def build() -> Path:
    filas = json.loads(FACT_TRENDS.read_text(encoding="utf-8"))

    por_pais: dict[str, dict[str, Any]] = {}
    for f in filas:
        geo = f["geo"]
        por_pais.setdefault(geo, {"pais": f["pais"], "clasificacion": f["clasificacion"], "por_mes": defaultdict(dict)})
        por_pais[geo]["por_mes"][f["mes"]][f["termino"]] = f["indice"]

    rows: list[dict[str, Any]] = []
    for geo, info in por_pais.items():
        meses_ordenados = sorted(info["por_mes"])
        if len(meses_ordenados) < 2:
            continue
        ultimos_3 = meses_ordenados[-3:]
        anteriores_3 = meses_ordenados[-6:-3] if len(meses_ordenados) >= 6 else meses_ordenados[:-3]

        ratio_reciente = _ratio_trimestre(meses_ordenados, info["por_mes"], ultimos_3)
        ratio_anterior = _ratio_trimestre(meses_ordenados, info["por_mes"], anteriores_3) if anteriores_3 else None

        variacion_pct = None
        if ratio_reciente is not None and ratio_anterior:
            variacion_pct = round((ratio_reciente - ratio_anterior) / ratio_anterior * 100, 1)

        rows.append(
            {
                "fecha_dato": f"{meses_ordenados[-1]}-01",
                "geo": geo,
                "pais": info["pais"],
                "clasificacion": info["clasificacion"],
                "ratio_padel_tenis_reciente": ratio_reciente,
                "ratio_padel_tenis_anterior": ratio_anterior,
                "variacion_pct": variacion_pct,
                "meses_con_dato": len(meses_ordenados),
                "fuente_txt": FUENTE_TXT,
                "publicable": ratio_reciente is not None,
            }
        )

    rows.sort(key=lambda r: (r["variacion_pct"] is None, -(r["variacion_pct"] or 0)))

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    publicables = [r for r in rows if r["publicable"]]
    print(f"trends_geo: {len(rows)} países ({len(publicables)} publicables)")
    if publicables:
        top = publicables[0]
        print(f"Mayor crecimiento de interés relativo: {top['pais']} ({top['variacion_pct']}%)")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
