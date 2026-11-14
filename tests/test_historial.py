"""Memoria anti-repetición de la cola (content/copy_factory/historial.py),
devolución del número de registro y sorpresas del torneo en curso."""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

from content.chart_factory import marca
from content.chart_factory.sorpresas import sorpresas_del_ultimo_torneo
from content.copy_factory.historial import candidato_repetido, protagonistas

REPO_ROOT = Path(__file__).resolve().parents[1]


def _cola(queue_root: Path, fecha: str, *candidatos: dict) -> None:
    d = queue_root / fecha
    d.mkdir(parents=True, exist_ok=True)
    (d / "candidates.json").write_text(json.dumps(list(candidatos), ensure_ascii=False), encoding="utf-8")


H2H_11_04 = {
    "registro": "#0257", "serie": "Cara a cara",
    "values": {"pareja_1": "Agustin Tapia / Arturo Coello", "pareja_2": "Juan Lebron / Leo Augsburger",
               "victorias_pareja_1": 8, "victorias_pareja_2": 1, "total_enfrentamientos": 9,
               "circuito": "masculino"},
}


def test_protagonistas_separa_parejas_y_normaliza():
    assert protagonistas({"pareja": "Agustín Tapia / Arturo Coello", "circuito": "masculino"}) == {
        "agustin tapia", "arturo coello"}


def test_repite_el_mismo_cara_a_cara_una_semana_despues(tmp_path):
    # Caso real: el h2h del 4/11 y el del 11/11 eran idénticos.
    _cola(tmp_path, "2026-11-04", H2H_11_04)
    anterior = candidato_repetido("Cara a cara", H2H_11_04["values"], date(2026, 11, 11), queue_root=tmp_path)
    assert anterior and anterior["registro"] == "#0257"


def test_repite_si_comparte_un_jugador_aunque_cambie_el_formato(tmp_path):
    # Forma reciente: el 6/11 la pareja Tapia/Coello, el 13/11 Tapia solo.
    _cola(tmp_path, "2026-11-06", {"registro": "#0263", "serie": "Forma reciente",
                                   "values": {"pareja": "Agustin Tapia / Arturo Coello", "circuito": "masculino"}})
    assert candidato_repetido("Forma reciente", {"jugador": "Agustin Tapia", "circuito": "masculino"},
                              date(2026, 11, 13), queue_root=tmp_path)


def test_no_repite_otra_serie_otro_circuito_ni_fuera_de_plazo(tmp_path):
    _cola(tmp_path, "2026-10-01", H2H_11_04)  # 41 días antes
    _cola(tmp_path, "2026-11-02", {**H2H_11_04, "serie": "Forma reciente"})  # otra serie, hace 9 días
    _cola(tmp_path, "2026-11-05", {**H2H_11_04, "values": {**H2H_11_04["values"], "circuito": "femenino"}})
    assert candidato_repetido("Cara a cara", H2H_11_04["values"], date(2026, 11, 11), queue_root=tmp_path) is None


def test_misma_pareja_en_otra_serie_la_misma_semana_repite(tmp_path):
    # Simulación del 17-18/11: Tapia/Coello encabezaban "Saque y resto" el
    # martes y "Remontadas" el miércoles.
    _cola(tmp_path, "2026-11-17", {"registro": "#0292", "serie": "Saque y resto",
                                   "values": {"pareja": "Agustin Tapia / Arturo Coello", "circuito": "masculino"}})
    assert candidato_repetido("Remontadas", {"pareja": "Agustin Tapia / Arturo Coello", "circuito": "masculino"},
                              date(2026, 11, 18), queue_root=tmp_path)
    assert candidato_repetido("Remontadas", {"pareja": "Agustin Tapia / Arturo Coello", "circuito": "masculino"},
                              date(2026, 11, 20), queue_root=tmp_path) is None


def test_series_semanales_y_pedidos_a_medida_no_se_filtran(tmp_path):
    lunes = {"registro": "#0267", "serie": "#RankingLunes",
             "values": {"pareja": "Agustin Tapia / Arturo Coello", "circuito": "masculino"}}
    _cola(tmp_path, "2026-11-09", lunes, {**H2H_11_04, "pedido": {"tipo": "jugadores"}})
    assert candidato_repetido("#RankingLunes", lunes["values"], date(2026, 11, 16), queue_root=tmp_path) is None
    assert candidato_repetido("Cara a cara", H2H_11_04["values"], date(2026, 11, 16), queue_root=tmp_path) is None


