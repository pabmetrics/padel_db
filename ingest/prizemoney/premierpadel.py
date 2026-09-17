"""Prize money real de Premier Padel, por torneo — padelearnings.com.

Sustituye al enfoque anterior (tabla genérica por categoría con cifras
"aproximadas"): cada torneo tiene su propia página con el reparto real por
ronda, y en Major/P1/P2 el reparto no es siempre igual entre hombres y
mujeres (hallazgo real, 17/09/2026 — contradice lo que decía la página
general de resumen). La lista de torneos a consultar es
data/manual/prize_torneo_slugs_2026.csv (curada a mano: el cruce automático
por nombre daba falsos positivos entre categorías/ediciones distintas, ver
docs/campos-prize-money-2026.md).
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
SLUGS_CSV = REPO_ROOT / "data" / "manual" / "prize_torneo_slugs_2026.csv"
BRONZE_ROOT = REPO_ROOT / "bronze" / "prizemoney" / "premierpadel"
USER_AGENT = "padeldb.es research bot; contacto hola@padeldb.es"

ROUND_MAP = {"Winner": "W", "Final": "F", "Semi-final": "SF", "Quarter-final": "QF", "Round of 16": "R16", "Round of 32": "R32", "Round of 64": "R64"}


def load_slugs() -> list[tuple[str, str]]:
    with SLUGS_CSV.open(encoding="utf-8") as f:
        return [(row["torneo_nombre_bronze"], row["slug"]) for row in csv.DictReader(f) if row["fuente"] == "padelearnings"]


def parse_breakdown(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    marker = soup.find(string=lambda s: s and "Prize money breakdown per round" in s)
    if not marker:
        return []
    table = marker.find_parent("div").find_next("table")
    rows: list[dict[str, Any]] = []
    for tr in table.find("tbody").find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not tds:
            continue
        ronda = ROUND_MAP.get(tds[0])
        if not ronda:
            continue
        euros = [t.replace("€", "").replace(",", "") for t in tds[1:]]
        if len(euros) == 2:
            rows.append({"sexo": "ambos", "ronda": ronda, "pareja_eur": int(euros[0]), "jugador_eur": int(euros[1])})
        elif len(euros) == 4:
            rows.append({"sexo": "M", "ronda": ronda, "pareja_eur": int(euros[0]), "jugador_eur": int(euros[1])})
            rows.append({"sexo": "F", "ronda": ronda, "pareja_eur": int(euros[2]), "jugador_eur": int(euros[3])})
    return rows


def fetch_all() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for torneo_nombre, slug in load_slugs():
            response = client.get(f"https://padelearnings.com/tournaments/{slug}")
            if response.status_code != 200:
                print(f"  {torneo_nombre}: HTTP {response.status_code}, saltado")
                continue
            rows = parse_breakdown(response.text)
            for row in rows:
                items.append({"torneo_nombre_bronze": torneo_nombre, "slug": slug, **row})
            print(f"  {torneo_nombre}: {len(rows)} filas")
            time.sleep(0.3)
    return items


def write_snapshot(items: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    snapshot = {
        "source": "padelearnings",
        "endpoint": "https://padelearnings.com/tournaments/{slug}",
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
    items = fetch_all()
    out_file = write_snapshot(items)
    print(f"{len(items)} filas totales -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
