"""El torneo en datos (doc 02 §4) — mayores sorpresas por diferencia de
semilla.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    CRISTAL,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    Tema,
    colores_tema,
    guardar_figura,
    MARGEN_DERECHO,
    limpiar_ejes,
    margen_etiquetas_y,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "torneo_sorpresas"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "padelapi.org · elaboración propia"
N_SORPRESAS = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(top: list[dict], categoria: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    top_asc = sorted(top, key=lambda r: r["diferencia_semillas"])
    nombres = [f"({r['semilla_ganador']}) {r['equipo_ganador']}\nvs ({r['semilla_perdedor']}) {r['equipo_perdedor']}" for r in top_asc]
    valores = [r["diferencia_semillas"] for r in top_asc]

    y_pos = range(len(top_asc))
    ax.barh(y_pos, valores, color=CRISTAL, height=0.55, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=9.5)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=9.5)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_val = max(valores)
    ax.set_xlim(0, max_val * 1.25)
    for i, r in enumerate(top_asc):
        ax.text(r["diferencia_semillas"] + max_val * 0.02, i, f"{r['diferencia_semillas']} puestos", va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=10.5, color=colores["texto_principal"])

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    pildora_serie(fig, "El torneo en datos", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{lider['equipo_ganador']}, la mayor sorpresa de la temporada",
        f"Eliminaciones por diferencia de semilla, circuito {cat_txt} · {fecha}",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.1)
    else:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.09)

    return fig


def build(categoria: str = "men") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    candidatos = [r for r in rows if r["publicable"] and r["categoria"] == categoria]
    candidatos.sort(key=lambda r: -r["diferencia_semillas"])
    top = candidatos[:N_SORPRESAS]

    if not top:
        raise SystemExit(f"Sin sorpresas publicables para categoria={categoria} en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(top, categoria, fecha, tamano, tema, registro)
        out_file = out_dir / f"torneo_sorpresas_{categoria}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    return {
        "registro": registro,
        "serie": "El torneo en datos",
        "tabla_gold": "torneo_sorpresas",
        "fecha_dato": fecha,
        "values": {
            "equipo_ganador": lider["equipo_ganador"],
            "semilla_ganador": lider["semilla_ganador"],
            "equipo_perdedor": lider["equipo_perdedor"],
            "semilla_perdedor": lider["semilla_perdedor"],
            "diferencia_semillas": lider["diferencia_semillas"],
            "torneo": lider["torneo_nombre"],
            "circuito": cat_txt,
        },
        "fuente_txt": f"{FUENTE_TXT} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("men")
    build("women")
