"""Gold: ranking_semana (doc 01 §3.3 / doc 02 #RankingLunes).

Una fila = un jugador del top 100 en el ranking de esta semana. Alimenta
los dos gráficos de #RankingLunes (`chart_factory/ranking_top10.py` y
`chart_factory/ranking_puntos.py`), que sustituyen al de puestos ganados
(`ranking_movimientos_semana` sigue construyéndose para la web).

A diferencia de `ranking_movimientos_semana`, aquí entran también los
jugadores que no se han movido de puesto: el top 10 casi nunca cambia de
posición y la mayor subida de puntos puede no mover a nadie (Stupaczuk,
+90 puntos y el mismo #8 el 28/09/2026).

`resultado_semana` explica de dónde salen los puntos: el mejor resultado
del jugador en los torneos que terminaron la semana anterior al ranking
(`fact_resultado_torneo`). Es contexto, no la cifra: el Δ de puntos es el
de F2, que también descuenta lo que caduca (comprobado el 29/09/2026: el Δ
de F2 coincide con la resta de nuestros dos snapshots en 72 de 72 jugadores
del top 100 con puntos las dos semanas).

`publicable` exige puntos y Δ de puntos: el 28/09/2026 padelapi solo había
publicado el ranking masculino y el femenino quedó sin puntos (F1 da la
posición, no los puntos) — sin ellos no hay gráfico.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_ROOT = REPO_ROOT / "silver"
FACT_RESULTADO = SILVER_ROOT / "fact_resultado_torneo" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "ranking_semana"

TOP_N = 100
RONDA_TXT = {"W": "Campeón", "F": "Final", "SF": "Semifinal", "QF": "Cuartos", "R16": "Octavos", "R32": "Dieciseisavos"}


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def resultados_semana(resultados: list[dict[str, Any]], fecha_ranking: date) -> dict[str, dict[str, Any]]:
    """jugador_id -> su mejor resultado (más puntos) en torneos terminados
    entre el lunes y el domingo anteriores a `fecha_ranking`."""
    ini, fin = fecha_ranking - timedelta(days=7), fecha_ranking - timedelta(days=1)
    mejor: dict[str, dict[str, Any]] = {}
    for r in resultados:
        if not r.get("fecha") or not (ini <= date.fromisoformat(str(r["fecha"])[:10]) <= fin):
            continue
        for jid in (r["jugador_1_id"], r["jugador_2_id"]):
            actual = mejor.get(jid)
            if actual is None or (r.get("puntos_ganados") or 0) > (actual.get("puntos_ganados") or 0):
                mejor[jid] = r
    return mejor


def build() -> Path:
    dt_dir = _latest_dir(SILVER_ROOT / "fact_ranking_semanal")
    fecha = dt_dir.name.removeprefix("fecha_ranking=")

    con = duckdb.connect()
    rows = con.execute(
        f"""
        SELECT fecha_ranking AS fecha_dato, circuito, sexo, jugador_id, jugador_nombre,
               posicion, puntos, puntos_diff_semana, posicion_diff_semana, fuente_txt
        FROM read_parquet('{(dt_dir / "data.parquet").as_posix()}')
        WHERE posicion <= {TOP_N}
        ORDER BY sexo, posicion, jugador_nombre
        """
    ).fetchall()
    columns = [d[0] for d in con.description]

    resultados = json.loads(FACT_RESULTADO.read_text(encoding="utf-8")) if FACT_RESULTADO.exists() else []
    por_jugador = resultados_semana(resultados, date.fromisoformat(fecha))

    records: list[dict[str, Any]] = []
    for row in rows:
        r = dict(zip(columns, row))
        r["fecha_dato"] = str(r["fecha_dato"])
        for clave in ("puntos_diff_semana", "posicion_diff_semana"):
            if r[clave] is not None:
                r[clave] = int(r[clave])
        res = por_jugador.get(r["jugador_id"])
        r["resultado_semana"] = (
            f"{RONDA_TXT.get(res['ronda_alcanzada'], res['ronda_alcanzada'])} · {res['torneo_nombre']}" if res else None
        )
        r["puntos_torneo_semana"] = res.get("puntos_ganados") if res else None
        r["publicable"] = r["puntos"] is not None and r["puntos_diff_semana"] is not None
        records.append(r)

    out_dir = GOLD_ROOT / f"fecha_dato={fecha}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    for sexo in ("M", "F"):
        pub = [r for r in records if r["sexo"] == sexo and r["publicable"]]
        print(f"ranking_semana {fecha} {sexo}: {len(pub)} de {sum(r['sexo'] == sexo for r in records)} publicables")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
