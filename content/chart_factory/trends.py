"""#MapaDelPádel (doc 02 §4) — interés de búsqueda en países en expansión.
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
GOLD_ROOT = REPO_ROOT / "gold" / "trends_geo"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "Google Trends (pytrends, no oficial) · elaboración propia"
N_PAISES = 10


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(top: list[dict], fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    top_asc = list(reversed(top))
    nombres = [r["pais"] for r in top_asc]
    valores = [r["variacion_pct"] for r in top_asc]
    colores_barra = [CRISTAL if v > 0 else CORAL for v in valores]

    y_pos = range(len(top_asc))
    ax.barh(y_pos, valores, color=colores_barra, height=0.6, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=12)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=12)
    ax.axvline(0, color=colores["grid"], linewidth=1)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_abs = max(abs(v) for v in valores)
    ax.set_xlim(-max_abs * 1.3, max_abs * 1.3)
    for i, valor in enumerate(valores):
        signo = "+" if valor > 0 else ""
        offset = max_abs * 0.02
        x, align = (valor + offset, "left") if valor > 0 else (valor - offset, "right")
        ax.text(x, i, f"{signo}{valor:.0f}%", va="center", ha=align, fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])

    lider = top[0]
    pildora_serie(fig, "#MapaDelPádel", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{lider['pais']} acelera más el interés por el pádel",
        f"Variación trimestral del interés de búsqueda pádel/tenis, países en expansión · {fecha}",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.1)
    else:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.09)

    return fig


def build() -> list[Path]:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    candidatos = [r for r in rows if r["publicable"] and r["variacion_pct"] is not None]
    candidatos.sort(key=lambda r: -r["variacion_pct"])
    top = candidatos[:N_PAISES]

    if not top:
        raise SystemExit(f"Sin datos de trends publicables en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas = []
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(top, fecha, tamano, tema, registro)
        out_file = out_dir / f"trends_geo_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas.append(out_file)
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    return salidas


if __name__ == "__main__":
    build()
