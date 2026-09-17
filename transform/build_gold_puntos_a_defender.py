"""Gold: puntos_a_defender (doc 01 §3.3 / doc 02 #RankingLunes).

Una fila = un jugador con puntos que caducan (ranking rodante a 52 semanas)
en las próximas 4/8 semanas.

Aviso real (17-18/09/2026): con ~240 días de fact_resultado_torneo hacia
atrás (ampliado desde 180 el 18/09), ningún resultado actual caduca todavía
(caducarían ~un año después de haberse ganado, muy por delante de la
ventana de 4-8 semanas). Esta tabla sale vacía o casi vacía hasta que el
backfill de partidos cubra un año completo (Fase 5, doc 01 §8: "Backfill").
El cálculo es correcto y queda listo para cuando haya datos suficientes —
no es un error de este script.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_RESULTADO = REPO_ROOT / "silver" / "fact_resultado_torneo" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "puntos_a_defender"

CICLO_RANKING_DIAS = 364  # 52 semanas


def build() -> Path:
    resultados = json.loads(FACT_RESULTADO.read_text(encoding="utf-8"))
    hoy = date.today()
    corte_4sem = hoy + timedelta(weeks=4)
    corte_8sem = hoy + timedelta(weeks=8)

    dim_dir = REPO_ROOT / "silver" / "dim_jugador"
    dt_dirs = sorted((p for p in dim_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    nombres: dict[str, str] = {}
    sexo_por_jugador: dict[str, str] = {}
    if dt_dirs:
        filas = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        nombres = {r["jugador_id"]: r["nombre_canonico"] for r in filas}
        sexo_por_jugador = {r["jugador_id"]: r["sexo"] for r in filas}

    acumulado: dict[str, dict[str, Any]] = defaultdict(lambda: {"defender_4sem": 0, "defender_8sem": 0, "torneos": []})

    for r in resultados:
        if r["puntos_ganados"] is None:
            continue
        fecha_caducidad = date.fromisoformat(r["fecha"]) + timedelta(days=CICLO_RANKING_DIAS)
        if fecha_caducidad < hoy or fecha_caducidad > corte_8sem:
            continue
        for jugador_id in (r["jugador_1_id"], r["jugador_2_id"]):
            entry = acumulado[jugador_id]
            if fecha_caducidad <= corte_4sem:
                entry["defender_4sem"] += r["puntos_ganados"]
            entry["defender_8sem"] += r["puntos_ganados"]
            entry["torneos"].append(
                {
                    "torneo_nombre": r["torneo_nombre"],
                    "ronda_alcanzada": r["ronda_alcanzada"],
                    "puntos": r["puntos_ganados"],
                    "fecha_caducidad": fecha_caducidad.isoformat(),
                }
            )

    rows: list[dict[str, Any]] = []
    for jugador_id, datos in acumulado.items():
        rows.append(
            {
                "fecha_dato": hoy.isoformat(),
                "jugador_id": jugador_id,
                "jugador_nombre": nombres.get(jugador_id),
                "sexo": sexo_por_jugador.get(jugador_id),
                "puntos_a_defender_4sem": datos["defender_4sem"],
                "puntos_a_defender_8sem": datos["defender_8sem"],
                "detalle": datos["torneos"],
                "fuente_txt": "padelapi.org + FIP Ranking Point Table 2026 · elaboración propia",
                "publicable": datos["defender_8sem"] > 0,
            }
        )

    rows.sort(key=lambda r: -r["puntos_a_defender_8sem"])

    out_dir = GOLD_ROOT / f"fecha_dato={hoy.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"puntos_a_defender: {len(rows)} jugadores con puntos que caducan en las próximas 8 semanas "
        f"(con los datos actuales, {CICLO_RANKING_DIAS} días de ciclo de ranking y solo ~240 días de "
        f"histórico, se espera que sean pocos o ninguno)"
    )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
