"""Conector F1 — calendario de torneos (getfanapptournaments).

Snapshot a bronze/premierpadel/tournaments/dt=<fecha>/data.json.

Nota importante (17/09/2026): el endpoint de cuadro/resultados de este mismo
SDK (`tournaments.draw`, `tournaments.results`) devolvió vacío para el Paris
Major recién acabado (7-13 sept 2026), pese a que el calendario sí lo lista
correctamente. `updated_at` del torneo se quedó en julio, antes de que
empezara — este endpoint de "fan app" no parece recibir los resultados reales
del torneo. Para partidos/resultados, la fuente que funciona es F2 (padelapi
`/players/{id}/matches`, ver docs/campos-f2-padelapi.md). Este conector se
limita, por tanto, al calendario (`dim_torneo`), no a partidos.

Cruce entre fuentes: `event_code` de F1 (ej. "3603") coincide con el sufijo
numérico del `key_name` de F2 (ej. "FIP-2025-3603") — es la clave para unir
`dim_torneo` (F1) con el historial de torneos por jugador de F2 en Fase 2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from calendar import month_name
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pypadel

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "tournaments"
ENDPOINT = "/beforeauth/getfanapptournaments"


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def fetch_tournaments(client: pypadel.PremierPadelClient, months_back: int, months_forward: int) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc)
    seen_ids: set[int] = set()
    items: list[dict[str, Any]] = []

    offsets = range(-months_back, months_forward + 1)
    for offset in offsets:
        month_index0 = today.month - 1 + offset
        year = today.year + month_index0 // 12
        month_index = month_index0 % 12
        month = month_name[month_index + 1]

        page = client.tournaments.list(month, year, page_size=100)
        for tournament in page.items:
            if tournament.id in seen_ids:
                continue
            seen_ids.add(tournament.id)
            items.append(asdict(tournament))
    return items


def write_snapshot(items: list[dict[str, Any]], months_back: int, months_forward: int) -> Path:
    today = datetime.now(timezone.utc).date()
    ingest_ts = datetime.now(timezone.utc).isoformat()

    payload_bytes = json.dumps(items, sort_keys=True, default=_json_default).encode("utf-8")
    sha256 = hashlib.sha256(payload_bytes).hexdigest()

    snapshot = {
        "source": "premierpadel",
        "endpoint": ENDPOINT,
        "ingest_ts": ingest_ts,
        "sha256": sha256,
        "params": {"months_back": months_back, "months_forward": months_forward},
        "n_items": len(items),
        "items": items,
    }

    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months-back", type=int, default=2)
    parser.add_argument("--months-forward", type=int, default=4)
    args = parser.parse_args()

    with pypadel.PremierPadelClient() as client:
        items = fetch_tournaments(client, args.months_back, args.months_forward)
    out_file = write_snapshot(items, args.months_back, args.months_forward)
    print(f"{len(items)} torneos -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
