"""Gold: ganancias_temporada (doc 01 §3.3 / doc 02 "Cierre de torneo").

Una fila = un jugador con ganancias conocidas en la temporada (ventana de
datos de fact_partido, 180 días). Cruza fact_resultado_torneo con
silver/prize_por_torneo (cifras reales por torneo, no una tabla genérica
por categoría — ver docs/campos-prize-money-2026.md sobre por qué se
abandonó ese enfoque el 17/09/2026).

Cobertura real hoy: 16 torneos de Premier Padel (padelearnings.com) + 36
de FIP Tour (padelfip.com, oficial) de los ~65 torneos de fact_partido.
Faltan por descuido: los que no se han podido emparejar con seguridad con
una página de premios (nombre ambiguo entre categorías/ediciones) — mejor
dejarlos fuera que arriesgar una cifra mal cruzada.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_RESULTADO = REPO_ROOT / "silver" / "fact_resultado_torneo" / "data.json"
PRIZE_POR_TORNEO = REPO_ROOT / "silver" / "prize_por_torneo" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "ganancias_temporada"

SEXO_PARTIDO_A_PRIZE = {"men": "M", "women": "F"}


def normalize_name(name: str) -> str:
    ascii_name = unidecode(name or "").lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()


def build() -> Path:
    resultados = json.loads(FACT_RESULTADO.read_text(encoding="utf-8"))
    prize_rows = json.loads(PRIZE_POR_TORNEO.read_text(encoding="utf-8"))

    prize_por_clave: dict[tuple[str, str, str], int] = {}
    for p in prize_rows:
        prize_por_clave[(p["torneo_nombre_norm"], p["sexo"], p["ronda"])] = p["prize_money_jugador_eur"]

    dim_dir = REPO_ROOT / "silver" / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    nombres: dict[str, str] = {}
    sexo_por_jugador: dict[str, str] = {}
    if dt_dirs:
        filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        nombres = {r["jugador_id"]: r["nombre_canonico"] for r in filas}
        sexo_por_jugador = {r["jugador_id"]: r["sexo"] for r in filas}

    acumulado: dict[str, dict[str, Any]] = defaultdict(lambda: {"total_eur": 0, "torneos": set(), "detalle": []})
    torneos_con_premio: set[str] = set()

    for r in resultados:
        torneo_norm = normalize_name(r["torneo_nombre"])
        sexo_prize = SEXO_PARTIDO_A_PRIZE.get(r.get("categoria_sexo"))
        premio = prize_por_clave.get((torneo_norm, sexo_prize, r["ronda_alcanzada"]))
        if premio is None:
            premio = prize_por_clave.get((torneo_norm, "ambos", r["ronda_alcanzada"]))
        if premio is None:
            continue
        torneos_con_premio.add(r["torneo_nombre"])
        for jugador_id in (r["jugador_1_id"], r["jugador_2_id"]):
            entry = acumulado[jugador_id]
            entry["total_eur"] += premio
            entry["torneos"].add(r["torneo_id"])
            entry["detalle"].append(
                {"torneo_nombre": r["torneo_nombre"], "ronda_alcanzada": r["ronda_alcanzada"], "premio_eur": premio, "fecha": r["fecha"]}
            )

    rows: list[dict[str, Any]] = []
    for jugador_id, datos in acumulado.items():
        rows.append(
            {
                "fecha_dato": date.today().isoformat(),
                "jugador_id": jugador_id,
                "jugador_nombre": nombres.get(jugador_id),
                "sexo": sexo_por_jugador.get(jugador_id),
                "ganancias_conocidas_eur": datos["total_eur"],
                "n_torneos_con_premio_conocido": len(datos["torneos"]),
                "detalle": sorted(datos["detalle"], key=lambda d: d["fecha"], reverse=True),
                "alcance": f"Cifras reales de {len(torneos_con_premio)} torneos (padelearnings.com + padelfip.com), no una estimación genérica",
                "fuente_txt": "padelearnings.com + padelfip.com + padelapi.org · elaboración propia",
                "publicable": datos["total_eur"] > 0,
            }
        )

    rows.sort(key=lambda r: -r["ganancias_conocidas_eur"])

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"ganancias_temporada: {len(rows)} jugadores, {len(torneos_con_premio)} torneos con premio real cruzado")
    if rows:
        top = rows[0]
        print(f"  Máximo: {top['jugador_nombre']} ({top['ganancias_conocidas_eur']:,} €, {top['n_torneos_con_premio_conocido']} torneos)")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
