"""fact_partido a partir de los snapshots de partidos por torneo de F2.

Alcance de esta primera versión (17/09/2026): todavía no existe `dim_pareja`
(SCD2, previsto para Fase 2 — doc 01 §8), así que cada partido guarda los
`jugador_id` de los 2+2 jugadores en vez de un `pareja_id`. Cuando se derive
`dim_pareja` desde este mismo `fact_partido`, se añade esa columna sin tener
que volver a tocar el conector.

`torneo_id` usa un espacio de ids propio de padelapi (distinto del de
`dim_torneo`, que sale del calendario de F1): unificarlos vía `event_code`
(ver docs/campos-f1-premierpadel.md) es trabajo de Fase 2, cuando además
haga falta cruzar con `dim_puntos_categoria` y prize money (F4).

Partidos sin cruce de algún jugador en `map_jugador_fuente` (jugador fuera
del alcance de nuestros snapshots de /players) se guardan igualmente, con
`jugador_id` a NULL y el nombre e id de padelapi en claro — mejor eso que
perder el partido entero.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_MATCHES_ROOT = REPO_ROOT / "bronze" / "padelapi" / "matches"
SILVER_ROOT = REPO_ROOT / "silver"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay snapshots en {root}")
    return dirs[-1]


def _load_map_padelapi() -> dict[str, str]:
    map_dir = _latest_dir(SILVER_ROOT / "map_jugador_fuente")
    rows = json.loads((map_dir / "data.json").read_text(encoding="utf-8"))
    return {r["id_fuente"]: r["jugador_id"] for r in rows if r["fuente"] == "padelapi"}


def torneo_id_for_padelapi(tournament_id: int) -> str:
    return f"T2{hashlib.sha1(f'padelapi:{tournament_id}'.encode()).hexdigest()[:9]}"


def _jugador_ref(player: dict[str, Any], jugador_por_id_fuente: dict[str, str]) -> dict[str, Any]:
    id_fuente = str(player["id"])
    return {
        "jugador_id": jugador_por_id_fuente.get(id_fuente),
        "id_padelapi": player["id"],
        "nombre_padelapi": player["name"],
        "lado_pista": player.get("side"),
    }


def _resumen_marcador(score: Any) -> tuple[int | None, int | None, int | None, int | None, str | None]:
    if not isinstance(score, list):
        # Confirmado en vivo (17/09/2026): un 2,5% de los partidos "finished"
        # trae el marcador oculto tras "hidden_free_plan" incluso siendo el
        # mismo plan gratuito que en otros partidos sí lo muestra — no es un
        # error del conector.
        return None, None, None, None, None

    sets_a = sets_b = juegos_a = juegos_b = 0
    partes = []
    for set_score in score:
        a_txt, b_txt = set_score["team_1"], set_score["team_2"]
        a_juegos = int("".join(c for c in a_txt if c.isdigit())[:1] or 0)
        b_juegos = int("".join(c for c in b_txt if c.isdigit())[:1] or 0)
        # el primer dígito es suficiente salvo en marcadores tipo "6(1)"; para
        # el recuento de juegos ganados basta el número de juegos del set
        a_juegos = int(a_txt.split("(")[0])
        b_juegos = int(b_txt.split("(")[0])
        juegos_a += a_juegos
        juegos_b += b_juegos
        if a_juegos > b_juegos:
            sets_a += 1
        elif b_juegos > a_juegos:
            sets_b += 1
        partes.append(f"{a_txt}-{b_txt}")
    return sets_a, sets_b, juegos_a, juegos_b, ", ".join(partes)


def build() -> Path:
    jugador_por_id_fuente = _load_map_padelapi()

    rows: list[dict[str, Any]] = []
    tournament_dirs = sorted(BRONZE_MATCHES_ROOT.glob("tournament_id=*"))
    for tournament_dir in tournament_dirs:
        dt_dirs = sorted((p for p in tournament_dir.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
        if not dt_dirs:
            continue
        payload = json.loads((dt_dirs[-1] / "data.json").read_text(encoding="utf-8"))
        torneo_id = torneo_id_for_padelapi(payload["tournament"]["id"])

        for match in payload["items"]:
            sets_a, sets_b, juegos_a, juegos_b, marcador_txt = _resumen_marcador(match["score"])
            team_1 = [_jugador_ref(p, jugador_por_id_fuente) for p in match["players"]["team_1"]]
            team_2 = [_jugador_ref(p, jugador_por_id_fuente) for p in match["players"]["team_2"]]
            ganador = match.get("winner")

            # Ruido confirmado en la fuente (17/09/2026, 1 de 3.291 partidos):
            # el "winner" declarado por padelapi a veces no coincide con quién
            # ganó más sets según su propio marcador. Se guarda el partido
            # igualmente (participantes y fecha son válidos) pero marcado, para
            # que forma_reciente y futuras tablas de dominio de sets lo excluyan.
            marcador_incoherente = False
            if sets_a is not None and ganador in ("team_1", "team_2"):
                sets_ganador = sets_a if ganador == "team_1" else sets_b
                sets_perdedor = sets_b if ganador == "team_1" else sets_a
                marcador_incoherente = sets_ganador <= sets_perdedor

            rows.append(
                {
                    "partido_id": f"M2{match['id']}",
                    "torneo_id": torneo_id,
                    "torneo_nombre": payload["tournament"]["name"],
                    "categoria": match.get("category"),
                    "fase": match.get("draw"),
                    "ronda": match.get("round_name"),
                    "fecha": match.get("played_at"),
                    "equipo_1_jugador_1": team_1[0] if len(team_1) > 0 else None,
                    "equipo_1_jugador_2": team_1[1] if len(team_1) > 1 else None,
                    "equipo_2_jugador_1": team_2[0] if len(team_2) > 0 else None,
                    "equipo_2_jugador_2": team_2[1] if len(team_2) > 1 else None,
                    "ganador": ganador,
                    "sets_equipo_1": sets_a,
                    "sets_equipo_2": sets_b,
                    "juegos_equipo_1": juegos_a,
                    "juegos_equipo_2": juegos_b,
                    "marcador_txt": marcador_txt,
                    "marcador_incoherente": marcador_incoherente,
                    "fuente_txt": "padelapi.org · elaboración propia",
                }
            )

    out_dir = SILVER_ROOT / "fact_partido"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    con_ambos_jugadores_cruzados = sum(
        1
        for r in rows
        if all(
            r[k] is not None and r[k]["jugador_id"] is not None
            for k in ("equipo_1_jugador_1", "equipo_1_jugador_2", "equipo_2_jugador_1", "equipo_2_jugador_2")
            if r[k] is not None
        )
    )
    print(
        f"fact_partido: {len(rows)} partidos de {len(tournament_dirs)} torneos "
        f"({con_ambos_jugadores_cruzados} con los 4 jugadores cruzados a jugador_id) "
        f"-> {out_file.relative_to(REPO_ROOT)}"
    )
    return out_file


if __name__ == "__main__":
    build()
