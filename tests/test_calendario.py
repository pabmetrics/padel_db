"""Calendario de series de `content_candidates` (doc 02 §4 y §5)."""

from __future__ import annotations

from datetime import date

from content.copy_factory.calendario import series_del_dia

TORNEOS = [
    {"nombre": "PARIS MAJOR", "fecha_ini": "2026-09-07", "fecha_fin": "2026-09-13"},
    {"nombre": "ROTTERDAM P2", "fecha_ini": "2026-09-28", "fecha_fin": "2026-10-04"},
]


def test_lunes_sin_torneo_reciente_solo_ranking():
    assert series_del_dia(date(2026, 9, 21), TORNEOS) == {"ranking_moves"}


def test_lunes_tras_torneo_incluye_cierre():
    assert series_del_dia(date(2026, 9, 14), TORNEOS) == {"ranking_moves", "ganancias"}


def test_serie_de_torneo_solo_durante_el_torneo():
    assert "sorpresas" in series_del_dia(date(2026, 9, 30), TORNEOS)
    assert "sorpresas" not in series_del_dia(date(2026, 9, 24), TORNEOS)


def test_torneo_activo_en_fin_de_semana():
    assert series_del_dia(date(2026, 10, 3), TORNEOS) == {"sorpresas"}  # sábado


def test_fin_de_semana_sin_torneo_descansa():
    assert series_del_dia(date(2026, 9, 19), TORNEOS) == set()  # sábado
    assert series_del_dia(date(2026, 9, 20), TORNEOS) == set()  # domingo


def test_mercado_solo_semanas_iso_pares():
    assert series_del_dia(date(2026, 9, 22), []) == set()  # martes, semana 39
    assert series_del_dia(date(2026, 9, 29), []) == {"mercado", "licencias"}  # semana 40


def test_miercoles_y_jueves():
    assert series_del_dia(date(2026, 9, 23), []) == {"parejas", "h2h"}
    assert series_del_dia(date(2026, 9, 24), []) == {"pistas", "trends"}


def test_perfil_solo_el_primer_viernes_del_mes():
    assert series_del_dia(date(2026, 9, 4), []) == {"forma_reciente", "perfil"}
    assert series_del_dia(date(2026, 9, 25), []) == {"forma_reciente"}


def test_sin_calendario_de_torneos_no_falla():
    assert series_del_dia(date(2026, 9, 21), []) == {"ranking_moves"}
