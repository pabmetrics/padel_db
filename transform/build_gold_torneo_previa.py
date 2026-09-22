"""Gold: torneo_previa (doc 01 §3.3 / doc 02 "Previa en datos").

Una fila = un cruce de primera ronda del cuadro principal de un torneo
próximo, con cabezas de serie, h2h histórico entre los dos equipos y
puntos a defender de cada uno en las próximas 8 semanas (doc 01 §3.3:
"Cuadro, cabezas de serie, puntos a defender de los favoritos, h2h de los
cruces").

"Primera ronda del cuadro principal" = los cruces con `fase == "main"` y el
`ronda_num` más alto presente para ese torneo+categoría (el número de
`round` cuenta partidos, no rondas jugadas: 32 = R64, 16 = R32... 1 =
final — el valor más alto es siempre la ronda que se juega primero). Se
excluyen los `bye` (pasan de ronda sin jugar, no son un cruce real).

El h2h se calcula aquí mismo desde `fact_partido` (misma lógica de clave
que `build_gold_h2h.py`, por jugador_id) en vez de leer `gold.h2h`: esa
tabla expone las parejas por nombre, no por jugador_id, y no vale la pena
reconstruir la clave a partir de texto pudiendo partir del mismo dato
crudo. Los puntos a defender sí se reutilizan de `gold.puntos_a_defender`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_CUADRO = REPO_ROOT / "silver" / "fact_cuadro_previo" / "data.json"
FACT_PARTIDO = REPO_ROOT / "silver" / "fact_partido" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "torneo_previa"


def _mostrar(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _pareja_key(a: dict[str, Any] | None, b: dict[str, Any] | None) -> tuple[str, str] | None:
    if not a or not b or not a.get("jugador_id") or not b.get("jugador_id"):
        return None
    return tuple(sorted((a["jugador_id"], b["jugador_id"])))


def _nombre_equipo(a: dict[str, Any] | None, b: dict[str, Any] | None) -> str | None:
    if not a or not b:
        return None
    return f"{a['nombre_padelapi']} / {b['nombre_padelapi']}"


def _indice_h2h() -> dict[tuple[tuple[str, str], tuple[str, str]], dict[str, int]]:
    """(pareja_izq, pareja_der) ordenadas -> {victorias_izquierda, victorias_derecha},
    igual que build_gold_h2h.py pero solo se necesita el índice, no la tabla completa."""
    if not FACT_PARTIDO.exists():
        return {}
    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    indice: dict[tuple[tuple[str, str], tuple[str, str]], dict[str, int]] = {}
    for p in partidos:
        if p.get("ganador") not in ("team_1", "team_2"):
            continue
        pareja_1 = _pareja_key(p.get("equipo_1_jugador_1"), p.get("equipo_1_jugador_2"))
        pareja_2 = _pareja_key(p.get("equipo_2_jugador_1"), p.get("equipo_2_jugador_2"))
        if not pareja_1 or not pareja_2:
            continue
        if pareja_1 <= pareja_2:
            clave, gano_izquierda = (pareja_1, pareja_2), p["ganador"] == "team_1"
        else:
            clave, gano_izquierda = (pareja_2, pareja_1), p["ganador"] == "team_2"
        entry = indice.setdefault(clave, {"victorias_izquierda": 0, "victorias_derecha": 0, "ultimo": None})
        entry["victorias_izquierda" if gano_izquierda else "victorias_derecha"] += 1
        if entry["ultimo"] is None or p["fecha"] > entry["ultimo"]:
            entry["ultimo"] = p["fecha"]
    return indice


def _h2h_para_cruce(indice: dict[Any, dict[str, int]], pareja_1: tuple[str, str] | None, pareja_2: tuple[str, str] | None) -> dict[str, Any]:
    if not pareja_1 or not pareja_2:
        return {"victorias_equipo_1": 0, "victorias_equipo_2": 0, "total": 0, "ultimo_enfrentamiento": None}
    if pareja_1 <= pareja_2:
        clave, orden_directo = (pareja_1, pareja_2), True
    else:
        clave, orden_directo = (pareja_2, pareja_1), False
    entry = indice.get(clave)
    if entry is None:
        return {"victorias_equipo_1": 0, "victorias_equipo_2": 0, "total": 0, "ultimo_enfrentamiento": None}
    v_1 = entry["victorias_izquierda"] if orden_directo else entry["victorias_derecha"]
    v_2 = entry["victorias_derecha"] if orden_directo else entry["victorias_izquierda"]
    return {"victorias_equipo_1": v_1, "victorias_equipo_2": v_2, "total": v_1 + v_2, "ultimo_enfrentamiento": entry["ultimo"]}


def _puntos_a_defender_por_jugador() -> dict[str, int]:
    root = REPO_ROOT / "gold" / "puntos_a_defender"
    dt_dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dt_dirs:
        return {}
    filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
    return {f["jugador_id"]: f["puntos_a_defender_8sem"] for f in filas}


def _puntos_equipo(a: dict[str, Any] | None, b: dict[str, Any] | None, puntos_por_jugador: dict[str, int]) -> int:
    total = 0
    for jugador in (a, b):
        if jugador and jugador.get("jugador_id"):
            total += puntos_por_jugador.get(jugador["jugador_id"], 0)
    return total


def build() -> Path:
    if not FACT_CUADRO.exists():
        cruces_torneo: list[dict[str, Any]] = []
    else:
        cruces_torneo = json.loads(FACT_CUADRO.read_text(encoding="utf-8"))

    indice_h2h = _indice_h2h()
    puntos_por_jugador = _puntos_a_defender_por_jugador()

    # ronda más alta (== primera ronda real) por (torneo_id, categoria), solo cuadro principal
    max_ronda: dict[tuple[str, str], int] = defaultdict(int)
    for c in cruces_torneo:
        if c.get("fase") != "main" or c.get("ronda_num") is None:
            continue
        clave = (c["torneo_id"], c.get("categoria"))
        max_ronda[clave] = max(max_ronda[clave], c["ronda_num"])

    rows: list[dict[str, Any]] = []
    for c in cruces_torneo:
        if c.get("fase") != "main" or c.get("status") == "bye":
            continue
        clave = (c["torneo_id"], c.get("categoria"))
        if c.get("ronda_num") != max_ronda.get(clave):
            continue  # no es la primera ronda de este torneo/categoría

        equipo_1 = _nombre_equipo(c.get("equipo_1_jugador_1"), c.get("equipo_1_jugador_2"))
        equipo_2 = _nombre_equipo(c.get("equipo_2_jugador_1"), c.get("equipo_2_jugador_2"))
        if not equipo_1 or not equipo_2:
            continue  # cruce todavía sin resolver (p. ej. depende de la qualy)

        pareja_1 = _pareja_key(c.get("equipo_1_jugador_1"), c.get("equipo_1_jugador_2"))
        pareja_2 = _pareja_key(c.get("equipo_2_jugador_1"), c.get("equipo_2_jugador_2"))
        h2h = _h2h_para_cruce(indice_h2h, pareja_1, pareja_2)

        semilla_1, semilla_2 = c.get("semilla_equipo_1"), c.get("semilla_equipo_2")
        rows.append(
            {
                "fecha_dato": date.today().isoformat(),
                "torneo_nombre": c["torneo_nombre"],
                "torneo_nivel": c.get("torneo_nivel_padelapi"),
                "fecha_inicio_torneo": c.get("fecha_inicio_torneo"),
                "categoria": c.get("categoria"),
                "ronda_nombre": c.get("ronda_nombre"),
                "equipo_1": equipo_1,
                "equipo_1_semilla": semilla_1,
                "equipo_1_puntos_a_defender_8sem": _puntos_equipo(c.get("equipo_1_jugador_1"), c.get("equipo_1_jugador_2"), puntos_por_jugador),
                "equipo_2": equipo_2,
                "equipo_2_semilla": semilla_2,
                "equipo_2_puntos_a_defender_8sem": _puntos_equipo(c.get("equipo_2_jugador_1"), c.get("equipo_2_jugador_2"), puntos_por_jugador),
                "h2h_victorias_equipo_1": h2h["victorias_equipo_1"],
                "h2h_victorias_equipo_2": h2h["victorias_equipo_2"],
                "h2h_total": h2h["total"],
                "h2h_ultimo_enfrentamiento": h2h["ultimo_enfrentamiento"],
                "fuente_txt": f"padelapi.org · elaboración propia — {date.today().isoformat()}",
                # Historia con gancho: alguna cabeza de serie de por medio, o
                # un cruce que ya se ha dado antes. Un cruce sin semilla ni
                # historial es un dato correcto pero sin ángulo publicable.
                "publicable": semilla_1 is not None or semilla_2 is not None or h2h["total"] > 0,
            }
        )

    rows.sort(key=lambda r: (r["torneo_nombre"], r["categoria"] or "", min(r["equipo_1_semilla"] or 99, r["equipo_2_semilla"] or 99)))

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    publicables = [r for r in rows if r["publicable"]]
    print(f"torneo_previa: {len(rows)} cruces de primera ronda, {len(publicables)} publicables")
    if publicables:
        top = min(publicables, key=lambda r: min(r["equipo_1_semilla"] or 99, r["equipo_2_semilla"] or 99))
        print(f"  cruce más destacado: {top['equipo_1']} (semilla {top['equipo_1_semilla']}) vs {top['equipo_2']} (semilla {top['equipo_2_semilla']})")
    print(f"-> {_mostrar(out_file)}")
    return out_file


if __name__ == "__main__":
    build()
