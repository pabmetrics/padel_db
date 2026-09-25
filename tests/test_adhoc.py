"""Gráficos a medida (`content/chart_factory/adhoc.py`): lo que se puede
comprobar sin dibujar ni llamar a la API."""

from __future__ import annotations

import pytest

from content.chart_factory.adhoc import PedidoInvalido, _comprobar_textos_del_pedido, resolver_jugadores, spearman, tramos
from content.copy_factory.nombres import nombres_en_values

DIM = [
    {"jugador_id": "J1", "nombre_canonico": "Gemma Triay Pons", "sexo": "F"},
    {"jugador_id": "J2", "nombre_canonico": "Alejandro Galan", "sexo": "M"},
    {"jugador_id": "J3", "nombre_canonico": "Javier Garrido", "sexo": "M"},
    {"jugador_id": "J4", "nombre_canonico": "Javier Garcia", "sexo": "M"},
]


def test_resolver_exacto_sin_acentos_y_subconjunto():
    ids = [f["jugador_id"] for f in resolver_jugadores(["Alejandro Galán", "Gemma Triay", "Javier Garrido"], DIM)]
    assert ids == ["J2", "J1", "J3"]


def test_resolver_ambiguo_o_desconocido_falla_con_sugerencia():
    with pytest.raises(PedidoInvalido, match="ambiguo"):
        resolver_jugadores(["Javier"], DIM)
    with pytest.raises(PedidoInvalido, match="Javier Garrido"):
        resolver_jugadores(["Javi Garrido"], DIM)


def test_tramos_juntan_extremos_pequenos_y_usan_el_dato_real():
    valores = [168, 172] + [176] * 6 + [181] * 6 + [193]
    assert tramos(valores, 5, minimo=5) == [(168, 179), (180, 193)]


def test_spearman():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1)


def test_titulo_sin_cifras_inventadas_ni_valoraciones():
    values = {"jugador_1": "Alejandro Galan", "pct_victorias_1": 90.0}
    _comprobar_textos_del_pedido("Galan, 90% en 8 semanas", "sub", "A medida", values, "padelapi.org")
    with pytest.raises(PedidoInvalido, match="cifras"):
        _comprobar_textos_del_pedido("Galan, 95%", "sub", "A medida", values, "padelapi.org")
    with pytest.raises(PedidoInvalido):
        _comprobar_textos_del_pedido("Una forma impresionante", "sub", "A medida", values, "padelapi.org")


def test_contexto_puede_nombrar_lo_que_gold_no_trae_pero_no_valorar():
    values = {"contexto": "Convocatoria de España para el Mundial 2026", "jugador_1": "Alejandro Galan"}
    _comprobar_textos_del_pedido("España llega al Mundial", "sub", "Mundial 2026", values, "padelapi.org")
    with pytest.raises(PedidoInvalido, match="contexto"):
        _comprobar_textos_del_pedido("t", "s", "A medida", {"contexto": "Una convocatoria histórica"}, "x")


def test_nombres_numerados_se_verifican():
    assert nombres_en_values({"jugador_1": "A B", "jugador_12": "C D", "pct_victorias_1": 90}) == ["A B", "C D"]


def test_apodos_por_alias_jugadores_csv():
    dim = DIM + [{"jugador_id": "J5", "nombre_canonico": "Jorge Nieto", "sexo": "M"}]
    assert [f["jugador_id"] for f in resolver_jugadores(["Coki Nieto", "ale galan"], dim)] == ["J5", "J2"]


def test_motivo_sin_fila_dice_por_que_se_descarta():
    from content.chart_factory.adhoc import _motivo_sin_fila

    solo_f1 = {"jugador_id": "J9", "nombre_canonico": "Ariana Sanchez", "en_f1": True, "en_f2": False}
    assert "alias_jugadores.csv" in _motivo_sin_fila(solo_f1, None, "forma_reciente")
    cruzada = {**solo_f1, "en_f2": True}
    assert "sin partidos" in _motivo_sin_fila(cruzada, None, "forma_reciente")
    assert "solo 2 partidos" in _motivo_sin_fila(cruzada, {"partidos_8sem": 2, "publicable": False}, "forma_reciente")


def test_alias_fusiona_fichas_de_f1_y_f2(tmp_path, monkeypatch):
    """Un alias del CSV debe dejar un solo jugador_id (el del nombre
    canónico, que es el que usa fact_partido vía map_jugador_fuente), no
    dos fichas con nombre bonito."""
    from transform import build_dim_jugador as b

    monkeypatch.setattr(b, "SILVER_ROOT", tmp_path)
    monkeypatch.setattr(b, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(b, "load_alias_overrides", lambda: {"ariana sanchez": "Ariana Sanchez Fallada"})
    monkeypatch.setattr(b, "load_f1_players", lambda: [
        {"fuente": "premierpadel", "id_fuente": "1", "nombre_en_fuente": "Ariana Sanchez", "sexo": "F", "activo": True},
        {"fuente": "premierpadel", "id_fuente": "2", "nombre_en_fuente": "Paula Josemaria", "sexo": "F", "activo": True},
    ])
    monkeypatch.setattr(b, "load_f2_players", lambda: [
        {"fuente": "padelapi", "id_fuente": "10", "nombre_en_fuente": "Ariana Sanchez Fallada", "sexo": "F"},
        {"fuente": "padelapi", "id_fuente": "20", "nombre_en_fuente": "Paula Josemaria Martin", "sexo": "F"},
    ])
    b.build()
    import json
    dim = json.loads(next(tmp_path.glob("dim_jugador/*/data.json")).read_text())
    mapa = json.loads(next(tmp_path.glob("map_jugador_fuente/*/data.json")).read_text())
    recon = json.loads(next(tmp_path.glob("_reconciliacion/*.json")).read_text())

    ariana = [f for f in dim if f["nombre_canonico"] == "Ariana Sanchez Fallada"]
    assert len(ariana) == 1 and ariana[0]["en_f1"] and ariana[0]["en_f2"]
    assert ariana[0]["jugador_id"] == b.jugador_id_for("ariana sanchez fallada", "F")
    assert {m["id_fuente"] for m in mapa if m["jugador_id"] == ariana[0]["jugador_id"]} == {"1", "10"}
    # Sin alias no se fusiona: solo se sugiere.
    assert len([f for f in dim if "Josemaria" in f["nombre_canonico"]]) == 2
    assert recon["sugerencias_alias"] == [{"alias": "Paula Josemaria", "nombre_canonico": "Paula Josemaria Martin"}]
