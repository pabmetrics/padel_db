"""Gold: partidos_nacionalidad — base del gráfico a medida
`parejas_nacionalidad` (content/chart_factory/adhoc.py).

Una fila = un partido de fact_partido, con cada pareja clasificada:

- `mismo_pais`: los dos jugadores comparten nacionalidad (dim_jugador),
- `mixta`: no la comparten,
- `None`: falta la nacionalidad de alguno ("ZZ" en F2 cuenta como falta).

Y el nivel de cada pareja, para poder comparar a igual ranking: no existe un
ranking oficial de parejas ni un ranking histórico por fecha en este
proyecto, así que el nivel es la suma de los puntos *actuales* de los dos
jugadores (último fact_ranking_semanal), situada entre las parejas activas
de dim_pareja: `posicion_equivalente` = 1 + nº de parejas activas con más
puntos. Una pareja ya separada recibe la posición que tendría hoy. Es una
aproximación y lo dice en los avisos del gráfico, no en silencio.

Puntos que faltan en fact_ranking_semanal (jugador con posición pero sin
puntos de F2): se interpolan entre los vecinos de posición con puntos, que
son monótonos (test_ranking_puntos_no_crecen_con_la_posicion). Fuera del
top 500 de F1: 0 puntos.

`publicable` = las dos parejas clasificadas y ganador conocido y coherente.
"""

from __future__ import annotations

import json
from bisect import bisect_left
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER = REPO_ROOT / "silver"
FACT_PARTIDO = SILVER / "fact_partido" / "data.json"
DIM_PAREJA = SILVER / "dim_pareja" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "partidos_nacionalidad"

NACIONALIDAD_DESCONOCIDA = {None, "", "ZZ"}
SEXO_POR_CATEGORIA = {"men": "M", "women": "F"}


def _ultimo(root: Path) -> Path:
    dirs = sorted(p for p in root.glob("*=*") if p.is_dir())
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def interpolar_puntos(filas: list[dict[str, Any]]) -> dict[str, float]:
    """jugador_id -> puntos, rellenando los huecos por posición. Sin vecino
    con puntos por uno de los lados, se toma el del otro lado."""
    con_puntos = sorted((f["posicion"], f["puntos"]) for f in filas if f["puntos"] is not None)
    if not con_puntos:
        return {}
    posiciones = [p for p, _ in con_puntos]
    resultado = {}
    for f in filas:
        if f["puntos"] is not None:
            resultado[f["jugador_id"]] = float(f["puntos"])
            continue
        i = bisect_left(posiciones, f["posicion"])
        if i == 0:
            resultado[f["jugador_id"]] = float(con_puntos[0][1])
        elif i == len(con_puntos):
            resultado[f["jugador_id"]] = float(con_puntos[-1][1])
        else:
            (p0, v0), (p1, v1) = con_puntos[i - 1], con_puntos[i]
            peso = (f["posicion"] - p0) / (p1 - p0) if p1 != p0 else 0
            resultado[f["jugador_id"]] = v0 + (v1 - v0) * peso
    return resultado


def clasificar(nacionalidad_1: str | None, nacionalidad_2: str | None) -> str | None:
    if nacionalidad_1 in NACIONALIDAD_DESCONOCIDA or nacionalidad_2 in NACIONALIDAD_DESCONOCIDA:
        return None
    return "mismo_pais" if nacionalidad_1 == nacionalidad_2 else "mixta"


def posicion_equivalente(puntos: float, puntos_activas_desc: list[float]) -> int:
    """1 + parejas activas con estrictamente más puntos (empates comparten puesto)."""
    return 1 + sum(1 for p in puntos_activas_desc if p > puntos)


