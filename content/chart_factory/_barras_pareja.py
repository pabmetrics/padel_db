"""Dibujo compartido de las series de barras "por pareja" (14/11/2026):
remontadas y matagigantes. Barras horizontales, la primera en el color de
énfasis y el resto en gris (doc 02 §1.2: un solo énfasis), la cifra a la
derecha y, opcionalmente, una línea de referencia (la media del circuito).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    GRIS_PARED,
    MARGEN_DERECHO,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    Tema,
    colores_tema,
    guardar_figura,
    limpiar_ejes,
    margen_etiquetas_y,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Referencia:
    valor: float
    texto: str


def empatadas_en_cabeza(filas: list[dict], valor: Callable[[dict], float]) -> int:
    return sum(1 for r in filas if valor(r) == valor(filas[0]))


@dataclass
class GraficoBarras:
    serie: str
    titulo: str
    subtitulo: str
    fuente_txt: str
    valor: Callable[[dict], float]
    cifra: Callable[[dict], str]
    detalle: Callable[[dict], str] | None = None
    referencia: Referencia | None = None
    destacadas: int = 1  # empate en cabeza: todas las empatadas en el color de énfasis


def _dibujar(g: GraficoBarras, filas: list[dict], tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    etiquetas = [r["pareja"].replace(" / ", "\n") if tamano == TAMANO_IG else r["pareja"] for r in filas]
    valores = [g.valor(r) for r in filas]
    maximo = max(valores + ([g.referencia.valor] if g.referencia else []))
    gris = GRIS_PARED if tema == "claro" else "#4A6A94"
    ax.barh(range(len(filas)), valores, color=[colores["enfasis"] if i < g.destacadas else gris for i in range(len(filas))],
            height=0.62, zorder=3)
    ax.invert_yaxis()
    ax.set_yticks(list(range(len(filas))))
    ax.set_yticklabels(etiquetas, fontsize=11.5 if tamano == TAMANO_X else 11)
    margen_izq = margen_etiquetas_y(fig, etiquetas, fontsize_pt=11.5)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)
    ax.set_xlim(0, maximo * (1.45 if tamano == TAMANO_X else 1.35))

    for i, r in enumerate(filas):
        x = g.valor(r) + maximo * 0.015
        fondo = {"facecolor": colores["fondo"], "edgecolor": "none", "pad": 1.5}  # que la línea de referencia no tape la cifra
        ax.text(x, i, g.cifra(r), va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=11.5,
                color=colores["texto_principal"], bbox=fondo, zorder=5)
        if g.detalle:
            ax.text(x + maximo * 0.12, i, g.detalle(r), va="center", ha="left", fontproperties=Fuentes.cifra(),
                    fontsize=10, color=colores["texto_secundario"], bbox=fondo, zorder=5)

    if g.referencia:
        ax.axvline(g.referencia.valor, color=colores["texto_secundario"], linestyle=(0, (4, 3)), linewidth=1.2, zorder=4)
        ax.text(g.referencia.valor, len(filas) - 0.35, f" {g.referencia.texto}", va="top", ha="left",
                fontproperties=Fuentes.cifra(), fontsize=10, color=colores["texto_secundario"])

    pildora_serie(fig, g.serie, tema)
    top_grafico = titulo_y_subtitulo(fig, g.titulo, g.subtitulo, tema)
    pie_de_grafico(fig, g.fuente_txt, tema, registro)
    fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico,
                        bottom=0.1 if tamano == TAMANO_X else 0.09)
    return fig


def dibujar_y_guardar(g: GraficoBarras, filas: list[dict], out_dir: Path, nombre: str, registro: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(g, filas, tamano, tema, registro)
        out_file = out_dir / f"{nombre}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT) if out_file.is_relative_to(REPO_ROOT) else out_file}")
    return salidas
