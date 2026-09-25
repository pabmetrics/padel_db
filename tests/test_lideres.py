"""Titular de los gráficos de jugadores individuales cuando dos empatan en
cabeza (`content/chart_factory/lideres.py`): si son pareja, van los dos."""

from __future__ import annotations

import pytest

from content.chart_factory.lideres import lider
from content.copy_factory.nombres import nombres_en_values
from content.copy_factory.verificaciones import comprobar_pareja_completa


def _fila(jid: str, nombre: str, pct: float, v: int, p: int) -> dict:
    return {"jugador_id": jid, "jugador_nombre": nombre, "pct": pct, "v": v, "p": p}


TRIAY = _fila("J1", "Gemma Triay Pons", 86.7, 13, 15)
BREA = _fila("J2", "Delfina Brea Senesi", 86.7, 13, 15)
CAPARROS = _fila("J3", "Marta Caparros Maldonado", 81.8, 18, 22)
PAREJAS = {frozenset(("J1", "J2"))}


def test_lider_unico():
    l = lider([CAPARROS, _fila("J9", "Otra", 50.0, 5, 10)], "pct", "v", "p", parejas=PAREJAS)
    assert not l.es_pareja and not l.avisos
    assert l.values_nombre() == {"jugador": "Marta Caparros Maldonado"}


def test_empate_de_pareja_nombra_a_las_dos():
    l = lider([TRIAY, BREA, CAPARROS], "pct", "v", "p", parejas=PAREJAS)
    assert l.es_pareja and not l.avisos
    assert l.titular == "Gemma Triay Pons y Delfina Brea Senesi"
    assert l.values_nombre() == {"pareja": "Gemma Triay Pons / Delfina Brea Senesi"}
    assert nombres_en_values(l.values_nombre()) == ["Gemma Triay Pons", "Delfina Brea Senesi"]


def test_empate_sin_ser_pareja_avisa():
    l = lider([TRIAY, BREA, CAPARROS], "pct", "v", "p", parejas=set())
    assert not l.es_pareja
    assert l.values_nombre() == {"jugador": "Gemma Triay Pons"}
    assert l.avisos


def test_pareja_con_cifras_distintas_no_se_junta():
    # Mismo % pero distinto número de partidos: una fila no describe a las dos.
    brea_otra = {**BREA, "v": 8, "p": 9}
    l = lider([TRIAY, brea_otra], "pct", "v", "p", parejas=PAREJAS)
    assert not l.es_pareja and l.avisos


def test_texto_debe_nombrar_a_los_dos():
    values = {"pareja": "Gemma Triay Pons / Delfina Brea Senesi"}
    comprobar_pareja_completa("Gemma Triay y Delfina Brea: 13 victorias en 15 partidos.", values)
    with pytest.raises(ValueError):
        comprobar_pareja_completa("Gemma Triay Pons: 13 victorias en 15 partidos.", values)
    comprobar_pareja_completa("Cualquier texto", {"jugador": "Gemma Triay Pons"})
