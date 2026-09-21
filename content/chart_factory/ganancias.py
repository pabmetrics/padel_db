"""Cierre de torneo / #ParejasEnDatos — ranking de ganancias de la
temporada (doc 02 §4). Segunda serie migrada a la plantilla de marca.
"""

from __future__ import annotations

import json
from pathlib import Path

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
GOLD_ROOT = REPO_ROOT / "gold" / "ganancias_temporada"
OUT_ROOT = REPO_ROOT / "queue"

N_JUGADORES = 10


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(top: list[dict], sexo: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> "plt.Figure":  # noqa: F821
    import matplotlib.pyplot as plt

    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    top_ordenado = sorted(top, key=lambda r: r["ganancias_conocidas_eur"])
    nombres = [r["jugador_nombre"] for r in top_ordenado]
    valores = [r["ganancias_conocidas_eur"] for r in top_ordenado]

    y_pos = range(len(top_ordenado))
    ax.barh(y_pos, valores, color=CRISTAL, height=0.6, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=12)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=12)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_val = max(valores)
    ax.set_xlim(0, max_val * 1.22)

    for i, valor in enumerate(valores):
        ax.text(
            valor + max_val * 0.02,
            i,
            f"{valor:,.0f} €".replace(",", "."),
            va="center",
            ha="left",
            fontproperties=Fuentes.cifra(),
            fontsize=11,
            color=colores["texto_principal"],
        )

    lider = top_ordenado[-1]
    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, "Cierre de torneo", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{lider['jugador_nombre']} lidera las ganancias de la temporada",
        f"Ganancias conocidas por torneo, circuito {sexo_txt} · temporada 2026",
        tema,
    )
    pie_de_grafico(fig, f"padelearnings.com + padelfip.com + padelapi.org · elaboración propia — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.1)
    else:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.09)

    return fig


def build(sexo: str = "M") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    candidatos = [r for r in rows if r["publicable"] and r["sexo"] == sexo]
    candidatos.sort(key=lambda r: -r["ganancias_conocidas_eur"])
    top = candidatos[:N_JUGADORES]

    if not top:
        raise SystemExit(f"Sin ganancias publicables para sexo={sexo} en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    import matplotlib.pyplot as plt

    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(top, sexo, fecha, tamano, tema, registro)
        out_file = out_dir / f"ganancias_temporada_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    lider = top[0]
    sexo_txt = "masculino" if sexo == "M" else "femenino"
    return {
        "registro": registro,
        "serie": "Cierre de torneo",
        "tabla_gold": "ganancias_temporada",
        "fecha_dato": fecha,
        "values": {
            "jugador": lider["jugador_nombre"],
            "ganancias_eur": lider["ganancias_conocidas_eur"],
            "n_torneos": lider["n_torneos_con_premio_conocido"],
            "circuito": sexo_txt,
        },
        "fuente_txt": f"padelearnings.com + padelfip.com + padelapi.org · elaboración propia — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("M")
    build("F")
