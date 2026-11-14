"""Memoria de la cola: no repetir protagonista ni dato (14/11/2026).

Cada serie elige la fila extrema de una métrica que cambia despacio (la
pareja más longeva, el cruce más repetido, el mejor % de victorias), así
que semana tras semana salía el mismo protagonista con el mismo dato: el
cara a cara del 4/11 y el del 11/11 eran idénticos (8-1 y 5-6), y la misma
sorpresa de Milano P1 salió cinco días seguidos. Un candidato repetido no
llega a la cola: mejor un día sin ese gráfico que proponer otra vez lo
mismo.

Un candidato repite a otro anterior del mismo circuito si:
- es de la misma serie, de los últimos `DIAS_SIN_REPETIR` días, y comparten
  algún protagonista (jugador, pareja o país) o tienen los mismos `values`;
- o es de otra serie con filtro, de los últimos `DIAS_OTRA_SERIE` días, y
  comparten protagonista: que la misma pareja no encabece dos días seguidos
  con dos datos distintos.

No se filtran las series que son noticia de la semana por definición
(ranking del lunes, campeones, cierre y previa de torneo), donde repetir
líder es el dato, ni los gráficos a medida (los pide una persona).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_ROOT = REPO_ROOT / "queue"

DIAS_SIN_REPETIR = 28
DIAS_OTRA_SERIE = 2  # con 7, Tapia/Coello y Triay/Brea (líderes de casi todo) vaciaban la semana
SERIES_SIN_FILTRO = {
    "#RankingLunes",
    "Campeones de la semana",
    "Cierre de torneo",
    "Previa en datos",
    "Carrera a las Finals",
}
CLAVES_PROTAGONISTA = (
    "jugador", "pareja", "jugador_1", "jugador_2", "pareja_1", "pareja_2",
    "equipo_ganador", "equipo_perdedor", "pais",
)


def _normalizar(nombre: str) -> str:
    return " ".join(unidecode(nombre).lower().split())


def protagonistas(values: dict[str, Any]) -> set[str]:
    """Jugadores (sueltos, aunque vengan en pareja "A / B") y países."""
    nombres: set[str] = set()
    for clave in CLAVES_PROTAGONISTA:
        valor = values.get(clave)
        if isinstance(valor, str) and valor.strip():
            nombres |= {_normalizar(parte) for parte in valor.split(" / ") if parte.strip()}
    return nombres


def _candidatos_recientes(hoy: date, dias: int, queue_root: Path) -> list[tuple[str, dict[str, Any]]]:
    """(fecha de la cola, candidato) de los últimos `dias` días."""
    desde = hoy - timedelta(days=dias)
    recientes: list[tuple[str, dict[str, Any]]] = []
    for fichero in queue_root.glob("*/candidates.json"):
        try:
            fecha = date.fromisoformat(fichero.parent.name)
        except ValueError:
            continue
        if desde <= fecha <= hoy:
            recientes += [(fecha.isoformat(), c) for c in json.loads(fichero.read_text(encoding="utf-8"))]
    return recientes


def candidato_repetido(
    serie: str,
    values: dict[str, Any],
    hoy: date,
    *,
    dias: int = DIAS_SIN_REPETIR,
    queue_root: Path = QUEUE_ROOT,
) -> dict[str, Any] | None:
    """El candidato anterior al que repite este, o None si es nuevo."""
    if serie in SERIES_SIN_FILTRO:
        return None
    mios = protagonistas(values)
    otra_serie_desde = (hoy - timedelta(days=DIAS_OTRA_SERIE)).isoformat()
    for fecha, anterior in _candidatos_recientes(hoy, dias, queue_root):
        if "pedido" in anterior or anterior.get("serie") in SERIES_SIN_FILTRO:
            continue
        previos = anterior.get("values") or {}
        if previos.get("circuito") != values.get("circuito"):
            continue
        comparten = bool(mios & protagonistas(previos))
        if anterior.get("serie") == serie:
            if previos == values or comparten:
                return anterior
        elif comparten and fecha >= otra_serie_desde:
            return anterior
    return None
