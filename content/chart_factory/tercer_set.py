"""Tercer set — las parejas que más ganan cuando el partido se decide en el
tercer set (lee `gold/tercer_set`, 14/11/2026).
"""

from __future__ import annotations

import json
from pathlib import Path

from content.chart_factory._barras_pareja import GraficoBarras, Referencia, dibujar_y_guardar, empatadas_en_cabeza
from content.chart_factory.marca import formato_es, siguiente_registro
from transform.build_gold_tercer_set import MIN_TERCEROS_SETS

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "tercer_set"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "Tercer set"
TOP = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], categoria: str, n: int = TOP) -> list[dict]:
    validas = [r for r in rows if r["categoria"] == categoria and r["publicable"]]
    return sorted(validas, key=lambda r: (-r["pct_tercer_set"], -r["terceros_sets"], r["pareja"]))[:n]


def build(categoria: str = "men") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    top = seleccionar(rows, categoria)
    if not top:
        raise SystemExit(f"Sin parejas con >= {MIN_TERCEROS_SETS} terceros sets para categoria={categoria} en {fecha}")

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    empatadas = empatadas_en_cabeza(top, lambda r: r["pct_tercer_set"])
    titulo = (f"{lider['pareja']}: {formato_es(lider['pct_tercer_set'], 0)} % en el tercer set, el máximo" if empatadas == 1 else
              f"{formato_es(lider['pct_tercer_set'], 0)} % en el tercer set: máximo compartido por {empatadas} parejas")
    g = GraficoBarras(
        serie=SERIE,
        titulo=titulo,
        destacadas=empatadas,
        subtitulo=(f"% de partidos ganados de los que llegaron al tercer set, circuito {cat_txt} {lider['temporada']} · "
                   f"mínimo {MIN_TERCEROS_SETS} · a la derecha, ganados de jugados"),
        fuente_txt=f"{lider['fuente_txt']} — {fecha}",
        valor=lambda r: r["pct_tercer_set"],
        cifra=lambda r: f"{formato_es(r['pct_tercer_set'], 0)} %",
        detalle=lambda r: f"{r['terceros_sets_ganados']} de {r['terceros_sets']}",
        referencia=Referencia(50, "50 %"),
    )
    registro = siguiente_registro()
    salidas = dibujar_y_guardar(g, top, OUT_ROOT / fecha, f"tercer_set_{categoria}", registro)

    avisos = []
    values_empate = {}
    if empatadas > 1:
        avisos.append(f"empate en cabeza entre {empatadas} parejas: values nombra a {lider['pareja']}, el título no")
        values_empate = {"parejas_empatadas_en_cabeza": empatadas}
    return {
        "publicable": True,
        "avisos": avisos,
        "registro": registro,
        "serie": SERIE,
        "tabla_gold": "tercer_set",
        "fecha_dato": fecha,
        "values": {
            "pareja": lider["pareja"],
            "pct_tercer_set": lider["pct_tercer_set"],
            "terceros_sets_ganados": lider["terceros_sets_ganados"],
            "terceros_sets": lider["terceros_sets"],
            "temporada": lider["temporada"],
            "circuito": cat_txt,
            **values_empate,
        },
        "fuente_txt": f"{lider['fuente_txt']} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("men")
    build("women")
