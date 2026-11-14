"""#StatsDePista, otro ángulo (14/11/2026): el mapa saque/resto de las
parejas de la temporada (lee `gold/stats_parejas`, F1).

Dispersión: % de puntos ganados con el saque (eje X) contra % ganados al
resto (eje Y), una pareja por punto (mínimo de partidos de
`build_gold_stats_parejas`, solo filas publicables). Las líneas de puntos
son la mediana de las parejas del gráfico, así que los cuadrantes se leen
solos: arriba a la derecha, las que dominan en los dos lados. Se nombran
la pareja con más puntos totales ganados (el titular, en el color de
énfasis), la mejor al saque, la mejor al resto y las siguientes en puntos
totales hasta `N_ETIQUETAS`.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    GRIS_PARED,
    MARGEN_DERECHO,
    MARGEN_IZQUIERDO,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    Tema,
    colores_tema,
    formato_es,
    guardar_figura,
    limpiar_ejes,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)
from transform.build_gold_stats_parejas import MIN_PARTIDOS

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "stats_parejas"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "Saque y resto"
FUENTE_TXT = "Premier Padel · elaboración propia"
N_ETIQUETAS = 5
MIN_PAREJAS = 8  # con menos, los cuadrantes no dicen nada


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], sexo: str) -> list[dict]:
    validas = [r for r in rows if r["sexo"] == sexo and r["publicable"]
               and None not in (r["pct_puntos_saque"], r["pct_puntos_resto"], r["pct_puntos_totales"])]
    return sorted(validas, key=lambda r: (-r["pct_puntos_totales"], -r["partidos"], r["pareja"]))


def a_etiquetar(parejas: list[dict]) -> list[dict]:
    """El líder en puntos totales, el mejor al saque, el mejor al resto y
    los siguientes en puntos totales, sin repetir."""
    elegidas = [parejas[0],
                max(parejas, key=lambda r: r["pct_puntos_saque"]),
                max(parejas, key=lambda r: r["pct_puntos_resto"])]
    elegidas += parejas[1:]
    vistas: list[dict] = []
    for r in elegidas:
        if r not in vistas:
            vistas.append(r)
    return vistas[:N_ETIQUETAS]


def _etiquetar(ax: plt.Axes, filas: list[dict], lider: dict, colores: dict, rango_x: tuple[float, float],
               rango_y: tuple[float, float]) -> None:
    """Nombres junto a sus puntos: los de la mitad derecha, escritos hacia la
    izquierda (si no, se salen del lienzo), y separados en vertical cuando
    chocan, con una línea fina hasta su punto."""
    centro_x = (rango_x[0] + rango_x[1]) / 2
    sep = (rango_y[1] - rango_y[0]) * 0.055
    colocadas: list[tuple[bool, float]] = []  # (lado izquierdo, y del texto)
    for r in sorted(filas, key=lambda r: -r["pct_puntos_resto"]):
        x, y = r["pct_puntos_saque"], r["pct_puntos_resto"]
        a_la_izquierda = x > centro_x
        y_txt = y + sep * 0.35
        for lado, y_otra in colocadas:
            if lado == a_la_izquierda and abs(y_txt - y_otra) < sep:
                y_txt = y_otra - sep
        colocadas.append((a_la_izquierda, y_txt))
        dx = -(rango_x[1] - rango_x[0]) * 0.012 if a_la_izquierda else (rango_x[1] - rango_x[0]) * 0.012
        es_lider = r is lider
        ax.annotate(
            r["pareja"], (x, y), xytext=(x + dx, y_txt), textcoords="data",
            ha="right" if a_la_izquierda else "left", va="center",
            fontsize=10.5 if es_lider else 9.5,
            fontproperties=Fuentes.titulo() if es_lider else None,
            color=colores["texto_principal"] if es_lider else colores["texto_secundario"], zorder=5,
            arrowprops=None if abs(y_txt - y) < sep * 0.5 else
            {"arrowstyle": "-", "color": colores["texto_secundario"], "linewidth": 0.6, "shrinkA": 0, "shrinkB": 4},
        )


def _dibujar(parejas: list[dict], sexo: str, fecha: str, temporada: int, tamano: tuple[float, float],
             tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)
    gris = GRIS_PARED if tema == "claro" else "#4A6A94"

    xs = [r["pct_puntos_saque"] for r in parejas]
    ys = [r["pct_puntos_resto"] for r in parejas]
    med_x, med_y = statistics.median(xs), statistics.median(ys)
    lider = parejas[0]

    ax.scatter(xs[1:], ys[1:], s=70, color=gris, zorder=3, linewidths=0)
    ax.scatter([xs[0]], [ys[0]], s=160, color=colores["enfasis"], zorder=4, linewidths=0)
    for v, eje in ((med_x, ax.axvline), (med_y, ax.axhline)):
        eje(v, color=colores["texto_secundario"], linestyle=(0, (4, 3)), linewidth=1, zorder=2)

    margen_x = (max(xs) - min(xs)) * 0.12
    margen_y = (max(ys) - min(ys)) * 0.12
    ax.set_xlim(min(xs) - margen_x, max(xs) + margen_x * 2.2)
    ax.set_ylim(min(ys) - margen_y, max(ys) + margen_y * 1.6)

    _etiquetar(ax, a_etiquetar(parejas), lider, colores, (min(xs), max(xs)), (min(ys), max(ys)))

    ax.text(0.99, 0.98, "Dominan con saque y resto", transform=ax.transAxes, ha="right", va="top",
            fontsize=10, color=colores["texto_secundario"])
    ax.set_xlabel("% de puntos ganados con el saque", fontsize=11, color=colores["texto_secundario"])
    ax.set_ylabel("% de puntos ganados al resto", fontsize=11, color=colores["texto_secundario"])
    ax.yaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    limpiar_ejes(ax, tema)
    ax.tick_params(colors=colores["texto_secundario"], labelsize=10)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_fontproperties(Fuentes.cifra())

    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, SERIE, tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{lider['pareja']}: {formato_es(lider['pct_puntos_totales'], 1)} % de los puntos, el máximo",
        f"Circuito {sexo_txt} {temporada}, {len(parejas)} parejas (mín. {MIN_PARTIDOS} partidos) · líneas: mediana",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)
    fig.subplots_adjust(left=MARGEN_IZQUIERDO + 0.04, right=1 - MARGEN_DERECHO, top=top_grafico,
                        bottom=0.16 if tamano == TAMANO_X else 0.12)
    return fig


def build(sexo: str = "M") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    parejas = seleccionar(rows, sexo)
    if len(parejas) < MIN_PAREJAS:
        raise SystemExit(f"Solo {len(parejas)} parejas publicables para sexo={sexo} en {fecha} (mínimo {MIN_PAREJAS})")
    temporada = parejas[0]["temporada"]

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(parejas, sexo, fecha, temporada, tamano, tema, registro)
        out_file = out_dir / f"saque_resto_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file}")

    lider = parejas[0]
    avisos = []
    if parejas[1]["pct_puntos_totales"] == lider["pct_puntos_totales"]:
        avisos.append(f"empate en cabeza con {parejas[1]['pareja']}: el titular nombra solo a {lider['pareja']}")
    return {
        "publicable": True,
        "avisos": avisos,
        "registro": registro,
        "serie": SERIE,
        "tabla_gold": "stats_parejas",
        "fecha_dato": fecha,
        "values": {
            "pareja": lider["pareja"],
            "pct_puntos_totales": lider["pct_puntos_totales"],
            "pct_puntos_saque": lider["pct_puntos_saque"],
            "pct_puntos_resto": lider["pct_puntos_resto"],
            "partidos": lider["partidos"],
            "temporada": temporada,
            "minimo_partidos": MIN_PARTIDOS,
            "circuito": "masculino" if sexo == "M" else "femenino",
        },
        "fuente_txt": f"{FUENTE_TXT} — {fecha}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("M")
    build("F")
