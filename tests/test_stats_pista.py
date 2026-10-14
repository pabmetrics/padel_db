"""Estadísticas de pista (F1, API nueva de premierpadel.com):
silver.fact_partido_stats, gold.stats_parejas y la selección del gráfico.
Sin datos reales del repo."""

from __future__ import annotations

from content.chart_factory import stats_resto
from transform import build_fact_partido_stats as fps
from transform import build_gold_stats_parejas as gsp

DIM = [
    {"jugador_id": "J1", "nombre_canonico": "Arturo Coello", "sexo": "M"},
    {"jugador_id": "J2", "nombre_canonico": "Agustin Tapia", "sexo": "M"},
    {"jugador_id": "J3", "nombre_canonico": "Alvaro Montiel Caruso", "sexo": "M"},
    {"jugador_id": "J4", "nombre_canonico": "Juan Lebron", "sexo": "M"},
    {"jugador_id": "J5", "nombre_canonico": "Juan Lebron Chincoa", "sexo": "M"},
]


def _stat(titulo: str, t1: dict, t2: dict) -> dict:
    vacio = {"title": "", "won": "", "played": "", "percentage": "", "is_winner": "No"}
    return {"title": titulo, "team_1": {**vacio, **t1}, "team_2": {**vacio, **t2}}


def _item(match_id: str = "18609", draw: str = "MD", ganador: str = "1", con_stats: bool = True) -> dict:
    bloque = {
        "title": "Match",
        "service": [
            _stat("Aces", {"title": "0"}, {"title": "0"}),
            _stat("Second Serve Points Won", {"won": 3, "played": 3}, {"won": 7, "played": 9}),
            _stat("Services Games Played", {"title": "16"}, {"title": "15"}),
        ],
        "return": [_stat("First Return Points Won", {"won": 29, "played": 83}, {"won": 27, "played": 90})],
        "total_points": [
            _stat("Total Points Won", {"won": 101, "played": 185}, {"won": 84, "played": 185}),
            _stat("Total Return Points Won", {"won": 31, "played": 92}, {"won": 27, "played": 93}),
            _stat("Longest Points Won Streak", {"title": "7"}, {"title": "5"}),
        ],
    }

    def equipo(n: int, jugadores: list[tuple[str, str]]) -> dict:
        return {"team_no": n, "tournament_id": "270", "seed_number": n, "score": {"set1": 6, "set2": 4, "set3": 7},
                "players": [{"player_id": 100 + i, "first_name": a, "last_name": b} for i, (a, b) in enumerate(jugadores)]}

    return {
        "match": {"match_id": match_id, "status": "F", "round_name": "F", "date": "2026-09-13", "duration": "01:59:49",
                  "draw_type": draw, "winner_id": ganador,
                  "teams": [equipo(1, [("Arturo", "Coello"), ("Agustin", "Tapia")]), equipo(2, [("Alvaro", "Montiel"), ("Juan", "Lebron")])]},
        "stats": {"match_state": [bloque, {**bloque, "title": "set 1"}]} if con_stats else None,
    }


def test_duracion_en_minutos():
    assert fps.duracion_min("01:59:49") == 120
    assert fps.duracion_min("00:00:00") is None
    assert fps.duracion_min("") is None


def test_cruce_por_nombre_exacto_y_por_primer_apellido_unico():
    cruce = fps.CruceJugadores(DIM)
    assert cruce.buscar("Arturo", "Coello", "M") == "J1"
    assert cruce.buscar("Alvaro", "Montiel", "M") == "J3"  # "Alvaro Montiel Caruso", único candidato
    assert cruce.buscar("Arturo", "Coello", "F") is None


def test_cruce_ambiguo_no_adivina():
    # "Juan Lebron" existe tal cual (exacto gana), pero sin el exacto hay dos candidatos
    cruce = fps.CruceJugadores([r for r in DIM if r["jugador_id"] != "J4"] + [{"jugador_id": "J6", "nombre_canonico": "Juan Lebron Otro", "sexo": "M"}])
    assert cruce.buscar("Juan", "Lebron", "M") is None


def test_filas_de_partido_lee_metricas_y_descarta_aces():
    sin_cruzar: list = []
    filas = fps.filas_de_partido(_item(), "paris-major", fps.CruceJugadores(DIM), sin_cruzar)
    assert {(f["equipo"], f["bloque"]) for f in filas} == {(1, "partido"), (2, "partido"), (1, "set_1"), (2, "set_1")}
    e1 = next(f for f in filas if f["equipo"] == 1 and f["bloque"] == "partido")
    assert (e1["puntos_resto_ganados"], e1["puntos_resto_jugados"]) == (31, 92)
    assert (e1["segundo_saque_ganados"], e1["segundo_saque_jugados"]) == (3, 3)
    assert e1["juegos_saque"] == 16 and e1["racha_max"] == 7
    assert e1["gana"] and e1["duracion_min"] == 120 and e1["sexo"] == "M" and e1["fase"] == "main"
    assert not any(k.startswith(("aces", "dobles")) for k in e1)
    assert sin_cruzar == []


def test_partido_sin_stats_deja_una_fila_vacia():
    filas = fps.filas_de_partido(_item(con_stats=False), "paris-major", fps.CruceJugadores(DIM), [])
    assert len(filas) == 2 and all(f["stats_vacias"] and f["bloque"] == "partido" for f in filas)


def test_agregado_suma_recuentos_y_excluye_previa_y_sets():
    filas = []
    for i in range(gsp.MIN_PARTIDOS):
        filas += fps.filas_de_partido(_item(match_id=str(i)), "t", fps.CruceJugadores(DIM), [])
    filas += fps.filas_de_partido(_item(match_id="q", draw="MQ"), "t", fps.CruceJugadores(DIM), [])
    salida = gsp.agregar(filas, 2026, {"J1": "Arturo Coello", "J2": "Agustin Tapia", "J3": "Alvaro Montiel Caruso", "J4": "Juan Lebron"})
    coello = next(r for r in salida if r["jugador_1_id"] in ("J1", "J2"))
    assert coello["partidos"] == gsp.MIN_PARTIDOS  # ni la previa ni los bloques de set
    assert coello["puntos_resto_jugados"] == 92 * gsp.MIN_PARTIDOS
    assert coello["pct_puntos_resto"] == round(100 * 31 / 92, 1)
    assert coello["publicable"]


def test_pareja_sin_cruzar_o_con_pocos_partidos_no_es_publicable():
    filas = fps.filas_de_partido(_item(), "t", fps.CruceJugadores(DIM[:1]), [])  # solo Coello en dim
    salida = gsp.agregar(filas, 2026, {})
    assert not any(r["publicable"] for r in salida)


def test_grafico_ordena_por_resto():
    filas = [
        {"sexo": "M", "publicable": True, "pct_puntos_resto": 30.0, "partidos": 10, "pareja": "A"},
        {"sexo": "M", "publicable": True, "pct_puntos_resto": 35.5, "partidos": 9, "pareja": "B"},
        {"sexo": "M", "publicable": False, "pct_puntos_resto": 50.0, "partidos": 3, "pareja": "C"},
        {"sexo": "F", "publicable": True, "pct_puntos_resto": 40.0, "partidos": 9, "pareja": "D"},
    ]
    assert [r["pareja"] for r in stats_resto.seleccionar(filas, "M")] == ["B", "A"]
