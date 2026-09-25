"""Fase 1: dim_jugador + map_jugador_fuente a partir de los snapshots F1 y F2.

Cruza premierpadel.com (F1) y padelapi.org (F2) por nombre normalizado
(unidecode + minúsculas, doc 01 §6) y género/categoría. Es un cruce
determinista por nombre, no fuzzy matching: los que no casan exactamente se
quedan fuera de dim_jugador y se listan en un informe de reconciliación para
revisión manual (alimenta `data/manual/alias_jugadores.csv`).

jugador_id es un id propio (hash estable de nombre normalizado + sexo), no el
id de ninguna fuente — doc 01 §3.2: "IDs propios; los de fuente solo en
map_jugador_fuente".
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
F1_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "rankings"
F2_PLAYERS_ROOT = REPO_ROOT / "bronze" / "padelapi" / "players"
SILVER_ROOT = REPO_ROOT / "silver"
ALIAS_CSV = REPO_ROOT / "data" / "manual" / "alias_jugadores.csv"

GENDER_TO_SEXO = {"Male": "M", "Female": "F", "men": "M", "women": "F"}


def normalize_name(name: str) -> str:
    ascii_name = unidecode(name or "").lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def load_alias_overrides() -> dict[str, str]:
    """nombre_normalizado_alias -> nombre_canonico, desde el CSV de curación manual."""

    if not ALIAS_CSV.exists():
        return {}
    overrides: dict[str, str] = {}
    with ALIAS_CSV.open(encoding="utf-8") as f:
        next(f, None)  # cabecera
        for line in f:
            line = line.strip()
            if not line:
                continue
            alias, canonico = (line.split(",", 1) + [""])[:2]
            if alias and canonico:
                overrides[normalize_name(alias)] = canonico.strip()
    return overrides


def load_f1_players() -> list[dict[str, Any]]:
    dt_dir = _latest_dir(F1_ROOT)
    records = []
    for filename in ("male.json", "female.json"):
        path = dt_dir / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload["items"]:
            records.append(
                {
                    "fuente": "premierpadel",
                    "id_fuente": str(item["id"]),
                    "nombre_en_fuente": item["full_name"],
                    "sexo": GENDER_TO_SEXO.get(item.get("gender"), "?"),
                    "activo": item.get("status") == "Active",
                    "posicion_f1": item.get("posicion_lista"),
                }
            )
    return records


def load_f2_players() -> list[dict[str, Any]]:
    dt_dir = _latest_dir(F2_PLAYERS_ROOT)
    payload = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    records = []
    for item in payload["items"]:
        records.append(
            {
                "fuente": "padelapi",
                "id_fuente": str(item["id"]),
                "nombre_en_fuente": item["name"],
                "sexo": GENDER_TO_SEXO.get(item.get("category"), "?"),
                "nacionalidad": item.get("nationality"),
                "fecha_nac": item.get("birthdate"),
                "altura_cm": int(item["height"]) if item.get("height") else None,
                "mano": item.get("hand"),
                "lado_pista": item.get("side"),
                "ranking_f2": item.get("ranking"),
                "puntos_f2": item.get("points"),
            }
        )
    return records


def sugerir_alias(solo_f1: list[dict[str, Any]], solo_f2: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Fichas de F1 sin cruzar cuyas palabras están todas en un único nombre
    de F2 del mismo sexo ("Paula Josemaria" -> "Paula Josemaria Martin").
    No se aplican solas: van al informe y alguien las pasa al CSV."""
    sugerencias = []
    for f1 in solo_f1:
        palabras = set(normalize_name(f1["nombre_en_fuente"]).split())
        candidatos = [
            f2 for f2 in solo_f2
            if f2["sexo"] == f1["sexo"] and palabras <= set(normalize_name(f2["nombre_en_fuente"]).split())
        ]
        if len(candidatos) == 1:
            sugerencias.append({"alias": f1["nombre_en_fuente"], "nombre_canonico": candidatos[0]["nombre_en_fuente"]})
    return sorted(sugerencias, key=lambda s: s["alias"])


def jugador_id_for(nombre_normalizado: str, sexo: str) -> str:
    digest = hashlib.sha1(f"{nombre_normalizado}|{sexo}".encode("utf-8")).hexdigest()
    return f"J{digest[:10]}"


