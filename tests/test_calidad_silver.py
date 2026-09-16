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
