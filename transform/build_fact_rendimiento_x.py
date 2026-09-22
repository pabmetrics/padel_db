"""fact_rendimiento_x: cruza los CSV manuales de analíticas de X
(`data/manual/rendimiento_x/*.csv`, export de analytics.x.com) con la cola
(`queue/*/candidates.json`) para atribuir impresiones/interacciones a un
`registro` y una `serie` (doc 01 §3.4/§5, `ingest_metrics`).

El cruce es por `Tweet permalink` == `url_x` del candidato marcado como
`publicado`/`medido` (ver `content/copy_factory/cola.marcar_publicado`).
Sin esa anotación manual no hay forma fiable de saber qué post de X
corresponde a qué gráfico: se deja constancia en
`silver/_reconciliacion/rendimiento_x_sin_cruzar.json` en vez de adivinar.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = REPO_ROOT / "data" / "manual" / "rendimiento_x"
QUEUE_ROOT = REPO_ROOT / "queue"
OUT_PATH = REPO_ROOT / "silver" / "fact_rendimiento_x" / "data.json"
RECONCILIACION_PATH = REPO_ROOT / "silver" / "_reconciliacion" / "rendimiento_x_sin_cruzar.json"

def _mostrar(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


METRICAS_INT = {
    "impressions": "impresiones",
    "engagements": "interacciones",
    "retweets": "retweets",
    "replies": "respuestas",
    "likes": "me_gusta",
    "url clicks": "clics_url",
}


def _cargar_candidatos_publicados() -> dict[str, dict[str, Any]]:
    """url_x -> {registro, serie, fecha_dato}, solo candidatos con url_x."""
    por_url: dict[str, dict[str, Any]] = {}
    for candidates_file in sorted(QUEUE_ROOT.glob("*/candidates.json")):
        for candidato in json.loads(candidates_file.read_text(encoding="utf-8")):
            url_x = candidato.get("url_x")
            if url_x and candidato.get("estado") in ("publicado", "medido"):
                por_url[url_x] = {
                    "registro": candidato["registro"],
                    "serie": candidato["serie"],
                    "fecha_dato": candidato["fecha_dato"],
                }
    return por_url


def _leer_csvs() -> dict[str, dict[str, Any]]:
    """Tweet id -> última fila vista (por orden de lectura de ficheros,
    nombrados por fecha de export: el último export tiene las cifras más
    altas, ya que impresiones e interacciones solo crecen)."""
    por_tweet: dict[str, dict[str, Any]] = {}
    for csv_path in sorted(CSV_DIR.glob("*.csv")):
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                tweet_id = row.get("Tweet id")
                if not tweet_id:
                    continue
                por_tweet[tweet_id] = row
    return por_tweet


def _extraer_metricas(row: dict[str, Any]) -> dict[str, int]:
    """De una fila del CSV de analytics.x.com, las métricas que nos
    interesan como {metrica: valor}, ignorando columnas vacías."""
    metricas: dict[str, int] = {}
    for columna, metrica in METRICAS_INT.items():
        valor = row.get(columna)
        if valor not in (None, ""):
            metricas[metrica] = int(float(valor))
    return metricas


def build() -> Path:
    publicados = _cargar_candidatos_publicados()
    filas_csv = _leer_csvs() if CSV_DIR.exists() else {}

    rows: list[dict[str, Any]] = []
    sin_cruzar: list[dict[str, Any]] = []

    for tweet_id, row in filas_csv.items():
        permalink = row.get("Tweet permalink", "")
        meta = publicados.get(permalink)
        if meta is None:
            sin_cruzar.append({"tweet_id": tweet_id, "permalink": permalink, "time": row.get("time")})
            continue

        for metrica, valor in _extraer_metricas(row).items():
            rows.append(
                {
                    "registro": meta["registro"],
                    "serie": meta["serie"],
                    "fecha_dato": meta["fecha_dato"],
                    "tiempo_publicado": row.get("time"),
                    "metrica": metrica,
                    "valor": valor,
                    "url_x": permalink,
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    RECONCILIACION_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECONCILIACION_PATH.write_text(json.dumps(sin_cruzar, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"fact_rendimiento_x: {len(rows)} filas ({len(publicados)} candidatos publicados, {len(filas_csv)} posts en CSV)")
    if sin_cruzar:
        print(f"  {len(sin_cruzar)} posts del CSV sin candidato publicado que cruce -> {_mostrar(RECONCILIACION_PATH)}")
    print(f"-> {_mostrar(OUT_PATH)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
