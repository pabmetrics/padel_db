"""Remontadas — las parejas que más ganan tras perder el primer set
(lee `gold/remontadas`, 14/11/2026).

Las 8 parejas con mejor % de remontada (mínimo de primeros sets perdidos en
`build_gold_remontadas.MIN_PRIMER_SET_PERDIDO`) y, como referencia, la
media de todo el circuito, que es lo que da sentido al dato.
"""

from __future__ import annotations

import json
from pathlib import Path

from content.chart_factory._barras_pareja import GraficoBarras, Referencia, dibujar_y_guardar, empatadas_en_cabeza
from content.chart_factory.marca import formato_es, siguiente_registro
from transform.build_gold_remontadas import MIN_PRIMER_SET_PERDIDO

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "remontadas"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "Remontadas"
TOP = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], categoria: str, n: int = TOP) -> list[dict]:
    validas = [r for r in rows if r["categoria"] == categoria and r["publicable"]]
    return sorted(validas, key=lambda r: (-r["pct_remontada"], -r["primer_set_perdido"], r["pareja"]))[:n]


def build(categoria: str = "men") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    top = seleccionar(rows, categoria)
    if not top:
        raise SystemExit(f"Sin remontadas publicables para categoria={categoria} en {fecha}")

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    media = lider["pct_remontada_circuito"]
    empatadas = empatadas_en_cabeza(top, lambda r: r["pct_remontada"])
    titulo = (f"{lider['pareja']}, la pareja que más remonta" if empatadas == 1 else
              f"{formato_es(lider['pct_remontada'], 0)} % de remontadas: máximo compartido por {empatadas} parejas")
    g = GraficoBarras(
        serie=SERIE,
        titulo=titulo,
        destacadas=empatadas,
        subtitulo=(f"% de partidos ganados tras perder el primer set, circuito {cat_txt} {lider['temporada']} · "
                   f"mínimo {MIN_PRIMER_SET_PERDIDO} primeros sets perdidos · a la derecha, remontadas de las ocasiones"),
        fuente_txt=f"{lider['fuente_txt']} — {fecha}",
        valor=lambda r: r["pct_remontada"],
        cifra=lambda r: f"{formato_es(r['pct_remontada'], 0)} %",
        detalle=lambda r: f"{r['remontadas']} de {r['primer_set_perdido']}",
        referencia=Referencia(media, f"media del circuito: {formato_es(media, 1)} %"),
    )
    registro = siguiente_registro()
    salidas = dibujar_y_guardar(g, top, OUT_ROOT / fecha, f"remontadas_{categoria}", registro)

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
        "tabla_gold": "remontadas",
        "fecha_dato": fecha,
        "values": {
            "pareja": lider["pareja"],
            "pct_remontada": lider["pct_remontada"],
            "remontadas": lider["remontadas"],
            "primer_set_perdido": lider["primer_set_perdido"],
            "pct_remontada_circuito": media,
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
