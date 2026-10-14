"""#RankingLunes — mayores subidas de puntos de la semana (top 100).

Sustituye al gráfico de puestos (`ranking_moves.py`): en la zona alta del
ranking los puestos casi no se mueven aunque entren cientos de puntos
(Stupaczuk, +90 y el mismo #8 el 28/09/2026), y en la baja un puñado de
puntos mueve decenas de puestos. Los puntos cuentan lo que ha pasado en
pista.

Cada barra lleva al lado el puesto actual y, si lo hay, el resultado de la
semana que explica la subida (`resultado_semana` en gold). Solo el
líder en cristal; el resto, en gris pared.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from content.chart_factory.lideres import lider, values_con_lider
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

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "ranking_semana"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "FIP / Premier Padel · padelapi.org · elaboración propia"
N_JUGADORES = 8
# Criterio editorial: una subida menor no sostiene el titular. El gráfico
# sale igual; el candidato queda sin borrador.
UMBRAL_PUNTOS_PUBLICABLE = 50


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], sexo: str, n: int = N_JUGADORES) -> list[dict]:
    subidas = [r for r in rows if r["sexo"] == sexo and r["publicable"] and r["puntos_diff_semana"] > 0]
    return sorted(subidas, key=lambda r: (-r["puntos_diff_semana"], r["posicion"], r["jugador_nombre"]))[:n]


def _dibujar(top: list[dict], sexo: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    nombres = [r["jugador_nombre"] for r in top]
    valores = [r["puntos_diff_semana"] for r in top]
    maximo = valores[0]
    gris = GRIS_PARED if tema == "claro" else "#4A6A94"
    alto_barra = 0.62 if tamano == TAMANO_X else 0.5
    ax.barh(range(len(top)), valores, color=[colores["enfasis"] if v == maximo else gris for v in valores], height=alto_barra, zorder=3)
    ax.invert_yaxis()
    ax.set_yticks(list(range(len(top))))
    ax.set_yticklabels(nombres, fontsize=12)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=12)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    # Contexto (puesto + resultado de la semana): en 16:9, en una columna a
    # la derecha; en 4:5 no cabe al lado y va debajo de la barra.
    en_columna = tamano == TAMANO_X
    ax.set_xlim(0, maximo * (1.9 if en_columna else 1.15))
    for i, r in enumerate(top):
        x = r["puntos_diff_semana"] + maximo * 0.015
        ax.text(x, i, formato_es(r["puntos_diff_semana"], signo=True), va="center", ha="left",
                fontproperties=Fuentes.cifra(), fontsize=11.5, color=colores["texto_principal"])
        contexto = f"#{r['posicion']}"
        if r.get("resultado_semana"):
            contexto += f" · {r['resultado_semana']}"
        if en_columna:
            ax.text(maximo * 1.15, i, contexto, va="center", ha="left",
                    fontproperties=Fuentes.texto(), fontsize=10.5, color=colores["texto_secundario"])
        else:
            ax.text(0, i + 0.46, contexto, va="center", ha="left",
                    fontproperties=Fuentes.texto(), fontsize=10, color=colores["texto_secundario"])

    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, "#RankingLunes", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"Δ +{formato_es(maximo)} puntos: la mayor subida de la semana",
        f"Puntos ganados en el ranking {sexo_txt} (top 100) · puesto actual y resultado de la semana, {fecha}",
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
        raise SystemExit(f"Sin subidas de puntos publicables para sexo={sexo} en {fecha}")

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(top, sexo, fecha, tamano, tema, registro)
        out_file = out_dir / f"ranking_puntos_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    cabeza = lider(top, "puntos_diff_semana", "posicion", "puntos", "resultado_semana")
    fila = cabeza.fila
    subida = fila["puntos_diff_semana"]
    avisos = list(cabeza.avisos)
    if subida < UMBRAL_PUNTOS_PUBLICABLE:
        avisos.append(f"mayor subida de la semana: {subida:+d} puntos, por debajo del umbral de {UMBRAL_PUNTOS_PUBLICABLE}")
    values = {
        "delta_puntos": subida,
        "puntos": fila["puntos"],
        "posicion": fila["posicion"],
        "circuito": "masculino" if sexo == "M" else "femenino",
    }
    if fila.get("resultado_semana"):
        values["resultado_semana"] = fila["resultado_semana"]
    return {
        "publicable": subida >= UMBRAL_PUNTOS_PUBLICABLE,
        "avisos": avisos,
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
