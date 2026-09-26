"""Gráfico a medida `parejas_nacionalidad` y su gold
(`transform/build_gold_partidos_nacionalidad.py`): lo que se puede
comprobar sin dibujar ni llamar a la API."""

from __future__ import annotations

import pytest

from content.chart_factory.adhoc import agrupar_tramos, etiqueta_tramo, lectura_control, wilson
from content.copy_factory.verificaciones import comprobar_control_nivel
from transform.build_gold_partidos_nacionalidad import clasificar, interpolar_puntos, posicion_equivalente


def _cruces(n: int, pos_mp: int, pos_mx: int, victorias: int) -> list[dict]:
    return [{"gana_mp": i < victorias, "pos_mp": pos_mp, "pos_mx": pos_mx} for i in range(n)]


def test_clasificar_descarta_nacionalidad_desconocida():
    assert clasificar("ES", "ES") == "mismo_pais"
    assert clasificar("ES", "AR") == "mixta"
    assert clasificar("ES", None) is None
    assert clasificar("ZZ", "ZZ") is None  # "ZZ" = desconocida en F2, no un país


def test_interpolar_puntos_por_posicion():
    filas = [
        {"jugador_id": "a", "posicion": 1, "puntos": 1000},
        {"jugador_id": "b", "posicion": 2, "puntos": None},
        {"jugador_id": "c", "posicion": 3, "puntos": 800},
        {"jugador_id": "d", "posicion": 4, "puntos": None},
    ]
    assert interpolar_puntos(filas) == {"a": 1000, "b": 900, "c": 800, "d": 800}


def test_posicion_equivalente_con_empates():
    activas = [500, 400, 400, 300]
    assert posicion_equivalente(600, activas) == 1
    assert posicion_equivalente(400, activas) == 2
    assert posicion_equivalente(350, activas) == 4


def test_tramo_solo_cuenta_partidos_con_las_dos_parejas_dentro():
    # 40 cruces top 10 vs top 10 y 40 top 10 vs 31+: el tramo top 10 tiene 40, no 80.
    cruces = _cruces(40, 5, 8, 20) + _cruces(40, 5, 50, 40) + _cruces(40, 50, 60, 20) + _cruces(40, 15, 20, 20)
    assert agrupar_tramos(cruces) == [(1, 10), (11, 30), (31, None)]


def test_tramos_pequenos_se_agrupan_o_no_hay_control():
    cruces = _cruces(10, 5, 8, 5) + _cruces(25, 15, 20, 12) + _cruces(60, 40, 50, 30)
    assert agrupar_tramos(cruces) == [(1, 30), (31, None)]  # 10 + 25 = 35 >= 30
    # Nada llega a 30 ni agrupando hasta cubrir todo el ranking: sin control.
    assert agrupar_tramos(_cruces(10, 5, 8, 5) + _cruces(10, 40, 50, 5)) == []


def test_etiqueta_tramo():
    assert [etiqueta_tramo(*t) for t in ((1, 10), (11, 30), (31, None), (1, 30))] == ["Top 10", "11–30", "31+", "Top 30"]


def test_wilson():
    bajo, alto = wilson(50, 100)
    assert bajo < 0.5 < alto
    assert wilson(80, 100)[0] > 0.5


def test_lectura_control():
    assert lectura_control((50, 100), [(15, 30)]) == "sin_efecto_global"
    assert lectura_control((400, 600), [(25, 30), (160, 200)]) == "se_mantiene"
    assert lectura_control((400, 600), [(16, 30), (100, 200)]) == "desaparece"
    assert lectura_control((400, 600), [(25, 30), (100, 200)]) == "parcial"


def test_texto_tiene_que_decir_que_desaparece_a_igual_ranking():
    values = {"control_nivel": "La diferencia desaparece al comparar parejas del mismo tramo de ranking",
              "efecto_desaparece_por_tramo": True}
    comprobar_control_nivel("Ganan el 60 %, pero dentro de cada tramo de ranking no hay diferencia", values)
    with pytest.raises(ValueError, match="desaparece"):
        comprobar_control_nivel("Las parejas del mismo país ganan el 60 %", values)
    comprobar_control_nivel("Las parejas del mismo país ganan el 60 %", {"efecto_desaparece_por_tramo": False})
