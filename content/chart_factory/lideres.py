"""Quién encabeza un gráfico de jugadores individuales.

Los dos miembros de una pareja juegan los mismos partidos y cobran los
mismos premios, así que en forma reciente o ganancias suelen empatar
arriba (Triay/Brea, Tapia/Coello). Nombrar solo a uno en el título y en el
texto es un titular falso: la otra mitad tiene exactamente la misma cifra.

`lider()` devuelve el titular del gráfico:

- un solo jugador arriba -> ese jugador, como siempre;
- dos empatados que forman pareja activa en `dim_pareja` y comparten
  también el resto de cifras que salen en `values` -> los dos, y `values`
  lleva `pareja: "A / B"` en vez de `jugador` (el copy_factory sabe
  entonces que la cifra es de cada uno, no la suma de los dos);
- cualquier otro empate (no son pareja, o más de dos) -> el primero, como
  hasta ahora, con un aviso para la revisión humana: no se inventa una
  relación entre jugadores que los datos no dan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIM_PAREJA = REPO_ROOT / "silver" / "dim_pareja" / "data.json"


@dataclass
class Lider:
    filas: list[dict]
    es_pareja: bool
    avisos: list[str] = field(default_factory=list)

    @property
    def fila(self) -> dict:
        """Fila de referencia para las cifras (idénticas en un empate)."""
        return self.filas[0]

    @property
    def titular(self) -> str:
        """Nombre(s) para el título del gráfico."""
        return " y ".join(r["jugador_nombre"] for r in self.filas)

    @property
    def verbo_plural(self) -> bool:
        return len(self.filas) > 1

    def values_nombre(self) -> dict[str, str]:
        """Clave de nombre para `values` del candidato."""
        if self.es_pareja:
            return {"pareja": " / ".join(r["jugador_nombre"] for r in self.filas)}
        return {"jugador": self.fila["jugador_nombre"]}


def parejas_activas(ruta: Path = DIM_PAREJA) -> set[frozenset[str]]:
    if not ruta.exists():
        return set()
    filas = json.loads(ruta.read_text(encoding="utf-8"))
    return {frozenset((r["jugador_1_id"], r["jugador_2_id"])) for r in filas if r.get("activa")}


def lider(top: list[dict], clave: str, *tambien_iguales: str, parejas: set[frozenset[str]] | None = None) -> Lider:
    """`top` en el orden del gráfico; `clave` es la cifra del titular y
    `tambien_iguales` las demás columnas que van a `values`: si difieren
    entre los dos, una sola fila no describe a ambos y no se juntan."""
    maximo = max(r[clave] for r in top)
    empatados = [r for r in top if r[clave] == maximo]
    if len(empatados) == 1:
        return Lider(empatados, es_pareja=False)

    if parejas is None:
        parejas = parejas_activas()
    a, b = empatados[0], empatados[-1]
    if (
        len(empatados) == 2
        and frozenset((a["jugador_id"], b["jugador_id"])) in parejas
        and all(a[c] == b[c] for c in tambien_iguales)
    ):
        return Lider(empatados, es_pareja=True)

    otros = ", ".join(r["jugador_nombre"] for r in empatados[1:])
    return Lider(
        empatados[:1],
        es_pareja=False,
        avisos=[
            f"empate en cabeza ({clave}={maximo}) con {otros}, sin ser pareja activa con las mismas cifras: "
            f"el titular nombra solo a {empatados[0]['jugador_nombre']}"
        ],
    )


def values_con_lider(l: Lider, cifras: dict[str, Any]) -> dict[str, Any]:
    return {**l.values_nombre(), **cifras}
