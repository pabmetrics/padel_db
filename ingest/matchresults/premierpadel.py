"""Resultado alternativo por jugador y torneo — padelearnings.com.

Para los torneos donde padelapi (F2) oculta el campo `winner` en el 100% de
los partidos (ventana móvil de ~180 días desde hoy, ver
docs/campos-f2-padelapi.md), esta es la fuente de respaldo: la tabla
"Results & Earnings" de cada torneo en padelearnings.com da la ronda de
eliminación de cada jugador directamente, sin depender de reconstruir
quién ganó cada partido.

Usa el mismo mapeo de torneos que `ingest/prizemoney/premierpadel.py`
(data/manual/prize_torneo_slugs_2026.csv).
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
BRONZE_ROOT = REPO_ROOT / "bronze" / "matchresults" / "premierpadel"
USER_AGENT = "padeldb.es research bot; contacto hola@padeldb.es"

ROUND_MAP = {"Winner": "W", "Final": "F", "Semi-final": "SF", "Quarter-final": "QF", "Round of 16": "R16", "Round of 32": "R32", "Round of 64": "R64"}


def load_slugs() -> list[tuple[str, str]]:
    with SLUGS_CSV.open(encoding="utf-8") as f:
        return [(row["torneo_nombre_bronze"], row["slug"]) for row in csv.DictReader(f) if row["fuente"] == "padelearnings"]


def parse_results(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    marker = soup.find(string=lambda s: s and "Results & Earnings" in s)
    if not marker:
        return []
    table = marker.find_parent("div").find_next("table")
    rows: list[dict[str, Any]] = []
    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        link = tds[1].find("a", href=True)
        if not link:
            continue
        jugador_slug = link["href"].rsplit("/", 1)[-1]
        nombre_div = link.find("div", class_="font-semibold")
        jugador_nombre = nombre_div.get_text(strip=True) if nombre_div else None
        partner_span = tds[1].find("span", class_=lambda c: c and "text-gray-500" in c)
        compañero_nombre = partner_span.get_text(strip=True).removeprefix("w/").strip() if partner_span else None
        ronda = ROUND_MAP.get(tds[2].get_text(strip=True))
        if not ronda or not jugador_nombre:
            continue
        rows.append(
            {
                "jugador_slug": jugador_slug,
                "jugador_nombre": jugador_nombre,
                "compañero_nombre": compañero_nombre,
                "ronda": ronda,
            }
        )
    return rows


def fetch_all() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for torneo_nombre, slug in load_slugs():
            response = client.get(f"https://padelearnings.com/tournaments/{slug}")
            if response.status_code != 200:
                print(f"  {torneo_nombre}: HTTP {response.status_code}, saltado")
                continue
            rows = parse_results(response.text)
            for row in rows:
                items.append({"torneo_nombre_bronze": torneo_nombre, "slug": slug, **row})
            print(f"  {torneo_nombre}: {len(rows)} jugadores")
            time.sleep(0.3)
    return items


def write_snapshot(items: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    snapshot = {
        "source": "padelearnings",
        "endpoint": "https://padelearnings.com/tournaments/{slug} (tabla Results & Earnings)",
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
