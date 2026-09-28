"""Sugerencias de alias F1 (premierpadel.com) <-> F2 (padelapi.org) para revisión manual.

build_dim_jugador cruza las dos fuentes por nombre normalizado exacto (más
`data/manual/alias_jugadores.csv`). Lo que no casa se queda como dos fichas
distintas: la de F1 sin puntos ni variación semanal en fact_ranking_semanal y
la de F2 con los partidos, así que el jugador desaparece de #RankingLunes y
sus parejas salen con 0 puntos en partidos_nacionalidad.

Doc 01 §6: el cruce aproximado es solo una sugerencia, nunca automático. Este
script no toca silver: escribe un CSV en `silver/_reconciliacion/` para que
una persona lo revise y pase lo aprobado a alias_jugadores.csv.

Evidencia que usa, para cada ficha de F1 sin cruzar:
- mismo sexo y ficha de F2 también sin cruzar;
- un nombre contiene al otro ("Delfina Brea" / "Delfina Brea Senesi"), o
  comparten un apellido y además el nombre de pila (Edu/Eduardo), un apellido
  poco frecuente ("Nacho Vilariño") o una posición parecida en el ranking
  (F1: orden de lista; F2: ranking oficial de /rankings de esa categoría).

Confianza: "alta" (candidato único con nombre de pila compatible y otra
prueba), "media" (candidato único con menos pruebas), "revisar" (varios
candidatos, o la ficha de F2 sale para varias de F1) y "sin_candidato".

    python transform/sugerir_alias_f1_f2.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_dim_jugador import (  # noqa: E402
    load_alias_overrides,
    load_f1_players,
    load_f2_players,
    normalize_name,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
F2_RANKINGS_ROOT = REPO_ROOT / "bronze" / "padelapi" / "rankings"
OUT_FILE = REPO_ROOT / "silver" / "_reconciliacion" / "sugerencias_alias_f1_f2.csv"

MAX_DIFERENCIA_POSICION = 15
# A más distancia que esto, dos fichas parecidas son más probablemente dos personas.
DIFERENCIA_POSICION_SOSPECHOSA = 300
PARTICULAS = {"de", "del", "la", "las", "los", "da", "das", "do", "dos", "di", "y", "e"}
CATEGORIA_A_SEXO = {"men": "M", "women": "F"}


def posiciones_f2() -> tuple[dict[str, int], dict[str, str]]:
    """id padelapi -> ranking oficial, del snapshot más reciente que traiga
    cada categoría (padelapi publica hombres y mujeres por separado y a veces
    el del lunes llega con una sola)."""
    posiciones: dict[str, int] = {}
    fecha: dict[str, str] = {}
    for dt_dir in sorted(F2_RANKINGS_ROOT.glob("dt=*"), reverse=True):
        items = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))["items"]
        for sexo in {CATEGORIA_A_SEXO.get(i.get("category")) for i in items} - set(fecha) - {None}:
            fecha[sexo] = dt_dir.name.removeprefix("dt=")
            for i in items:
                if CATEGORIA_A_SEXO.get(i.get("category")) == sexo and i.get("ranking"):
                    posiciones[str(i["id"])] = int(i["ranking"])
        if len(fecha) == 2:
            break
    return posiciones, fecha


def _nombre_compatible(a: list[str], b: list[str]) -> bool:
    """Mismo nombre de pila, o uno es abreviatura del otro (Edu/Eduardo)."""
    return bool(a and b) and (a[0] == b[0] or a[0].startswith(b[0]) or b[0].startswith(a[0]))


def sugerir() -> list[dict[str, Any]]:
    alias = load_alias_overrides()

    def clave(rec: dict[str, Any]) -> tuple[str, str]:
        norm = normalize_name(rec["nombre_en_fuente"])
        return normalize_name(alias.get(norm, norm)), rec["sexo"]

    f1 = load_f1_players()
    f2 = load_f2_players()
    claves_f1 = {clave(r) for r in f1}
    claves_f2 = {clave(r) for r in f2}
    solo_f1 = [r for r in f1 if clave(r) not in claves_f2]
    solo_f2 = [r for r in f2 if clave(r) not in claves_f1]

    pos_f2, _ = posiciones_f2()
    # Cuántas fichas de F2 sin cruzar llevan cada apellido: "Lancha" o
    # "Vilarino" señalan a una persona; "Sanchez" o "Hernandez", no.
    frecuencia: dict[tuple[str, str], int] = {}
    for b in solo_f2:
        for t in set(normalize_name(b["nombre_en_fuente"]).split()[1:]):
            frecuencia[(b["sexo"], t)] = frecuencia.get((b["sexo"], t), 0) + 1

    propuestas: list[tuple[dict[str, Any], list[tuple]]] = []
    for a in solo_f1:
        ta = normalize_name(a["nombre_en_fuente"]).split()
        pa = a.get("posicion_f1")
        candidatos = []
        for b in solo_f2:
            if b["sexo"] != a["sexo"]:
                continue
            tb = normalize_name(b["nombre_en_fuente"]).split()
            pb = pos_f2.get(b["id_fuente"])
            dif = abs(pa - pb) if pa and pb else None
            # Apellido con apellido: "Teresa" de "Maria Teresa Bica" no es un apellido.
            comunes = (set(ta[1:]) & set(tb[1:])) - PARTICULAS
            contenido = set(ta) <= set(tb) or set(tb) <= set(ta)
            nombre = _nombre_compatible(ta, tb)
            raro = any(frecuencia.get((a["sexo"], t), 0) == 1 for t in comunes)
            if not (contenido or (comunes and (nombre or raro or (dif is not None and dif <= MAX_DIFERENCIA_POSICION)))):
                continue
            candidatos.append((b, pb, dif, contenido, bool(comunes), nombre, raro))
        # Con un candidato del mismo nombre de pila, los que solo comparten
        # apellido sobran ("David Gala Sanchez" no es "Maxi Sanchez Blasco").
        if any(c[5] for c in candidatos):
            candidatos = [c for c in candidatos if c[5]]
        propuestas.append((a, candidatos))

    veces_f2: dict[str, int] = {}
    for _, candidatos in propuestas:
        for c in candidatos:
            veces_f2[c[0]["id_fuente"]] = veces_f2.get(c[0]["id_fuente"], 0) + 1

    filas = []
    for a, candidatos in propuestas:
        pa = a.get("posicion_f1")
        if not candidatos:
            filas.append({
                "sexo": a["sexo"], "posicion_f1": pa, "nombre_f1": a["nombre_en_fuente"],
                "nombre_f2": "", "posicion_f2": "", "confianza": "sin_candidato", "motivo": "",
            })
            continue
        unico = len(candidatos) == 1
        for b, pb, dif, contenido, apellido, nombre, raro in sorted(candidatos, key=lambda c: (c[2] is None, c[2] or 0)):
            repetido = veces_f2[b["id_fuente"]] > 1
            cerca = dif is not None and dif <= 3
            lejos = dif is not None and dif > DIFERENCIA_POSICION_SOSPECHOSA
            # Sin nombre de pila compatible ni posición, solo queda un apellido: poco.
            flojo = not nombre and dif is None
            if repetido or not unico or lejos or flojo:
                confianza = "revisar"
            elif nombre and (contenido or cerca or raro):
                confianza = "alta"
            else:
                confianza = "media"
            motivo = ", ".join(m for m, ok in (
                ("mismo nombre de pila", nombre),
                ("nombre contenido en el otro", contenido),
                ("apellido en común", apellido),
                ("apellido poco frecuente", raro),
                (f"posición a {dif}" if dif is not None else "sin posición en F2", True),
                (f"{len(candidatos)} candidatos", not unico),
                ("esta ficha de F2 sale para varias de F1", repetido),
            ) if ok)
            filas.append({
                "sexo": a["sexo"], "posicion_f1": pa, "nombre_f1": a["nombre_en_fuente"],
                "nombre_f2": b["nombre_en_fuente"], "posicion_f2": pb or "",
                "confianza": confianza, "motivo": motivo,
            })

    filas.sort(key=lambda f: (f["sexo"], f["posicion_f1"] or 10**6))
    return filas


def main() -> None:
    filas = sugerir()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]) if filas else ["sexo"])
        w.writeheader()
        w.writerows(filas)
    n_f1 = len({(f["sexo"], f["nombre_f1"]) for f in filas})
    print(f"{n_f1} fichas de F1 sin cruzar, {len(filas)} filas -> {OUT_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
