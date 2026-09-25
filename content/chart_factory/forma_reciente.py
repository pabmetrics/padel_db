"""Forma reciente (doc 02 §4) — % de victorias en las últimas 8 semanas.
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
from content.chart_factory.lideres import Lider, lider, values_con_lider

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "forma_reciente"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "padelapi.org · elaboración propia"
N_JUGADORES = 10
MIN_PARTIDOS = 8


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(top: list[dict], cabeza: Lider, sexo: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    top_asc = sorted(top, key=lambda r: r["pct_victorias_8sem"])
    nombres = [r["jugador_nombre"] for r in top_asc]
    valores = [r["pct_victorias_8sem"] for r in top_asc]

    y_pos = range(len(top_asc))
    ax.barh(y_pos, valores, color=CRISTAL, height=0.6, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=12)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=12)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)
    ax.set_xlim(0, 108)

    for i, r in enumerate(top_asc):
        etiqueta = f"{r['pct_victorias_8sem']:.0f}% ({r['victorias_8sem']}/{r['partidos_8sem']})"
        ax.text(r["pct_victorias_8sem"] + 2, i, etiqueta, va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])

    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, "Forma reciente", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{cabeza.titular}, el mejor porcentaje de victorias",
        f"% de victorias últimas 8 semanas, circuito {sexo_txt} (mín. {MIN_PARTIDOS} partidos) · {fecha}",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.1)
    else:
        fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.09)

    return fig


def build(sexo: str = "M") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    candidatos = [r for r in rows if r["publicable"] and r["sexo"] == sexo and r["partidos_8sem"] >= MIN_PARTIDOS]
    candidatos.sort(key=lambda r: (-r["pct_victorias_8sem"], -r["partidos_8sem"]))
    top = candidatos[:N_JUGADORES]

    if not top:
        raise SystemExit(f"Sin forma reciente publicable para sexo={sexo} en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    cabeza = lider(top, "pct_victorias_8sem", "victorias_8sem", "partidos_8sem")
    registro = siguiente_registro()

    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(top, cabeza, sexo, fecha, tamano, tema, registro)
        out_file = out_dir / f"forma_reciente_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    fila = cabeza.fila
    sexo_txt = "masculino" if sexo == "M" else "femenino"
    return {
        "avisos": cabeza.avisos,
        "registro": registro,
        "serie": "Forma reciente",
        "tabla_gold": "forma_reciente",
        "fecha_dato": fecha,
        "values": values_con_lider(cabeza, {
            "pct_victorias": fila["pct_victorias_8sem"],
            "victorias": fila["victorias_8sem"],
            "partidos": fila["partidos_8sem"],
            "circuito": sexo_txt,
        }),
        "fuente_txt": f"{FUENTE_TXT} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("M")
    build("F")
