"""Previa en datos (doc 02 §4) — cruces de primera ronda a vigilar del
próximo torneo: cabezas de serie y h2h de los cruces más señalados.

Una sola pieza (no el hilo completo de 5-7 tuits de doc 02 §7): el gráfico
que abre esa previa, con los cruces más interesantes de primera ronda
(los que tienen una cabeza de serie de por medio, o historial entre las
parejas). El resto del hilo (puntos a defender de los favoritos con más
detalle, pregunta de cierre) es texto, y lo cubre copy_factory con los
mismos datos.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    CRISTAL,
    GRIS_PARED,
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
GOLD_ROOT = REPO_ROOT / "gold" / "torneo_previa"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "padelapi.org · elaboración propia"
N_CRUCES = 6


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _orden_interes(r: dict) -> tuple[int, int]:
    """Primero los cruces con cabeza de serie (más baja = más favorita),
    luego por historial entre las parejas."""
    mejor_semilla = min(r["equipo_1_semilla"] or 99, r["equipo_2_semilla"] or 99)
    return (mejor_semilla, -r["h2h_total"])


def _dibujar(top: list[dict], categoria: str, torneo_nombre: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    top_asc = list(reversed(top))
    etiquetas = []
    for r in top_asc:
        s1 = f" (S{r['equipo_1_semilla']})" if r["equipo_1_semilla"] else ""
        s2 = f" (S{r['equipo_2_semilla']})" if r["equipo_2_semilla"] else ""
        etiquetas.append(f"{r['equipo_1']}{s1}\nvs {r['equipo_2']}{s2}")

    y_pos = range(len(top_asc))
    valores = [max(r["h2h_total"], 1) for r in top_asc]  # barra mínima visible aunque no haya h2h
    destacado = [i for i, r in enumerate(top_asc) if r["equipo_1_semilla"] or r["equipo_2_semilla"]]
    colores_barra = [CRISTAL if i in destacado else GRIS_PARED for i in range(len(top_asc))]
    ax.barh(y_pos, valores, color=colores_barra, height=0.55, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(etiquetas, fontsize=9.5)
    margen_izq = margen_etiquetas_y(fig, etiquetas, fontsize_pt=9.5)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_val = max(valores)
    ax.set_xlim(0, max_val * 1.3)
    for i, r in enumerate(top_asc):
        etiqueta = f"{r['h2h_victorias_equipo_1']}-{r['h2h_victorias_equipo_2']}" if r["h2h_total"] else "sin h2h"
        ax.text(valores[i] + max_val * 0.03, i, etiqueta, va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])

    cat_txt = "masculino" if categoria == "men" else "femenino"
    pildora_serie(fig, "Previa en datos", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"Cruces a vigilar en {torneo_nombre}",
        f"Primera ronda, circuito {cat_txt} · cristal = con cabeza de serie · h2h histórico",
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
    if not candidatos:
        raise SystemExit(f"Sin cruces publicables de torneo_previa para categoria={categoria} en {fecha}")
    candidatos.sort(key=_orden_interes)
    top = candidatos[:N_CRUCES]
    torneo_nombre = top[0]["torneo_nombre"]

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(top, categoria, torneo_nombre, fecha, tamano, tema, registro)
        out_file = out_dir / f"torneo_previa_{categoria}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    destacado = top[0]
    cat_txt = "masculino" if categoria == "men" else "femenino"
    return {
        "registro": registro,
        "serie": "Previa en datos",
        "tabla_gold": "torneo_previa",
        "fecha_dato": fecha,
        "values": {
            "torneo": torneo_nombre,
            # "pareja_1"/"pareja_2": mismas claves que h2h.py, reconocidas por
            # nombres.CLAVES_NOMBRE para la verificación de grafía/alias.
            "pareja_1": destacado["equipo_1"],
            "pareja_2": destacado["equipo_2"],
            "pareja_1_semilla": destacado["equipo_1_semilla"],
            "pareja_2_semilla": destacado["equipo_2_semilla"],
            "h2h_victorias_pareja_1": destacado["h2h_victorias_equipo_1"],
            "h2h_victorias_pareja_2": destacado["h2h_victorias_equipo_2"],
            "circuito": cat_txt,
        },
        "fuente_txt": f"{FUENTE_TXT} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("men")
    build("women")
