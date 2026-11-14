"""Gold: carrera_finals (15/11/2026) — la carrera a las Premier Padel Finals.

Reglas (StudyPadel, "Clasificados Premier Padel Finals 2026", foto del
12/10/2026, pasada por el usuario): se clasifican los 16 primeros jugadores
y las 16 primeras jugadoras del FIP Race, a título individual. Una pareja
solo entra si los dos están dentro del corte; si uno se queda fuera, el
otro juega con otro clasificado. Vale el Race tal como quede tras el Major
de México (23-29/11/2026); los siguientes quedan como suplentes. Además,
hay que haber jugado al menos 15 torneos de Premier Padel en el año: ese
requisito NO se comprueba aquí (nuestras stats de Premier no cubren el año
entero), y cada candidato lo avisa.

Una fila = un jugador del Race (F2, `/rankings?type=race`, ver
`ingest/padelapi/snapshot.py fetch_race`), con su distancia al corte.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "padelapi" / "race"
MAP_ROOT = REPO_ROOT / "silver" / "map_jugador_fuente"
DIM_JUGADOR_ROOT = REPO_ROOT / "silver" / "dim_jugador"
GOLD_ROOT = REPO_ROOT / "gold" / "carrera_finals"

PLAZAS = 16
PUBLICABLE_HASTA = 24  # el gráfico enseña el corte y los que lo persiguen
FUENTE_TXT = "FIP Race vía padelapi.org · elaboración propia"


def _latest(root: Path) -> Path | None:
    dirs = sorted(p for p in root.glob("dt=*") if p.is_dir())
    return dirs[-1] if dirs else None


def calcular(items: list[dict[str, Any]], ids: dict[str, str], nombres: dict[str, str]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for categoria in ("men", "women"):
        del_race = sorted((i for i in items if i.get("category") == categoria and i.get("ranking")),
                          key=lambda i: (i["ranking"], -(i.get("points") or 0)))
        if len(del_race) <= PLAZAS:
            continue
        dentro = [i for i in del_race if i["ranking"] <= PLAZAS]
        fuera = [i for i in del_race if i["ranking"] > PLAZAS]
        puntos_ultimo_dentro = min(i["points"] for i in dentro)
        puntos_primero_fuera = fuera[0]["points"] if fuera else None
        empate_en_corte = len(dentro) > PLAZAS
        for i in del_race:
            esta_dentro = i["ranking"] <= PLAZAS
            jugador_id = ids.get(str(i["id"]))
            filas.append({
                "categoria": categoria,
                "posicion": i["ranking"],
                "jugador_id": jugador_id,
                "jugador_nombre": nombres.get(jugador_id) or i.get("name"),
                "puntos": i["points"],
                "puntos_diff_semana": i.get("points_diff"),
                "posicion_diff_semana": i.get("ranking_diff"),
                "dentro": esta_dentro,
                # Dentro: lo que saca al primero de fuera. Fuera: lo que le falta para el último de dentro.
                "margen_corte": (i["points"] - puntos_primero_fuera) if esta_dentro and puntos_primero_fuera is not None
                else (puntos_ultimo_dentro - i["points"]),
                "plazas": PLAZAS,
                "empate_en_corte": empate_en_corte,
                "fecha_race": i.get("date"),
                "fecha_dato": i.get("date"),
                "fuente_txt": FUENTE_TXT,
                "publicable": i["ranking"] <= PUBLICABLE_HASTA and jugador_id is not None,
            })
    return filas


def build() -> Path | None:
    d = _latest(BRONZE_ROOT)
    if d is None:
        print("carrera_finals: no hay snapshot del Race en bronze")
        return None
    items = json.loads((d / "data.json").read_text(encoding="utf-8"))["items"]
    mapa = _latest(MAP_ROOT)
    ids = {r["id_fuente"]: r["jugador_id"] for r in json.loads((mapa / "data.json").read_text(encoding="utf-8"))
           if r["fuente"] == "padelapi"} if mapa else {}
    dim = _latest(DIM_JUGADOR_ROOT)
    nombres = {r["jugador_id"]: r["nombre_canonico"] for r in json.loads((dim / "data.json").read_text(encoding="utf-8"))} if dim else {}

    filas = calcular(items, ids, nombres)
    fecha = max((f["fecha_race"] for f in filas if f["fecha_race"]), default=d.name.removeprefix("dt="))
    out_dir = GOLD_ROOT / f"fecha_dato={fecha}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"carrera_finals: {len(filas)} filas (Race del {fecha}) -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
