"""Conector F1 (premierpadel.com vía SDK pypadel) — snapshot del ranking.

Escribe en bronze un snapshot append-only por género y fecha:
    bronze/premierpadel/rankings/dt=<YYYY-MM-DD>/<gender>.json

Ver docs/campos-f1-premierpadel.md para el diccionario de campos y sus
limitaciones conocidas (la posición es el orden de la lista, no viene un
campo explícito de puntos en este endpoint).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pypadel
from pypadel.enums import Gender, RankingScope

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "rankings"

SOURCE = "premierpadel"
ENDPOINT = "/beforeauth/getplayerrankingv2"


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):  # enums (Gender, RankingScope)
        return value.value
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def fetch_ranking(
    client: pypadel.PremierPadelClient, gender: Gender, max_pages: int
) -> tuple[list[dict[str, Any]], int]:
    """Fetch up to `max_pages` pages of the overall ranking for a gender.

    Returns (items_with_position, total_pages_reported_by_the_api).
    """

    items: list[dict[str, Any]] = []
    total_pages: int | None = None
    position = 0
    page_number = 1
    while page_number <= max_pages:
        page = client.players.list(gender=gender, page=page_number, scope=RankingScope.OVERALL)
        total_pages = page.total_pages
        for player in page.items:
            position += 1
            record = asdict(player)
            record["posicion_lista"] = position
            items.append(record)
        if not page.has_next_page:
            break
        page_number += 1
    return items, total_pages or page_number


def _latest_previous_snapshot(gender_value: str, before: date) -> dict[str, Any] | None:
    if not BRONZE_ROOT.exists():
        return None
    candidates = sorted(
        (p for p in BRONZE_ROOT.glob("dt=*") if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    for dt_dir in candidates:
        dt_str = dt_dir.name.removeprefix("dt=")
        try:
            if date.fromisoformat(dt_str) >= before:
                continue
        except ValueError:
            continue
        snapshot_file = dt_dir / f"{gender_value}.json"
        if snapshot_file.exists():
            return json.loads(snapshot_file.read_text(encoding="utf-8"))
    return None


def write_snapshot(gender: Gender, items: list[dict[str, Any]], total_pages: int, max_pages: int) -> Path:
    today = datetime.now(timezone.utc).date()
    ingest_ts = datetime.now(timezone.utc).isoformat()
    gender_value = gender.value.lower()

    payload_bytes = json.dumps(items, sort_keys=True, default=_json_default).encode("utf-8")
    sha256 = hashlib.sha256(payload_bytes).hexdigest()

    previous = _latest_previous_snapshot(gender_value, before=today)
    sin_cambios = previous is not None and previous.get("sha256") == sha256

    snapshot = {
        "source": SOURCE,
        "endpoint": ENDPOINT,
        "ingest_ts": ingest_ts,
        "sha256": sha256,
        "params": {
            "gender": gender.value,
            "scope": RankingScope.OVERALL.value,
            "max_pages": max_pages,
        },
        "gender": gender.value,
        "n_items": len(items),
        "n_pages_fetched": min(max_pages, total_pages),
        "total_pages_available": total_pages,
        "sin_cambios": sin_cambios,
        "items": items,
    }

    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{gender_value}.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=25,
        help="Páginas de 20 jugadores a recorrer por género (25 = top ~500). "
        "El ranking completo de premierpadel.com incluye miles de jugadores "
        "inactivos/históricos que no aportan a las series de contenido.",
    )
    parser.add_argument(
        "--gender",
        choices=["male", "female", "both"],
        default="both",
    )
    args = parser.parse_args()

    genders = {
        "male": [Gender.MALE],
        "female": [Gender.FEMALE],
        "both": [Gender.MALE, Gender.FEMALE],
    }[args.gender]

    with pypadel.PremierPadelClient() as client:
        for gender in genders:
            items, total_pages = fetch_ranking(client, gender, args.max_pages)
            out_file = write_snapshot(gender, items, total_pages, args.max_pages)
            print(f"{gender.value}: {len(items)} jugadores -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
