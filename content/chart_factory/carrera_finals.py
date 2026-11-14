"""Carrera a las Finals (15/11/2026): quién entra en las Premier Padel
Finals y quién se queda a las puertas (lee `gold/carrera_finals`).

Los 20 primeros del Race de cada categoría: los 16 que hoy entran, en el
color de énfasis, y los 4 siguientes en gris, con la línea del corte entre
el 16.º y el 17.º. El titular es el primero que se queda fuera y lo que le
falta: ahí está la carrera. Sale los lunes hasta las Finals (calendario.py)
y no pasa por el filtro de repetidos (historial.py): repetir nombres es el
dato.

Reglas y su fuente, en `transform/build_gold_carrera_finals.py`. El mínimo
de 15 torneos de Premier Padel no se comprueba: cada candidato lo avisa.
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

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "gold" / "carrera_finals"
OUT_ROOT = REPO_ROOT / "queue"

SERIE = "Carrera a las Finals"
FINALS_TXT = "Barcelona, del 10 al 13 de diciembre"  # StudyPadel, 12/10/2026
CIERRE_TXT = "tras el Major de México"
MOSTRAR = 20


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("fecha_dato=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise SystemExit(f"No hay datos en {root}")
    return dirs[-1]


def seleccionar(rows: list[dict], categoria: str) -> list[dict]:
    filas = [r for r in rows if r["categoria"] == categoria and r["publicable"]]
    return sorted(filas, key=lambda r: (r["posicion"], -r["puntos"]))[:MOSTRAR]


def _dibujar(filas: list[dict], categoria: str, fecha: str, tamano: tuple[float, float], tema: Tema,
             registro: str, titulo: str, subtitulo: str, fuente: str) -> plt.Figure:
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)
    gris = GRIS_PARED if tema == "claro" else "#4A6A94"
    etiquetas = [f"{r['posicion']}. {r['jugador_nombre']}" for r in filas]
    maximo = max(r["puntos"] for r in filas)
    ax.barh(range(len(filas)), [r["puntos"] for r in filas], height=0.66, zorder=3,
            color=[colores["enfasis"] if r["dentro"] else gris for r in filas])
    ax.invert_yaxis()
    ax.set_yticks(list(range(len(filas))))
    ax.set_yticklabels(etiquetas, fontsize=10.5 if tamano == TAMANO_X else 10)
    margen_izq = margen_etiquetas_y(fig, etiquetas, fontsize_pt=10.5)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)
    ax.set_xlim(0, maximo * 1.32)
    fondo = {"facecolor": colores["fondo"], "edgecolor": "none", "pad": 1}
    for i, r in enumerate(filas):
        texto = formato_es(r["puntos"])
        if r.get("puntos_diff_semana"):
            texto += f"  ({formato_es(r['puntos_diff_semana'], signo=True)})"
        ax.text(r["puntos"] + maximo * 0.012, i, texto, va="center", ha="left", fontproperties=Fuentes.cifra(),
                fontsize=9.5, color=colores["texto_principal"], bbox=fondo, zorder=5)
    n_dentro = sum(r["dentro"] for r in filas)
    if 0 < n_dentro < len(filas):
        ax.axhline(n_dentro - 0.5, color=colores["texto_principal"], linestyle=(0, (4, 3)), linewidth=1.2, zorder=4)
        ax.text(maximo * 1.3, n_dentro - 0.6, f"corte: {filas[0]['plazas']} plazas", ha="right", va="bottom",
                fontproperties=Fuentes.cifra(), fontsize=10, color=colores["texto_principal"], zorder=5)

    pildora_serie(fig, SERIE, tema)
    top = titulo_y_subtitulo(fig, titulo, subtitulo, tema)
    pie_de_grafico(fig, fuente, tema, registro)
    fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top, bottom=0.1 if tamano == TAMANO_X else 0.08)
    return fig


def build(categoria: str = "men") -> dict:
    dt_dir = _latest_dir(GOLD_ROOT)
    fecha = dt_dir.name.removeprefix("fecha_dato=")
    rows = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
    filas = seleccionar(rows, categoria)
    dentro = [r for r in filas if r["dentro"]]
    fuera = [r for r in filas if not r["dentro"]]
    if not dentro or not fuera:
        raise SystemExit(f"Race sin corte visible para categoria={categoria} en {fecha}")
    ultimo, primero_fuera = dentro[-1], fuera[0]
    falta = primero_fuera["margen_corte"]
    cat_txt = "masculino" if categoria == "men" else "femenino"

    titulo = (f"{primero_fuera['jugador_nombre']}, a {formato_es(falta)} puntos de las Finals" if falta > 0 else
              f"Empate en el corte de las Finals: {ultimo['jugador_nombre']} y {primero_fuera['jugador_nombre']}")
    subtitulo = (f"Race {cat_txt} 2026: entran los {ultimo['plazas']} primeros, uno a uno · cierra {CIERRE_TXT} · "
                 f"(puntos de la semana)")
    fuente = f"{ultimo['fuente_txt']} — Race del {fecha}"

    out_dir = OUT_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    registro = siguiente_registro()
    salidas: dict[str, Path] = {}
    for tema, tamano, sufijo in (("claro", TAMANO_X, "16x9"), ("claro", TAMANO_IG, "4x5"), ("oscuro", TAMANO_X, "16x9_oscuro")):
        fig = _dibujar(filas, categoria, fecha, tamano, tema, registro, titulo, subtitulo, fuente)
        out_file = out_dir / f"carrera_finals_{categoria}_{sufijo}.png"
        guardar_figura(fig, out_file, tema)
        plt.close(fig)
        salidas[sufijo] = out_file
        print(f"{registro} {out_file}")

    avisos = ["el mínimo de 15 torneos de Premier Padel para optar a las Finals no está comprobado: "
              "revisa que nadie de dentro del corte lo incumpla"]
    if ultimo["empate_en_corte"]:
        avisos.append("hay un empate en el puesto del corte: más de 16 jugadores con posición <= 16")
    return {
        "publicable": True,
        "avisos": avisos,
        "registro": registro,
        "serie": SERIE,
        "tabla_gold": "carrera_finals",
        "fecha_dato": fecha,
        "values": {
            "jugador_ultimo_dentro": ultimo["jugador_nombre"],
            "puntos_ultimo_dentro": ultimo["puntos"],
            "jugador_primero_fuera": primero_fuera["jugador_nombre"],
            "puntos_primero_fuera": primero_fuera["puntos"],
            "puntos_que_le_faltan": falta,
            "plazas": ultimo["plazas"],
            "cierre_race": CIERRE_TXT,
            "finals": FINALS_TXT,
            "circuito": cat_txt,
        },
        "fuente_txt": fuente,
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
    }


if __name__ == "__main__":
    build("men")
    build("women")
