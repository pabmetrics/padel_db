"""Orquesta `chart_factory` + `copy_factory` + la cola (doc 03 §6):
genera el gráfico, el texto, y escribe el candidato en
`queue/<fecha>/candidates.json`.

`png_16x9`/`png_4x5` guardan aquí la ruta relativa al repo (p.ej.
`queue/2026-09-21/ranking_movimientos_m_16x9.png`), no la URL pública
`https://padeldb.es/cola/...` que describe doc 03 §6 — esa URL solo existe
cuando haya web definitiva y despliegue (Fase 4, migración a Astro). Hasta
entonces, la vía de lectura de la cola es el propio repo de GitHub (doc 03
§4, "vía la URL de la web" es la alternativa que falta).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from content.chart_factory import ganancias, ranking_moves
from content.copy_factory.cola import anadir_candidato
from content.copy_factory.copy_factory import generar_texto

REPO_ROOT = Path(__file__).resolve().parents[2]

# Un generador por serie: build(sexo) -> metadatos del candidato (doc 03 §6).
GENERADORES: dict[str, Callable[[str], dict]] = {
    "ranking_moves": ranking_moves.build,
    "ganancias": ganancias.build,
}


def _ruta_relativa(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)).replace("\\", "/")


def generar_candidato(generador: Callable[[str], dict], sexo: str) -> Path:
    metadatos = generador(sexo)

    textos = generar_texto(metadatos["serie"], metadatos["values"], metadatos["fuente_txt"])

    candidato = {
        "registro": metadatos["registro"],
        "serie": metadatos["serie"],
        "tabla_gold": metadatos["tabla_gold"],
        "fecha_dato": metadatos["fecha_dato"],
        "values": metadatos["values"],
        "fuente_txt": metadatos["fuente_txt"],
        "png_16x9": _ruta_relativa(metadatos["png_16x9"]),
        "png_4x5": _ruta_relativa(metadatos["png_4x5"]),
        "borrador_x": textos["x"],
        "borrador_ig": textos["instagram"],
        "publicable": True,
        "estado": "candidato",
    }

    out_file = anadir_candidato(candidato)
    print(f"{metadatos['registro']} {metadatos['serie']} ({sexo}) -> {out_file.relative_to(REPO_ROOT)}")
    print(f"  X: {textos['x']}")
    return out_file


def main() -> None:
    for generador in GENERADORES.values():
        for sexo in ("M", "F"):
            try:
                generar_candidato(generador, sexo)
            except ValueError as e:
                print(f"  descartado ({sexo}): {e}")


if __name__ == "__main__":
    main()
