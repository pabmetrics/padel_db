"""Silver: fact_partido_stats (doc 01 §3.2), desde F1 (API nueva de
premierpadel.com, `ingest/premierpadel/match_stats.py`).

Una fila = (partido, equipo, bloque): `bloque` es "partido" (totales) o
"set_1", "set_2"… Métricas en recuentos (ganados/jugados), nunca solo el
porcentaje que da la fuente: así se pueden sumar entre partidos.

Fuera a propósito: aces y dobles faltas. La fuente los devuelve a 0 en
todos los partidos revisados (29/09/2026): no se registran, y publicar
"0 aces" sería publicar un dato falso.

Jugadores: la API nueva tiene su propio espacio de ids (Coello es 14945;
en la API antigua de F1, 12), así que se cruzan por nombre contra
`dim_jugador` — exacto tras normalizar y, si no, nombre + primer apellido
con un único candidato del mismo sexo. Lo que no cruza queda con
`jugador_id = None` y va a `silver/_reconciliacion/partido_stats_sin_cruzar.json`;
nunca se adivina.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from unidecode import unidecode

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_ROOT = REPO_ROOT / "bronze" / "premierpadel" / "match_stats"
SILVER_ROOT = REPO_ROOT / "silver"
OUT_PATH = SILVER_ROOT / "fact_partido_stats" / "data.json"
RECONCILIACION = SILVER_ROOT / "_reconciliacion" / "partido_stats_sin_cruzar.json"

# título en la fuente -> (columna, forma): "ratio" = won/played, "cuenta" = número en `title`
METRICAS = {
    "First Serve Points Won": ("primer_saque", "ratio"),
    "Second Serve Points Won": ("segundo_saque", "ratio"),
    "Services Games Played": ("juegos_saque", "cuenta"),
    "First Return Points Won": ("primer_resto", "ratio"),
    "Second Return Points Won": ("segundo_resto", "ratio"),
    "Return Games Played": ("juegos_resto", "cuenta"),
    "Total Points Won": ("puntos_totales", "ratio"),
    "Total Serve Points Won": ("puntos_saque", "ratio"),
    "Total Return Points Won": ("puntos_resto", "ratio"),
    "Longest Points Won Streak": ("racha_max", "cuenta"),
}
DRAW = {"MD": ("M", "main"), "WD": ("F", "main"), "MQ": ("M", "qualy"), "WQ": ("F", "qualy")}


def normalizar(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unidecode(texto or "").lower()).strip()


def _entero(valor: Any) -> int | None:
    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return None


def duracion_min(txt: str | None) -> int | None:
    """'01:59:49' -> 120 (redondeado al minuto)."""
    if not txt or not re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", txt):
        return None
    h, m, s = (int(x) for x in txt.split(":"))
    total = h * 60 + m + round(s / 60)
    return total or None


class CruceJugadores:
    def __init__(self, dim: list[dict[str, Any]]) -> None:
        self.exacto: dict[tuple[str, str], list[str]] = {}
        self.por_sexo: dict[str, list[tuple[str, list[str]]]] = {}
        for r in dim:
            n = normalizar(r["nombre_canonico"])
            self.exacto.setdefault((n, r["sexo"]), []).append(r["jugador_id"])
            self.por_sexo.setdefault(r["sexo"], []).append((r["jugador_id"], n.split()))

    def buscar(self, nombre: str, apellido: str, sexo: str) -> str | None:
        completo = normalizar(f"{nombre} {apellido}")
        ids = self.exacto.get((completo, sexo), [])
        if len(ids) == 1:
            return ids[0]
        nom, ape = normalizar(nombre).split(), normalizar(apellido).split()
        if not nom or not ape:
            return None
        jugadores = self.por_sexo.get(sexo, [])
        # 1) mismo nombre de pila y el primer apellido está en el canónico
        candidatos = [jid for jid, tokens in jugadores if tokens and tokens[0] == nom[0] and ape[0] in tokens[1:]]
        if len(candidatos) == 1:
            return candidatos[0]
        # 2) el canónico entero está dentro del nombre de la fuente
        #    ("Virginia Riera" en "Maria Virginia Riera")
        fuente = set(nom + ape)
        candidatos = [jid for jid, tokens in jugadores if len(tokens) >= 2 and set(tokens) <= fuente]
        if len(candidatos) == 1:
            return candidatos[0]
        # 3) apellido que solo lleva un jugador de ese sexo y el nombre de pila
        #    empieza igual ("Leandro Roman Augsburger" -> "Leo Augsburger"). Con
        #    solo la inicial cruzaba "Muhamad Zaid Patel" con "Manan Patel".
        apellido = ape[-1] if len(ape) == 1 else ape[0]
        con_apellido = [(jid, tokens) for jid, tokens in jugadores if apellido in tokens[1:]]
        if len(con_apellido) == 1 and con_apellido[0][1][0][:2] == nom[0][:2]:
            return con_apellido[0][0]
        return None


def _bloques(stats: dict[str, Any] | None) -> list[tuple[str, dict[str, Any]]]:
    if not stats:
        return []
    salida = []
    for bloque in stats.get("match_state") or []:
        titulo = (bloque.get("title") or "").strip().lower()
        nombre = "partido" if titulo == "match" else titulo.replace(" ", "_")
        salida.append((nombre, bloque))
    return salida


def _metricas(bloque: dict[str, Any], equipo: int) -> dict[str, Any]:
    fila: dict[str, Any] = {}
    for grupo in ("service", "return", "total_points"):
        for s in bloque.get(grupo) or []:
            destino = METRICAS.get(s.get("title"))
            if not destino:
                continue
            col, forma = destino
            v = s.get(f"team_{equipo}") or {}
            if forma == "ratio":
                fila[f"{col}_ganados"] = _entero(v.get("won"))
                fila[f"{col}_jugados"] = _entero(v.get("played"))
            else:
                fila[col] = _entero(v.get("title"))
    return fila


def filas_de_partido(item: dict[str, Any], slug: str, cruce: CruceJugadores, sin_cruzar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    m = item["match"]
    sexo, fase = DRAW.get(m.get("draw_type"), (None, None))
    equipos = {t.get("team_no"): t for t in m.get("teams") or []}
    ganador = _entero(m.get("winner_id"))

    base_equipo: dict[int, dict[str, Any]] = {}
    for n in (1, 2):
        t = equipos.get(n) or {}
        jugadores = (t.get("players") or [])[:2]
        ids, nombres = [], []
        for j in jugadores:
            jid = cruce.buscar(j.get("first_name", ""), j.get("last_name", ""), sexo) if sexo else None
            ids.append(jid)
            nombres.append(f"{j.get('first_name', '')} {j.get('last_name', '')}".strip())
            if jid is None:
                sin_cruzar.append({"torneo": slug, "match_id": m.get("match_id"), "player_id_f1v2": j.get("player_id"),
                                   "nombre": nombres[-1], "sexo": sexo})
        score = t.get("score") or {}
        juegos = [score.get(f"set{i}") for i in range(1, 6) if isinstance(score.get(f"set{i}"), int)]
        base_equipo[n] = {
            "jugador_1_id": ids[0] if ids else None,
            "jugador_2_id": ids[1] if len(ids) > 1 else None,
            "jugador_1_nombre_fuente": nombres[0] if nombres else None,
            "jugador_2_nombre_fuente": nombres[1] if len(nombres) > 1 else None,
            "semilla": _entero(t.get("seed_number")),
            "juegos_por_set": juegos,
            "gana": ganador == n,
        }

    comunes = {
        "partido_id": f"PP2-{m.get('match_id')}",
        "match_id_fuente": str(m.get("match_id")),
        "torneo_slug": slug,
        "torneo_id_fuente": str((equipos.get(1) or {}).get("tournament_id") or ""),
        "fecha": m.get("date"),
        "sexo": sexo,
        "fase": fase,
        "ronda": m.get("round_name"),
        "duracion_min": duracion_min(m.get("duration")),
        "fuente_txt": "Premier Padel · elaboración propia",
    }
    filas = []
    # Sin stats el partido sigue contando (duración, marcador): una fila
    # "partido" por equipo con `stats_vacias`.
    for bloque, datos in _bloques(item.get("stats")) or [("partido", {})]:
        for n in (1, 2):
            fila = {**comunes, "equipo": n, "bloque": bloque, **base_equipo[n], **_metricas(datos, n)}
            fila["stats_vacias"] = not fila.get("puntos_totales_jugados")
            filas.append(fila)
    return filas


def build() -> Path:
    dim_dirs = sorted(p for p in (SILVER_ROOT / "dim_jugador").glob("dt=*") if p.is_dir())
    cruce = CruceJugadores(json.loads((dim_dirs[-1] / "data.json").read_text(encoding="utf-8")))

    # Un partido puede aparecer en varios snapshots; manda el más reciente.
    por_partido: dict[str, tuple[str, dict[str, Any]]] = {}
    for f in sorted(BRONZE_ROOT.glob("tournament=*/dt=*/data.json")):
        slug = f.parent.parent.name.removeprefix("tournament=")
        for item in json.loads(f.read_text(encoding="utf-8"))["items"]:
            por_partido[str(item["match"]["match_id"])] = (slug, item)

    sin_cruzar: list[dict[str, Any]] = []
    filas: list[dict[str, Any]] = []
    for slug, item in por_partido.values():
        filas += filas_de_partido(item, slug, cruce, sin_cruzar)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")
    RECONCILIACION.parent.mkdir(parents=True, exist_ok=True)
    unicos = {(r["player_id_f1v2"], r["nombre"]): r for r in sin_cruzar}
    RECONCILIACION.write_text(json.dumps(list(unicos.values()), indent=2, ensure_ascii=False), encoding="utf-8")

    partidos = {r["partido_id"] for r in filas}
    con_stats = {r["partido_id"] for r in filas if r["bloque"] == "partido" and not r["stats_vacias"]}
    print(f"fact_partido_stats: {len(filas)} filas, {len(partidos)} partidos ({len(con_stats)} con stats), "
          f"{len(unicos)} jugadores sin cruzar -> {OUT_PATH.relative_to(REPO_ROOT)}")
    return OUT_PATH


if __name__ == "__main__":
    build()
