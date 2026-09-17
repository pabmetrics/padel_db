"""Tests de calidad obligatorios (doc 01 §6) sobre las tablas silver actuales.

Se ejecutan con pytest. Si fallan, el job de build_silver debe fallar (doc
01 §5): no se genera contenido con datos que no pasan estas comprobaciones.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_ROOT = REPO_ROOT / "silver"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        pytest.skip(f"No hay datos en {root} todavía")
    return dirs[-1]


@pytest.fixture(scope="module")
def dim_jugador_rows() -> list[dict]:
    dt_dir = _latest_dir(SILVER_ROOT / "dim_jugador")
    return json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fact_partido_rows() -> list[dict]:
    path = SILVER_ROOT / "fact_partido" / "data.json"
    if not path.exists():
        pytest.skip("fact_partido todavía no se ha generado")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fact_ranking_con() -> duckdb.DuckDBPyConnection:
    dt_dir = _latest_dir(SILVER_ROOT / "fact_ranking_semanal")
    con = duckdb.connect()
    con.execute(
        f"CREATE VIEW fact_ranking_semanal AS "
        f"SELECT * FROM read_parquet('{(dt_dir / 'data.parquet').as_posix()}')"
    )
    return con


def test_jugador_id_unico(dim_jugador_rows: list[dict]) -> None:
    ids = [r["jugador_id"] for r in dim_jugador_rows]
    duplicados = {i for i in ids if ids.count(i) > 1}
    assert not duplicados, f"jugador_id duplicado en dim_jugador: {duplicados}"


def test_dim_jugador_no_vacio(dim_jugador_rows: list[dict]) -> None:
    assert len(dim_jugador_rows) > 0


def test_ranking_empates_solo_con_mismos_puntos(fact_ranking_con: duckdb.DuckDBPyConnection) -> None:
    """El ranking oficial tiene empates (parejas con los mismos puntos comparten
    posición, ej. Galán/Chingotto ambos #3 el 17/09/2026). Dos jugadores con la
    misma posición SIEMPRE deben tener los mismos puntos; si no, es un error de
    cruce, no un empate real."""

    incoherentes = fact_ranking_con.execute(
        """
        SELECT fecha_ranking, circuito, sexo, posicion, COUNT(DISTINCT puntos) AS n_puntos_distintos
        FROM fact_ranking_semanal
        WHERE puntos IS NOT NULL
        GROUP BY 1, 2, 3, 4
        HAVING COUNT(DISTINCT puntos) > 1
        """
    ).fetchall()
    assert not incoherentes, f"Misma posición con puntos distintos: {incoherentes[:5]}"


def test_ranking_puntos_no_crecen_con_la_posicion(fact_ranking_con: duckdb.DuckDBPyConnection) -> None:
    """A mayor posición (número más alto = peor puesto), los puntos no pueden
    ser mayores que los de una posición mejor — el ranking debe ser monótono."""

    grupos = fact_ranking_con.execute(
        "SELECT DISTINCT fecha_ranking, circuito, sexo FROM fact_ranking_semanal"
    ).fetchall()
    for fecha_ranking, circuito, sexo in grupos:
        filas = fact_ranking_con.execute(
            "SELECT posicion, puntos FROM fact_ranking_semanal "
            "WHERE fecha_ranking = ? AND circuito = ? AND sexo = ? AND puntos IS NOT NULL "
            "ORDER BY posicion",
            [fecha_ranking, circuito, sexo],
        ).fetchall()
        anterior_puntos = None
        for posicion, puntos in filas:
            if anterior_puntos is not None:
                assert puntos <= anterior_puntos, (
                    f"{circuito}/{sexo}/{fecha_ranking}: posición {posicion} tiene más "
                    f"puntos ({puntos}) que una posición mejor ({anterior_puntos})"
                )
            anterior_puntos = puntos


def test_sin_fechas_futuras(fact_ranking_con: duckdb.DuckDBPyConnection) -> None:
    fechas = fact_ranking_con.execute("SELECT DISTINCT fecha_ranking FROM fact_ranking_semanal").fetchall()
    hoy = date.today()
    futuras = [f[0] for f in fechas if f[0] > hoy]
    assert not futuras, f"fecha_ranking en el futuro: {futuras}"


def test_puntos_no_negativos(fact_ranking_con: duckdb.DuckDBPyConnection) -> None:
    negativos = fact_ranking_con.execute(
        "SELECT COUNT(*) FROM fact_ranking_semanal WHERE puntos < 0"
    ).fetchone()[0]
    assert negativos == 0


def test_partido_id_unico(fact_partido_rows: list[dict]) -> None:
    ids = [r["partido_id"] for r in fact_partido_rows]
    duplicados = {i for i in ids if ids.count(i) > 1}
    assert not duplicados, f"partido_id duplicado: {duplicados}"


def test_partido_marcador_sin_sets_imposibles(fact_partido_rows: list[dict]) -> None:
    """Nunca más de 3 sets por lado (doc 01 §6: 'sin marcadores imposibles:
    sets > 3, juegos negativos')."""

    for r in fact_partido_rows:
        assert r["sets_equipo_1"] is None or 0 <= r["sets_equipo_1"] <= 3
        assert r["sets_equipo_2"] is None or 0 <= r["sets_equipo_2"] <= 3


def test_partido_ganador_coherente_con_el_marcador(fact_partido_rows: list[dict]) -> None:
    """El ganador declarado por la fuente debería tener más sets que el rival.
    Se ha confirmado en vivo (17/09/2026) que padelapi se equivoca en un
    partido puntual (1 de 3.291) — se tolera una tasa muy baja de esta
    incoherencia, ya marcada como `marcador_incoherente` por
    build_fact_partido.py, en vez de exigir cero (que fallaría por un dato
    ajeno que no controlamos) o mirar para otro lado (que dejaría pasar un
    fallo de cruce real si la tasa creciera)."""

    con_marcador = [r for r in fact_partido_rows if r["sets_equipo_1"] is not None]
    incoherentes = [r for r in con_marcador if r["marcador_incoherente"]]
    tasa = len(incoherentes) / len(con_marcador) if con_marcador else 0
    assert tasa <= 0.01, f"Demasiados marcadores incoherentes con el ganador: {tasa:.1%} ({incoherentes[:5]})"


def test_partido_sin_fechas_futuras(fact_partido_rows: list[dict]) -> None:
    hoy = date.today().isoformat()
    futuros = [r["partido_id"] for r in fact_partido_rows if r["fecha"] > hoy]
    assert not futuros, f"Partidos con fecha futura: {futuros[:5]}"


def test_forma_reciente_porcentajes_validos() -> None:
    dt_dir = _latest_dir(REPO_ROOT / "gold" / "forma_reciente")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    for r in rows:
        assert 0 <= r["pct_victorias_8sem"] <= 100
        assert 0 <= r["victorias_8sem"] <= r["partidos_8sem"]


def test_dim_pareja_coherente() -> None:
    path = SILVER_ROOT / "dim_pareja" / "data.json"
    if not path.exists():
        pytest.skip("dim_pareja todavía no se ha generado")
    rows = json.loads(path.read_text(encoding="utf-8"))
    ids = [r["pareja_id"] for r in rows]
    assert len(ids) == len(set(ids)), "pareja_id duplicado"
    for r in rows:
        assert r["jugador_1_id"] != r["jugador_2_id"], f"Pareja consigo mismo: {r}"
        assert r["fecha_inicio"] <= r["fecha_fin"], f"fecha_inicio posterior a fecha_fin: {r}"


def test_h2h_victorias_suman_el_total() -> None:
    dt_dir = _latest_dir(REPO_ROOT / "gold" / "h2h")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    for r in rows:
        assert r["victorias_pareja_1"] + r["victorias_pareja_2"] == r["total_enfrentamientos"]


def test_torneo_sorpresas_semilla_ganadora_peor() -> None:
    """Por definición, una 'sorpresa' es que gane la semilla numéricamente
    peor situada (número más alto)."""

    dt_dir = _latest_dir(REPO_ROOT / "gold" / "torneo_sorpresas")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    for r in rows:
        assert r["semilla_ganador"] > r["semilla_perdedor"], f"No es una sorpresa real: {r}"


def test_dim_puntos_categoria_sin_duplicados_y_positiva() -> None:
    path = SILVER_ROOT / "dim_puntos_categoria" / "data.json"
    if not path.exists():
        pytest.skip("dim_puntos_categoria todavía no se ha generado")
    rows = json.loads(path.read_text(encoding="utf-8"))
    claves = [(r["circuito"], r["categoria"], r["temporada"], r["ronda"]) for r in rows]
    assert len(claves) == len(set(claves)), "Fila duplicada en dim_puntos_categoria"
    for r in rows:
        assert r["puntos"] > 0


def test_fact_resultado_torneo_rondas_conocidas() -> None:
    path = SILVER_ROOT / "fact_resultado_torneo" / "data.json"
    if not path.exists():
        pytest.skip("fact_resultado_torneo todavía no se ha generado")
    rows = json.loads(path.read_text(encoding="utf-8"))
    rondas_validas = {"W", "F", "SF", "QF", "R16", "R32", "R64", "BQ", "LQ", "Q2", "Q1", "3RD", "4TH"}
    for r in rows:
        assert r["ronda_alcanzada"] in rondas_validas, f"Ronda desconocida: {r}"
        assert r["puntos_ganados"] is None or r["puntos_ganados"] > 0


def test_puntos_a_defender_8sem_incluye_4sem() -> None:
    dt_dir = _latest_dir(REPO_ROOT / "gold" / "puntos_a_defender")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    for r in rows:
        assert r["puntos_a_defender_8sem"] >= r["puntos_a_defender_4sem"] >= 0


def test_prize_por_torneo_positivo_y_monotono() -> None:
    """Cifras reales por torneo (padelearnings.com / padelfip.com): siempre
    positivas, y dentro de un mismo torneo+sexo, ganar debe pagar más que
    perder en una ronda anterior."""

    path = SILVER_ROOT / "prize_por_torneo" / "data.json"
    if not path.exists():
        pytest.skip("prize_por_torneo todavía no se ha generado")
    rows = json.loads(path.read_text(encoding="utf-8"))
    orden = {"R64": 0, "R32": 1, "R16": 2, "QF": 3, "SF": 4, "F": 5, "W": 6}
    for r in rows:
        # FIP Silver no paga nada por perder en R32 (confirmado en vivo,
        # 17/09/2026, consistente en todos los FIP Silver del dataset) —
        # >= 0, no > 0.
        assert r["prize_money_jugador_eur"] >= 0

    por_torneo: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        por_torneo.setdefault((r["torneo_nombre_norm"], r["sexo"]), []).append(r)
    for filas in por_torneo.values():
        filas.sort(key=lambda r: orden.get(r["ronda"], -1))
        anterior = None
        for r in filas:
            if anterior is not None:
                assert r["prize_money_jugador_eur"] >= anterior, f"Premio no monótono: {filas}"
            anterior = r["prize_money_jugador_eur"]


def test_ganancias_temporada_no_negativa() -> None:
    dt_dir = _latest_dir(REPO_ROOT / "gold" / "ganancias_temporada")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    for r in rows:
        assert r["ganancias_conocidas_eur"] >= 0
        assert r["n_torneos_con_premio_conocido"] >= 1
