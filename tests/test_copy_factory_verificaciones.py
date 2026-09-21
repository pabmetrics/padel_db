"""Comprobaciones del texto de copy_factory y verificación de nombres, sin
llamar a la API. Los casos malos son los que salieron en la primera cola
real (21/09/2026)."""

from __future__ import annotations

import pytest

from content.copy_factory import nombres, verificaciones
from content.copy_factory.copy_factory import _validar_y_ensamblar

VALUES = {"jugador": "Maria Laura Ferreyra", "delta_puestos": 3, "posicion": 83, "circuito": "femenino"}
FUENTE = "FIP / Premier Padel · padelapi.org · elaboración propia — 2026-09-21"
SERIE = "#RankingLunes"


def _ok(cuerpo_x: str, cuerpo_ig: str = "Maria Laura Ferreyra sube 3 puestos.", hashtags: str = "#padel #PadelDB"):
    return _validar_y_ensamblar({"x": cuerpo_x, "instagram": cuerpo_ig, "hashtags": hashtags}, SERIE, VALUES, FUENTE)


def test_texto_correcto_pasa_y_lleva_fuente_ensamblada():
    salida = _ok("📈 Maria Laura Ferreyra sube 3 puestos: ya es 83 en el ranking femenino.")
    assert salida["x"].endswith(f"Fuente: {FUENTE}")
    assert salida["instagram"].endswith("#padel #PadelDB")
    assert f"Fuente: {FUENTE}" in salida["instagram"]


@pytest.mark.parametrize(
    "cuerpo",
    [
        "Maria Laura Ferreyra sube 3 puestos. Movimiento destacado de la jugadora argentina.",  # valorativo + nacionalidad
        "Maria Laura Ferreyra sube 3 puestos, lo que refleja su desempeño.",  # especulación
        "Maria Laura Ferreyra sube 3 puestos en el ranking mundial.",  # 'mundial' no está en los datos
        "Maria Laura Ferreyra sube 3 puestos. ¡Comenta qué te parece!",  # interacción
        "Maria Laura Ferreyra sube 3 puestos. Fuente: FIP",  # la fuente la pone el sistema
        "Maria Laura Ferreyra sube 4 puestos.",  # cifra inventada
        "📈 Maria Laura Ferreyra sube 3 puestos 🎾",  # dos emojis
        "Sube 3 puestos 📈 Maria Laura Ferreyra",  # emoji no al inicio
        "María Laura Ferreyra sube 3 puestos.",  # grafía del nombre alterada
    ],
)
def test_textos_que_deben_rechazarse(cuerpo):
    with pytest.raises(ValueError):
        _ok(cuerpo)


def test_hashtags_invalidos():
    with pytest.raises(ValueError):
        _ok("Maria Laura Ferreyra sube 3 puestos.", hashtags="#a #b #c #d")


def test_texto_de_x_por_encima_del_limite():
    with pytest.raises(ValueError):
        _ok("Maria Laura Ferreyra sube 3 puestos. " + "x" * 200)


def test_gentilicio_permitido_si_los_datos_traen_el_pais():
    values = {"pais": "España", "n_jugadores": 27, "circuito": "masculino"}
    verificaciones.comprobar_lexico("27 jugadores españoles en el top 100", "Perfil del top 100", values, FUENTE)


def test_mundial_permitido_solo_en_series_de_mercado():
    verificaciones.comprobar_lexico("77.355 pistas en el mundo, dato mundial", "Pádel Mercado", {"pistas_fip": 77355}, FUENTE)
    with pytest.raises(ValueError):
        verificaciones.comprobar_lexico("ranking mundial", SERIE, VALUES, FUENTE)


def test_particulas_de_apellido_no_dan_falso_positivo():
    values = {"jugador_1": "Youp De Kroon", "jugador_2": "Julian Prins"}
    verificaciones.comprobar_grafia_nombres("Youp de Kroon y Julian Prins", values)


def test_palabra_de_los_datos_no_se_marca_como_invencion():
    # 'seguramente' no es un dato, pero una palabra que ya está en los datos sí es legítima.
    values = {"torneo": "Historic Open", "jugador": "Ana Perez"}
    verificaciones.comprobar_lexico("Ana Perez gana el Historic Open", SERIE, values, FUENTE)


@pytest.fixture
def silver_falso(tmp_path, monkeypatch):
    import json

    d = tmp_path / "dt=2026-09-21"
    d.mkdir()
    filas = [
        {"fuente": "premierpadel", "id_fuente": "1", "nombre_en_fuente": "Juan Zamorà Perez", "jugador_id": "J1", "vigente": True},
        {"fuente": "padelapi", "id_fuente": "2", "nombre_en_fuente": "Juan Zamora Perez", "jugador_id": "J1", "vigente": True},
        {"fuente": "premierpadel", "id_fuente": "3", "nombre_en_fuente": "Ana Perez", "jugador_id": "J2", "vigente": True},
        {"fuente": "padelapi", "id_fuente": "4", "nombre_en_fuente": "Ana Perez", "jugador_id": "J2", "vigente": True},
        {"fuente": "padelapi", "id_fuente": "5", "nombre_en_fuente": "Solo Uno", "jugador_id": "J3", "vigente": True},
    ]
    (d / "data.json").write_text(json.dumps(filas), encoding="utf-8")
    monkeypatch.setattr(nombres, "MAP_JUGADOR_ROOT", tmp_path)
    monkeypatch.setattr(nombres, "ALIAS_CSV", tmp_path / "no_existe.csv")


def test_nombre_con_grafia_discrepante_bloquea(silver_falso):
    avisos, bloquea = nombres.verificar_nombres({"jugador": "Juan Zamorà Perez"})
    assert bloquea and "alias_jugadores.csv" in avisos[0]


def test_nombre_coincidente_en_dos_fuentes_pasa(silver_falso):
    assert nombres.verificar_nombres({"jugador": "Ana Perez"}) == ([], False)


def test_nombre_de_una_sola_fuente_avisa_sin_bloquear(silver_falso):
    avisos, bloquea = nombres.verificar_nombres({"jugador": "Solo Uno"})
    assert avisos and not bloquea


def test_nombre_desconocido_bloquea(silver_falso):
    assert nombres.verificar_nombres({"jugador": "Nadie Conocido"})[1] is True


def test_pareja_se_verifica_nombre_a_nombre(silver_falso):
    avisos, bloquea = nombres.verificar_nombres({"pareja_1": "Ana Perez / Juan Zamora Perez"})
    assert bloquea


def test_alias_del_csv_resuelve_la_discrepancia(silver_falso, tmp_path, monkeypatch):
    csv_ = tmp_path / "alias.csv"
    csv_.write_text("alias,nombre_canonico\nJuan Zamorà Perez,Juan Zamora Perez\n", encoding="utf-8")
    monkeypatch.setattr(nombres, "ALIAS_CSV", csv_)
    values = nombres.normalizar_nombres({"pareja_1": "Ana Perez / Juan Zamorà Perez"})
    assert values["pareja_1"] == "Ana Perez / Juan Zamora Perez"
    assert nombres.verificar_nombres(values) == ([], False)
