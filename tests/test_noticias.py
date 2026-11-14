"""Noticias del día (14/11/2026): conector RSS, reconocimiento de jugadores
en titulares, tipo de noticia y elección de la historia del día. Sin red ni
API: titulares de ejemplo y jugadores de prueba."""

from __future__ import annotations

import json
from datetime import date

from content.copy_factory import noticias as nt
from ingest.noticias.rss import parsear
from transform.build_fact_noticia import claves_de_busqueda, construir, reconocer, tipo_por_palabras

TOP = [
    {"jugador_id": "tapia", "nombre": "Agustin Tapia", "sexo": "M", "posicion": 1},
    {"jugador_id": "coello", "nombre": "Arturo Coello", "sexo": "M", "posicion": 1},
    {"jugador_id": "galan", "nombre": "Alejandro Galan", "sexo": "M", "posicion": 3},
    {"jugador_id": "triay", "nombre": "Gemma Triay Pons", "sexo": "F", "posicion": 1},
    {"jugador_id": "brea", "nombre": "Delfina Brea Senesi", "sexo": "F", "posicion": 1},
    {"jugador_id": "icardo", "nombre": "Tamara Icardo Alcorisa", "sexo": "F", "posicion": 12},
    {"jugador_id": "cjensen", "nombre": "Claudia Jensen", "sexo": "F", "posicion": 12},
    {"jugador_id": "ejensen", "nombre": "Enzo Jensen", "sexo": "M", "posicion": 60},
    {"jugador_id": "asanchez", "nombre": "Ariana Sanchez Fallada", "sexo": "F", "posicion": 3},
    {"jugador_id": "psanchez", "nombre": "Pablo Sanchez", "sexo": "M", "posicion": 90},
    {"jugador_id": "pascual", "nombre": "Juan Ignacio De Pascual", "sexo": "M", "posicion": 30},
    {"jugador_id": "juan", "nombre": "Juan Lebron", "sexo": "M", "posicion": 5},
]
ALIAS = {"Ale Galán": "Alejandro Galan"}
COMPANERO = {"tapia": "coello", "coello": "tapia", "triay": "brea", "brea": "triay", "icardo": "cjensen",
             "cjensen": "icardo"}


def _nombres(titulo: str) -> list[str]:
    return [j["nombre"] for j in reconocer(titulo, claves_de_busqueda(TOP, ALIAS))]


def test_rss_quita_el_medio_del_titulo():
    xml = """<rss><channel><item><title>Tapia y Coello, a semis - Marca</title><link>https://x/1</link>
    <source url="https://marca.com">Marca</source><pubDate>Sat, 14 Nov 2026 08:00:00 GMT</pubDate></item>
    <item><title></title><link>https://x/2</link></item></channel></rss>"""
    [n] = parsear(xml, "pádel")
    assert (n["titulo"], n["medio"], n["publicada"][:10]) == ("Tapia y Coello, a semis", "Marca", "2026-11-14")


def test_reconoce_apellidos_alias_y_tildes():
    assert set(_nombres("Ale Galán cae ante Tapia")) == {"Alejandro Galan", "Agustin Tapia"}
    assert _nombres("Triay y Brea, campeonas") == ["Gemma Triay Pons", "Delfina Brea Senesi"]
    assert _nombres("De Pascual da la sorpresa") == ["Juan Ignacio De Pascual"]


def test_no_adivina_con_claves_ambiguas_ni_nombres_de_pila():
    assert _nombres("Jensen gana en Dubái") == []      # Claudia o Enzo
    assert _nombres("Sánchez a semifinales") == []      # Ariana o Pablo
    assert _nombres("Juan, el más joven del cuadro") == []  # nombre de pila suelto
    assert _nombres("Tapiador gana") == []               # palabra entera, no trozo


def test_tipo_por_palabras_salud_va_antes():
    assert tipo_por_palabras("Lebrón cae lesionado") == "salud"
    assert tipo_por_palabras("Tapia y Coello se separan") == "parejas"
    assert tipo_por_palabras("Icardo y Jensen dan la campanada") == "eliminacion"
    assert tipo_por_palabras("Triay y Brea, campeonas en Dubái") == "resultado"
    assert tipo_por_palabras("Galán habla del calendario") is None


def test_construir_descarta_salud_y_pregunta_solo_los_dudosos():
    preguntados = {}

    def clasificar(dudosos):
        preguntados.update(dudosos)
        return {k: "otro" for k in dudosos}

    filas = construir([{"titulo": "Lebrón, baja por lesión"}, {"titulo": "Galán habla del calendario"},
                       {"titulo": "El pádel crece en Alemania"}], TOP, ALIAS, clasificar)
    assert [f["usable"] for f in filas] == [False, True, False]
    assert filas[1]["tipo_origen"] == "gemini"
    assert list(preguntados.values()) == ["Galán habla del calendario"]  # ni el de salud ni el sin jugadores


def _silver(tmp_path, titulares):
    filas = construir([{"titulo": t, "enlace": f"https://x/{i}", "medio": "M"} for i, t in enumerate(titulares)],
                      TOP, ALIAS, lambda d: {})
    d = tmp_path / "silver" / "dt=2026-11-14"
    d.mkdir(parents=True)
    (d / "data.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")


def test_misma_historia_desde_dos_lados_y_con_su_pareja(tmp_path):
    _silver(tmp_path, ["Triay y Brea caen en cuartos", "Icardo da la campanada ante Triay y Brea",
                       "Ale Galán, campeón en Dubái"])
    pedidos = nt.pedidos_del_dia(date(2026, 11, 14), TOP, silver_root=tmp_path / "silver",
                                 queue_root=tmp_path / "queue", companero=COMPANERO)
    pedido, noticia = pedidos[0]
    # Dos titulares de la misma historia; Jensen entra por ser pareja de Icardo.
    assert set(pedido["jugadores"]) == {"Gemma Triay Pons", "Delfina Brea Senesi", "Tamara Icardo Alcorisa",
                                        "Claudia Jensen"}
    assert noticia["tipo"] == "eliminacion" and len(noticia["otros_titulares"]) == 1
    assert pedido["contexto"] == nt.CONTEXTO["eliminacion"]
    # Galán solo, sin pareja activa en el top: no hay comparación posible.
    assert len(pedidos) == 1


def test_no_repite_la_historia_de_dias_anteriores(tmp_path):
    _silver(tmp_path, ["Tapia y Coello, campeones en Dubái"])
    cola = tmp_path / "queue" / "2026-11-13"
    cola.mkdir(parents=True)
    (cola / "candidates.json").write_text(json.dumps([{"noticia": {"enlace": "https://otro",
                                                                   "jugador_ids": ["tapia", "coello"]}}]))
    assert nt.pedidos_del_dia(date(2026, 11, 14), TOP, silver_root=tmp_path / "silver",
                              queue_root=tmp_path / "queue", companero=COMPANERO) == []


def test_pareja_actual_es_la_del_ultimo_partido_de_premier(tmp_path):
    ruta = tmp_path / "fact_partido_stats.json"
    ruta.write_text(json.dumps([
        {"bloque": "partido", "fecha": "2026-11-12", "jugador_1_id": "icardo", "jugador_2_id": "cjensen"},
        {"bloque": "partido", "fecha": "2026-06-01", "jugador_1_id": "icardo", "jugador_2_id": "josemaria"},
        {"bloque": "set_1", "fecha": "2026-11-13", "jugador_1_id": "icardo", "jugador_2_id": "otra"},
    ]))
    actual = nt.pareja_actual(ruta)
    assert actual["icardo"] == "cjensen" and actual["cjensen"] == "icardo"
