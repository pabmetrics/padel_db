"""Fase 2: dim_pareja (SCD2) derivada de fact_partido.

Regla del doc 01 §3.2: "una pareja 'nace' en el primer torneo que juegan
juntos y 'muere' cuando uno de los dos juega otro torneo con otro
compañero. Se guarda historial completo (SCD2)."

Implementación: para cada jugador se construye su secuencia cronológica de
compañeros (uno por partido) y se agrupa en tramos consecutivos con el mismo
compañero — cada tramo es una "vida" de la pareja. Si los mismos dos
jugadores se separan y se reencuentran más tarde, son dos tramos (dos filas),
no uno: así se respeta el "nace/muere" literal del documento en vez de
fusionar toda su historia en una sola fila.

`pareja_id` es un hash de (par de jugadores ordenado + fecha_inicio de ese
tramo): un reencuentro genera un pareja_id nuevo, porque es una "vida"
distinta de la pareja, aunque sean las mismas dos personas.
"""

from __future__ import annotations

import hashlib
import json
from itertools import groupby
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold"
SILVER_ROOT = REPO_ROOT / "silver"

SLOTS_POR_EQUIPO = (
    ("equipo_1_jugador_1", "equipo_1_jugador_2"),
    ("equipo_2_jugador_1", "equipo_2_jugador_2"),
)


def pareja_id_for(jugador_a: str, jugador_b: str, fecha_inicio: str) -> str:
    par = "|".join(sorted((jugador_a, jugador_b)))
    digest = hashlib.sha1(f"{par}|{fecha_inicio}".encode()).hexdigest()
    return f"P{digest[:10]}"


def _eventos_por_jugador(partidos: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    eventos: dict[str, list[dict[str, Any]]] = {}
    for partido in partidos:
        for slot_a, slot_b in SLOTS_POR_EQUIPO:
            a = partido.get(slot_a)
            b = partido.get(slot_b)
            if not a or not b or not a.get("jugador_id") or not b.get("jugador_id"):
                continue
            for yo, compañero in ((a, b), (b, a)):
                eventos.setdefault(yo["jugador_id"], []).append(
                    {
                        "fecha": partido["fecha"],
                        "compañero_id": compañero["jugador_id"],
                        "torneo_id": partido["torneo_id"],
                        "categoria": partido.get("categoria"),
                    }
                )
    for jugador_id, lista in eventos.items():
        lista.sort(key=lambda e: e["fecha"])
    return eventos


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    eventos_por_jugador = _eventos_por_jugador(partidos)

    tramos: dict[tuple[str, str, str], dict[str, Any]] = {}
    ultimo_tramo_clave_por_jugador: dict[str, tuple[str, str, str]] = {}

    for jugador_id, eventos in eventos_por_jugador.items():
        grupos = [(compañero_id, list(grupo)) for compañero_id, grupo in groupby(eventos, key=lambda e: e["compañero_id"])]
        for compañero_id, grupo in grupos:
            fecha_inicio = grupo[0]["fecha"]
            fecha_fin = grupo[-1]["fecha"]
            torneos = {e["torneo_id"] for e in grupo}
            clave = tuple(sorted((jugador_id, compañero_id))) + (fecha_inicio,)
            if clave in tramos:
                tramos[clave]["torneos"] |= torneos
                tramos[clave]["n_partidos"] += len(grupo)
                tramos[clave]["fecha_fin"] = max(tramos[clave]["fecha_fin"], fecha_fin)
            else:
                tramos[clave] = {
                    "jugador_1_id": clave[0],
                    "jugador_2_id": clave[1],
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "torneos": set(torneos),
                    "n_partidos": len(grupo),
                    "categoria": grupo[0]["categoria"],
                }
        # el último grupo de la secuencia cronológica de este jugador es su
        # pareja "activa" ahora mismo, según sus propios datos
        if grupos:
            compañero_id, grupo = grupos[-1]
            ultimo_tramo_clave_por_jugador[jugador_id] = tuple(sorted((jugador_id, compañero_id))) + (grupo[0]["fecha"],)

    dim_dir = SILVER_ROOT / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    nombres = {}
    if dt_dirs:
        rows = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        nombres = {r["jugador_id"]: r["nombre_canonico"] for r in rows}

    rows_out: list[dict[str, Any]] = []
    for clave, tramo in tramos.items():
        jugador_1_id, jugador_2_id, _ = clave
        # activa = este tramo es, a la vez, el compañero más reciente de
        # jugador_1 Y de jugador_2 según su propio historial — si cualquiera
        # de los dos ha jugado después con otra persona, la pareja "murió"
        # (doc 01 §3.2), aunque este tramo siga teniendo la fecha_fin más
        # alta de los datos que tenemos de ESTA pareja en concreto.
        activa = (
            ultimo_tramo_clave_por_jugador.get(jugador_1_id) == clave
            and ultimo_tramo_clave_por_jugador.get(jugador_2_id) == clave
        )
        rows_out.append(
            {
                "pareja_id": pareja_id_for(jugador_1_id, jugador_2_id, tramo["fecha_inicio"]),
                "jugador_1_id": jugador_1_id,
                "jugador_2_id": jugador_2_id,
                "jugador_1_nombre": nombres.get(jugador_1_id),
                "jugador_2_nombre": nombres.get(jugador_2_id),
                "categoria": tramo["categoria"],
                "fecha_inicio": tramo["fecha_inicio"],
                "fecha_fin": tramo["fecha_fin"],
                "n_torneos": len(tramo["torneos"]),
                "n_partidos": tramo["n_partidos"],
                "activa": activa,
            }
        )

    rows_out.sort(key=lambda r: r["fecha_inicio"])

    out_dir = SILVER_ROOT / "dim_pareja"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows_out, indent=2, ensure_ascii=False), encoding="utf-8")

    reencuentros = sum(
        1
        for _, grupo in groupby(
            sorted(rows_out, key=lambda r: tuple(sorted((r["jugador_1_id"], r["jugador_2_id"])))),
            key=lambda r: tuple(sorted((r["jugador_1_id"], r["jugador_2_id"]))),
        )
        if len(list(grupo)) > 1
    )
    print(f"dim_pareja: {len(rows_out)} tramos de pareja ({reencuentros} parejas con más de un tramo) -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
