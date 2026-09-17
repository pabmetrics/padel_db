"""silver/resultado_alternativo_fip: ronda alcanzada por pareja y torneo,
desde el widget de respaldo del FIP Tour (bronze/matchresults/fip).

Los nombres del widget vienen abreviados ("M. Di Nenno"), así que el cruce
a jugador_id no es un match global de nombre (arriesgado: dos jugadores
pueden compartir apellido) sino contra el **censo de participantes de ese
torneo concreto**, que sí conocemos por fact_partido aunque padelapi oculte
quién ganó cada partido — la lista de quién jugó no está oculta, solo el
resultado. Si dos jugadores del mismo torneo comparten apellido, se deja
sin cruzar en vez de adivinar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "matchresults" / "fip"
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
OUT_PATH = REPO_ROOT / "silver" / "resultado_alternativo_fip" / "data.json"

RONDA_ORDEN = {"Q1": 0, "Q2": 1, "Q3": 2, "Round of 32": 3, "Round of 16": 4, "Quarterfinals": 5, "SemiFinals": 6, "Final": 7}
RONDA_CODIGO = {"Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "Round of 32": "R32", "Round of 16": "R16", "Quarterfinals": "QF", "SemiFinals": "SF"}


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unidecode(name or "").lower()).strip()


def apellido(nombre_completo: str) -> str:
    """Último 'apellido' del nombre normalizado — suficiente para casar
    contra la abreviatura 'M. Di Nenno' del widget cuando es único en el
    censo del torneo."""

    return normalize(nombre_completo).split(" ")[-1]


def _latest_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def build() -> Path:
    dt_dir = _latest_dir(BRONZE_ROOT)
    if dt_dir is None:
        raise SystemExit(f"No hay snapshots en {BRONZE_ROOT}")
    widget_items = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))["items"]

    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))

    # censo por torneo: apellido normalizado -> jugador_id (None si ambiguo)
    censo_por_torneo: dict[str, dict[str, str | None]] = {}
    for p in partidos:
        censo = censo_por_torneo.setdefault(p["torneo_nombre"], {})
        for slot in ("equipo_1_jugador_1", "equipo_1_jugador_2", "equipo_2_jugador_1", "equipo_2_jugador_2"):
            jugador = p.get(slot)
            if not jugador or not jugador.get("jugador_id"):
                continue
            ap = apellido(jugador["nombre_padelapi"])
            if ap in censo and censo[ap] != jugador["jugador_id"]:
                censo[ap] = None  # apellido ambiguo en este torneo
            else:
                censo[ap] = jugador["jugador_id"]

    def resolver(nombre_abreviado: str, torneo: str) -> str | None:
        censo = censo_por_torneo.get(torneo, {})
        ap = normalize(nombre_abreviado).split(" ")[-1]
        return censo.get(ap)

    # (torneo, pareja) -> mejor partido visto
    mejor: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}

    sin_cruzar = 0
    for m in widget_items:
        orden = RONDA_ORDEN.get(m["ronda"])
        if orden is None:
            continue
        torneo = m["torneo_nombre_bronze"]
        for jugadores, es_ganador in ((m["equipo_ganador"], True), (m["equipo_perdedor"], False)):
            if len(jugadores) != 2:
                continue
            ids = [resolver(j, torneo) for j in jugadores]
            if not all(ids):
                sin_cruzar += 1
                continue
            pareja = tuple(sorted(ids))
            clave = (torneo, pareja)
            actual = mejor.get(clave)
            if actual is None or orden > actual["_orden"]:
                mejor[clave] = {"_orden": orden, "_ronda": m["ronda"], "_es_ganador": es_ganador, "categoria": m["categoria"]}

    rows: list[dict[str, Any]] = []
    for (torneo, pareja), datos in mejor.items():
        ronda_alcanzada = ("W" if datos["_es_ganador"] else "F") if datos["_ronda"] == "Final" else RONDA_CODIGO[datos["_ronda"]]
        rows.append(
            {
                "torneo_nombre": torneo,
                "jugador_id": pareja[0],
                "compañero_id": pareja[1],
                "sexo": "M" if datos["categoria"] == "Men" else "F",
                "ronda_alcanzada": ronda_alcanzada,
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"resultado_alternativo_fip: {len(rows)} filas de pareja/torneo ({sin_cruzar} jugadores sin cruzar al censo) -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
