"""Campeones de la semana — infografía con los ganadores de los torneos que
terminaron la semana anterior (lee `gold/ganadores_semana`).

No es un gráfico de barras sino una tabla: una fila por torneo (de más a
menos puntos en juego), una columna por categoría. En cada celda, la
pareja campeona y, debajo, la final (finalistas y marcador). Un cuadro no
publicable (sin final en la fuente, o cuadro mezclado entre categorías)
sale como "sin dato verificado": se ve que falta, pero no se inventa.

El torneo de más nivel lleva la marca cristal (regla de un solo énfasis,
doc 02 §1.2).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.marca import (
    MARGEN_DERECHO,
    MARGEN_IZQUIERDO,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    Tema,
    colores_tema,
    guardar_figura,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "ganadores_semana"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "Campeones de la semana"
MAX_TORNEOS = {TAMANO_X: 5, TAMANO_IG: 8}


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def agrupar_por_torneo(filas: list[dict]) -> list[dict]:
    """[{torneo_nombre, nivel, orden_nivel, M: fila|None, F: fila|None}], en
    el orden del gold (nivel y nombre)."""
    torneos: dict[str, dict] = {}
    for f in filas:
        t = torneos.setdefault(f["torneo_id"], {"torneo_nombre": f["torneo_nombre"], "nivel": f["nivel"], "orden_nivel": f["orden_nivel"], "M": None, "F": None})
        t[f["sexo"]] = f
    return sorted(torneos.values(), key=lambda t: (t["orden_nivel"], t["torneo_nombre"]))


def _fecha_es(iso: str) -> str:
    a, m, d = iso.split("-")
    return f"{int(d)}/{int(m)}/{a}"


def _celda(fig: plt.Figure, x: float, y: float, fila: dict | None, colores: dict, alto_linea: float, fs: float) -> None:
    if not fila or not fila["publicable"]:
        fig.text(x, y, "sin dato verificado", fontproperties=Fuentes.texto(), fontsize=fs - 1,
                 color=colores["texto_secundario"], va="top", style="italic")
        return
    j1, j2 = fila["campeones"].split(" / ")
    for i, nombre in enumerate((j1, j2)):
        fig.text(x, y - i * alto_linea, nombre, fontproperties=Fuentes.texto_medio(), fontsize=fs,
                 color=colores["texto_principal"], va="top")
    detalle = []
    if fila.get("marcador_final"):
        detalle.append(fila["marcador_final"])
    if fila.get("semilla_campeones"):
        detalle.append(f"cabezas de serie nº {fila['semilla_campeones']}")
    if detalle:
        fig.text(x, y - 2 * alto_linea - alto_linea * 0.15, "Final: " + " · ".join(detalle), fontproperties=Fuentes.cifra(),
                 fontsize=fs - 3, color=colores["texto_secundario"], va="top")


def _dibujar(torneos: list[dict], ini: str, fin: str, n_total: int, tamano: tuple[float, float], tema: Tema, registro: str, titulo: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)
    ax.set_axis_off()

    pildora_serie(fig, SERIE, tema)
    omitidos = n_total - len(torneos)
    subtitulo = f"Torneos terminados del {_fecha_es(ini)} al {_fecha_es(fin)} · parejas campeonas y final"
    if omitidos > 0:
        subtitulo += f" · y {omitidos} más en padeldb.es"
    y_top = titulo_y_subtitulo(fig, titulo, subtitulo, tema)
    pie_de_grafico(fig, f"Premier Padel / FIP · padelapi.org · elaboración propia — {fin}", tema, registro)

    alto_in = fig.get_size_inches()[1]
    fs = 15 if len(torneos) <= 3 else (13.5 if tamano == TAMANO_X else 12.5)
    alto_linea = fs * 1.35 / 72 / alto_in
    # Filas repartidas en el alto disponible (hasta el pie), con un tope
    # para que tres torneos no queden separados por medio lienzo.
    lineas_por_fila = 4.6 if tamano == TAMANO_IG else 3.4
    disponible = y_top - 0.13 - alto_linea * 1.8
    alto_fila = min(alto_linea * lineas_por_fila * 1.6, max(alto_linea * lineas_por_fila, disponible / max(len(torneos), 1)))
    if tamano == TAMANO_IG:
        alto_fila -= alto_linea * 1.25  # la línea del nombre del torneo ya baja `y` aparte
    x_torneo = MARGEN_IZQUIERDO
    x_m = 0.36 if tamano == TAMANO_X else 0.38
    x_f = 0.66 if tamano == TAMANO_X else 0.69
    if tamano == TAMANO_IG:
        # En 4:5 no caben tres columnas con nombres completos: el torneo va
        # encima, a ancho completo, y las dos categorías debajo.
        x_m, x_f = MARGEN_IZQUIERDO, 0.53

    y = y_top - 0.01
    for etiqueta, x in (("TORNEO", x_torneo), ("MASCULINO", x_m), ("FEMENINO", x_f)):
        if tamano == TAMANO_IG and etiqueta == "TORNEO":
            continue
        fig.text(x, y, etiqueta, fontproperties=Fuentes.cifra(), fontsize=10, color=colores["texto_secundario"], va="top")
    y -= alto_linea * 1.3

    for i, t in enumerate(torneos):
        fig.add_artist(plt.Line2D([MARGEN_IZQUIERDO, 1 - MARGEN_DERECHO], [y, y], transform=fig.transFigure,
                                  color=colores["grid"], linewidth=0.8, alpha=0.7))
        y -= alto_linea * 0.5
        if i == 0:
            fig.patches.append(plt.Rectangle((MARGEN_IZQUIERDO - 0.018, y - alto_linea * 0.8), 0.007, alto_linea * 0.75,
                                             transform=fig.transFigure, facecolor=colores["enfasis"], edgecolor="none"))
        if tamano == TAMANO_IG:
            fig.text(x_torneo, y, t["torneo_nombre"], fontproperties=Fuentes.titulo(), fontsize=fs + 0.5,
                     color=colores["texto_principal"], va="top")
            y -= alto_linea * 1.25
            _celda(fig, x_m, y, t["M"], colores, alto_linea, fs)
            _celda(fig, x_f, y, t["F"], colores, alto_linea, fs)
            y -= alto_fila
        else:
            fig.text(x_torneo, y, t["torneo_nombre"], fontproperties=Fuentes.titulo(), fontsize=fs + 0.5,
                     color=colores["texto_principal"], va="top", wrap=False)
            fig.text(x_torneo, y - alto_linea * 1.1, t["nivel"] or "", fontproperties=Fuentes.cifra(), fontsize=fs - 3,
                     color=colores["texto_secundario"], va="top")
            _celda(fig, x_m, y, t["M"], colores, alto_linea, fs)
            _celda(fig, x_f, y, t["F"], colores, alto_linea, fs)
            y -= alto_fila
    return fig


def build() -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    filas = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    torneos = agrupar_por_torneo(filas)
    publicables = [f for f in filas if f["publicable"]]
    if not publicables:
        raise SystemExit(f"Sin campeones verificados en {dt_dir.name}")
    ini, fin = filas[0]["semana_ini"], filas[0]["semana_fin"]

    principal = torneos[0]
    titulo = f"{len(torneos)} torneos, {len(publicables)} parejas campeonas" if len(torneos) > 1 else f"Campeones del {principal['torneo_nombre']}"

    out_dir = OUT_ROOT / fin
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(torneos[: MAX_TORNEOS[tamano]], ini, fin, len(torneos), tamano, tema, registro, titulo)
        out_file = out_dir / f"ganadores_semana_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    # Solo los campeones verificados van a `values`: el texto no puede
    # nombrar a nadie que no esté aquí. Numerados en el orden del gráfico.
    values: dict = {"n_torneos": len(torneos), "n_parejas_campeonas": len(publicables)}
    for i, f in enumerate(sorted(publicables, key=lambda f: (f["orden_nivel"], f["torneo_nombre"], f["sexo"])), start=1):
        values[f"torneo_{i}"] = f"{f['torneo_nombre']} ({'masculino' if f['sexo'] == 'M' else 'femenino'})"
        values[f"campeones_{i}"] = f["campeones"]
    avisos = [f"{f['torneo_nombre']} ({f['sexo']}): {f['motivo_no_publicable']}" for f in filas if not f["publicable"]]
    return {
        "publicable": True,
        "avisos": avisos,
        "registro": registro,
        "serie": SERIE,
        "tabla_gold": "ganadores_semana",
        "fecha_dato": fin,
        "values": values,
        "fuente_txt": f"Premier Padel / FIP · padelapi.org · elaboración propia — {fin}",
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build()