def test_mismos_datos_sin_protagonista_tambien_repiten(tmp_path):
    mercado = {"registro": "#0200", "serie": "Pádel Mercado", "values": {"pistas_fip": 77355, "pistas_playtomic": 58334}}
    _cola(tmp_path, "2026-10-27", mercado)
    assert candidato_repetido("Pádel Mercado", dict(mercado["values"]), date(2026, 11, 10), queue_root=tmp_path)


def test_devolver_registro_solo_el_ultimo(tmp_path, monkeypatch):
    monkeypatch.setattr(marca, "REGISTRO_PATH", tmp_path / "registro.json")
    (tmp_path / "registro.json").write_text(json.dumps({"ultimo": 291}))
    reg = marca.siguiente_registro()
    assert reg == "#0292"
    assert not marca.devolver_registro("#0291")  # ya hay otro detrás: el hueco no se cierra
    assert marca.devolver_registro(reg)
    assert marca.siguiente_registro() == "#0292"


def _gold_sorpresas():
    spec = importlib.util.spec_from_file_location("gold_sorpresas", REPO_ROOT / "transform" / "build_gold_torneo_sorpresas.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fila_f1(partido, equipo, semilla, gana, nombres, ids):
    return {"partido_id": partido, "bloque": "partido", "fase": "main", "equipo": equipo, "semilla": semilla,
            "gana": gana, "fecha": "2026-11-13", "torneo_slug": "dubai-p1-3", "sexo": "F", "ronda": "QF",
            "jugador_1_nombre_fuente": nombres[0], "jugador_2_nombre_fuente": nombres[1],
            "jugador_1_id": ids[0], "jugador_2_id": ids[1], "juegos_por_set": []}


def test_sorpresas_de_premier_padel_desde_las_stats_diarias():
    gold = _gold_sorpresas()
    filas = [
        # Caso real del 13/11: la semilla 6 elimina a la 1 en cuartos de Dubai P1.
        _fila_f1("PP2-1", 1, 6, True, ("Tamara Icardo Alcorisa", "Claudia Jensen"), ("a", "b")),
        _fila_f1("PP2-1", 2, 1, False, ("Gemma Triay Pons", "Delfina Brea Senesi"), ("c", "d")),
        # Gana la mejor semilla: no es sorpresa.
        _fila_f1("PP2-2", 1, 2, True, ("A", "B"), ("e", "f")),
        _fila_f1("PP2-2", 2, 7, False, ("C", "D"), ("g", "h")),
        # Qualy: fuera.
        {**_fila_f1("PP2-3", 1, 9, True, ("E", "F"), ("i", "j")), "fase": "qualy"},
        {**_fila_f1("PP2-3", 2, 1, False, ("G", "H"), ("k", "l")), "fase": "qualy"},
    ]
    rows = gold.sorpresas_f1(filas, {})
    assert len(rows) == 1
    r = rows[0]
    assert (r["torneo_nombre"], r["categoria"], r["ronda"]) == ("Dubai P1 2026", "women", "Quarter")
    assert (r["semilla_ganador"], r["semilla_perdedor"], r["diferencia_semillas"]) == (6, 1, 5)
    assert r["publicable"] and r["_ids"] == frozenset("abcd")


def test_nombre_de_torneo_premier_padel():
    gold = _gold_sorpresas()
    assert gold.nombre_torneo_f1("dubai-p1-3", {}) == "Dubai P1"
    assert gold.nombre_torneo_f1("kuwait-major", {"kuwait-major": "KUWAIT MAJOR"}) == "Kuwait Major"


def test_el_torneo_en_datos_solo_mira_el_torneo_reciente():
    def fila(torneo, fecha, dif):
        return {"torneo_nombre": torneo, "fecha": fecha, "categoria": "men", "publicable": True,
                "diferencia_semillas": dif}
    rows = [fila("Milano P1", "2026-10-15", 11), fila("Dubai P1", "2026-11-12", 9),
            fila("Dubai P1", "2026-11-12", 5), fila("FIP Gold X", "2026-11-11", 7)]
    top = sorpresas_del_ultimo_torneo(rows, "men", date(2026, 11, 13))
    assert [r["torneo_nombre"] for r in top] == ["Dubai P1", "Dubai P1"]
    assert top[0]["diferencia_semillas"] == 9
    # Sin partidos en los últimos días, no hay serie (antes salía Milano otra vez).
    assert sorpresas_del_ultimo_torneo(rows, "men", date(2026, 11, 25)) == []
