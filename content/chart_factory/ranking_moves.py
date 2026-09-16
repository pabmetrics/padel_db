"""#RankingLunes — gráfico de movimientos de la semana.

Primera versión, suficiente para el "hecho" de Fase 1 (doc 01 §8: "el lunes
se genera solo el gráfico de movimientos del ranking"). No es todavía el
`chart_factory` completo de Fase 4 (faltan tipografías de marca instaladas,
píldora de serie, marca de agua, exportado a los tres tamaños) — eso se hace
cuando se monte la fábrica de contenido de verdad.

Paleta y reglas de doc 02 §1.2: fondo arena, cristal para lo positivo, coral
para lo negativo, gris pared para lo neutro, un solo color de énfasis por
gráfico (aquí, dos, porque el formato es "quién sube / quién baja").
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "ranking_movimientos_semana"
OUT_ROOT = REPO_ROOT / "queue"

PISTA = "#0F3463"
CRISTAL = "#1FB5A8"
CORAL = "#FF6B4A"
ARENA = "#F4F1EA"
GRIS_PARED = "#B8B5AD"
TEXTO_SECUNDARIO = "#6B6963"

N_JUGADORES = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def build(sexo: str = "M") -> Path:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    candidatos = [r for r in rows if r["publicable"] and r["sexo"] == sexo]
    candidatos.sort(key=lambda r: -abs(r["posicion_diff_semana"]))
    top = candidatos[:N_JUGADORES]
    top.sort(key=lambda r: r["posicion_diff_semana"])  # mayor caída arriba, mayor subida abajo

    if not top:
        raise SystemExit(f"Sin movimientos publicables para sexo={sexo} en {fecha}")

    fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
    fig.patch.set_facecolor(ARENA)
    ax.set_facecolor(ARENA)

    nombres = [r["jugador_nombre"] for r in top]
    valores = [r["posicion_diff_semana"] for r in top]
    colores = [CRISTAL if v > 0 else CORAL for v in valores]

    y_pos = range(len(top))
    ax.barh(y_pos, valores, color=colores, height=0.6, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=13, color=PISTA)
    ax.axvline(0, color=GRIS_PARED, linewidth=1)
    ax.xaxis.grid(True, color=GRIS_PARED, linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False)

    max_abs = max(abs(v) for v in valores)
    ax.set_xlim(-max_abs * 1.35, max_abs * 1.35)

    for i, r in enumerate(top):
        signo = "+" if r["posicion_diff_semana"] > 0 else ""
        etiqueta = f"{signo}{int(r['posicion_diff_semana'])} (#{r['posicion']})"
        # Etiqueta siempre fuera de la barra, hacia el lado en el que hay hueco
        # (nunca hacia el eje de las categorías): así no se solapa ni con la
        # barra ni con los nombres, sea cual sea su longitud.
        offset = max_abs * 0.02
        if r["posicion_diff_semana"] > 0:
            x, align = r["posicion_diff_semana"] + offset, "left"
        else:
            x, align = r["posicion_diff_semana"] - offset, "right"
        ax.text(
            x,
            i,
            etiqueta,
            va="center",
            ha=align,
            fontsize=11,
            color=PISTA,
            family="monospace",
        )

    top_subida = max(top, key=lambda r: r["posicion_diff_semana"])
    sexo_txt = "masculino" if sexo == "M" else "femenino"
    fig.suptitle(
        f"Mayor subida de la semana: {top_subida['jugador_nombre']}",
        fontsize=20,
        color=PISTA,
        weight="bold",
        x=0.06,
        ha="left",
    )
    ax.set_title(
        f"Movimientos del ranking {sexo_txt} · puestos ganados o perdidos esta semana",
        fontsize=12,
        color=TEXTO_SECUNDARIO,
        loc="left",
        pad=14,
    )

    fig.text(
        0.06,
        0.02,
        f"Fuente: FIP / Premier Padel · padelapi.org · elaboración propia — {fecha}",
        fontsize=9,
        color=TEXTO_SECUNDARIO,
    )
    fig.text(0.94, 0.02, "@padeldb", fontsize=9, color=PISTA, ha="right", weight="bold")

    fig.subplots_adjust(left=0.22, right=0.95, top=0.85, bottom=0.1)

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"ranking_movimientos_{sexo.lower()}_16x9.png"
    fig.savefig(out_file, facecolor=ARENA)
    plt.close(fig)

    print(f"{out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build("M")
    build("F")
