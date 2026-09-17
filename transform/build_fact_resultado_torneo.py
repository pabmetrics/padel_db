"""fact_resultado_torneo: última ronda alcanzada por pareja y torneo, cruzada
con dim_puntos_categoria para sacar los puntos ganados.

Limitaciones reales conocidas (17/09/2026):
- fact_partido solo tiene partidos de cuadro principal (`fase == "main"`);
  no hay partidos de clasificación en los datos de F2 que hemos ingerido,
  así que no se puede calcular el resultado de quien cayó en qualy.
- El nivel de torneo `fip_other` (ej. "Mediterranean Games") no está en la
  tabla de puntos oficial que aportó el usuario — se deja sin puntos,
  marcado explícitamente, en vez de inventar una categoría.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from unidecode import unidecode


def normalize_name(name: str) -> str:
    ascii_name = unidecode(name or "").lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", ascii_name).strip()

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
DIM_PUNTOS = REPO_ROOT / "silver" / "dim_puntos_categoria" / "data.json"
RESULTADO_ALTERNATIVO = REPO_ROOT / "silver" / "resultado_alternativo" / "data.json"
RESULTADO_ALTERNATIVO_FIP = REPO_ROOT / "silver" / "resultado_alternativo_fip" / "data.json"
OUT_PATH = REPO_ROOT / "silver" / "fact_resultado_torneo" / "data.json"

NIVEL_PADELAPI_A_CATEGORIA = {
    "major": ("Premier Padel", "Major"),
    "p1": ("Premier Padel", "P1"),
    "p2": ("Premier Padel", "P2"),
    "finals": ("Premier Padel", "Finals"),
    "fip_platinum": ("FIP Tour", "FIP Platinum"),
    "fip_gold": ("FIP Tour", "FIP Gold"),
    "fip_silver": ("FIP Tour", "FIP Silver"),
    "fip_bronze": ("FIP Tour", "FIP Bronze"),
    "fip_finals": ("FIP Tour", "FIP Finals"),
}

RONDA_ORDEN = {"Round of 64": 0, "Round of 32": 1, "Round of 16": 2, "Quarter": 3, "Semifinals": 4, "Finals": 5}
RONDA_CODIGO = {"Round of 64": "R64", "Round of 32": "R32", "Round of 16": "R16", "Quarter": "QF", "Semifinals": "SF"}


def _pareja_key(a: dict[str, Any] | None, b: dict[str, Any] | None) -> tuple[str, str] | None:
    if not a or not b or not a.get("jugador_id") or not b.get("jugador_id"):
        return None
    return tuple(sorted((a["jugador_id"], b["jugador_id"])))


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    puntos_tabla = json.loads(DIM_PUNTOS.read_text(encoding="utf-8"))
    puntos_por_clave = {(p["circuito"], p["categoria"], p["ronda"]): p["puntos"] for p in puntos_tabla}

    dim_dir = REPO_ROOT / "silver" / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    nombres: dict[str, str] = {}
    sexo_por_jugador: dict[str, str] = {}
    if dt_dirs:
        filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        nombres = {r["jugador_id"]: r["nombre_canonico"] for r in filas}
        sexo_por_jugador = {r["jugador_id"]: r["sexo"] for r in filas}

    # (torneo_id, pareja_key) -> mejor partido (por orden de ronda)
    mejor_partido: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}

    for p in partidos:
        if p.get("ronda") not in RONDA_ORDEN or p.get("ganador") not in ("team_1", "team_2"):
            continue
        orden = RONDA_ORDEN[p["ronda"]]

        for lado, pareja_slots, es_ganador in (
            ("team_1", ("equipo_1_jugador_1", "equipo_1_jugador_2"), p["ganador"] == "team_1"),
            ("team_2", ("equipo_2_jugador_1", "equipo_2_jugador_2"), p["ganador"] == "team_2"),
        ):
            pareja = _pareja_key(p.get(pareja_slots[0]), p.get(pareja_slots[1]))
            if not pareja:
                continue
            clave = (p["torneo_id"], pareja)
            actual = mejor_partido.get(clave)
            if actual is None or orden > actual["_orden"]:
                mejor_partido[clave] = {
                    "_orden": orden,
                    "_es_ganador": es_ganador,
                    "torneo_id": p["torneo_id"],
                    "torneo_nombre": p["torneo_nombre"],
                    "torneo_nivel_padelapi": p.get("torneo_nivel_padelapi"),
                    "categoria_partido": p.get("categoria"),
                    "ronda": p["ronda"],
                    "fecha": p["fecha"],
                    "jugador_1_id": pareja[0],
                    "jugador_2_id": pareja[1],
                }

    # Metadatos de torneo (nombre/nivel) por torneo_id, tomados de cualquier
    # partido de ese torneo — hacen falta incluso para partidos con `winner`
    # oculto, que no llegan a mejor_partido pero sí traen esta metadata.
    torneo_id_por_nombre: dict[str, str] = {}
    nombre_canonico_por_torneo_id: dict[str, str] = {}
    nivel_por_torneo_id: dict[str, str | None] = {}
    fecha_max_por_torneo_id: dict[str, str] = {}
    for p in partidos:
        torneo_id_por_nombre[normalize_name(p["torneo_nombre"])] = p["torneo_id"]
        nombre_canonico_por_torneo_id.setdefault(p["torneo_id"], p["torneo_nombre"])
        nivel_por_torneo_id.setdefault(p["torneo_id"], p.get("torneo_nivel_padelapi"))
        fecha_max_por_torneo_id[p["torneo_id"]] = max(fecha_max_por_torneo_id.get(p["torneo_id"], ""), p["fecha"])

    parejas_cubiertas: set[tuple[str, tuple[str, str]]] = set(mejor_partido.keys())

    # Respaldo para torneos donde padelapi oculta el `winner` (ventana móvil
    # de ~180 días, ver docs/campos-f2-padelapi.md): padelearnings.com para
    # Premier Padel, el widget de padelfip.com para FIP Tour. Solo se añade
    # una pareja si ninguna fuente ya vista la cubrió (así no hay doble
    # conteo cuando el ocultamiento es parcial, ej. Cancún).
    vistos_alt: set[tuple[str, tuple[str, str]]] = set()
    for fuente_path in (RESULTADO_ALTERNATIVO, RESULTADO_ALTERNATIVO_FIP):
        if not fuente_path.exists():
            continue
        for r in json.loads(fuente_path.read_text(encoding="utf-8")):
            torneo_id = torneo_id_por_nombre.get(normalize_name(r["torneo_nombre"]))
            compañero_id = r.get("compañero_id")
            if not torneo_id or not compañero_id:
                continue
            pareja = tuple(sorted((r["jugador_id"], compañero_id)))
            clave = (torneo_id, pareja)
            if clave in parejas_cubiertas or clave in vistos_alt:
                continue
            vistos_alt.add(clave)
            sexo = r.get("sexo") or sexo_por_jugador.get(r["jugador_id"])
            mejor_partido[clave] = {
                "_orden": None,
                "_es_ganador": r["ronda_alcanzada"] == "W",
                "_ronda_alternativa": r["ronda_alcanzada"],
                "torneo_id": torneo_id,
                "torneo_nombre": nombre_canonico_por_torneo_id.get(torneo_id, r["torneo_nombre"]),
                "torneo_nivel_padelapi": nivel_por_torneo_id.get(torneo_id),
                "categoria_partido": "men" if sexo == "M" else "women" if sexo == "F" else None,
                "ronda": None,
                "fecha": fecha_max_por_torneo_id.get(torneo_id),
                "jugador_1_id": pareja[0],
                "jugador_2_id": pareja[1],
            }

    rows: list[dict[str, Any]] = []
    niveles_sin_mapear: set[str] = set()

    for datos in mejor_partido.values():
        if "_ronda_alternativa" in datos:
            ronda_alcanzada = datos["_ronda_alternativa"]
        elif datos["ronda"] == "Finals":
            ronda_alcanzada = "W" if datos["_es_ganador"] else "F"
        else:
            ronda_alcanzada = RONDA_CODIGO[datos["ronda"]]

        mapeo = NIVEL_PADELAPI_A_CATEGORIA.get(datos["torneo_nivel_padelapi"])
        if mapeo is None:
            if datos["torneo_nivel_padelapi"]:
                niveles_sin_mapear.add(datos["torneo_nivel_padelapi"])
            circuito = categoria = puntos = None
        else:
            circuito, categoria = mapeo
            puntos = puntos_por_clave.get((circuito, categoria, ronda_alcanzada))

        rows.append(
            {
                "torneo_id": datos["torneo_id"],
                "torneo_nombre": datos["torneo_nombre"],
                "circuito": circuito,
                "categoria": categoria,
                "jugador_1_id": datos["jugador_1_id"],
                "jugador_2_id": datos["jugador_2_id"],
                "jugador_1_nombre": nombres.get(datos["jugador_1_id"]),
                "jugador_2_nombre": nombres.get(datos["jugador_2_id"]),
                "categoria_sexo": datos["categoria_partido"],
                "ronda_alcanzada": ronda_alcanzada,
                "puntos_ganados": puntos,
                "fecha": datos["fecha"],
                "fuente_resultado": "padelearnings_respaldo" if "_ronda_alternativa" in datos else "padelapi",
                "fuente_txt": "padelapi.org + FIP Ranking Point Table 2026 · elaboración propia",
            }
        )

    rows.sort(key=lambda r: r["fecha"], reverse=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    con_puntos = sum(1 for r in rows if r["puntos_ganados"] is not None)
    de_respaldo = sum(1 for r in rows if r["fuente_resultado"] == "padelearnings_respaldo")
    print(f"fact_resultado_torneo: {len(rows)} resultados de pareja ({con_puntos} con puntos calculados, {de_respaldo} de la fuente de respaldo)")
    if niveles_sin_mapear:
        print(f"  Niveles de torneo sin mapear a la tabla de puntos: {sorted(niveles_sin_mapear)}")
    print(f"-> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
