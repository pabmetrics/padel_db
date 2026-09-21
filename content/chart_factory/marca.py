"""Plantilla de marca compartida por todo `chart_factory` (doc 02 §1.2).

Centraliza lo que todas las series tienen que respetar igual: paleta,
tipografía, píldora de serie, pie con fuente y @padeldb, número de
registro correlativo, y las dos variantes (clara/oscura) y dos tamaños
(1600×900 para X, 1080×1350 para Instagram) que pide el doc.

Las fuentes se referencian siempre por fichero (`FontProperties(fname=...)`)
en vez de por nombre de familia: los TTF de `fonts/` son instancias
estáticas generadas a partir de las variables de Google Fonts
(`fontTools.varLib.instancer`), y su tabla `name` no distingue bien
"Medium" de "Bold" por nombre — referenciar el fichero exacto evita
cualquier ambigüedad de sustitución de fuente de matplotlib.

Icono de marca: `brand/padeldb-favicon.svg` (versión simplificada sin la
rejilla de puntos, rasterizada a mano con `svg.path` + matplotlib — ver
`_icono_favicon()`). El pie de cada gráfico lo usa a 24 px de alto (doc 02
§1.2, punto 6); la píldora "DB" de texto queda como firma compacta para
miniaturas pequeñas, tal como describe el propio doc, no como sustituto
general del icono.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch

REPO_ROOT = Path(__file__).resolve().parents[2]
FONTS_DIR = REPO_ROOT / "fonts"
BRAND_DIR = REPO_ROOT / "brand"
REGISTRO_PATH = Path(__file__).resolve().parent / "registro.json"

# Paleta (doc 02 §1.2)
PISTA = "#0F3463"
CRISTAL = "#1FB5A8"
BOLA = "#D6F000"
CORAL = "#FF6B4A"
ARENA = "#F4F1EA"
GRIS_PARED = "#B8B5AD"
TEXTO_SECUNDARIO = "#6B6963"
TEXTO_SECUNDARIO_OSCURO = "#B8C4D6"

# Tamaños de exportación (doc 02 §1.2, punto 8)
TAMANO_X = (16.0, 9.0)  # -> 1600x900 a dpi=100
TAMANO_IG = (10.8, 13.5)  # -> 1080x1350 a dpi=100
DPI = 100

# Posición del icono en el pie (fracción de figura; origen abajo-izquierda,
# como el resto de coordenadas de `transFigure`).
ICONO_X = 0.935
ICONO_Y = 0.036
ICONO_ALTO_PX = 24

Tema = Literal["claro", "oscuro"]


def _font(nombre_fichero: str) -> FontProperties:
    path = FONTS_DIR / nombre_fichero
    if not path.exists():
        raise FileNotFoundError(f"Falta la fuente de marca: {path}. Ver docs/campos-chart-factory.md")
    font_manager.fontManager.addfont(str(path))
    return FontProperties(fname=str(path))


class Fuentes:
    """Instancia perezosa: cargar los TTF solo cuando hace falta dibujar."""

    _cache: dict[str, FontProperties] = {}

    @classmethod
    def _get(cls, clave: str, fichero: str) -> FontProperties:
        if clave not in cls._cache:
            cls._cache[clave] = _font(fichero)
        return cls._cache[clave]

    @classmethod
    def titulo(cls) -> FontProperties:
        return cls._get("titulo", "SpaceGrotesk-Bold.ttf")

    @classmethod
    def titulo_medio(cls) -> FontProperties:
        return cls._get("titulo_medio", "SpaceGrotesk-Medium.ttf")

    @classmethod
    def cifra(cls) -> FontProperties:
        return cls._get("cifra", "IBMPlexMono-SemiBold.ttf")

    @classmethod
    def cifra_regular(cls) -> FontProperties:
        return cls._get("cifra_regular", "IBMPlexMono-Regular.ttf")

    @classmethod
    def texto(cls) -> FontProperties:
        return cls._get("texto", "IBMPlexSans-Regular.ttf")

    @classmethod
    def texto_medio(cls) -> FontProperties:
        return cls._get("texto_medio", "IBMPlexSans-Medium.ttf")


def colores_tema(tema: Tema) -> dict[str, str]:
    if tema == "claro":
        return {"fondo": ARENA, "texto_principal": PISTA, "texto_secundario": TEXTO_SECUNDARIO, "grid": GRIS_PARED, "enfasis": CRISTAL}
    return {"fondo": PISTA, "texto_principal": ARENA, "texto_secundario": TEXTO_SECUNDARIO_OSCURO, "grid": "#2A4D7A", "enfasis": BOLA}


def siguiente_registro() -> str:
    """Número de registro correlativo (doc 02 §1.2): un contador persistente
    en `content/chart_factory/registro.json`, no reutilizable ni inventado
    por gráfico. En la Fase 4 real este contador lo llevará la cola
    (`queue/`); esta es la versión mínima mientras no exista esa cola."""
    estado = {"ultimo": 0}
    if REGISTRO_PATH.exists():
        estado = json.loads(REGISTRO_PATH.read_text(encoding="utf-8"))
    estado["ultimo"] += 1
    REGISTRO_PATH.write_text(json.dumps(estado), encoding="utf-8")
    return f"#{estado['ultimo']:04d}"


def nueva_figura(tamano: tuple[float, float], tema: Tema) -> tuple[plt.Figure, plt.Axes]:
    colores = colores_tema(tema)
    fig, ax = plt.subplots(figsize=tamano, dpi=DPI)
    fig.patch.set_facecolor(colores["fondo"])
    ax.set_facecolor(colores["fondo"])
    return fig, ax


def pildora_serie(fig: plt.Figure, texto: str, tema: Tema) -> None:
    """Marca de serie arriba a la izquierda (doc 02 §1.2, punto 1): un
    cuadrado cristal seguido del nombre de la serie en mayúsculas,
    monoespaciado (IBM Plex Mono), sin caja de fondo — versión "minimal"
    elegida tras comparar varias alternativas de píldora con el usuario
    (ver docs/campos-chart-factory.md)."""
    colores = colores_tema(tema)
    fontsize = 12.5
    x0, y0 = 0.045, 0.925
    marca_w, marca_h = 0.014, 0.014

    fig.patches.append(
        plt.Rectangle(
            (x0, y0 - marca_h / 2),
            marca_w,
            marca_h,
            transform=fig.transFigure,
            facecolor=CRISTAL,
            edgecolor="none",
            zorder=5,
        )
    )
    fig.text(
        x0 + marca_w + 0.012,
        y0,
        texto.upper(),
        transform=fig.transFigure,
        ha="left",
        va="center",
        fontproperties=Fuentes.cifra(),
        fontsize=fontsize,
        color=colores["texto_principal"],
        zorder=6,
    )


MARGEN_IZQUIERDO = 0.06
MARGEN_DERECHO = 0.06
ANCHO_MAX_TITULO_FRAC = 1 - MARGEN_IZQUIERDO - 0.06
GAP_SUBTITULO_GRAFICO_IN = 0.45


def _envolver_texto(fig: plt.Figure, texto: str, fontproperties: FontProperties, fontsize_pt: float, ancho_max_frac: float) -> list[str]:
    """Parte `texto` en las líneas que hagan falta para no salirse del
    ancho disponible, midiendo con el mismo TTF que se va a dibujar (no
    con `wrap=True` de matplotlib, que estima el ancho con la fuente por
    defecto y no con la de marca)."""
    from PIL import ImageFont

    size_px = round(fontsize_pt * fig.dpi / 72)
    font = ImageFont.truetype(fontproperties.get_file(), size=size_px)
    ancho_max_px = ancho_max_frac * fig.get_size_inches()[0] * fig.dpi

    palabras = texto.split(" ")
    lineas: list[str] = []
    actual = ""
    for palabra in palabras:
        candidato = f"{actual} {palabra}".strip()
        izq, _, der, _ = font.getbbox(candidato)
        if der - izq <= ancho_max_px or not actual:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def titulo_y_subtitulo(fig: plt.Figure, titulo: str, subtitulo: str, tema: Tema) -> float:
    """Título (envuelto a un máximo de 2 líneas; si con la letra normal no
    entra en 2, se reduce el tamaño) + subtítulo. Devuelve la fracción de
    figura en la que debe empezar el área de dibujo del gráfico, a una
    distancia fija **en pulgadas** del subtítulo — no una fracción fija de
    la altura, que en el formato 4:5 (mucho más alto que el 16:9) dejaba un
    hueco enorme entre el texto y el gráfico."""
    colores = colores_tema(tema)
    altura_in = fig.get_size_inches()[1]

    fontsize_titulo = 23
    lineas = _envolver_texto(fig, titulo, Fuentes.titulo(), fontsize_titulo, ANCHO_MAX_TITULO_FRAC)
    if len(lineas) > 2:
        fontsize_titulo = 18
        lineas = _envolver_texto(fig, titulo, Fuentes.titulo(), fontsize_titulo, ANCHO_MAX_TITULO_FRAC)[:2]

    y = 0.83
    paso = (fontsize_titulo * 1.25) / 72 / altura_in
    for i, linea in enumerate(lineas):
        fig.text(
            MARGEN_IZQUIERDO,
            y - i * paso,
            linea,
            transform=fig.transFigure,
            fontproperties=Fuentes.titulo(),
            fontsize=fontsize_titulo,
            color=colores["texto_principal"],
            ha="left",
        )

    y_subtitulo = y - (len(lineas) - 1) * paso - paso * 0.85
    fig.text(
        MARGEN_IZQUIERDO,
        y_subtitulo,
        subtitulo,
        transform=fig.transFigure,
        fontproperties=Fuentes.texto(),
        fontsize=12.5,
        color=colores["texto_secundario"],
        ha="left",
    )

    return y_subtitulo - GAP_SUBTITULO_GRAFICO_IN / altura_in


_ICONO_CACHE: dict[Tema, "Image.Image"] = {}
_FAVICON_SVG = BRAND_DIR / "padeldb-favicon.svg"
_FAVICON_RENDER_PX = 480  # resolución de trabajo antes del downsample final


def _icono_favicon(tema: Tema) -> "Image.Image":
    """Rasteriza `brand/padeldb-icon.png` no vale para el pie del gráfico:
    a 24 px de alto, la rejilla de 12 puntos de la pala se convierte en
    bloques — el detalle del icono completo excede lo que esos píxeles
    pueden resolver, sea cual sea el filtro de reescalado (comprobado con
    LANCZOS y con varios caminos de matplotlib, mismo resultado). El propio
    sistema de marca ya prevé esto: `padeldb-favicon.svg` es la "versión
    simplificada sin agujeros para tamaños pequeños" (doc 02 §1.2).

    No hay una librería de rasterizado de SVG sin dependencias nativas
    fiable en todos los entornos (cairosvg necesita libcairo del sistema;
    no está garantizado en todos los runners de CI), así que este SVG
    concreto —un único `<path>` más 3 `<rect>`, con una transformación
    `translate·scale·translate` fija— se parsea a mano con `svg.path`
    (puro Python) y se dibuja con matplotlib/Agg, que ya es una
    dependencia del proyecto. Si el fichero cambia de estructura, esta
    función falla explícitamente en vez de renderizar algo distinto sin
    avisar."""
    if tema in _ICONO_CACHE:
        return _ICONO_CACHE[tema]

    import re
    import xml.etree.ElementTree as ET

    import numpy as np
    from PIL import Image
    from svg.path import parse_path

    if not _FAVICON_SVG.exists():
        raise FileNotFoundError(f"Falta el favicon de marca: {_FAVICON_SVG}")

    ns = {"svg": "http://www.w3.org/2000/svg"}
    root = ET.parse(_FAVICON_SVG).getroot()
    grupo = root.find("svg:g", ns)
    m = re.match(
        r"translate\(([-\d.]+) ([-\d.]+)\)\s*scale\(([-\d.]+)\)\s*translate\(([-\d.]+) ([-\d.]+)\)",
        grupo.attrib["transform"],
    )
    if not m:
        raise ValueError(f"Transform de {_FAVICON_SVG} con una forma inesperada: {grupo.attrib['transform']}")
    tx1, ty1, escala, tx2, ty2 = (float(v) for v in m.groups())

    def transformar(px: float, py: float) -> tuple[float, float]:
        return (px + tx2) * escala + tx1, (py + ty2) * escala + ty1

    color = ARENA if tema == "oscuro" else PISTA
    fig = plt.figure(figsize=(2, 2), dpi=_FAVICON_RENDER_PX / 2)
    ax = fig.add_axes((0, 0, 1, 1))
    fig.patch.set_alpha(0)

    grupo_relleno = grupo.find("svg:g", ns)
    for elem in grupo_relleno:
        tag = elem.tag.split("}")[-1]
        if tag == "path":
            puntos = []
            for seg in parse_path(elem.attrib["d"]):
                for i in range(21):
                    p = seg.point(i / 20)
                    puntos.append(transformar(p.real, p.imag))
            ax.add_patch(plt.Polygon(puntos, closed=True, facecolor=color, edgecolor="none"))
        elif tag == "rect":
            x, y = float(elem.attrib["x"]), float(elem.attrib["y"])
            w, h = float(elem.attrib["width"]), float(elem.attrib["height"])
            esquinas = [transformar(cx, cy) for cx, cy in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))]
            ax.add_patch(plt.Polygon(esquinas, closed=True, facecolor=color, edgecolor="none"))

    ax.set_xlim(0, 1000)
    ax.set_ylim(0, 1000)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")

    fig.canvas.draw()
    arr = np.asarray(fig.canvas.buffer_rgba())
    img = Image.fromarray(arr, "RGBA")
    plt.close(fig)

    _ICONO_CACHE[tema] = img
    return img


def guardar_figura(fig: plt.Figure, out_file: Path, tema: Tema) -> None:
    """Guarda la figura y compone el icono de marca encima con Pillow, en
    vez de dibujarlo dentro de matplotlib (`OffsetImage`/`imshow`): a los
    tamaños pequeños del pie, componerlo aparte con un resize LANCZOS al
    tamaño final exacto en píxeles da un resultado nítido y predecible,
    frente al reescalado peor (o mal alineado en píxeles) de los caminos
    internos de matplotlib."""
    from PIL import Image

    fig.savefig(out_file, facecolor=fig.get_facecolor())

    icono = _icono_favicon(tema)
    alto_px = round(ICONO_ALTO_PX)
    ancho_px = round(icono.width * alto_px / icono.height)
    icono_final = icono.resize((ancho_px, alto_px), Image.LANCZOS)

    lienzo = Image.open(out_file).convert("RGBA")
    x_px = round(ICONO_X * lienzo.width - ancho_px / 2)
    y_px = round((1 - ICONO_Y) * lienzo.height - alto_px / 2)
    lienzo.paste(icono_final, (x_px, y_px), icono_final)
    lienzo.convert("RGB").save(out_file)


def pildora_db(fig: plt.Figure, x: float, y: float, tema: Tema) -> None:
    """La píldora DB (doc 02 §1.2): firma compacta para miniaturas pequeñas
    donde el icono no cabe — rectángulo 2:1 cristal con 'DB' en IBM Plex
    Mono negrita en color pista. En el pie normal se usa el icono real
    (compuesto en `guardar_figura`); esta píldora queda disponible para
    formatos pequeños."""
    ancho, alto = 0.042, 0.032
    fig.patches.append(
        FancyBboxPatch(
            (x - ancho / 2, y - alto / 2),
            ancho,
            alto,
            transform=fig.transFigure,
            boxstyle="round,pad=0.003,rounding_size=0.006",
            facecolor=CRISTAL,
            edgecolor="none",
            zorder=6,
        )
    )
    fig.text(x, y, "DB", transform=fig.transFigure, ha="center", va="center", fontproperties=Fuentes.cifra(), fontsize=11, color=PISTA, zorder=7)


def pie_de_grafico(fig: plt.Figure, fuente_txt: str, tema: Tema, registro: str | None = None) -> None:
    """Pie fijo (doc 02 §1.2, punto 6): número de registro (discreto, junto
    a la fuente en vez de arriba a la derecha como marca el doc — se
    mantiene el dato pero fuera del área del título, menos protagonismo),
    fuente a la izquierda, hueco para el icono e @padeldb a la derecha. El
    icono en sí no se dibuja aquí (ver `guardar_figura`): se compone con
    Pillow sobre el PNG ya guardado, en la posición `ICONO_X`/`ICONO_Y`."""
    colores = colores_tema(tema)
    texto_fuente = f"{registro} · Fuente: {fuente_txt}" if registro else f"Fuente: {fuente_txt}"
    fig.text(
        0.06,
        0.035,
        texto_fuente,
        transform=fig.transFigure,
        fontproperties=Fuentes.texto(),
        fontsize=9.5,
        color=colores["texto_secundario"],
        ha="left",
    )
    fig.text(
        0.895,
        0.035,
        "@padeldb",
        transform=fig.transFigure,
        fontproperties=Fuentes.texto_medio(),
        fontsize=9.5,
        color=colores["texto_principal"],
        ha="right",
        va="center",
    )

def margen_etiquetas_y(fig: plt.Figure, etiquetas: list[str], fontsize_pt: float = 12, max_frac: float = 0.42, min_frac: float = 0.12) -> float:
    """Margen izquierdo necesario para que las etiquetas del eje Y (nombres
    de jugadores, parejas, provincias...) no se corten — mide el ancho real
    de la línea más larga de cada etiqueta (las hay de dos líneas, p.ej.
    "pareja 1\\nvs pareja 2") con el mismo TTF que se va a dibujar, igual
    que `_envolver_texto` para los títulos. Antes cada gráfico fijaba el
    margen a ojo con un número distinto por formato; con nombres reales de
    jugadoras más largos que los de prueba, el margen se quedaba corto y
    el texto salía cortado por la izquierda en vez de verse completo.
    Limitado a `max_frac` para que un nombre desmesuradamente largo no deje
    el área de dibujo reducida a nada — a partir de ahí, matplotlib recorta
    igualmente, pero es un caso extremo que no se ha visto con datos reales.

    El resultado incluye `MARGEN_IZQUIERDO` (el mismo margen exterior que
    respetan el título, el subtítulo y el pie): sin él, la etiqueta más
    larga quedaba pegada al borde izquierdo del lienzo — cabía entera, pero
    sin aire, mientras que a la derecha sí quedaba el hueco de
    `MARGEN_DERECHO` hasta el borde. Con los dos lados usando el mismo
    margen exterior, la composición queda centrada de verdad."""
    from PIL import ImageFont

    size_px = round(fontsize_pt * fig.dpi / 72)
    font = ImageFont.truetype(Fuentes.texto().get_file(), size=size_px)
    max_ancho_px = 0
    for etiqueta in etiquetas:
        for linea in etiqueta.split("\n"):
            izq, _, der, _ = font.getbbox(linea)
            max_ancho_px = max(max_ancho_px, der - izq)

    fig_w_px = fig.get_size_inches()[0] * fig.dpi
    gap_texto_barra = 0.02
    frac = MARGEN_IZQUIERDO + max_ancho_px / fig_w_px + gap_texto_barra
    return min(max(frac, min_frac), max_frac)


def limpiar_ejes(ax: plt.Axes, tema: Tema) -> None:
    colores = colores_tema(tema)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelcolor=colores["texto_principal"])
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(Fuentes.texto())