def build() -> None:
    alias_overrides = load_alias_overrides()
    f1_records = load_f1_players()
    f2_records = load_f2_players()

    def clave(rec: dict[str, Any]) -> tuple[str, str]:
        # Un alias lleva a la misma clave que su nombre canónico: así el CSV
        # fusiona las dos fichas en un solo jugador_id, no solo cambia el
        # nombre que se enseña ("Ariana Sanchez" de F1 y "Ariana Sanchez
        # Fallada" de F2 eran dos jugadoras, y la de F1 no tenía partidos).
        norm = normalize_name(rec["nombre_en_fuente"])
        return normalize_name(alias_overrides.get(norm, norm)), rec["sexo"]

    f1_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in f1_records:
        f1_by_key[clave(rec)] = rec

    f2_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in f2_records:
        f2_by_key[clave(rec)] = rec

    all_keys = set(f1_by_key) | set(f2_by_key)

    dim_jugador_rows: list[dict[str, Any]] = []
    map_rows: list[dict[str, Any]] = []
    solo_f1: list[str] = []
    solo_f2: list[str] = []

    for norm, sexo in sorted(all_keys):
        f1 = f1_by_key.get((norm, sexo))
        f2 = f2_by_key.get((norm, sexo))
        jugador_id = jugador_id_for(norm, sexo)

        nombre_canonico = next(
            (alias_overrides[normalize_name(r["nombre_en_fuente"])] for r in (f1, f2)
             if r and normalize_name(r["nombre_en_fuente"]) in alias_overrides),
            None,
        )
        if not nombre_canonico:
            nombre_canonico = f1["nombre_en_fuente"] if f1 else f2["nombre_en_fuente"]

        dim_jugador_rows.append(
            {
                "jugador_id": jugador_id,
                "nombre_canonico": nombre_canonico,
                "sexo": sexo,
                "nacionalidad": f2.get("nacionalidad") if f2 else None,
                "fecha_nac": f2.get("fecha_nac") if f2 else None,
                "altura_cm": f2.get("altura_cm") if f2 else None,
                "mano": f2.get("mano") if f2 else None,
                "lado_pista": f2.get("lado_pista") if f2 else None,
                "lado_desde": None,
                "activo": f1.get("activo") if f1 else None,
                "en_f1": f1 is not None,
                "en_f2": f2 is not None,
            }
        )

        if f1:
            map_rows.append(
                {
                    "fuente": "premierpadel",
                    "id_fuente": f1["id_fuente"],
                    "nombre_en_fuente": f1["nombre_en_fuente"],
                    "jugador_id": jugador_id,
                    "vigente": True,
                }
            )
        else:
            solo_f2.append(f2["nombre_en_fuente"])

        if f2:
            map_rows.append(
                {
                    "fuente": "padelapi",
                    "id_fuente": f2["id_fuente"],
                    "nombre_en_fuente": f2["nombre_en_fuente"],
                    "jugador_id": jugador_id,
                    "vigente": True,
                }
            )
        else:
            solo_f1.append(f1["nombre_en_fuente"])

    fecha = datetime.now(timezone.utc).date().isoformat()

    dim_dir = SILVER_ROOT / "dim_jugador" / f"dt={fecha}"
    dim_dir.mkdir(parents=True, exist_ok=True)
    (dim_dir / "data.json").write_text(
        json.dumps(dim_jugador_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    map_dir = SILVER_ROOT / "map_jugador_fuente" / f"dt={fecha}"
    map_dir.mkdir(parents=True, exist_ok=True)
    (map_dir / "data.json").write_text(
        json.dumps(map_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    sugerencias = sugerir_alias(
        [f1_by_key[k] for k in f1_by_key if k not in f2_by_key],
        [f2_by_key[k] for k in f2_by_key if k not in f1_by_key],
    )

    recon_dir = SILVER_ROOT / "_reconciliacion"
    recon_dir.mkdir(parents=True, exist_ok=True)
    (recon_dir / f"jugadores_sin_cruzar_{fecha}.json").write_text(
        json.dumps(
            {
                "fecha": fecha,
                "solo_en_f1_premierpadel": sorted(solo_f1),
                "solo_en_f2_padelapi": sorted(solo_f2),
                "sugerencias_alias": sugerencias,
                "nota": (
                    "Nombres que no han casado por normalización exacta entre fuentes. "
                    "Revisar y, si son la misma persona con grafía distinta, añadir una "
                    "fila a data/manual/alias_jugadores.csv (alias,nombre_canonico). "
                    "`sugerencias_alias` son solo sugerencias (doc 01 §6): nombre de F1 "
                    "cuyas palabras están todas en un único nombre de F2 del mismo sexo."
                ),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"dim_jugador: {len(dim_jugador_rows)} jugadores -> {dim_dir.relative_to(REPO_ROOT)}")
    print(f"map_jugador_fuente: {len(map_rows)} filas -> {map_dir.relative_to(REPO_ROOT)}")
    print(f"Sin cruzar: {len(solo_f1)} solo en F1, {len(solo_f2)} solo en F2 (ver _reconciliacion/)")
    if sugerencias:
        print(f"  {len(sugerencias)} posibles alias por revisar (sugerencias_alias en _reconciliacion/)")


if __name__ == "__main__":
    build()
