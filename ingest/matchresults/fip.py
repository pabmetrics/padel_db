"""Resultado alternativo por partido — widget de terceros (Crionet /
matchscorerlive.com) incrustado en la pestaña "Results" de cada evento de
padelfip.com.

Para los torneos del FIP Tour donde padelapi (F2) oculta el `winner`
(ventana móvil de ~180 días, ver docs/campos-f2-padelapi.md), esta es la
fuente de respaldo. A diferencia de padelearnings.com (Premier Padel), aquí
los nombres vienen abreviados ("M. Di Nenno"), así que el cruce a
jugador_id no se hace aquí (necesita el censo de participantes del torneo,
que sale de fact_partido) sino en transform/build_resultado_alternativo_fip.py.

El `id` interno de cada torneo en este widget y el número de días
(`totalday`) se leen de la propia página del evento en padelfip.com — no
hay que mantenerlos a mano.
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
BRONZE_ROOT = REPO_ROOT / "bronze" / "matchresults" / "fip"
USER_AGENT = "padeldb.es research bot; contacto hola@padeldb.es"

# Torneos del FIP Tour donde ya se confirmó que padelapi oculta el winner —
# no hace falta consultar el widget para los que padelapi ya cubre bien.
TORNEOS_A_CONSULTAR = {
    "FIP Silver Caen",
    "FIP Platinum Ville De Marseille",
    "FIP Silver Wadi Padel Tournament",
    "FIP Silver Esc Padel 2026",
    "FIP Gold Ponta Delgada",
    "FIP Silver Joinville",
    "FIP Silver Manila",
    "FIP Silver Damac Dubai",
    "FIP Silver Mediolanum Padel Cup",
}


def load_slugs() -> list[tuple[str, str]]:
    with SLUGS_CSV.open(encoding="utf-8") as f:
        return [
            (row["torneo_nombre_bronze"], row["slug"])
            for row in csv.DictReader(f)
            if row["fuente"] == "padelfip" and row["torneo_nombre_bronze"] in TORNEOS_A_CONSULTAR
        ]


def _widget_id_y_dias(event_html: str) -> tuple[str, int] | None:
    m = re.search(r"get-result-data\.php\?year=\d+&id=(\d+)&day=\d+&totalday=(\d+)", event_html)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def _parse_equipo(tr: Any) -> tuple[list[str], bool] | None:
    player_names_div = tr.find("div", class_="player-names")
    if not player_names_div:
        return None
    jugadores: list[str] = []
    es_ganador = False
    for name_div in player_names_div.find_all("div", class_="ml-2"):
        if "winner" in (name_div.get("class") or []):
            es_ganador = True
        spans = [s for s in name_div.find_all("span") if "separator" not in (s.get("class") or [])]
        nombre = " ".join(s.get_text(strip=True) for s in spans)
        if nombre:
            jugadores.append(nombre)
    return (jugadores, es_ganador) if jugadores else None


def parse_day(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for tabla in soup.find_all("table", class_="w-100"):
        header = tabla.find("tr", class_=lambda c: c and "header" in c)
        if not header:
            continue
        round_div = header.find("div", class_="round-name")
        if not round_div:
            continue
        b_tag = round_div.find("b")
        categoria = b_tag.get_text(strip=True) if b_tag else None
        ronda_div = round_div.find("div")
        ronda = ronda_div.get_text(strip=True) if ronda_div else None

        equipos = []
        for tr in tabla.find_all("tr"):
            if tr.find("td", class_="team"):
                equipo = _parse_equipo(tr)
                if equipo:
                    equipos.append(equipo)
        if len(equipos) != 2:
            continue
        (jug_1, gano_1), (jug_2, gano_2) = equipos
        if gano_1 == gano_2:
            continue  # no se pudo determinar ganador (ninguno o ambos marcados)

        rows.append(
            {
                "categoria": categoria,
                "ronda": ronda,
                "equipo_ganador": jug_1 if gano_1 else jug_2,
                "equipo_perdedor": jug_2 if gano_1 else jug_1,
            }
        )
    return rows


def fetch_all() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for torneo_nombre, slug in load_slugs():
            event_resp = client.get(f"https://www.padelfip.com/events/{slug}/")
            widget_info = _widget_id_y_dias(event_resp.text) if event_resp.status_code == 200 else None
            if not widget_info:
                print(f"  {torneo_nombre}: no se encontró el id del widget, saltado")
                continue
            widget_id, total_days = widget_info

            torneo_rows: list[dict[str, Any]] = []
            for day in range(1, total_days + 1):
                url = f"https://widget.matchscorerlive.com/screen/resultsbyday/FIP-2026-{widget_id}/{day}?t=tol"
                response = client.get(url)
                if response.status_code != 200:
                    continue
                for row in parse_day(response.text):
                    torneo_rows.append({"torneo_nombre_bronze": torneo_nombre, "slug": slug, "dia": day, **row})
                time.sleep(0.2)
            items.extend(torneo_rows)
            print(f"  {torneo_nombre}: {len(torneo_rows)} partidos ({total_days} días)")
    return items


def write_snapshot(items: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
    snapshot = {
        "source": "matchscorerlive (widget de padelfip.com)",
        "endpoint": "https://widget.matchscorerlive.com/screen/resultsbyday/FIP-2026-{id}/{day}",
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
    print(f"{len(items)} partidos totales -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
