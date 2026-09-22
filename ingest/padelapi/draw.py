"""Conector F2 — cuadro de un torneo próximo, antes de que se juegue
(`ingest_torneo`, doc 01 §5; `torneo_previa`, doc 01 §3.3/doc 02 §4).

Deliberadamente separado de `matches.py`: ese conector solo mira torneos ya
terminados (`status == "finished"`) para construir resultados. Este mira
torneos con `status == "pending"` que empiezan pronto, y no filtra por
estado de partido — el cuadro trae ronda, semillas y jugadores incluso
antes de jugarse, pero sin marcador ni ganador todavía.

Exploración en vivo (22/09/2026): `/tournaments` viene ordenado por
`end_date` descendente (confirmado ya en `matches.py`), así que los
torneos `pending` (con `end_date` en el futuro, mayor que el de cualquier
`finished`) quedan agrupados al principio del listado — se puede parar en
cuanto se deja de ver `status == "pending"`.

El cuadro de Rotterdam P2 2026 (id 745, empieza 28/09) seguía vacío a
22/09/2026: los cuadros de P2 no se publican con tanta antelación. Este
conector se deja listo para cuando lo esté; probado de punta a punta con
el cuadro ya completo de Rotterdam P1 2025 (id 564, terminado) como
sustituto real mientras tanto (ver docs/campos-torneo-previa.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .client import PadelApiClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "padelapi" / "draw"


def fetch_upcoming_tournaments(client: PadelApiClient, days_forward: int) -> list[dict[str, Any]]:
    hoy = datetime.now(timezone.utc).date()
    limite_superior = hoy + timedelta(days=days_forward)

    seleccionados: list[dict[str, Any]] = []
    for item in client.paginate("/tournaments"):
        if item.get("status") != "pending":
            break  # ver nota de módulo: los pending están agrupados al principio
        start_date = date.fromisoformat(item["start_date"]) if item.get("start_date") else None
        if start_date is not None and start_date <= limite_superior:
            seleccionados.append(item)
    return seleccionados


def fetch_draw(client: PadelApiClient, tournament_id: int) -> list[dict[str, Any]]:
    """Todo el cuadro tal cual está hoy, sin filtrar por estado: para un
    torneo próximo la mayoría de partidos estarán `pending`/sin jugar."""
    return list(client.paginate(f"/tournaments/{tournament_id}/matches"))


def write_snapshot(tournament: dict[str, Any], items: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    ingest_ts = datetime.now(timezone.utc).isoformat()
    payload_bytes = json.dumps(items, sort_keys=True).encode("utf-8")
    sha256 = hashlib.sha256(payload_bytes).hexdigest()

    snapshot = {
        "source": "padelapi",
        "endpoint": f"/tournaments/{tournament['id']}/matches",
        "ingest_ts": ingest_ts,
        "sha256": sha256,
        "tournament": {
            "id": tournament["id"],
            "name": tournament.get("name"),
            "country": tournament.get("country"),
            "level": tournament.get("level"),
            "start_date": tournament.get("start_date"),
            "end_date": tournament.get("end_date"),
        },
        "n_items": len(items),
        "items": items,
    }

    out_dir = BRONZE_ROOT / f"tournament_id={tournament['id']}" / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-forward", type=int, default=10,
                         help="Ventana de días hacia delante para considerar un torneo 'próximo' (default 10).")
    parser.add_argument("--tournament-id", type=int, default=None,
                         help="Fuerza un torneo concreto por id de padelapi, ignorando la ventana (pruebas/backfill).")
    args = parser.parse_args()

    with PadelApiClient() as client:
        if args.tournament_id is not None:
            tournament = client.get(f"/tournaments/{args.tournament_id}")
            tournaments = [tournament]
        else:
            tournaments = fetch_upcoming_tournaments(client, args.days_forward)
        print(f"{len(tournaments)} torneos próximos")
        for tournament in tournaments:
            items = fetch_draw(client, tournament["id"])
            out_file = write_snapshot(tournament, items)
            print(f"  {tournament['name']}: {len(items)} partidos en el cuadro -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
