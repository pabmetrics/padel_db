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