def build() -> Path:
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    dim = json.loads((_ultimo(SILVER / "dim_jugador") / "data.json").read_text(encoding="utf-8"))
    nacionalidad = {j["jugador_id"]: j.get("nacionalidad") for j in dim}
    nombre = {j["jugador_id"]: j["nombre_canonico"] for j in dim}

    ranking_dir = _ultimo(SILVER / "fact_ranking_semanal")
    fecha_ranking = ranking_dir.name.split("=", 1)[1]
    con = duckdb.connect()
    filas_ranking = con.execute(
        f"SELECT sexo, jugador_id, posicion, puntos FROM read_parquet('{(ranking_dir / 'data.parquet').as_posix()}')"
    ).fetchall()
    puntos: dict[str, float] = {}
    for sexo in ("M", "F"):
        puntos |= interpolar_puntos(
            [{"jugador_id": j, "posicion": p, "puntos": pt} for s, j, p, pt in filas_ranking if s == sexo]
        )

    def puntos_pareja(a: str, b: str) -> float:
        return puntos.get(a, 0.0) + puntos.get(b, 0.0)

    activas: dict[str, list[float]] = {"men": [], "women": []}
    for p in json.loads(DIM_PAREJA.read_text(encoding="utf-8")):
        if p["activa"] and p["categoria"] in activas:
            activas[p["categoria"]].append(puntos_pareja(p["jugador_1_id"], p["jugador_2_id"]))
    for lista in activas.values():
        lista.sort(reverse=True)

    hoy = date.today().isoformat()
    fuente_txt = "padelapi.org / FIP · elaboración propia"
    rows: list[dict[str, Any]] = []
    for partido in partidos:
        categoria = partido.get("categoria")
        if categoria not in SEXO_POR_CATEGORIA:
            continue
        fila: dict[str, Any] = {
            "fecha_dato": hoy,
            "partido_id": partido["partido_id"],
            "fecha": partido["fecha"],
            "sexo": SEXO_POR_CATEGORIA[categoria],
            "torneo_nombre": partido.get("torneo_nombre"),
            "ronda": partido.get("ronda"),
        }
        completo = True
        for eq in (1, 2):
            j1 = (partido.get(f"equipo_{eq}_jugador_1") or {}).get("jugador_id")
            j2 = (partido.get(f"equipo_{eq}_jugador_2") or {}).get("jugador_id")
            if not j1 or not j2:
                completo = False
                break
            n1, n2 = nacionalidad.get(j1), nacionalidad.get(j2)
            pts = puntos_pareja(j1, j2)
            fila |= {
                f"pareja_{eq}_ids": sorted((j1, j2)),
                f"pareja_{eq}": f"{nombre.get(j1, j1)} / {nombre.get(j2, j2)}",
                f"pareja_{eq}_nacionalidades": [n1, n2],
                f"pareja_{eq}_tipo": clasificar(n1, n2),
                f"pareja_{eq}_puntos": round(pts, 1),
                f"pareja_{eq}_posicion_equivalente": posicion_equivalente(pts, activas[categoria]),
            }
        if not completo:
            continue
        ganador = partido.get("ganador")
        fila["ganador"] = {"team_1": 1, "team_2": 2}.get(ganador)
        motivo = None
        if fila["pareja_1_tipo"] is None or fila["pareja_2_tipo"] is None:
            motivo = "nacionalidad_desconocida"
        elif fila["ganador"] is None:
            motivo = "ganador_oculto"
        elif partido.get("marcador_incoherente"):
            motivo = "marcador_incoherente"
        fila |= {
            "cruce": {fila["pareja_1_tipo"], fila["pareja_2_tipo"]} == {"mismo_pais", "mixta"},
            "motivo_descarte": motivo,
            "fecha_ranking": fecha_ranking,
            "fuente_txt": fuente_txt,
            "publicable": motivo is None,
        }
        rows.append(fila)

    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    cruces = sum(1 for r in rows if r["cruce"] and r["publicable"])
    print(f"partidos_nacionalidad: {len(rows)} partidos, {cruces} cruces mismo país vs mixta publicables")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
