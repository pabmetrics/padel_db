"""Conector F2 — partidos por torneo (/tournaments, /tournaments/{id}/matches).

Diseño deliberadamente distinto de rankings.py/snapshot.py: en vez de pedir
el historial completo de cada jugador (caro y muy redundante: un partido
aparece en el historial de sus 4 jugadores), se pide por torneo. Un torneo
tiene 100-130 partidos en 2-3 páginas de 50, cubre a todos sus jugadores de
una vez, y es del tamaño adecuado para automatizar semanalmente (o a diario
durante un torneo activo, como describe `ingest_torneo` en doc 01 §5).

`/tournaments` no expone filtro de estado fiable observado (los próximos
salen "pending"; no se ha visto un valor para los ya jugados), así que el
recorte de "reciente" se hace por fecha (`end_date`), no por `status`.
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
BRONZE_ROOT = REPO_ROOT / "bronze" / "padelapi" / "matches"


def fetch_recent_tournaments(client: PadelApiClient, days_back: int) -> list[dict[str, Any]]:
    """Torneos cuyo end_date cae dentro de la ventana [hoy-days_back, hoy].

    /tournaments viene ordenado por fecha descendente, así que se puede parar
    en cuanto se cruza el límite inferior de la ventana sin paginar toda la
    historia (537 torneos en total a fecha 17/09/2026).
    """

    hoy = datetime.now(timezone.utc).date()
    limite_inferior = hoy - timedelta(days=days_back)

    seleccionados: list[dict[str, Any]] = []
    for item in client.paginate("/tournaments"):
        end_date = date.fromisoformat(item["end_date"]) if item.get("end_date") else None
        if end_date is None:
            continue
        if end_date > hoy:
            continue  # todavía no ha terminado
        if end_date < limite_inferior:
            break  # ya hemos pasado la ventana; el resto es más antiguo aún
        seleccionados.append(item)
    return seleccionados


def fetch_matches(client: PadelApiClient, tournament_id: int) -> list[dict[str, Any]]:
    return [
        item
        for item in client.paginate(f"/tournaments/{tournament_id}/matches")
        if item.get("status") == "finished"
    ]


def write_snapshot(tournament: dict[str, Any], matches: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    ingest_ts = datetime.now(timezone.utc).isoformat()
    payload_bytes = json.dumps(matches, sort_keys=True).encode("utf-8")
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
        "n_items": len(matches),
        "items": matches,
    }

    out_dir = BRONZE_ROOT / f"tournament_id={tournament['id']}" / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days-back",
        type=int,
        default=90,
        help="Ventana de días hacia atrás para considerar un torneo 'reciente' (default 90).",
    )
    args = parser.parse_args()

    with PadelApiClient() as client:
        tournaments = fetch_recent_tournaments(client, args.days_back)
        print(f"{len(tournaments)} torneos terminados en los últimos {args.days_back} días")
        for tournament in tournaments:
            matches = fetch_matches(client, tournament["id"])
            out_file = write_snapshot(tournament, matches)
            print(f"  {tournament['name']}: {len(matches)} partidos -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
