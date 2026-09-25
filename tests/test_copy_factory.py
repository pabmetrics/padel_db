"""Tests de las partes de copy_factory que no dependen de la API (doc 03
§4, regla 1: "si un texto contiene un número que no está en los datos, no
se aprueba"). La generación de texto en sí (que sí llama a la API) no se
prueba aquí.
"""

from __future__ import annotations

import json

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


def test_candidato_va_a_la_cola_de_hoy_con_png_fijo(tmp_path, monkeypatch):
    """El candidato va a `queue/<fecha_cola>/`, no a `queue/<fecha_dato>/`
    (si no, `cola/hoy.json` sale vacío), y su PNG es una copia con el
    registro delante que el siguiente dibujo de la serie no pisa."""
    from content.copy_factory import candidatos, cola

    queue_root = tmp_path / "queue"
    monkeypatch.setattr(cola, "QUEUE_ROOT", queue_root)
    monkeypatch.setattr(candidatos, "QUEUE_ROOT", queue_root)
    monkeypatch.setattr(candidatos, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(candidatos, "generar_texto", lambda *a: {"x": "x", "instagram": "ig"})

    dibujado = {}
    for sufijo in ("16x9", "4x5"):
        png = queue_root / "2026-09-21" / f"forma_reciente_f_{sufijo}.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        png.write_bytes(b"original")
        dibujado[sufijo] = png

    out_file = candidatos._escribir_candidato({
        "registro": "#0101", "serie": "Forma reciente", "tabla_gold": "forma_reciente",
        "fecha_dato": "2026-09-21", "values": {"partidos": 15}, "fuente_txt": "padelapi.org",
        "png_16x9": dibujado["16x9"], "png_4x5": dibujado["4x5"],
    }, "2026-09-25")

    assert out_file == queue_root / "2026-09-25" / "candidates.json"
    c = json.loads(out_file.read_text(encoding="utf-8"))[0]
    assert c["png_16x9"] == "queue/2026-09-25/0101_forma_reciente_f_16x9.png"
    assert c["fecha_dato"] == "2026-09-21"

    dibujado["16x9"].write_bytes(b"siguiente dibujo")
    assert (tmp_path / c["png_16x9"]).read_bytes() == b"original"


def test_numeros_en_values_acepta_el_redondeo_del_grafico():
    numeros = _numeros_en_values({"pct_victorias": 69.2, "ganancias_eur": 310700.4})
    assert {"69,2", "69", "310.700"} <= numeros
    assert "70" not in numeros
