"""Conector F3 (padelfip.com) — scraper del ranking oficial FIP.

Doc 01 §2: F3 es la referencia "oficial" para el ranking cuando F1 y F2
discrepan. En la práctica (17/09/2026) solo el top 10 M/F viene renderizado
en el HTML servido; el resto se carga por AJAX (no identificado desde el
HTML, probablemente WordPress admin-ajax con una acción específica del tema
— pendiente de investigar si algún día hace falta más profundidad que 10).
Con el top 10 basta para el uso previsto: contrastar, no sustituir, a F1/F2.

Respeta robots.txt (comprobado 17/09/2026: /ranking/ y /fip-rankings/ no
están bloqueados) y va con ritmo bajo (una página, sin repetir peticiones).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "padelfip" / "ranking"
URL = "https://www.padelfip.com/ranking/"
USER_AGENT = "padeldb.es research bot; contacto hola@padeldb.es"

GENDER_BY_WRAP_CLASS = {"ranking__female": "F", "ranking__male": "M"}


def fetch_html() -> str:
    response = httpx.get(
        URL,
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def parse_ranking(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []

    for wrap_class, sexo in GENDER_BY_WRAP_CLASS.items():
        wrap = soup.select_one(f".{wrap_class}")
        if wrap is None:
            continue
        for card in wrap.select(".ranking__player.player__card"):
            rank_el = card.select_one(".player__rank")
            name_el = card.select_one(".player__name")
            country_el = card.select_one(".player__country")
            points_el = card.select_one(".player__pointTNumber")
            link_el = card.select_one("a.player__link")

            if not (rank_el and name_el and points_el):
                continue

            rows.append(
                {
                    "sexo": sexo,
                    "posicion": int(rank_el.get_text(strip=True)),
                    "nombre": name_el.get_text(strip=True),
                    "pais": country_el.get_text(strip=True) if country_el else None,
                    "puntos": int(points_el.get_text(strip=True).replace(" ", "")),
                    "slug_padelfip": (link_el["href"].rstrip("/").rsplit("/", 1)[-1] if link_el else None),
                }
            )
    return rows


def write_snapshot(rows: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    ingest_ts = datetime.now(timezone.utc).isoformat()
    payload_bytes = json.dumps(rows, sort_keys=True).encode("utf-8")
    sha256 = hashlib.sha256(payload_bytes).hexdigest()

    snapshot = {
        "source": "padelfip",
        "endpoint": URL,
        "ingest_ts": ingest_ts,
        "sha256": sha256,
        "n_items": len(rows),
        "nota": "Solo top 10 M/F: es lo que sirve el HTML sin ejecutar JavaScript.",
        "items": rows,
    }

    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    html = fetch_html()
    rows = parse_ranking(html)
    if not rows:
        raise SystemExit("El scraper no encontró filas — probablemente cambió el HTML de padelfip.com")
    out_file = write_snapshot(rows)
    print(f"{len(rows)} filas (top 10 M/F) -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
