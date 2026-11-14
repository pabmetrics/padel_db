"""Matagigantes — las parejas que más ganan a cabezas de serie mejor
situadas (lee `gold/matagigantes`, 14/11/2026).

Las 8 parejas con más victorias de la temporada ante una pareja mejor
sembrada en ese torneo. No es "la sorpresa del día" (eso es "El torneo en
datos"), es quién lo hace a menudo.
"""

from __future__ import annotations

import json
from pathlib import Path

from content.chart_factory._barras_pareja import GraficoBarras, dibujar_y_guardar, empatadas_en_cabeza
from content.chart_factory.marca import siguiente_registro
from transform.build_gold_matagigantes import MIN_VICTORIAS

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "matagigantes"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "Matagigantes"
TOP = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], categoria: str, n: int = TOP) -> list[dict]:
    validas = [r for r in rows if r["categoria"] == categoria and r["publicable"]]
    return sorted(validas, key=lambda r: (-r["victorias_ante_mejor_semilla"], r["partidos_ante_mejor_semilla"],
                                          r["pareja"]))[:n]


def build(categoria: str = "men") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    top = seleccionar(rows, categoria)
    if not top:
        raise SystemExit(f"Sin matagigantes publicables para categoria={categoria} en {fecha}")

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    empatadas = empatadas_en_cabeza(top, lambda r: r["victorias_ante_mejor_semilla"])
    n = lider["victorias_ante_mejor_semilla"]
    titulo = (f"{lider['pareja']}, quien más gana a mejores cabezas de serie" if empatadas == 1 else
              f"{n} victorias ante mejores cabezas de serie: máximo compartido por {empatadas} parejas")
    g = GraficoBarras(
        serie=SERIE,
        titulo=titulo,
        destacadas=empatadas,
        subtitulo=(f"Victorias ante una pareja mejor sembrada en el torneo, circuito {cat_txt} {lider['temporada']} · "
                   f"a la derecha, de cuántos partidos así"),
        fuente_txt=f"{lider['fuente_txt']} — {fecha}",
        valor=lambda r: r["victorias_ante_mejor_semilla"],
        cifra=lambda r: str(r["victorias_ante_mejor_semilla"]),
        detalle=lambda r: f"de {r['partidos_ante_mejor_semilla']}",
    )
    registro = siguiente_registro()
    salidas = dibujar_y_guardar(g, top, OUT_ROOT / fecha, f"matagigantes_{categoria}", registro)

    avisos = []
    values_empate = {}
    if empatadas > 1:
        avisos.append(f"empate en cabeza entre {empatadas} parejas: values nombra a {lider['pareja']} "
                      f"(menos partidos así), el título no")
        values_empate = {"parejas_empatadas_en_cabeza": empatadas}
    return {
        "publicable": True,
        "avisos": avisos,
        "registro": registro,
        "serie": SERIE,
        "tabla_gold": "matagigantes",
        "fecha_dato": fecha,
        "values": {
            "pareja": lider["pareja"],
            "victorias": lider["victorias_ante_mejor_semilla"],
            "partidos": lider["partidos_ante_mejor_semilla"],
            "mejor_semilla_eliminada": lider["mejor_semilla_eliminada"],
            "temporada": lider["temporada"],
            "minimo_victorias": MIN_VICTORIAS,
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
