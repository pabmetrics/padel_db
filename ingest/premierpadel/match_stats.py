"""Conector F1 (API nueva) — partidos y estadísticas de partido.

premierpadel.com se rehízo en 2026 y su web usa ahora
`https://api-prod.premierpadel.com/api/` (sin autenticación); la API de la
"fan app" que usa `pypadel` dejó de recibir partidos a mitad de temporada
(ver docs/campos-f1-premierpadel.md, "Estadísticas de partido"). De la
API nueva se usan dos llamadas:

- `POST tournament/getTournamentMatches` {slug, date?, matchStatus}: sin
  `date` devuelve las fechas del torneo; con `date`, los partidos del día
  (marcador por set, duración, cabezas de serie, jugadores).
- `POST tournament/getTournamentMatchDetailsByType` match_id=…&type=Stats:
  saque, resto y puntos totales, del partido y de cada set.

Bronze append-only: `bronze/premierpadel/match_stats/tournament=<slug>/
dt=<fecha>/data.json` guarda solo los partidos terminados que no estaban
ya en un snapshot anterior del mismo torneo, así que reejecutarlo a diario
cuesta unas pocas peticiones. Ritmo: 1 petición por segundo (doc 01 §7,
endpoints no documentados de un tercero).

Uso:
    python -m ingest.premierpadel.match_stats                   # torneos de la temporada ya empezados
    python -m ingest.premierpadel.match_stats --slug paris-major
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "match_stats"
CALENDARIO_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "tournaments"

BASE_URL = "https://api-prod.premierpadel.com/api/"
PAUSA_S = 1.0
ESTADO_TERMINADO = "F"


class PremierPadelApi:
    def __init__(self) -> None:
        self._http = httpx.Client(
            base_url=BASE_URL,
            timeout=30,
            headers={
                "User-Agent": "PadelDB/1.0 (+https://padeldb.es)",
                "language_code": "en",
                "Origin": "https://premierpadel.com",
                "Referer": "https://premierpadel.com/",
            },
        )
        self._ultima = 0.0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PremierPadelApi:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _esperar(self) -> None:
        espera = PAUSA_S - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        self._ultima = time.monotonic()

    def _post(self, path: str, **kwargs: Any) -> Any:
        for intento in range(3):
            self._esperar()
            try:
                r = self._http.post(path, **kwargs)
                r.raise_for_status()
                return r.json().get("data")
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                if intento == 2 or (isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500):
                    raise
                time.sleep(5 * (intento + 1))
        return None

    def fechas(self, slug: str) -> list[str]:
        data = self._post("tournament/getTournamentMatches", json={"slug": slug, "matchStatus": "All"}) or {}
        return list(data.get("date") or [])

    def partidos_del_dia(self, slug: str, fecha: str) -> list[dict[str, Any]]:
        data = self._post("tournament/getTournamentMatches", json={"slug": slug, "date": fecha, "matchStatus": "All"}) or {}
        partidos = []
        for pista in data.get("courts") or []:
            for m in pista.get("matches") or []:
                partidos.append({**m, "court_name": pista.get("court_name")})
        return partidos

    def torneos_jugados(self, anio: int) -> list[dict[str, Any]]:
        """Torneos de la temporada ya empezados o jugados (`type: "past"`
        devuelve el año entero con `status` F = terminado, P = en juego,
        N = por jugar)."""
        return list(self._post("tournament/getTournaments", json={"type": "past", "year": anio}) or [])

    def stats(self, match_id: str) -> dict[str, Any] | None:
        data = self._post(
            "tournament/getTournamentMatchDetailsByType",
            content=f"match_id={match_id}&type=Stats",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return data or None


def slugs_de_la_temporada(api: PremierPadelApi, hoy: date) -> list[tuple[str, str | None]]:
    """[(slug, status)] de los torneos empezados o terminados."""
    torneos = api.torneos_jugados(hoy.year)
    return [(t["slug"], t.get("status")) for t in sorted(torneos, key=lambda t: t.get("start_date_utc") or "")
            if t.get("status") in ("F", "P") and (t.get("start_date_utc") or "")[:10] <= hoy.isoformat()]


def slugs_del_calendario(hoy: date) -> list[str]:
    """Respaldo si la lista de la API nueva falla: slugs de todos los snapshots del calendario de F1 con torneos ya
    empezados (no solo el último: el calendario mira unos meses atrás y
    un torneo de junio desaparece del snapshot de octubre)."""
    slugs: dict[str, str] = {}
    for f in sorted(CALENDARIO_ROOT.glob("dt=*/data.json")):
        for t in json.loads(f.read_text(encoding="utf-8"))["items"]:
            inicio = t.get("start_date")
            if t.get("slug") and inicio and inicio[:10] <= hoy.isoformat() and inicio[:4] != "1970":
                slugs[t["slug"]] = inicio[:10]
    return [s for s, _ in sorted(slugs.items(), key=lambda kv: kv[1])]


def cerrado_en_bronze(slug: str) -> bool:
    """Un snapshot ya se hizo con el torneo terminado: no queda nada por
    bajar (el torneo no cambia una vez cerrado)."""
    for f in (BRONZE_ROOT / f"tournament={slug}").glob("dt=*/data.json"):
        if json.loads(f.read_text(encoding="utf-8")).get("torneo_status") == ESTADO_TERMINADO:
            return True
    return False


def ya_guardados(slug: str) -> set[str]:
    ids: set[str] = set()
    for f in (BRONZE_ROOT / f"tournament={slug}").glob("dt=*/data.json"):
        ids |= {str(i["match"]["match_id"]) for i in json.loads(f.read_text(encoding="utf-8"))["items"]}
    return ids


def ingerir_torneo(api: PremierPadelApi, slug: str, hoy: date, status: str | None = None) -> Path | None:
    if status == ESTADO_TERMINADO and cerrado_en_bronze(slug):
        return None
    previos = ya_guardados(slug)
    nuevos: list[dict[str, Any]] = []
    for fecha in api.fechas(slug):
        if fecha > hoy.isoformat():
            continue
        for m in api.partidos_del_dia(slug, fecha):
            mid = str(m.get("match_id"))
            if m.get("status") != ESTADO_TERMINADO or mid in previos:
                continue
            previos.add(mid)
            nuevos.append({"match": m, "stats": api.stats(mid)})
    if not nuevos:
        if status == ESTADO_TERMINADO and previos and not cerrado_en_bronze(slug):
            # Todo estaba ya bajado, pero hay que dejar constancia del cierre.
            nuevos_vacio = _snapshot(slug, [], status)
            return _escribir(slug, hoy, nuevos_vacio)
        return None

    return _escribir(slug, hoy, _snapshot(slug, nuevos, status))


def _snapshot(slug: str, items: list[dict[str, Any]], status: str | None) -> dict[str, Any]:
    return {
        "source": "premierpadel",
        "endpoint": BASE_URL + "tournament/getTournamentMatchDetailsByType",
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(json.dumps(items, sort_keys=True).encode("utf-8")).hexdigest(),
        "params": {"slug": slug, "type": "Stats"},
        "torneo_status": status,  # "F" = cerrado: las siguientes pasadas se lo saltan
        "n_items": len(items),
        "items": items,
    }


def _escribir(slug: str, hoy: date, snapshot: dict[str, Any]) -> Path:
    out_dir = BRONZE_ROOT / f"tournament={slug}" / f"dt={hoy.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    if out_file.exists():  # segunda pasada el mismo día: se suman, no se pisan
        anterior = json.loads(out_file.read_text(encoding="utf-8"))
        snapshot["items"] = anterior["items"] + snapshot["items"]
        snapshot["n_items"] = len(snapshot["items"])
    out_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--slug", action="append", help="torneo concreto (repetible); por defecto, el calendario de F1")
    args = parser.parse_args()

    hoy = datetime.now(timezone.utc).date()
    with PremierPadelApi() as api:
        torneos: list[tuple[str, str | None]] = [(s, None) for s in args.slug or []]
        if not torneos:
            try:
                torneos = slugs_de_la_temporada(api, hoy)
            except httpx.HTTPError as e:
                print(f"  lista de torneos de la API nueva no disponible ({e}); se usa el calendario de F1")
                torneos = [(s, None) for s in slugs_del_calendario(hoy)]
        for slug, status in torneos:
            try:
                out = ingerir_torneo(api, slug, hoy, status)
            except httpx.HTTPError as e:
                print(f"  {slug}: ERROR {type(e).__name__}: {e}")
                continue
            print(f"  {slug}: {'sin partidos nuevos' if out is None else out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
