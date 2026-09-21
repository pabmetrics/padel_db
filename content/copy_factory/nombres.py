"""Nombres de jugadores en los candidatos (CLAUDE.md: "usar siempre
`data/manual/alias_jugadores.csv` como fuente de la grafía correcta").

Dos cosas, las dos antes de llamar a la API:

1. `normalizar_nombres`: sustituye cada alias del CSV por su nombre
   canónico, también dentro de las parejas ("A / B").
2. `verificar_nombres`: comprueba cada nombre contra `map_jugador_fuente`
   (silver). Si F1 y F2 escriben distinto al mismo jugador ("Zamorà" /
   "Zamora") y el CSV no dice cuál es la grafía buena, el candidato queda
   no publicable hasta que una persona lo resuelva en el CSV. Si el
   jugador solo está en una fuente no hay con qué contrastar: aviso, sin
   bloquear.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ALIAS_CSV = REPO_ROOT / "data" / "manual" / "alias_jugadores.csv"
MAP_JUGADOR_ROOT = REPO_ROOT / "silver" / "map_jugador_fuente"

# Claves de `values` que contienen nombres de jugadores; las parejas van
# como "Nombre Apellido / Nombre Apellido".
CLAVES_NOMBRE = ("jugador", "jugador_1", "jugador_2", "pareja_1", "pareja_2", "equipo_ganador", "equipo_perdedor")
SEPARADOR_PAREJA = " / "


def cargar_alias() -> dict[str, str]:
    """alias -> nombre_canonico."""
    if not ALIAS_CSV.exists():
        return {}
    with ALIAS_CSV.open(encoding="utf-8") as f:
        return {
            row["alias"]: row["nombre_canonico"]
            for row in csv.DictReader(f)
            if row.get("alias") and row.get("nombre_canonico")
        }


def _nombres_de(valor: str) -> list[str]:
    return [p.strip() for p in valor.split(SEPARADOR_PAREJA) if p.strip()]


def nombres_en_values(values: dict[str, Any]) -> list[str]:
    """Nombres individuales de `values`, sin repetidos y en orden de aparición."""
    vistos: dict[str, None] = {}
    for clave in CLAVES_NOMBRE:
        valor = values.get(clave)
        if isinstance(valor, str):
            for nombre in _nombres_de(valor):
                vistos.setdefault(nombre)
    return list(vistos)


def normalizar_nombres(values: dict[str, Any]) -> dict[str, Any]:
    alias = cargar_alias()
    if not alias:
        return values
    salida = dict(values)
    for clave in CLAVES_NOMBRE:
        valor = values.get(clave)
        if isinstance(valor, str):
            salida[clave] = SEPARADOR_PAREJA.join(alias.get(n, n) for n in _nombres_de(valor))
    return salida


def _grafias_por_jugador() -> tuple[dict[str, str], dict[str, tuple[set[str], set[str]]]]:
    """(grafía -> jugador_id, jugador_id -> (grafías, fuentes)) del último silver."""
    dirs = sorted(p for p in MAP_JUGADOR_ROOT.glob("dt=*") if p.is_dir())
    if not dirs:
        return {}, {}
    filas = json.loads((dirs[-1] / "data.json").read_text(encoding="utf-8"))
    por_grafia: dict[str, str] = {}
    por_jugador: dict[str, tuple[set[str], set[str]]] = {}
    for fila in filas:
        grafias, fuentes = por_jugador.setdefault(fila["jugador_id"], (set(), set()))
        grafias.add(fila["nombre_en_fuente"])
        fuentes.add(fila["fuente"])
        por_grafia[fila["nombre_en_fuente"]] = fila["jugador_id"]
    return por_grafia, por_jugador


def verificar_nombres(values: dict[str, Any]) -> tuple[list[str], bool]:
    """(avisos, bloquea). `bloquea` = hay un nombre cuya grafía no se puede
    dar por buena y el candidato no debe pasar a texto."""
    nombres = nombres_en_values(values)
    if not nombres:
        return [], False

    canonicos = set(cargar_alias().values())
    por_grafia, por_jugador = _grafias_por_jugador()

    avisos: list[str] = []
    bloquea = False
    for nombre in nombres:
        if nombre in canonicos:
            continue
        jugador_id = por_grafia.get(nombre)
        if jugador_id is None:
            avisos.append(f"nombre no encontrado en map_jugador_fuente: {nombre!r}")
            bloquea = True
            continue
        grafias, fuentes = por_jugador[jugador_id]
        if len(grafias) > 1:
            variantes = " | ".join(sorted(grafias))
            avisos.append(
                f"grafía discrepante entre fuentes ({variantes}); "
                "fijar la buena en data/manual/alias_jugadores.csv (alias,nombre_canonico)"
            )
            bloquea = True
        elif len(fuentes) < 2:
            avisos.append(f"{nombre!r} solo aparece en una fuente ({next(iter(fuentes))}): grafía sin contrastar")
    return avisos, bloquea
