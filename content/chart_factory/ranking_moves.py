"""#RankingLunes — gráfico de movimientos de la semana.

Primera serie migrada a la plantilla de marca completa de Fase 4
(`content/chart_factory/marca.py`): tipografía real (Space Grotesk / IBM
Plex), píldora de serie, número de registro correlativo, pie con fuente y
@padeldb, y las dos variantes claras/oscuras en los dos tamaños de
exportación (doc 02 §1.2).
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
    limpiar_ejes,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "ranking_movimientos_semana"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "FIP / Premier Padel · padelapi.org · elaboración propia"
N_JUGADORES = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(top: list[dict], sexo: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    nombres = [r["jugador_nombre"] for r in top]
    valores = [r["posicion_diff_semana"] for r in top]
    colores_barra = [CRISTAL if v > 0 else CORAL for v in valores]

    y_pos = range(len(top))
    ax.barh(y_pos, valores, color=colores_barra, height=0.6, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=12)
    ax.axvline(0, color=colores["grid"], linewidth=1)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_abs = max(abs(v) for v in valores)
    ax.set_xlim(-max_abs * 1.35, max_abs * 1.35)

    for i, r in enumerate(top):
        signo = "+" if r["posicion_diff_semana"] > 0 else ""
        etiqueta = f"{signo}{int(r['posicion_diff_semana'])} (#{r['posicion']})"
        offset = max_abs * 0.02
        if r["posicion_diff_semana"] > 0:
            x, align = r["posicion_diff_semana"] + offset, "left"
        else:
            x, align = r["posicion_diff_semana"] - offset, "right"
        ax.text(x, i, etiqueta, va="center", ha=align, fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])

    sexo_txt = "masculino" if sexo == "M" else "femenino"
    top_subida = max(top, key=lambda r: r["posicion_diff_semana"])
    pildora_serie(fig, "#RankingLunes", tema)
    titulo_y_subtitulo(
        fig,
        f"Δ +{int(top_subida['posicion_diff_semana'])}: la mayor subida de la semana",
        f"Movimientos del ranking {sexo_txt} · puestos ganados o perdidos, semana del {fecha}",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=0.22, right=0.95, top=0.72, bottom=0.1)
    else:
        fig.subplots_adjust(left=0.28, right=0.93, top=0.62, bottom=0.09)

    return fig


def build(sexo: str = "M") -> list[Path]:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    candidatos = [r for r in rows if r["publicable"] and r["sexo"] == sexo]
    candidatos.sort(key=lambda r: -abs(r["posicion_diff_semana"]))
    top = candidatos[:N_JUGADORES]
    top.sort(key=lambda r: r["posicion_diff_semana"])  # mayor caída arriba, mayor subida abajo

    if not top:
        raise SystemExit(f"Sin movimientos publicables para sexo={sexo} en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas = []
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(top, sexo, fecha, tamano, tema, registro)
        out_file = out_dir / f"ranking_movimientos_{sexo.lower()}_{sufijo}.png"
        fig.savefig(out_file, facecolor=fig.get_facecolor())
        plt.close(fig)
        salidas.append(out_file)
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    return salidas


if __name__ == "__main__":
    build("M")
    build("F")
