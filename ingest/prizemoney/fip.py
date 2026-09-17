"""Prize money real del FIP Tour, por torneo — padelfip.com (fuente oficial).

Cada evento tiene su propia página con "Prize distribution per tournament
round" y una bolsa total fija (no un rango como daba la tabla genérica de
padel-magazine.es). El reparto aquí no distingue género ("Price Per Player").

Lista de torneos en data/manual/prize_torneo_slugs_2026.csv, curada a mano:
el cruce automático por nombre normalizado dio varios falsos positivos entre
categorías y ediciones distintas (ej. "FIP Gold San Luis" casaba con la
página de "FIP Silver San Luis"; "FIP Silver Cyprus I" con "Cyprus II") —
se descartaron esos cruces en vez de arriesgarse con datos económicos mal
emparejados. Ver docs/campos-prize-money-2026.md.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[2]
SLUGS_CSV = REPO_ROOT / "data" / "manual" / "prize_torneo_slugs_2026.csv"
BRONZE_ROOT = REPO_ROOT / "bronze" / "prizemoney" / "fip"
USER_AGENT = "padeldb.es research bot; contacto hola@padeldb.es"

ROUND_MAP = {
    "R64": "R64",
    "R32": "R32",
    "R16": "R16",
    "1/4 FINAL": "QF",
    "QUARTERFINAL": "QF",
    "1/2 FINAL": "SF",
    "SEMIFINAL": "SF",
    "FINALIST": "F",
    "WINNER": "W",
    "FINAL": "F",
}


def _parse_euros(text: str) -> int | None:
    """'421,88€' -> 421; '1.406€' -> 1406; '337.50€' -> 337.

    El sitio mezcla, dentro de la misma tabla, coma decimal ("421,88"),
    punto de millar ("1.406") y punto decimal ("337.50") — no hay un
    convenio fijo (bug real de su plantilla, detectado el 17/09/2026 con
    dos torneos que salían con premios absurdos, ej. R32 pagando más que
    R16). Se distingue por la cantidad de dígitos tras el último separador:
    2 dígitos → parte decimal (se descarta); 3 dígitos → separador de miles
    (se quita, quedan como parte entera).
    """

    cleaned = text.replace("€", "").strip().replace(" ", "")
    if not cleaned:
        return None
    match = re.match(r"^[0-9]+(?:[.,][0-9]+)*$", cleaned)
    if not match:
        return None
    entero = cleaned
    for sep in (",", "."):
        if sep in entero:
            head, tail = entero.rsplit(sep, 1)
            if len(tail) == 3:
                entero = head + tail  # separador de miles: se une
            else:
                entero = head  # parte decimal: se descarta
    return int(entero) if entero.isdigit() else None


def load_slugs() -> list[tuple[str, str, str | None]]:
    """(nombre, slug, mes_aprox). `mes_aprox` ("AAAA-MM") solo está informado
    cuando el mismo nombre corresponde a varias ediciones distintas del
    torneo (ej. dos "FIP Silver Damac Dubai" en 2026) — desambigua cuál es
    cuál al construir prize_por_torneo."""

    with SLUGS_CSV.open(encoding="utf-8") as f:
        return [
            (row["torneo_nombre_bronze"], row["slug"], row.get("mes_aprox") or None)
            for row in csv.DictReader(f)
            if row["fuente"] == "padelfip"
        ]


def parse_event(html: str) -> tuple[list[dict[str, Any]], int | None]:
    idx = html.find("Prize distribution per tournament round")
    if idx == -1:
        return [], None
    soup = BeautifulSoup(html[idx : idx + 3000], "html.parser")
    rows: list[dict[str, Any]] = []
    for tr in soup.find_all("tr"):
        th = tr.find("th", attrs={"scope": "row"})
        td = tr.find("td")
        if not th or not td:
            continue
        ronda = ROUND_MAP.get(th.get_text(strip=True).upper())
        valor = _parse_euros(td.get_text())
        if ronda and valor is not None:
            rows.append({"sexo": "ambos", "ronda": ronda, "jugador_eur": valor})

    pool_match = re.search(r'Prize Money</span>\s*<p class="overview__text">([0-9.,]+)', html)
    pool_eur = int(re.sub(r"[.,]", "", pool_match.group(1))) if pool_match else None
    return rows, pool_eur


def fetch_all() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for torneo_nombre, slug, mes_aprox in load_slugs():
            response = client.get(f"https://www.padelfip.com/events/{slug}/")
            if response.status_code != 200:
                print(f"  {torneo_nombre}: HTTP {response.status_code}, saltado")
                continue
            rows, pool_eur = parse_event(response.text)
            for row in rows:
                items.append(
                    {"torneo_nombre_bronze": torneo_nombre, "slug": slug, "mes_aprox": mes_aprox, "pool_eur": pool_eur, **row}
                )
            print(f"  {torneo_nombre}{' (' + mes_aprox + ')' if mes_aprox else ''}: {len(rows)} filas, bolsa {pool_eur}")
            time.sleep(0.3)
    return items


def write_snapshot(items: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    snapshot = {
        "source": "padelfip",
        "endpoint": "https://www.padelfip.com/events/{slug}/",
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
