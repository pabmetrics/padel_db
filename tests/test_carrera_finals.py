"""Carrera a las Premier Padel Finals (15/11/2026): corte en el 16.º del
Race, individual, y calendario de los lunes."""

from __future__ import annotations

from datetime import date

from content.copy_factory.calendario import series_del_dia
from content.copy_factory.historial import SERIES_SIN_FILTRO
from transform.build_gold_carrera_finals import PLAZAS, calcular


def _race(categoria, puntos):
    # Puntos ya ordenados; los empates comparten puesto, como en padelapi.
    items, puesto = [], 0
    for i, p in enumerate(puntos):
        if i == 0 or p != puntos[i - 1]:
            puesto = i + 1
        items.append({"id": f"{categoria}{i}", "name": f"J{i}", "category": categoria, "ranking": puesto,
                      "points": p, "points_diff": 10, "ranking_diff": 0, "date": "2026-11-09"})
    return items


def test_corte_en_el_16_y_margenes():
    puntos = [20000 - 500 * i for i in range(20)]  # 16.º = 12500, 17.º = 12000
    filas = calcular(_race("men", puntos), {f"men{i}": f"id{i}" for i in range(20)}, {})
    assert PLAZAS == 16
    assert sum(f["dentro"] for f in filas) == 16
    dieciseis, diecisiete = filas[15], filas[16]
    assert (dieciseis["dentro"], dieciseis["margen_corte"]) == (True, 500)   # le saca 500 al primero de fuera
    assert (diecisiete["dentro"], diecisiete["margen_corte"]) == (False, 500)  # le faltan 500
    assert not dieciseis["empate_en_corte"]


def test_empate_en_el_corte_se_marca():
    puntos = [20000 - 500 * i for i in range(15)] + [12500, 12500, 12000, 11000]  # dos empatados en el 16.º
    filas = calcular(_race("women", puntos), {f"women{i}": f"id{i}" for i in range(19)}, {})
    assert sum(f["dentro"] for f in filas) == 17 and filas[0]["empate_en_corte"]


def test_sin_jugador_cruzado_no_es_publicable():
    filas = calcular(_race("men", [20000 - 100 * i for i in range(20)]), {}, {})
    assert not any(f["publicable"] for f in filas)


def test_los_lunes_del_ultimo_mes_y_medio_antes_de_las_finals():
    torneos = [{"categoria": "FINALS", "fecha_ini": "2026-12-07", "fecha_fin": "2026-12-13"}]
    assert "carrera_finals" in series_del_dia(date(2026, 11, 16), torneos)      # lunes, 21 días antes
    assert "carrera_finals" not in series_del_dia(date(2026, 11, 17), torneos)  # martes
    assert "carrera_finals" not in series_del_dia(date(2026, 10, 12), torneos)  # lunes, 56 días antes
    assert "carrera_finals" not in series_del_dia(date(2026, 12, 14), torneos)  # ya jugadas
    assert "Carrera a las Finals" in SERIES_SIN_FILTRO
