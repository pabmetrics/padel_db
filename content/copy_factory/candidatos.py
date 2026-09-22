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

import argparse
from datetime import date
from pathlib import Path
from typing import Callable

from content.chart_factory import (
    forma_reciente,
    ganancias,
    h2h,
    licencias,
    mercado,
    parejas,
    perfil,
    pistas,
    ranking_moves,
    sorpresas,
    torneo_previa,
    trends,
)
from content.copy_factory.calendario import cargar_torneos, series_del_dia
from content.copy_factory.cola import anadir_candidato
from content.copy_factory.copy_factory import _cliente, generar_texto
from content.copy_factory.nombres import normalizar_nombres, verificar_nombres

REPO_ROOT = Path(__file__).resolve().parents[2]

# Generadores que producen un candidato por cada valor de un parámetro
# (sexo "M"/"F", o categoría "men"/"women" — cada `build()` usa el nombre
# que ya tenía antes de integrarse aquí, no se ha unificado la convención
# de chart_factory solo para esto).
GENERADORES_CON_PARAMETRO: dict[str, tuple[Callable[[str], dict], tuple[str, str]]] = {
    "ranking_moves": (ranking_moves.build, ("M", "F")),
    "ganancias": (ganancias.build, ("M", "F")),
    "perfil": (perfil.build, ("M", "F")),
    "forma_reciente": (forma_reciente.build, ("M", "F")),
    "parejas": (parejas.build, ("men", "women")),
    "h2h": (h2h.build, ("men", "women")),
    "sorpresas": (sorpresas.build, ("men", "women")),
    "torneo_previa": (torneo_previa.build, ("men", "women")),
}

# Generadores de una sola serie, sin distinción de sexo/categoría.
GENERADORES_SIN_PARAMETRO: dict[str, Callable[[], dict]] = {
    "pistas": pistas.build,
    "licencias": licencias.build,
    "mercado": mercado.build,
    "trends": trends.build,
}


def _ruta_relativa(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT)).replace("\\", "/")


def _escribir_candidato(metadatos: dict) -> Path:
    """`metadatos` puede traer `publicable` (False si el propio gráfico sabe
    que el dato no da para un post) y `avisos`. Un candidato no publicable
    se guarda igualmente, con sus gráficos y el motivo, pero sin borrador:
    un texto pulido invita a publicarlo ("si dudas del dato, no sale")."""
    values = normalizar_nombres(metadatos["values"])
    avisos = list(metadatos.get("avisos", []))
    publicable = metadatos.get("publicable", True)

    avisos_nombres, bloquea = verificar_nombres(values)
    avisos += avisos_nombres
    publicable = publicable and not bloquea

    textos = generar_texto(metadatos["serie"], values, metadatos["fuente_txt"]) if publicable else None

    candidato = {
        "registro": metadatos["registro"],
        "serie": metadatos["serie"],
        "tabla_gold": metadatos["tabla_gold"],
        "fecha_dato": metadatos["fecha_dato"],
        "values": values,
        "fuente_txt": metadatos["fuente_txt"],
        "png_16x9": _ruta_relativa(metadatos["png_16x9"]),
        "png_4x5": _ruta_relativa(metadatos["png_4x5"]),
        "borrador_x": textos["x"] if textos else None,
        "borrador_ig": textos["instagram"] if textos else None,
        "publicable": publicable,
        "avisos": avisos,
        "estado": "candidato",
    }

    out_file = anadir_candidato(candidato)
    print(f"{metadatos['registro']} {metadatos['serie']} -> {out_file.relative_to(REPO_ROOT)}")
    for aviso in avisos:
        print(f"  aviso: {aviso}")
    print(f"  X: {textos['x']}" if textos else "  no publicable: sin borrador")
    return out_file


def generar_candidato(generador: Callable[[str], dict], parametro: str) -> Path:
    return _escribir_candidato(generador(parametro))


def generar_candidato_simple(generador: Callable[[], dict]) -> Path:
    return _escribir_candidato(generador())


SERIES_DISPONIBLES = sorted({*GENERADORES_CON_PARAMETRO, *GENERADORES_SIN_PARAMETRO})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today(),
                        help="día para el que se decide qué series tocan (por defecto, hoy)")
    parser.add_argument("--todas", action="store_true",
                        help="ignora el calendario y genera todas las series (solo para pruebas)")
    parser.add_argument("--serie", action="append", choices=SERIES_DISPONIBLES, metavar="SERIE",
                        help=f"genera solo esta serie (repetible), ignorando el calendario del día. "
                             f"Opciones: {', '.join(SERIES_DISPONIBLES)}. Sigue pasando por copy_factory "
                             f"y la cola igual que una generación normal (registro real, texto validado)")
    args = parser.parse_args(argv)

    if args.serie:
        series = set(args.serie)
        print(f"series pedidas a mano (fuera de calendario): {sorted(series)}")
    else:
        series = None if args.todas else series_del_dia(args.fecha, cargar_torneos())
        if series is not None:
            print(f"{args.fecha} ({args.fecha:%A}): series que tocan -> {sorted(series) or 'ninguna'}")

    # Falla antes de dibujar nada: cada gráfico consume un número de registro.
    _cliente()

    errores = 0
    for nombre, (generador, valores) in GENERADORES_CON_PARAMETRO.items():
        if series is not None and nombre not in series:
            continue
        for valor in valores:
            try:
                generar_candidato(generador, valor)
            except ValueError as e:
                print(f"  descartado ({nombre}, {valor}): {e}")
            except Exception as e:  # noqa: BLE001 - un fallo (API, red) no debe tumbar el resto
                errores += 1
                print(f"  ERROR ({nombre}, {valor}): {type(e).__name__}: {e}")

    for nombre, generador in GENERADORES_SIN_PARAMETRO.items():
        if series is not None and nombre not in series:
            continue
        try:
            generar_candidato_simple(generador)
        except ValueError as e:
            print(f"  descartado ({nombre}): {e}")
        except Exception as e:  # noqa: BLE001
            errores += 1
            print(f"  ERROR ({nombre}): {type(e).__name__}: {e}")

    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
