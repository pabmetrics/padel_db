"""Silver mínimo: bronze/premierpadel/rankings -> silver/fact_ranking_semanal.

Nota de alcance (Fase 0): esta tabla usa el `slug` de premierpadel.com como
clave de jugador porque `dim_jugador` y `map_jugador_fuente` (Fase 1) todavía
no existen. `jugador_slug` es, por tanto, un identificador provisional: en
Fase 1 se sustituye por `jugador_id` propio vía el mapeo de fuentes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "rankings"
SILVER_ROOT = REPO_ROOT / "silver" / "fact_ranking_semanal"

GENDER_FILES = {"male.json": "M", "female.json": "F"}


def latest_snapshot_dir() -> Path:
    dirs = sorted((p for p in BRONZE_ROOT.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {BRONZE_ROOT}")
    return dirs[-1]


def build(dt_dir: Path) -> Path:
    fecha_ranking = dt_dir.name.removeprefix("dt=")
    con = duckdb.connect()

    selects = []
    for filename, sexo in GENDER_FILES.items():
        path = dt_dir / filename
        if not path.exists():
            continue
        selects.append(
            f"""
            SELECT
                DATE '{fecha_ranking}' AS fecha_ranking,
                'Premier Padel' AS circuito,
                '{sexo}' AS sexo,
                item.slug AS jugador_slug,
                item.full_name AS jugador_nombre_fuente,
                item.id AS jugador_id_fuente,
                item.posicion_lista AS posicion,
                CAST(NULL AS BIGINT) AS puntos,
                CAST(NULL AS INTEGER) AS torneos_computados,
                'premierpadel' AS fuente_txt
            FROM read_json_auto('{path.as_posix()}') AS t, UNNEST(t.items) AS u(item)
            """
        )

    if not selects:
        raise SystemExit(f"No hay ficheros male.json/female.json en {dt_dir}")

    query = " UNION ALL ".join(selects)
    out_dir = SILVER_ROOT / f"fecha_ranking={fecha_ranking}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.parquet"
    con.execute(f"COPY ({query}) TO '{out_file.as_posix()}' (FORMAT PARQUET)")

    n_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out_file.as_posix()}')").fetchone()[0]
    print(f"fact_ranking_semanal {fecha_ranking}: {n_rows} filas -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dt",
        help="Fecha del snapshot bronze a procesar (YYYY-MM-DD). Por defecto, el más reciente.",
    )
    args = parser.parse_args()

    dt_dir = (BRONZE_ROOT / f"dt={args.dt}") if args.dt else latest_snapshot_dir()
    if not dt_dir.exists():
        raise SystemExit(f"No existe el snapshot {dt_dir}")

    build(dt_dir)


if __name__ == "__main__":
    main()
