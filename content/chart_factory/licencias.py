"""Pádel Mercado (doc 02 §4) — evolución de licencias federativas de pádel.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    BOLA,
    CRISTAL,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    Tema,
    colores_tema,
    guardar_figura,
    limpiar_ejes,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "licencias_nacional"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT_CSD = "CSD, Estadística de Deporte Federado"
FUENTE_TXT_FEP = "FEP (dato en vivo)"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(serie_csd: list[dict], punto_fep: dict | None, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    anios = [r["anio"] for r in serie_csd]
    valores = [r["licencias"] for r in serie_csd]

    ax.plot(anios, valores, color=CRISTAL, linewidth=2.5, zorder=3, solid_capstyle="round")
    ax.fill_between(anios, valores, color=CRISTAL, alpha=0.12, zorder=2)

    if punto_fep:
        ax.scatter([punto_fep["anio"]], [punto_fep["licencias"]], color=BOLA, s=70, zorder=4, edgecolor=colores["fondo"], linewidth=1.5)
        ax.annotate(
            f"{punto_fep['licencias']:,.0f}".replace(",", ".") + " (en vivo)",
            (punto_fep["anio"], punto_fep["licencias"]),
            textcoords="offset points",
            xytext=(-8, 12),
            ha="right",
            fontproperties=Fuentes.cifra(),
            fontsize=10.5,
            color=colores["texto_principal"],
        )

    primero, ultimo = serie_csd[0], serie_csd[-1]
    ax.annotate(
        f"{primero['licencias']:,.0f}".replace(",", "."),
        (primero["anio"], primero["licencias"]),
        textcoords="offset points",
        xytext=(0, 12),
        ha="center",
        fontproperties=Fuentes.cifra(),
        fontsize=10.5,
        color=colores["texto_secundario"],
    )
    ax.annotate(
        f"{ultimo['licencias']:,.0f}".replace(",", "."),
        (ultimo["anio"], ultimo["licencias"]),
        textcoords="offset points",
        xytext=(0, 12),
        ha="center",
        fontproperties=Fuentes.cifra(),
        fontsize=10.5,
        color=colores["texto_principal"],
    )

    ax.yaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_yticks([])
    ax.set_xticks([primero["anio"], 2000, 2010, 2020, ultimo["anio"]])
    limpiar_ejes(ax, tema)
    ax.set_ylim(0, max(valores) * 1.2)

    pildora_serie(fig, "Pádel Mercado", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"De {primero['licencias']:,.0f} a {ultimo['licencias']:,.0f} licencias".replace(",", "."),
        f"Licencias federativas de pádel en España, {primero['anio']}-{ultimo['anio']}",
        tema,
    )
    fuente_txt = f"{FUENTE_TXT_CSD}" + (f" + {FUENTE_TXT_FEP}" if punto_fep else "") + f" · elaboración propia — {fecha}"
    pie_de_grafico(fig, fuente_txt, tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=0.06, right=0.95, top=top_grafico, bottom=0.14)
    else:
        fig.subplots_adjust(left=0.1, right=0.93, top=top_grafico, bottom=0.12)

    return fig


def build() -> list[Path]:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    # Solo 2000 en adelante: 1980-1985 es un tramo real pero desconectado
    # (sin dato 1986-1999, ver docs/campos-licencias-padel.md) — dibujarlo
    # unido a 2000 con una línea recta sugeriría datos que no existen.
    # También coincide con el rango que ya cita el backlog del proyecto.
    serie_csd = sorted(
        (r for r in rows if r["fuente"] == "csd" and r["sexo"] == "total" and r["publicable"] and r["anio"] >= 2000),
        key=lambda r: r["anio"],
    )
    if not serie_csd:
        raise SystemExit(f"Sin serie de licencias CSD publicable en {fecha}")

    anio_max_csd = serie_csd[-1]["anio"]
    fep_totales = [r for r in rows if r["fuente"] == "fep" and r["sexo"] == "total" and r["anio"] > anio_max_csd]
    punto_fep = max(fep_totales, key=lambda r: r["anio"]) if fep_totales else None

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas = []
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(serie_csd, punto_fep, fecha, tamano, tema, registro)
        out_file = out_dir / f"licencias_nacional_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas.append(out_file)
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    return salidas


if __name__ == "__main__":
    build()
