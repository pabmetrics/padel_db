"""Comprobaciones duras del texto generado (doc 02 §6, doc 03 §4).

El prompt pide sobriedad, pero un modelo económico se sale (visto en la
primera cola real: "la jugadora argentina" sin que la nacionalidad
estuviera en los datos, "refleja su desempeño", "movimiento destacado").
Aquí se comprueba lo que se puede comprobar sin modelo:

- cifras que no están en `values` (ya existía en `copy_factory`),
- adjetivos valorativos y especulación,
- petición de interacción,
- gentilicios y "mundial" cuando los datos no los traen,
- emojis (como mucho uno, y al principio),
- grafía de los nombres (una palabra igual salvo acentos = grafía cambiada).

Todo lanza `ValueError`: el candidato no llega a la cola con ese texto.
Las listas son deliberadamente cortas y sin ambigüedad: prefieren dejar
pasar un adjetivo raro a bloquear texto correcto. Se comparan sobre el
texto sin acentos y en minúsculas.
"""

from __future__ import annotations

import re
from typing import Any

from unidecode import unidecode

from content.copy_factory.nombres import nombres_en_values

VALORATIVOS = (
    r"notable", r"destacad\w*", r"impresionante", r"espectacular", r"brillante", r"excelente",
    r"increible", r"sorprendente", r"historic\w*", r"extraordinari\w*", r"fantastic\w*",
    r"magnific\w*", r"significativ\w*", r"relevante", r"importante", r"impecable", r"sensacional", r"imparable", r"meteoric\w*", r"fulgurante",
)
ESPECULACION = (
    r"consolid\w*", r"progresion", r"desempeno", r"refleja\w*", r"demuestra\w*", r"evidencia\w*",
    r"sugiere\w*", r"indica que", r"apunta\w*", r"seguramente", r"probablemente", r"posiblemente",
    r"quiza\w*", r"podria\w*", r"parece\w*", r"promete\w*",
)
INTERACCION = (
    r"likes?", r"sigueme", r"siguenos", r"comenta\w*", r"rt", r"retuit\w*", r"suscri\w*",
    r"que opinas",
)
# Solo se aceptan si los datos ya traen el país (serie de perfil, mapas, mercado).
GENTILICIOS = (
    r"argentin\w*", r"espanol\w*", r"italian\w*", r"brasilen\w*", r"frances\w*", r"portugues\w*",
    r"chilen\w*", r"mexican\w*", r"aleman\w*", r"belga\w*", r"sueco\w*", r"neerlandes\w*",
    r"holandes\w*", r"paraguay\w*", r"uruguay\w*", r"ingles\w*", r"britanic\w*",
)
# "mundial" solo lo aceptan las series de mercado, que sí hablan del mundo.
HECHOS_NO_DADOS = (r"mundial\w*", r"record\w*")
SERIES_QUE_HABLAN_DEL_MUNDO = {"Pádel Mercado"}

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def _plano(texto: str) -> str:
    return unidecode(texto).lower()


def _buscar(patrones: tuple[str, ...], texto_plano: str) -> list[str]:
    encontrados = re.findall(r"\b(?:" + "|".join(patrones) + r")\b", texto_plano)
    return sorted(set(encontrados))


def comprobar_lexico(texto: str, serie: str, values: dict[str, Any], fuente_txt: str) -> None:
    plano = _plano(texto)
    datos_planos = _plano(" ".join(str(v) for v in values.values()) + " " + fuente_txt)

    problemas: list[str] = []
    for etiqueta, patrones in (("valorativo", VALORATIVOS), ("especulación", ESPECULACION), ("pide interacción", INTERACCION)):
        problemas += [f"{etiqueta}: {p!r}" for p in _buscar(patrones, plano)]

    if "pais" not in values:
        problemas += [f"nacionalidad que no está en los datos: {p!r}" for p in _buscar(GENTILICIOS, plano)]
    if serie not in SERIES_QUE_HABLAN_DEL_MUNDO:
        problemas += [f"hecho que no está en los datos: {p!r}" for p in _buscar(HECHOS_NO_DADOS, plano)]

    # Una palabra que ya aparece en los datos no es una invención del modelo.
    problemas = [p for p in problemas if not re.search(r"\b" + re.escape(p.split(": ", 1)[1].strip("'")) + r"\b", datos_planos)]
    if problemas:
        raise ValueError("Texto fuera de las reglas: " + "; ".join(problemas))


def comprobar_emojis(texto: str) -> None:
    emojis = EMOJI.findall(texto)
    if len(emojis) > 1:
        raise ValueError(f"Más de un emoji ({len(emojis)}): solo uno, al inicio")
    if emojis and not EMOJI.match(texto):
        raise ValueError("El emoji no está al inicio del texto")


def comprobar_grafia_nombres(texto: str, values: dict[str, Any]) -> None:
    """Toda palabra del texto que coincide con una palabra de un nombre de
    `values` salvo por acentos debe ser idéntica a ella (las mayúsculas no cuentan:
    "de" / "De")."""
    exactas: dict[str, set[str]] = {}
    for nombre in nombres_en_values(values):
        for palabra in nombre.split():
            exactas.setdefault(_plano(palabra), set()).add(palabra.lower())

    for palabra in re.findall(r"[^\W\d_]+", texto):
        formas = exactas.get(_plano(palabra))
        if formas and palabra.lower() not in formas:
            raise ValueError(f"Grafía de nombre alterada: {palabra!r} (en los datos: {sorted(formas)})")


def comprobar_texto(texto: str, serie: str, values: dict[str, Any], fuente_txt: str) -> None:
    comprobar_lexico(texto, serie, values, fuente_txt)
    comprobar_emojis(texto)
    comprobar_grafia_nombres(texto, values)
