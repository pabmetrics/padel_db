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


def test_misma_historia_con_su_pareja_y_cara_a_cara(tmp_path):
    _silver(tmp_path, ["Icardo da la campanada ante Triay y Brea", "Icardo y Jensen eliminan a Triay y Brea",
                       "Triay cae en cuartos", "Ale Galán, campeón en Dubái"])
    pedidos = nt.pedidos_del_dia(date(2026, 11, 14), TOP, silver_root=tmp_path / "silver",
                                 queue_root=tmp_path / "queue", companero=COMPANERO)
    (h2h, forma), noticia = pedidos[0]
    # Dos titulares de la misma historia (Jensen entra por ser pareja de
    # Icardo); como son dos parejas, primero se intenta su cara a cara.
    assert h2h["tipo"] == "h2h"
    assert {frozenset(h2h["pareja_1"]), frozenset(h2h["pareja_2"])} == {
        frozenset({"Gemma Triay Pons", "Delfina Brea Senesi"}), frozenset({"Tamara Icardo Alcorisa", "Claudia Jensen"})}
    assert set(forma["jugadores"]) == {"Gemma Triay Pons", "Delfina Brea Senesi", "Tamara Icardo Alcorisa",
                                       "Claudia Jensen"}
    assert noticia["tipo"] == "eliminacion" and len(noticia["otros_titulares"]) == 1
    assert h2h["contexto"] == forma["contexto"] == nt.CONTEXTO["eliminacion"]
    # "Triay cae" es otra historia (solo Triay/Brea), no se mezcla con la anterior;
    # Galán solo, sin pareja en el top, no da para un gráfico.
    assert [p[0]["jugadores"] for p, _ in pedidos[1:]] == [["Gemma Triay Pons", "Delfina Brea Senesi"]]


def test_no_mezcla_categorias_ni_resumenes_de_jornada():
    jug = {j["jugador_id"]: j for j in TOP}
    # Hombres y una mujer: se quedan los hombres.
    assert [j["nombre"] for j in nt.una_categoria([jug["tapia"], jug["triay"], jug["coello"]])] == [
        "Agustin Tapia", "Arturo Coello"]
    # Tres parejas en un titular: resumen de jornada, no historia.
    noticias = [{"titulo": "x", "enlace": "e", "tipo": "resultado",
                 "jugadores": [jug[i] for i in ("tapia", "galan", "juan")]}]
    companero = {"tapia": "coello", "galan": "pascual", "juan": "psanchez"}
    assert nt.historias(noticias, jug, companero) == []


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


def test_partidos_entre_dos_parejas_sin_duplicar_y_desde_la_pareja_1():
    from content.chart_factory.adhoc import partidos_entre

    def jug(i):
        return {"jugador_id": i}
    p1, p2 = frozenset({"a", "b"}), frozenset({"c", "d"})
    f2 = [  # padelapi: la pareja 1 juega de equipo 2
        {"fecha": "2026-07-01", "torneo_nombre": "Bordeaux P2 2026", "ronda": "Finals", "ganador": "team_2",
         "marcador_txt": "6-3, 1-6, 1-6", "equipo_1_jugador_1": jug("c"), "equipo_1_jugador_2": jug("d"),
         "equipo_2_jugador_1": jug("a"), "equipo_2_jugador_2": jug("b")},
        {"fecha": "2026-08-01", "torneo_nombre": "Otro", "ronda": "Finals", "ganador": "team_1",  # otra pareja
         "marcador_txt": "6-3, 6-3", "equipo_1_jugador_1": jug("a"), "equipo_1_jugador_2": jug("x"),
         "equipo_2_jugador_1": jug("c"), "equipo_2_jugador_2": jug("d")},
    ]
    def f1(equipo, ids, gana, juegos, fecha="2026-11-13", pid="PP2-1"):
        return {"partido_id": pid, "bloque": "partido", "equipo": equipo, "fecha": fecha, "torneo_slug": "dubai-p1-3",
                "ronda": "QF", "gana": gana, "jugador_1_id": ids[0], "jugador_2_id": ids[1], "juegos_por_set": juegos}
    f1_filas = [f1(1, ("c", "d"), False, [3, 6, 1]), f1(2, ("a", "b"), True, [6, 3, 6]),
                # el mismo partido de Bordeaux, también en Premier: no cuenta dos veces
                f1(1, ("a", "b"), True, [3, 6, 6], "2026-07-01", "PP2-0"), f1(2, ("c", "d"), False, [6, 1, 1], "2026-07-01", "PP2-0")]
    partidos = partidos_entre(p1, p2, f2, f1_filas, lambda slug, fecha: "Dubai P1 2026")
    assert [(r["fecha"], r["gana_1"], r["marcador"], r["ronda"]) for r in partidos] == [
        ("2026-11-13", True, "6-3, 3-6, 6-1", "Cuartos"),
        ("2026-07-01", True, "3-6, 6-1, 6-1", "Final"),
    ]


def test_forma_al_dia_no_cuenta_dos_veces_un_partido_con_un_jugador_sin_id():
    from content.chart_factory.adhoc import resultados_por_jugador

    def jug(i):
        return {"jugador_id": i}
    f2 = [{"fecha": "2026-11-10", "ganador": "team_1", "equipo_1_jugador_1": jug("a"), "equipo_1_jugador_2": jug("b"),
           "equipo_2_jugador_1": jug("c"), "equipo_2_jugador_2": jug("d")}]
    f1 = [  # el mismo partido en Premier, con "b" sin identificar; y uno nuevo de esta semana
        {"partido_id": "1", "bloque": "partido", "equipo": 1, "fecha": "2026-11-10", "gana": True,
         "jugador_1_id": "a", "jugador_2_id": None},
        {"partido_id": "1", "bloque": "partido", "equipo": 2, "fecha": "2026-11-10", "gana": False,
         "jugador_1_id": "c", "jugador_2_id": "d"},
        {"partido_id": "2", "bloque": "partido", "equipo": 1, "fecha": "2026-11-13", "gana": False,
         "jugador_1_id": "a", "jugador_2_id": "b"},
        {"partido_id": "2", "bloque": "partido", "equipo": 2, "fecha": "2026-11-13", "gana": True,
         "jugador_1_id": "e", "jugador_2_id": "f"},
    ]
    cuenta = resultados_por_jugador({"a", "b", "c"}, "2026-09-18", f2, f1)
    assert cuenta == {"a": [1, 2], "b": [1, 2], "c": [0, 1]}
