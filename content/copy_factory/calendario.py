"""Qué series toca generar cada día (doc 02 §4 y §5).

`content_candidates` corre a diario, pero cada serie tiene su día: si
generara las 11 cada mañana, la cola se llenaría de candidatos que no
tocan, se gastarían llamadas a la API y se quemarían números de registro
(correlativos, se muestran en el gráfico). Las claves son las de
`candidatos.GENERADORES_*`.

Lo que el doc deja abierto y aquí se ha decidido:
- "Pádel Mercado" es quincenal: semanas ISO pares.
- "Perfil del top 100" es mensual sin día fijo: primer viernes del mes.
- `forma_reciente` no tiene serie con nombre en el doc: viernes.
- Sábado y domingo, descanso (doc 02 §5), salvo la serie de torneo.
- Sin generador todavía: Archivo, Previa en datos, `puntos_a_defender`.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DIM_TORNEO_ROOT = REPO_ROOT / "silver" / "dim_torneo"

LUNES, MARTES, MIERCOLES, JUEVES, VIERNES = range(5)


def cargar_torneos() -> list[dict[str, Any]]:
    dirs = sorted(p for p in DIM_TORNEO_ROOT.glob("dt=*") if p.is_dir())
    if not dirs:
        return []
    return json.loads((dirs[-1] / "data.json").read_text(encoding="utf-8"))


def _fecha(valor: str | None) -> date | None:
    return date.fromisoformat(valor) if valor else None


def hay_torneo_activo(hoy: date, torneos: list[dict[str, Any]]) -> bool:
    for t in torneos:
        ini, fin = _fecha(t.get("fecha_ini")), _fecha(t.get("fecha_fin"))
        if ini and fin and ini <= hoy <= fin:
            return True
    return False


def termino_torneo_esta_semana(hoy: date, torneos: list[dict[str, Any]]) -> bool:
    """Algún torneo acabó en los 7 días anteriores (cierre del lunes)."""
    for t in torneos:
        fin = _fecha(t.get("fecha_fin"))
        if fin and hoy - timedelta(days=7) <= fin < hoy:
            return True
    return False


def series_del_dia(hoy: date, torneos: list[dict[str, Any]]) -> set[str]:
    series: set[str] = set()
    dia = hoy.weekday()

    if dia == LUNES:
        series.add("ranking_moves")
        if termino_torneo_esta_semana(hoy, torneos):
            series.add("ganancias")
    elif dia == MARTES and hoy.isocalendar().week % 2 == 0:
        series |= {"mercado", "licencias"}
    elif dia == MIERCOLES:
        series |= {"parejas", "h2h"}
    elif dia == JUEVES:
        series |= {"pistas", "trends"}
    elif dia == VIERNES:
        series.add("forma_reciente")
        if hoy.day <= 7:
            series.add("perfil")

    if hay_torneo_activo(hoy, torneos):
        series.add("sorpresas")

    return series
