"""Tests de las partes de copy_factory que no dependen de la API (doc 03
§4, regla 1: "si un texto contiene un número que no está en los datos, no
se aprueba"). La generación de texto en sí (que sí llama a la API) no se
prueba aquí.
"""

from __future__ import annotations

from content.copy_factory.copy_factory import (
    _formatear_numero_es,
    _numeros_en_texto,
    _numeros_en_values,
    _quitar_valla_markdown,
)


def test_formatear_numero_es_miles():
    assert _formatear_numero_es(310700) == "310.700"
    assert _formatear_numero_es(15) == "15"


def test_formatear_numero_es_decimal():
    assert _formatear_numero_es(27.8) == "27,8"
    assert _formatear_numero_es(4.0) == "4"


def test_numeros_en_values_incluye_miles_y_sueltos():
    numeros = _numeros_en_values({"jugador": "Agustin Tapia", "ganancias_eur": 310700, "n_torneos": 16})
    assert "310.700" in numeros
    assert "310700" in numeros
    assert "16" in numeros


def test_numeros_en_texto_extrae_formato_espanol():
    numeros = _numeros_en_texto("310.700 € en 16 torneos, +15 puestos")
    assert "310.700" in numeros
    assert "16" in numeros
    assert "15" in numeros


def test_numero_inventado_no_esta_en_values():
    values = {"delta_puestos": 15, "posicion": 99}
    numeros_validos = _numeros_en_values(values)
    numeros_texto = _numeros_en_texto("Sube +20 puestos hasta el 99")
    inventados = {n for n in numeros_texto if len(n) > 1 and n not in numeros_validos}
    assert inventados == {"20"}


def test_quitar_valla_markdown():
    assert _quitar_valla_markdown('```json\n{"x": "hola"}\n```') == '{"x": "hola"}'
    assert _quitar_valla_markdown('```\n{"x": "hola"}\n```') == '{"x": "hola"}'
    assert _quitar_valla_markdown('{"x": "hola"}') == '{"x": "hola"}'
