"""Ángulos nuevos (14/11/2026): gold de remontadas y matagigantes, rotación
de ángulos por hueco del calendario y empates en cabeza."""

from __future__ import annotations

from datetime import date

from content.chart_factory._barras_pareja import empatadas_en_cabeza
from content.copy_factory.candidatos import ANGULOS, GENERADORES_CON_PARAMETRO, orden_angulos
from transform.build_gold_matagigantes import calcular as calcular_matagigantes, peor_sembrada
from transform.build_gold_remontadas import calcular as calcular_remontadas, ganador_primer_set
from transform.build_gold_tercer_set import calcular as calcular_tercer_set


def _jug(i: str) -> dict:
    return {"jugador_id": i, "nombre_padelapi": i.upper()}


def _partido(a: tuple[str, str], b: tuple[str, str], ganador: str, marcador: str,
             semillas: tuple[int | None, int | None] = (None, None), fecha: str = "2026-05-01") -> dict:
    return {
        "fecha": fecha, "categoria": "men", "ganador": ganador, "marcador_txt": marcador,
        "marcador_incoherente": False,
        "equipo_1_jugador_1": _jug(a[0]), "equipo_1_jugador_2": _jug(a[1]),
        "equipo_2_jugador_1": _jug(b[0]), "equipo_2_jugador_2": _jug(b[1]),
        "semilla_equipo_1": semillas[0], "semilla_equipo_2": semillas[1],
    }


def test_ganador_primer_set():
    assert ganador_primer_set("6-4, 3-6, 7-5") == 1
    assert ganador_primer_set("6-7, 6-3, 6-2") == 2
    assert ganador_primer_set("hidden_free_plan") is None
    assert ganador_primer_set(None) is None


def test_remontadas_por_pareja_y_media_del_circuito():
    ab, cd = ("a", "b"), ("c", "d")
    partidos = [
        _partido(ab, cd, "team_1", "4-6, 6-3, 6-2"),   # ab remonta
        _partido(ab, cd, "team_2", "3-6, 6-3, 4-6"),   # ab pierde el 1.º y no remonta
        _partido(ab, cd, "team_1", "6-1, 6-1"),        # cd pierde el 1.º y no remonta
        _partido(ab, cd, "team_1", "4-6, 6-3, 6-2", fecha="2025-12-01"),  # otra temporada: fuera
    ]
    filas = {f["pareja"]: f for f in calcular_remontadas(partidos, 2026)}
    assert (filas["A / B"]["primer_set_perdido"], filas["A / B"]["remontadas"]) == (2, 1)
    assert filas["A / B"]["pct_remontada"] == 50.0
    assert (filas["C / D"]["primer_set_perdido"], filas["C / D"]["remontadas"]) == (1, 0)
    # Circuito: 3 primeros sets perdidos, 1 remontada.
    assert filas["A / B"]["pct_remontada_circuito"] == 33.3
    assert not filas["A / B"]["publicable"]  # por debajo del mínimo


def test_peor_sembrada():
    assert peor_sembrada(None, 3)       # sin semilla contra cabeza de serie
    assert peor_sembrada(8, 1)
    assert not peor_sembrada(1, 8)
    assert not peor_sembrada(4, None)   # la rival sin semilla: no es "mejor sembrada"
    assert not peor_sembrada(None, None)


def test_matagigantes_cuenta_victorias_y_partidos():
    ab, cd, ef = ("a", "b"), ("c", "d"), ("e", "f")
    partidos = [
        _partido(ab, cd, "team_1", "6-4, 6-4", semillas=(None, 2)),  # ab gana a la 2
        _partido(ab, ef, "team_2", "4-6, 4-6", semillas=(9, 1)),     # ab pierde ante la 1
        _partido(ab, ef, "team_1", "6-4, 6-4", semillas=(9, 5)),     # ab gana a la 5
        _partido(cd, ef, "team_1", "6-4, 6-4", semillas=(1, 3)),     # gana la mejor sembrada: no cuenta
    ]
    filas = {f["pareja"]: f for f in calcular_matagigantes(partidos, 2026)}
    assert (filas["A / B"]["victorias_ante_mejor_semilla"], filas["A / B"]["partidos_ante_mejor_semilla"]) == (2, 3)
    assert filas["A / B"]["mejor_semilla_eliminada"] == 2
    assert filas["E / F"]["partidos_ante_mejor_semilla"] == 1  # e/f (3) perdió ante c/d (1)
    assert "C / D" not in filas


def test_angulos_rotan_por_semana_y_existen():
    for hueco, angulos in ANGULOS.items():
        assert hueco in GENERADORES_CON_PARAMETRO
        assert all(a in GENERADORES_CON_PARAMETRO for a in angulos)
    semana_par, semana_impar = date(2026, 11, 11), date(2026, 11, 18)  # semanas ISO 46 y 47
    assert orden_angulos("parejas", semana_par) == ["parejas", "remontadas"]
    assert orden_angulos("parejas", semana_impar) == ["remontadas", "parejas"]
    assert orden_angulos("ganadores", semana_par) == ["ganadores"]  # sin ángulos: la serie tal cual


def test_parametros_masculino_primero():
    # El bucle de ángulos recorre el parámetro por posición: 0 = masculino.
    for _, (_, valores) in GENERADORES_CON_PARAMETRO.items():
        assert valores[0] in ("M", "men") and valores[1] in ("F", "women")


def test_empatadas_en_cabeza():
    assert empatadas_en_cabeza([{"v": 7}, {"v": 7}, {"v": 5}], lambda r: r["v"]) == 2
    assert empatadas_en_cabeza([{"v": 9}, {"v": 7}], lambda r: r["v"]) == 1


def test_tercer_set_solo_partidos_a_tres_sets():
    ab, cd = ("a", "b"), ("c", "d")
    partidos = [
        _partido(ab, cd, "team_1", "4-6, 6-3, 6-2"),
        _partido(ab, cd, "team_2", "6-3, 3-6, 4-6"),
        _partido(ab, cd, "team_1", "6-1, 6-1"),  # dos sets: no cuenta
    ]
    filas = {f["pareja"]: f for f in calcular_tercer_set(partidos, 2026)}
    assert (filas["A / B"]["terceros_sets"], filas["A / B"]["terceros_sets_ganados"]) == (2, 1)
    assert (filas["C / D"]["terceros_sets"], filas["C / D"]["terceros_sets_ganados"]) == (2, 1)
