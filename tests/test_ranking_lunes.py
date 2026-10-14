"""#RankingLunes (top 10 y subidas de puntos) y campeones de la semana:
gold.ranking_semana, gold.ganadores_semana y la selección de filas de
chart_factory. Sin datos reales del repo."""

from __future__ import annotations

from datetime import date

from content.chart_factory import ranking_puntos, ranking_top10
from content.copy_factory.nombres import nombres_en_values
from transform import build_gold_ganadores_semana as gs
from transform.build_gold_ranking_semana import resultados_semana

INI, FIN = date(2026, 9, 21), date(2026, 9, 27)
SEXOS = {"a1": "M", "a2": "M", "b1": "M", "b2": "M", "f1": "F", "f2": "F", "f3": "F", "f4": "F"}
NOMBRES = {k: k.upper() for k in SEXOS}


def _j(jid: str) -> dict:
    return {"jugador_id": jid, "nombre_padelapi": jid}


def _final(categoria: str, e1: tuple[str, str], e2: tuple[str, str], ganador: str = "team_2",
           marcador: str | None = "6-4, 4-6, 1-6", fecha: str = "2026-09-27", **extra) -> dict:
    return {
        "torneo_id": "T1", "torneo_nombre": "FIP Platinum Lyon", "torneo_nivel_padelapi": "fip_platinum",
        "categoria": categoria, "ronda": "Finals", "fecha": fecha, "ganador": ganador, "marcador_txt": marcador,
        "semilla_equipo_1": 1, "semilla_equipo_2": 2,
        "equipo_1_jugador_1": _j(e1[0]), "equipo_1_jugador_2": _j(e1[1]),
        "equipo_2_jugador_1": _j(e2[0]), "equipo_2_jugador_2": _j(e2[1]),
        **extra,
    }


def _filas(partidos: list[dict], resultados: list[dict] | None = None) -> list[dict]:
    return gs.construir_filas(partidos, resultados or [], SEXOS, NOMBRES, INI, FIN)


def test_marcador_se_lee_desde_el_campeon():
    assert gs.marcador_del_campeon("6-4, 4-6, 1-6", 2) == "4-6, 6-4, 6-1"
    assert gs.marcador_del_campeon("6-1, 6-3", 1) == "6-1, 6-3"
    assert gs.marcador_del_campeon(None, 2) is None


def test_campeones_de_la_final():
    (fila,) = _filas([_final("men", ("a1", "a2"), ("b1", "b2"))])
    assert fila["publicable"]
    assert fila["campeones"] == "B1 / B2"
    assert fila["finalistas"] == "A1 / A2"
    assert fila["marcador_final"] == "4-6, 6-4, 6-1"
    assert fila["semilla_campeones"] == 2


def test_final_por_walkover_da_campeon_sin_marcador():
    (fila,) = _filas([_final("men", ("a1", "a2"), ("b1", "b2"), ganador="team_1", marcador=None, estado="walkover")])
    assert fila["publicable"]
    assert fila["campeones"] == "A1 / A2"
    assert fila["marcador_final"] == "walkover"


def test_cuadro_con_jugadoras_en_categoria_masculina_no_es_publicable():
    # FIP Silver Houten, 29/09/2026: padelapi devolvió el cuadro femenino también como masculino
    (fila,) = _filas([_final("men", ("f1", "f2"), ("f3", "f4"))])
    assert not fila["publicable"]
    assert "otra categoría" in fila["motivo_no_publicable"]


def test_sin_final_no_se_inventa_campeon():
    semifinal = {**_final("men", ("a1", "a2"), ("b1", "b2")), "ronda": "Semifinals"}
    (fila,) = _filas([semifinal])
    assert not fila["publicable"]
    assert fila["campeones"] is None


def test_ganador_oculto_usa_el_resultado_de_respaldo():
    oculto = _final("men", ("a1", "a2"), ("b1", "b2"), ganador="hidden_free_plan")
    respaldo = [{"torneo_id": "T1", "categoria_sexo": "men", "ronda_alcanzada": "W",
                 "jugador_1_id": "a1", "jugador_2_id": "a2", "fuente_resultado": "matchresults_fip"}]
    (fila,) = _filas([oculto], respaldo)
    assert fila["publicable"]
    assert fila["campeones"] == "A1 / A2"
    assert fila["fuente_resultado"] == "matchresults_fip"


def test_solo_torneos_terminados_la_semana_anterior():
    assert _filas([_final("men", ("a1", "a2"), ("b1", "b2"), fecha="2026-09-28")]) == []
    assert _filas([_final("men", ("a1", "a2"), ("b1", "b2"), fecha="2026-09-20")]) == []
    assert gs.semana_anterior(date(2026, 9, 28)) == (INI, FIN)
    assert gs.semana_anterior(date(2026, 9, 30)) == (INI, FIN)


def test_resultado_de_la_semana_es_el_de_mas_puntos():
    resultados = [
        {"jugador_1_id": "a1", "jugador_2_id": "a2", "fecha": "2026-09-27", "puntos_ganados": 300, "ronda_alcanzada": "W", "torneo_nombre": "Lyon"},
        {"jugador_1_id": "a1", "jugador_2_id": "x", "fecha": "2026-09-24", "puntos_ganados": 45, "ronda_alcanzada": "SF", "torneo_nombre": "Otro"},
        {"jugador_1_id": "b1", "jugador_2_id": "b2", "fecha": "2026-09-20", "puntos_ganados": 300, "ronda_alcanzada": "W", "torneo_nombre": "Viejo"},
    ]
    por_jugador = resultados_semana(resultados, date(2026, 9, 28))
    assert por_jugador["a1"]["torneo_nombre"] == "Lyon"
    assert "b1" not in por_jugador


def _fila_ranking(nombre: str, posicion: int, puntos: int, diff: int, sexo: str = "M") -> dict:
    return {"sexo": sexo, "jugador_id": nombre, "jugador_nombre": nombre, "posicion": posicion, "puntos": puntos,
            "puntos_diff_semana": diff, "publicable": True, "resultado_semana": None}


def test_top10_incluye_empates_en_el_puesto_10():
    filas = [_fila_ranking(f"J{i}", i, 1000 - i, 0) for i in range(1, 10)]
    filas += [_fila_ranking("J10a", 10, 500, 0), _fila_ranking("J10b", 10, 500, 0), _fila_ranking("J12", 12, 400, 0)]
    assert [r["jugador_nombre"] for r in ranking_top10.seleccionar(filas, "M")][-2:] == ["J10a", "J10b"]


def test_subidas_de_puntos_solo_positivas_y_ordenadas():
    filas = [_fila_ranking("A", 15, 3699, 207), _fila_ranking("B", 8, 6090, 90), _fila_ranking("C", 1, 20383, -71),
             _fila_ranking("D", 5, 8040, 0), _fila_ranking("E", 20, 2000, 150, sexo="F")]
    assert [r["jugador_nombre"] for r in ranking_puntos.seleccionar(filas, "M")] == ["A", "B"]


def test_campeones_numerados_son_nombres_para_la_verificacion():
    values = {"torneo_1": "FIP Platinum Lyon (masculino)", "campeones_1": "Javier Leal / Francisco Guerrero"}
    assert nombres_en_values(values) == ["Javier Leal", "Francisco Guerrero"]
