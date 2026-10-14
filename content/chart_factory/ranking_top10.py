"""#RankingLunes — el top 10 de la semana, en puntos.

Barras de puntos de los diez primeros (con empates: el ranking oficial
reparte la misma posición a los dos miembros de una pareja con los mismos
puntos), y a la derecha la variación de puntos de la semana. El énfasis
(cristal) va solo al nº 1; el resto en gris pared (doc 02 §1.2, regla de
oro). Lee `gold/ranking_semana`.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.lideres import lider, values_con_lider
from content.chart_factory.marca import (
    CRISTAL,
    GRIS_PARED,
    MARGEN_DERECHO,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    Tema,
    colores_tema,
    formato_es,
    guardar_figura,
    limpiar_ejes,
    margen_etiquetas_y,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "ranking_semana"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "FIP / Premier Padel · padelapi.org · elaboración propia"
TOP = 10


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], sexo: str) -> list[dict]:
    """Los jugadores con posición <= 10 (pueden ser 11 si hay empate en el 10)."""
    top = [r for r in rows if r["sexo"] == sexo and r["publicable"] and r["posicion"] <= TOP]
    return sorted(top, key=lambda r: (r["posicion"], -r["puntos"], r["jugador_nombre"]))


def _dibujar(top: list[dict], titulo: str, sexo: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    etiquetas = [f"{r['posicion']:>2}  {r['jugador_nombre']}" for r in top]
    valores = [r["puntos"] for r in top]
    primero = top[0]["posicion"]
    colores_barra = [colores["enfasis"] if r["posicion"] == primero else (GRIS_PARED if tema == "claro" else "#4A6A94") for r in top]

    y_pos = list(range(len(top)))
    ax.barh(y_pos, valores, color=colores_barra, height=0.62, zorder=3)
    ax.invert_yaxis()
    ax.set_yticks(y_pos)
    ax.set_yticklabels(etiquetas, fontsize=12)
    margen_izq = margen_etiquetas_y(fig, etiquetas, fontsize_pt=12)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_val = max(valores)
    ax.set_xlim(0, max_val * 1.30)
    for i, r in enumerate(top):
        ax.text(r["puntos"] + max_val * 0.015, i, formato_es(r["puntos"]), va="center", ha="left",
                fontproperties=Fuentes.cifra(), fontsize=11.5, color=colores["texto_principal"])
        diff = r["puntos_diff_semana"]
        ax.text(max_val * 1.30, i, formato_es(diff, signo=True) if diff else "=", va="center", ha="right",
                fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_secundario"])
    ax.text(max_val * 1.30, -0.95, "vs. semana ant.", va="center", ha="right",
            fontproperties=Fuentes.texto(), fontsize=9.5, color=colores["texto_secundario"])

    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, "#RankingLunes", tema)
    top_grafico = titulo_y_subtitulo(fig, titulo, f"Top 10 del ranking {sexo_txt} · puntos y variación semanal, {fecha}", tema)
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)
    fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico - 0.02, bottom=0.1 if tamano == TAMANO_X else 0.09)
    return fig


def build(sexo: str = "M") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    top = seleccionar(rows, sexo)
    if not top:
        raise SystemExit(f"Sin ranking con puntos para sexo={sexo} en {fecha}")

    cabeza = lider(top, "puntos", "posicion", "puntos_diff_semana")
    siguiente = next((r for r in top if r["posicion"] > top[0]["posicion"]), None)
    ventaja = cabeza.fila["puntos"] - siguiente["puntos"] if siguiente else None
    # Título de conclusión en <= 8 palabras (doc 02 §1.2): los nombres ya
    # están en el gráfico; la cifra nueva es la distancia con el siguiente.
    titulo = f"{formato_es(ventaja)} puntos de ventaja en lo más alto" if ventaja else "Así queda el top 10"

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(top, titulo, sexo, fecha, tamano, tema, registro)
        out_file = out_dir / f"ranking_top10_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    values = {
        "puntos_lider": cabeza.fila["puntos"],
        "circuito": "masculino" if sexo == "M" else "femenino",
    }
    if siguiente:
        values |= {"ventaja_puntos": ventaja, "segundo_puesto": siguiente["posicion"]}
    return {
        "publicable": True,
        "avisos": list(cabeza.avisos),
        "registro": registro,
        "serie": "#RankingLunes",
        "tabla_gold": "ranking_semana",
        "fecha_dato": fecha,
        "values": values_con_lider(cabeza, values),
        "fuente_txt": f"{FUENTE_TXT} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("M")
    build("F")
