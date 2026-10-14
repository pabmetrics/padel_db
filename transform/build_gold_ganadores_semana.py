"""Gold: ganadores_semana (doc 02 §4, "Cierre de torneo", en formato de
infografía de la semana).

Una fila = un cuadro (torneo × categoría) cuya final se jugó entre el lunes
y el domingo anteriores a la fecha de referencia (por defecto, el lunes del
último ranking): campeones, finalistas y marcador de la final.

Fuente de los campeones, por orden:
1. la final de `fact_partido` (o de `fact_partido_incompleto`, si se ganó
   por walkover o abandono) con `ganador` conocido;
2. si padelapi oculta el ganador (plan gratuito), la fila `W` de
   `fact_resultado_torneo`, que ya integra las fuentes de respaldo.

`publicable = False`, con el motivo, cuando:
- no hay final en la fuente (o el snapshot de bronze es anterior al
  29/09/2026, cuando la ingesta aún descartaba walkovers y abandonos);
- algún jugador de la final no es del sexo de la categoría: padelapi
  devolvió el cuadro femenino de FIP Silver Houten también como masculino
  (29/09/2026). Publicarlo pondría a las campeonas como campeones.

Uso:
    python transform/build_gold_ganadores_semana.py [--fecha 2026-09-28]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))  # este script se ejecuta como `python transform/build_gold_ganadores_semana.py`

from content.copy_factory.nombres import cargar_alias  # noqa: E402
from transform.build_fact_resultado_torneo import NIVEL_PADELAPI_A_CATEGORIA  # noqa: E402

SILVER_ROOT = REPO_ROOT / "silver"
FACT_PARTIDO = SILVER_ROOT / "fact_partido" / "data.json"
FACT_PARTIDO_INCOMPLETO = SILVER_ROOT / "fact_partido_incompleto" / "data.json"
FACT_RESULTADO = SILVER_ROOT / "fact_resultado_torneo" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "ganadores_semana"

CATEGORIA_A_SEXO = {"men": "M", "women": "F"}
# Orden de la infografía: de más a menos puntos en juego.
ORDEN_NIVEL = ["Finals", "Major", "P1", "P2", "FIP Finals", "FIP Platinum", "FIP Gold", "FIP Silver", "FIP Bronze"]
FUENTE_TXT = "Premier Padel / FIP · padelapi.org · elaboración propia"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def semana_anterior(fecha_ref: date) -> tuple[date, date]:
    lunes = fecha_ref - timedelta(days=fecha_ref.weekday())
    return lunes - timedelta(days=7), lunes - timedelta(days=1)


def marcador_del_campeon(marcador: str | None, equipo_campeon: int) -> str | None:
    """`marcador_txt` de fact_partido va en el orden del equipo 1 de
    padelapi ("6-4, 4-6, 1-6" cuando gana el equipo 2); en la infografía
    se lee desde el campeón ("4-6, 6-4, 6-1")."""
    if not marcador or equipo_campeon == 1:
        return marcador
    return ", ".join("-".join(reversed(s.strip().split("-"))) for s in marcador.split(","))


def _jugadores(p: dict[str, Any], equipo: int) -> list[dict[str, Any]]:
    return [p[f"equipo_{equipo}_jugador_{n}"] for n in (1, 2)]


def construir_filas(
    partidos: list[dict[str, Any]],
    resultados: list[dict[str, Any]],
    sexo_por_jugador: dict[str, str],
    nombre_por_jugador: dict[str, str],
    ini: date,
    fin: date,
) -> list[dict[str, Any]]:
    cuadros: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for p in partidos:
        cuadros.setdefault((p["torneo_id"], p["categoria"]), []).append(p)

    campeones_respaldo = {
        (r["torneo_id"], r["categoria_sexo"]): r for r in resultados if r.get("ronda_alcanzada") == "W"
    }

    filas: list[dict[str, Any]] = []
    for (torneo_id, categoria), ps in cuadros.items():
        ultima = max(date.fromisoformat(str(p["fecha"])[:10]) for p in ps)
        if not (ini <= ultima <= fin):
            continue
        base = ps[0]
        circuito, nivel = NIVEL_PADELAPI_A_CATEGORIA.get(base.get("torneo_nivel_padelapi"), (None, base.get("torneo_nivel_padelapi")))
        sexo = CATEGORIA_A_SEXO.get(categoria)
        fila: dict[str, Any] = {
            "fecha_dato": fin.isoformat(),
            "semana_ini": ini.isoformat(),
            "semana_fin": fin.isoformat(),
            "torneo_id": torneo_id,
            "torneo_nombre": base["torneo_nombre"],
            "circuito": circuito,
            "nivel": nivel,
            "orden_nivel": ORDEN_NIVEL.index(nivel) if nivel in ORDEN_NIVEL else len(ORDEN_NIVEL),
            "sexo": sexo,
            "fecha_final": None,
            "campeones": None,
            "campeones_ids": None,
            "finalistas": None,
            "marcador_final": None,  # desde el campeón; "walkover" o "… (abandono)" si no se terminó
            "semilla_campeones": None,
            "fuente_resultado": None,
            "fuente_txt": FUENTE_TXT,
            "publicable": False,
            "motivo_no_publicable": None,
        }

        final = next((p for p in ps if p["ronda"] == "Finals"), None)
        ganadores = perdedores = None
        if final and final.get("ganador") in ("team_1", "team_2"):
            g = 1 if final["ganador"] == "team_1" else 2
            ganadores, perdedores = _jugadores(final, g), _jugadores(final, 3 - g)
            fila["marcador_final"] = marcador_del_campeon(final.get("marcador_txt"), g)
            if final.get("estado") == "walkover":
                fila["marcador_final"] = "walkover"
            elif final.get("estado") == "abandono":
                fila["marcador_final"] = f"{fila['marcador_final'] or ''} (abandono)".strip()
            fila["semilla_campeones"] = final.get(f"semilla_equipo_{g}")
            fila["fuente_resultado"] = "padelapi"
        elif (torneo_id, categoria) in campeones_respaldo:
            r = campeones_respaldo[(torneo_id, categoria)]
            ganadores = [{"jugador_id": r["jugador_1_id"]}, {"jugador_id": r["jugador_2_id"]}]
            fila["fuente_resultado"] = r.get("fuente_resultado")
        if final:
            fila["fecha_final"] = str(final["fecha"])[:10]

        if ganadores is None:
            fila["motivo_no_publicable"] = "sin final ni campeón en la fuente"
            filas.append(fila)
            continue

        ids = [j["jugador_id"] for j in ganadores]
        fila["campeones_ids"] = " / ".join(ids)
        fila["campeones"] = " / ".join(nombre_por_jugador.get(i, i) for i in ids)
        if perdedores:
            fila["finalistas"] = " / ".join(nombre_por_jugador.get(j["jugador_id"], j["jugador_id"]) for j in perdedores)

        en_final = ids + ([j["jugador_id"] for j in perdedores] if perdedores else [])
        fuera = [nombre_por_jugador.get(i, i) for i in en_final if sexo_por_jugador.get(i) != sexo]
        if fuera:
            fila["motivo_no_publicable"] = (
                f"jugadores de otra categoría en la final {categoria} ({', '.join(fuera)}): error de cuadro en la fuente"
            )
        else:
            fila["publicable"] = True
        filas.append(fila)

    filas.sort(key=lambda f: (f["orden_nivel"], f["torneo_nombre"], f["sexo"] or ""))
    return filas


def build(fecha_ref: date | None = None) -> Path:
    if fecha_ref is None:
        fecha_ref = date.fromisoformat(_latest_dir(SILVER_ROOT / "fact_ranking_semanal").name.removeprefix("fecha_ranking="))
    ini, fin = semana_anterior(fecha_ref)

    partidos = json.loads(FACT_PARTIDO.read_text(encoding="utf-8"))
    if FACT_PARTIDO_INCOMPLETO.exists():
        partidos += json.loads(FACT_PARTIDO_INCOMPLETO.read_text(encoding="utf-8"))
    resultados = json.loads(FACT_RESULTADO.read_text(encoding="utf-8")) if FACT_RESULTADO.exists() else []
    dim = json.loads((_latest_dir(SILVER_ROOT / "dim_jugador") / "data.json").read_text(encoding="utf-8"))
    alias = cargar_alias()
    nombres = {r["jugador_id"]: alias.get(r["nombre_canonico"], r["nombre_canonico"]) for r in dim}
    sexos = {r["jugador_id"]: r["sexo"] for r in dim}

    filas = construir_filas(partidos, resultados, sexos, nombres, ini, fin)

    out_dir = GOLD_ROOT / f"fecha_dato={fin.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"ganadores_semana {ini}..{fin}: {sum(f['publicable'] for f in filas)} de {len(filas)} cuadros publicables")
    for f in filas:
        estado = f["campeones"] if f["publicable"] else f"NO PUBLICABLE — {f['motivo_no_publicable']}"
        print(f"  {f['torneo_nombre']} ({f['sexo']}): {estado}")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fecha", type=date.fromisoformat, default=None,
                        help="fecha de referencia; se toma la semana (lunes-domingo) anterior")
    build(parser.parse_args().fecha)
