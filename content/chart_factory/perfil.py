"""Perfil del top 100 (doc 02 §4, mensual) — nacionalidades del top 100.
"""

from __future__ import annotations

import json
from collections import Counter
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
    limpiar_ejes,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "perfil_top100"
OUT_ROOT = REPO_ROOT / "queue"

FUENTE_TXT = "padelapi.org · elaboración propia"
N_PAISES = 10

# Códigos ISO-3166-1 alfa-2 que aparecen en el top 100 (F2). Se traducen a
# nombre en español para el gráfico; un código nuevo que no esté aquí se
# muestra tal cual en vez de fallar.
NOMBRE_PAIS = {
    "AE": "Emiratos Árabes Unidos", "AR": "Argentina", "BE": "Bélgica",
    "BR": "Brasil", "CL": "Chile", "DE": "Alemania", "ES": "España",
    "FR": "Francia", "GB": "Reino Unido", "IT": "Italia", "MX": "México",
    "NL": "Países Bajos", "PT": "Portugal", "PY": "Paraguay", "RU": "Rusia",
    "SE": "Suecia", "US": "Estados Unidos",
}


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def _dibujar(conteo: list[tuple[str, int]], sexo: str, fecha: str, tamano: tuple[float, float], tema: Tema, registro: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)

    conteo_asc = list(reversed(conteo))
    nombres = [NOMBRE_PAIS.get(pais, pais) for pais, _ in conteo_asc]
    valores = [n for _, n in conteo_asc]

    y_pos = range(len(conteo_asc))
    ax.barh(y_pos, valores, color=CRISTAL, height=0.6, zorder=3)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(nombres, fontsize=12)
    ax.xaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)

    max_val = max(valores)
    ax.set_xlim(0, max_val * 1.2)
    for i, valor in enumerate(valores):
        ax.text(valor + max_val * 0.02, i, str(valor), va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])

    lider_pais, lider_n = conteo[0]
    sexo_txt = "masculino" if sexo == "M" else "femenino"
    pildora_serie(fig, "Perfil del top 100", tema)
    top_grafico = titulo_y_subtitulo(
        fig,
        f"{NOMBRE_PAIS.get(lider_pais, lider_pais)} domina el top 100 {sexo_txt} con {lider_n} jugadores",
        f"Nacionalidades del top 100 {sexo_txt}, top {N_PAISES} países · {fecha}",
        tema,
    )
    pie_de_grafico(fig, f"{FUENTE_TXT} — {fecha}", tema, registro)

    if tamano == TAMANO_X:
        fig.subplots_adjust(left=0.16, right=0.95, top=top_grafico, bottom=0.1)
    else:
        fig.subplots_adjust(left=0.22, right=0.93, top=top_grafico, bottom=0.09)

    return fig


def build(sexo: str = "M") -> list[Path]:
    dt_dir = _latest_dir(GOLD_ROOT)
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    fecha = max(r["fecha_dato"] for r in rows)

    candidatos = [r for r in rows if r["sexo"] == sexo and r.get("nacionalidad")]
    if not candidatos:
        raise SystemExit(f"Sin perfil publicable para sexo={sexo}")
    conteo = Counter(r["nacionalidad"] for r in candidatos).most_common(N_PAISES)

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()

    salidas = []
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5")):
        fig = _dibujar(conteo, sexo, fecha, tamano, tema, registro)
        out_file = out_dir / f"perfil_top100_{sexo.lower()}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas.append(out_file)
        print(f"{registro} {out_file.relative_to(REPO_ROOT)}")

    return salidas


if __name__ == "__main__":
    build("M")
    build("F")
