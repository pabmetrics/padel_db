"""Cara a cara más repetidos (doc 02 §4) — h2h entre parejas.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    CORAL,
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
GOLD_ROOT = REPO_ROOT / "gold" / "h2h"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "padelapi.org · elaboración propia"
N_H2H = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(top: list[dict], categoria: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    top_asc = sorted(top, key=lambda r: r["total_enfrentamientos"])
    nombres = [f"{r['pareja_1']}\nvs {r['pareja_2']}" for r in top_asc]
    v1 = [r["victorias_pareja_1"] for r in top_asc]
    v2 = [r["victorias_pareja_2"] for r in top_asc]

    y_pos = range(len(top_asc))
    ax.barh(y_pos, v1, color=CRISTAL, height=0.55, zorder=3)
    ax.barh(y_pos, v2, left=v1, color=CORAL, height=0.55, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=9.5)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=9.5)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_val = max(r["total_enfrentamientos"] for r in top_asc)
    ax.set_xlim(0, max_val * 1.2)
    for i, r in enumerate(top_asc):
        etiqueta = f"{r['victorias_pareja_1']}-{r['victorias_pareja_2']}"
        ax.text(r["total_enfrentamientos"] + max_val * 0.02, i, etiqueta, va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    pildora_serie(fig, "Cara a cara", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        "El cruce más repetido del circuito",
        f"Enfrentamientos entre parejas, circuito {cat_txt} (cristal = 1ª pareja, coral = 2ª) · {fecha}",
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
    candidatos.sort(key=lambda r: -r["total_enfrentamientos"])
    top = candidatos[:N_H2H]

    if not top:
        raise SystemExit(f"Sin h2h publicable para categoria={categoria} en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(top, categoria, fecha, tamano, tema, registro)
        out_file = out_dir / f"h2h_{categoria}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    lider = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    return {
        "registro": registro,
        "serie": "Cara a cara",
        "tabla_gold": "h2h",
        "fecha_dato": fecha,
        "values": {
            "pareja_1": lider["pareja_1"],
            "pareja_2": lider["pareja_2"],
            "victorias_pareja_1": lider["victorias_pareja_1"],
            "victorias_pareja_2": lider["victorias_pareja_2"],
            "total_enfrentamientos": lider["total_enfrentamientos"],
            "circuito": cat_txt,
        },
        "fuente_txt": f"{FUENTE_TXT} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("men")
    build("women")
