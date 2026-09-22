"""Tests de gold.torneo_previa (doc 01 §3.3): selección de la primera
ronda real del cuadro principal, h2h calculado desde fact_partido, y
puntos a defender agregados por equipo. Aislados con tmp_path/monkeypatch,
sin depender de los datos reales del repo (mismo patrón que
tests/test_rendimiento.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from transform import build_gold_torneo_previa as tp


def _jugador(id_fuente: int, nombre: str, jugador_id: str) -> dict:
    return {"jugador_id": jugador_id, "id_padelapi": id_fuente, "nombre_padelapi": nombre, "lado_pista": None}


def _cruce(**kwargs) -> dict:
    base = {
        "cruce_id": "MC1",
        "torneo_id": "T2abc",
        "torneo_nombre": "Rotterdam P2 2026",
        "torneo_nivel_padelapi": "p2",
        "fecha_inicio_torneo": "2026-09-28",
        "categoria": "men",
        "fase": "main",
        "ronda_num": 16,
        "ronda_nombre": "Round of 32",
        "status": "pending",
        "equipo_1_jugador_1": None,
        "equipo_1_jugador_2": None,
        "equipo_2_jugador_1": None,
        "equipo_2_jugador_2": None,
        "semilla_equipo_1": None,
        "semilla_equipo_2": None,
        "fuente_txt": "padelapi.org · elaboración propia",
    }
    base.update(kwargs)
    return base


def test_solo_toma_la_ronda_mas_alta_del_cuadro_principal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a1, a2 = _jugador(1, "A Uno", "j1"), _jugador(2, "A Dos", "j2")
    b1, b2 = _jugador(3, "B Uno", "j3"), _jugador(4, "B Dos", "j4")
    c1, c2 = _jugador(5, "C Uno", "j5"), _jugador(6, "C Dos", "j6")
    d1, d2 = _jugador(7, "D Uno", "j7"), _jugador(8, "D Dos", "j8")

    cruces = [
        # ronda 16 (primera ronda real, más partidos)
        _cruce(cruce_id="MC1", ronda_num=16, equipo_1_jugador_1=a1, equipo_1_jugador_2=a2,
               equipo_2_jugador_1=b1, equipo_2_jugador_2=b2, semilla_equipo_2=3),
        # ronda 8 (segunda ronda, no debe aparecer)
        _cruce(cruce_id="MC2", ronda_num=8, ronda_nombre="Round of 16",
               equipo_1_jugador_1=c1, equipo_1_jugador_2=c2, equipo_2_jugador_1=d1, equipo_2_jugador_2=d2),
        # bye en primera ronda: no es un cruce real
        _cruce(cruce_id="MC3", ronda_num=16, status="bye", equipo_1_jugador_1=c1, equipo_1_jugador_2=c2),
    ]

    fact_cuadro = tmp_path / "fact_cuadro_previo.json"
    fact_cuadro.write_text(json.dumps(cruces), encoding="utf-8")
    fact_partido = tmp_path / "fact_partido.json"
    fact_partido.write_text(json.dumps([]), encoding="utf-8")
    gold_root = tmp_path / "gold" / "torneo_previa"

    monkeypatch.setattr(tp, "FACT_CUADRO", fact_cuadro)
    monkeypatch.setattr(tp, "FACT_PARTIDO", fact_partido)
    monkeypatch.setattr(tp, "GOLD_ROOT", gold_root)
    monkeypatch.setattr(tp, "_puntos_a_defender_por_jugador", lambda: {})

    out_file = tp.build()
    rows = json.loads(out_file.read_text(encoding="utf-8"))

    assert len(rows) == 1
    assert rows[0]["ronda_nombre"] == "Round of 32"
    assert rows[0]["equipo_1"] == "A Uno / A Dos"
    assert rows[0]["equipo_2_semilla"] == 3
    assert rows[0]["publicable"] is True  # tiene semilla


def test_h2h_se_calcula_desde_fact_partido(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a1, a2 = _jugador(1, "A Uno", "j1"), _jugador(2, "A Dos", "j2")
    b1, b2 = _jugador(3, "B Uno", "j3"), _jugador(4, "B Dos", "j4")

    cruces = [_cruce(equipo_1_jugador_1=a1, equipo_1_jugador_2=a2, equipo_2_jugador_1=b1, equipo_2_jugador_2=b2)]

    partidos = [
        {
            "ganador": "team_1",
            "fecha": "2026-05-01",
            "equipo_1_jugador_1": a1, "equipo_1_jugador_2": a2,
            "equipo_2_jugador_1": b1, "equipo_2_jugador_2": b2,
        },
        {
            "ganador": "team_1",
            "fecha": "2026-06-01",
            # mismo cruce, en el orden inverso y ganando el otro lado esta vez:
            # debe seguir contando para el mismo par, con el resultado correcto
            "equipo_1_jugador_1": b1, "equipo_1_jugador_2": b2,
            "equipo_2_jugador_1": a1, "equipo_2_jugador_2": a2,
        },
    ]

    fact_cuadro = tmp_path / "fact_cuadro_previo.json"
    fact_cuadro.write_text(json.dumps(cruces), encoding="utf-8")
    fact_partido = tmp_path / "fact_partido.json"
    fact_partido.write_text(json.dumps(partidos), encoding="utf-8")
    gold_root = tmp_path / "gold" / "torneo_previa"

    monkeypatch.setattr(tp, "FACT_CUADRO", fact_cuadro)
    monkeypatch.setattr(tp, "FACT_PARTIDO", fact_partido)
    monkeypatch.setattr(tp, "GOLD_ROOT", gold_root)
    monkeypatch.setattr(tp, "_puntos_a_defender_por_jugador", lambda: {})

    out_file = tp.build()
    rows = json.loads(out_file.read_text(encoding="utf-8"))

    assert len(rows) == 1
    r = rows[0]
    assert r["h2h_total"] == 2
    assert r["h2h_victorias_equipo_1"] == 1
    assert r["h2h_victorias_equipo_2"] == 1
    assert r["h2h_ultimo_enfrentamiento"] == "2026-06-01"
    assert r["publicable"] is True  # sin semilla pero con h2h


def test_puntos_a_defender_se_suman_por_equipo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a1, a2 = _jugador(1, "A Uno", "j1"), _jugador(2, "A Dos", "j2")
    b1, b2 = _jugador(3, "B Uno", "j3"), _jugador(4, "B Dos", "j4")
    cruces = [_cruce(equipo_1_jugador_1=a1, equipo_1_jugador_2=a2, equipo_2_jugador_1=b1, equipo_2_jugador_2=b2)]

    fact_cuadro = tmp_path / "fact_cuadro_previo.json"
    fact_cuadro.write_text(json.dumps(cruces), encoding="utf-8")
    fact_partido = tmp_path / "fact_partido.json"
    fact_partido.write_text(json.dumps([]), encoding="utf-8")
    gold_root = tmp_path / "gold" / "torneo_previa"

    monkeypatch.setattr(tp, "FACT_CUADRO", fact_cuadro)
    monkeypatch.setattr(tp, "FACT_PARTIDO", fact_partido)
    monkeypatch.setattr(tp, "GOLD_ROOT", gold_root)
    monkeypatch.setattr(tp, "_puntos_a_defender_por_jugador", lambda: {"j1": 500, "j2": 300, "j3": 100})

    out_file = tp.build()
    rows = json.loads(out_file.read_text(encoding="utf-8"))

    assert rows[0]["equipo_1_puntos_a_defender_8sem"] == 800
    assert rows[0]["equipo_2_puntos_a_defender_8sem"] == 100  # j4 sin datos, cuenta como 0


def test_cruce_sin_equipo_resuelto_se_descarta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un hueco de qualy (equipo_2 todavía sin jugadores asignados) no debe
    generar una fila a medias."""
    a1, a2 = _jugador(1, "A Uno", "j1"), _jugador(2, "A Dos", "j2")
    cruces = [_cruce(equipo_1_jugador_1=a1, equipo_1_jugador_2=a2)]  # equipo_2 vacío

    fact_cuadro = tmp_path / "fact_cuadro_previo.json"
    fact_cuadro.write_text(json.dumps(cruces), encoding="utf-8")
    fact_partido = tmp_path / "fact_partido.json"
    fact_partido.write_text(json.dumps([]), encoding="utf-8")
    gold_root = tmp_path / "gold" / "torneo_previa"

    monkeypatch.setattr(tp, "FACT_CUADRO", fact_cuadro)
    monkeypatch.setattr(tp, "FACT_PARTIDO", fact_partido)
    monkeypatch.setattr(tp, "GOLD_ROOT", gold_root)
    monkeypatch.setattr(tp, "_puntos_a_defender_por_jugador", lambda: {})

    out_file = tp.build()
    rows = json.loads(out_file.read_text(encoding="utf-8"))
    assert rows == []
