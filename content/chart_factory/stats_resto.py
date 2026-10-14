"""#StatsDePista — las parejas que más puntos ganan al resto en la temporada
(lee `gold/stats_parejas`, F1).

El resto es donde se rompe un partido de pádel: el saque domina y ganar
puntos al resto es lo escaso. Barras de % de puntos ganados al resto de
las 10 mejores parejas con un mínimo de partidos (ver
`build_gold_stats_parejas.MIN_PARTIDOS`); la primera en cristal.

Winners y errores no forzados no existen en ninguna fuente abierta
(investigado el 29/09/2026: solo los mide Padel Intelligence, sin acceso
programático); esta serie se limita a lo que publica Premier Padel.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
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
from transform.build_gold_stats_parejas import MIN_PARTIDOS

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "stats_parejas"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "#StatsDePista"
FUENTE_TXT = "Premier Padel · elaboración propia"
TOP = 10


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], sexo: str, n: int = TOP) -> list[dict]:
    validas = [r for r in rows if r["sexo"] == sexo and r["publicable"] and r["pct_puntos_resto"] is not None]
    return sorted(validas, key=lambda r: (-r["pct_puntos_resto"], -r["partidos"], r["pareja"]))[:n]


def _dibujar(top: list[dict], sexo: str, fecha: str, temporada: int, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    etiquetas = [r["pareja"].replace(" / ", "\n") if tamano == TAMANO_IG else r["pareja"] for r in top]
    valores = [r["pct_puntos_resto"] for r in top]
    maximo = valores[0]
    gris = GRIS_PARED if tema == "claro" else "#4A6A94"
    ax.barh(range(len(top)), valores, color=[colores["enfasis"] if i == 0 else gris for i in range(len(top))], height=0.62, zorder=3)
    ax.invert_yaxis()
    ax.set_yticks(list(range(len(top))))
    ax.set_yticklabels(etiquetas, fontsize=11.5 if tamano == TAMANO_X else 11)
    margen_izq = margen_etiquetas_y(fig, etiquetas, fontsize_pt=11.5)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    ax.set_xlim(0, maximo * (1.45 if tamano == TAMANO_X else 1.3))
    for i, r in enumerate(top):
        x = r["pct_puntos_resto"] + maximo * 0.015
        ax.text(x, i, f"{formato_es(r['pct_puntos_resto'], 1)} %", va="center", ha="left",
                fontproperties=Fuentes.cifra(), fontsize=11.5, color=colores["texto_principal"])
        ax.text(x + maximo * 0.13, i, f"{r['victorias']}-{r['partidos'] - r['victorias']}", va="center", ha="left",
                fontproperties=Fuentes.cifra(), fontsize=10, color=colores["texto_secundario"])

    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, SERIE, tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{formato_es(maximo, 1)} %: quién gana más puntos al resto",
        f"Puntos ganados al resto, circuito {sexo_txt} {temporada} · cuadro principal, mínimo {MIN_PARTIDOS} partidos · "
        f"a la derecha, victorias-derrotas",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)
    fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top_grafico, bottom=0.1 if tamano == TAMANO_X else 0.09)
    return fig


def build(sexo: str = "M") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    top = seleccionar(rows, sexo)
    if not top:
        raise SystemExit(f"Sin parejas con >= {MIN_PARTIDOS} partidos con stats para sexo={sexo} en {fecha}")
    temporada = top[0]["temporada"]

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(top, sexo, fecha, temporada, tamano, tema, registro)
        out_file = out_dir / f"stats_resto_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    lider = top[0]
    avisos = []
    if len(top) > 1 and top[1]["pct_puntos_resto"] == lider["pct_puntos_resto"]:
        avisos.append(f"empate en cabeza con {top[1]['pareja']}: el titular nombra solo a {lider['pareja']}")
    return {
        "publicable": True,
        "avisos": avisos,
        "registro": registro,
        "serie": SERIE,
        "tabla_gold": "stats_parejas",
        "fecha_dato": fecha,
        "values": {
            "pareja": lider["pareja"],
            "pct_puntos_resto": lider["pct_puntos_resto"],
            "partidos": lider["partidos"],
            "victorias": lider["victorias"],
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
