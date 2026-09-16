"""Conector F2 (padelapi.org) — snapshots de /rankings y /players a bronze.

F2 valida y rellena lo que falta en F1 (doc 01 §2, regla de precedencia):
trae puntos junto con la posición en un único endpoint (`/rankings`), y en
`/players` incluye `side` (drive/revés), que el documento de arquitectura
daba por curación manual obligatoria (F13). Ver docs/campos-f2-padelapi.md.

Uso:
    python -m ingest.padelapi.snapshot --what rankings
    python -m ingest.padelapi.snapshot --what players
    python -m ingest.padelapi.snapshot --what both
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .client import PadelApiClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "padelapi"
SOURCE = "padelapi"


def _latest_previous_snapshot(root: Path, before: date) -> dict[str, Any] | None:
    if not root.exists():
        return None
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name, reverse=True)
    for dt_dir in dirs:
        dt_str = dt_dir.name.removeprefix("dt=")
        try:
            if date.fromisoformat(dt_str) >= before:
                continue
        except ValueError:
            continue
        snapshot_file = dt_dir / "data.json"
        if snapshot_file.exists():
            return json.loads(snapshot_file.read_text(encoding="utf-8"))
    return None


def _write_snapshot(name: str, endpoint: str, params: dict[str, Any], items: list[dict[str, Any]]) -> Path:
    root = BRONZE_ROOT / name
    today = datetime.now(timezone.utc).date()
    ingest_ts = datetime.now(timezone.utc).isoformat()

    payload_bytes = json.dumps(items, sort_keys=True).encode("utf-8")
    sha256 = hashlib.sha256(payload_bytes).hexdigest()

    previous = _latest_previous_snapshot(root, before=today)
    sin_cambios = previous is not None and previous.get("sha256") == sha256

    snapshot = {
        "source": SOURCE,
        "endpoint": endpoint,
        "ingest_ts": ingest_ts,
        "sha256": sha256,
        "params": params,
        "n_items": len(items),
        "sin_cambios": sin_cambios,
        "items": items,
    }

    out_dir = root / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def fetch_rankings(client: PadelApiClient) -> Path:
    items = list(client.paginate("/rankings", {"type": "official"}))
    return _write_snapshot("rankings", "/rankings", {"type": "official"}, items)


def fetch_players(client: PadelApiClient, max_pages: int) -> Path:
    items: list[dict[str, Any]] = []
    for page_index, item in enumerate(client.paginate("/players")):
        if page_index >= max_pages * 50:
            break
        items.append(item)
    return _write_snapshot("players", "/players", {}, items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--what", choices=["rankings", "players", "both"], default="both")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Tope de páginas de 50 para /players (100 = hasta 5.000 jugadores).",
    )
    args = parser.parse_args()

    with PadelApiClient() as client:
        if args.what in ("rankings", "both"):
            out = fetch_rankings(client)
            print(f"rankings -> {out.relative_to(REPO_ROOT)}")
        if args.what in ("players", "both"):
            out = fetch_players(client, args.max_pages)
            print(f"players -> {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
