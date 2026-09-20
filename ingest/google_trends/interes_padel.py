"""Conector F12 (Google Trends, vía `pytrends` no oficial) — interés por
pádel en los "países en expansión" que señalan F5 (Playtomic) y F6 (FIP)
en sus informes 2025/2026 — ver `data/manual/paises_expansion.csv`.

Google Trends solo da un índice **relativo** (0-100), no comparable en
volumen absoluto entre países ni entre sesiones de consulta distintas. Para
poder comparar "interés por pádel" entre países de forma algo más honesta,
cada consulta pide "padel" y "tenis" **a la vez** para el mismo país: Google
Trends normaliza los términos de una misma consulta en la misma escala
0-100, así que el ratio padel/tenis dentro de esa consulta sí es
comparable entre países (aunque el valor absoluto de cada término no lo
sea entre consultas distintas). Es la misma idea que usa el propio informe
de la FIP, que cita datos de Google Trends como fuente de contraste para
Portugal, Argentina y Sudáfrica.

`pytrends` es una librería no oficial (doc 01 §2, riesgo ya anticipado):
puede bloquearse o dejar de funcionar sin aviso. Por eso el ritmo es bajo
(varios segundos entre países) y cada fallo se registra en vez de
interrumpir todo el conector.
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import truststore

truststore.inject_into_ssl()

from pytrends.request import TrendReq  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PAISES = REPO_ROOT / "data" / "manual" / "paises_expansion.csv"
BRONZE_ROOT = REPO_ROOT / "bronze" / "google_trends" / "interes_padel"

TIMEFRAME = "today 12-m"
SEGUNDOS_ENTRE_PAISES = 5


def _paises() -> list[dict[str, str]]:
    with CSV_PAISES.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch() -> dict[str, Any]:
    pytrends = TrendReq(hl="es-ES", tz=60)
    resultados: dict[str, Any] = {}
    errores: dict[str, str] = {}

    for i, pais in enumerate(_paises()):
        codigo = pais["codigo_iso2"]
        if i > 0:
            time.sleep(SEGUNDOS_ENTRE_PAISES)
        try:
            pytrends.build_payload(["padel", "tenis"], timeframe=TIMEFRAME, geo=codigo)
            df = pytrends.interest_over_time()
            if df.empty:
                errores[codigo] = "sin datos (volumen de búsqueda insuficiente en ese país)"
                continue
            serie = [
                {"fecha": idx.strftime("%Y-%m-%d"), "padel": int(row["padel"]), "tenis": int(row["tenis"])}
                for idx, row in df.iterrows()
            ]
            resultados[codigo] = {
                "pais": pais["pais"],
                "clasificacion": pais["clasificacion"],
                "fuente_clasificacion": pais["fuente"],
                "serie_semanal": serie,
            }
        except Exception as e:  # pytrends lanza excepciones variadas (429, timeouts, parseo)
            errores[codigo] = str(e)

    return {"timeframe": TIMEFRAME, "paises": resultados, "errores": errores}


def write_snapshot(data: dict[str, Any]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    payload = {
        "source": "google_trends",
        "endpoint": "pytrends (no oficial) — términos 'padel' + 'tenis', por país",
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256,
        **data,
    }
    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    data = fetch()
    out_file = write_snapshot(data)
    print(f"{len(data['paises'])} países con datos, {len(data['errores'])} sin datos/con error")
    if data["errores"]:
        for codigo, msg in data["errores"].items():
            print(f"  {codigo}: {msg}")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
