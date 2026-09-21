"""Pádel Mercado (doc 02 §4 / backlog #8-9) — pistas mundiales según FIP vs
Playtomic, la comparación "dos fuentes, dos cifras, sin mezclar" (doc 01 §6).
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
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "mercado_pais"
OUT_ROOT = REPO_ROOT / "queue"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(fip_pistas: float, playtomic_pistas: float, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    etiquetas = ["FIP\n(World Padel Report 2025)", "Playtomic\n(Global Padel Report 2026)"]
    valores = [fip_pistas, playtomic_pistas]
    colores_barra = [CRISTAL, GRIS_PARED]

    x_pos = range(len(etiquetas))
    ax.bar(x_pos, valores, color=colores_barra, width=0.5, zorder=3)
    ax.set_xticks(list(x_pos))
    ax.set_xticklabels(etiquetas, fontsize=12)
    ax.yaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_yticks([])
    limpiar_ejes(ax, tema)
    ax.set_ylim(0, max(valores) * 1.25)

    for x, valor in zip(x_pos, valores):
        ax.text(x, valor + max(valores) * 0.03, f"{valor:,.0f}".replace(",", "."), ha="center", va="bottom", fontproperties=Fuentes.cifra(), fontsize=14, color=colores["texto_principal"])

    pildora_serie(fig, "Pádel Mercado", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{fip_pistas:,.0f} o {playtomic_pistas:,.0f} pistas: depende de a quién preguntes".replace(",", "."),
        f"Pistas de pádel en el mundo según dos informes de mercado independientes · {fecha}",
        tema,
    )
    pie_de_grafico(fig, f"FIP World Padel Report 2025 + Playtomic Global Padel Report 2026 · elaboración propia — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=0.1, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.16)
    else:
        fig.subplots_adjust(left=0.14, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.14)

    return fig


def build() -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))

    fip_row = next(r for r in rows if r["fuente"] == "fip" and r["pais"] == "GLOBAL" and r["categoria"] == "pistas")
    # La cifra global de Playtomic vive en contexto_txt (texto libre), no en
    # un campo numérico propio — se valida que siga ahí antes de usarla.
    playtomic_global = next(r for r in rows if r["fuente"] == "playtomic" and r["pais"] == "GLOBAL")
    if "58.334 pistas" not in (playtomic_global.get("contexto_txt") or ""):
        raise SystemExit("La cifra de pistas de Playtomic ya no coincide con la transcrita a mano — revisar mercado_playtomic_2026.csv")
    playtomic_pistas = 58334.0

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(fip_row["valor"], playtomic_pistas, fecha, tamano, tema, registro)
        out_file = out_dir / f"mercado_pistas_mundo_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    return {
        "registro": registro,
        "serie": "Pádel Mercado",
        "tabla_gold": "mercado_pais",
        "fecha_dato": fecha,
        "values": {
            "pistas_fip": fip_row["valor"],
            "pistas_playtomic": playtomic_pistas,
        },
        "fuente_txt": f"FIP World Padel Report 2025 + Playtomic Global Padel Report 2026 · elaboración propia — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build()
