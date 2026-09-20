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

Icono de marca: `brand/padeldb-icon.png` (icono en negativo, PNG con
transparencia). El pie de cada gráfico lo usa a 24 px de alto (doc 02
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
    """Píldora de serie arriba a la izquierda: fondo cristal, texto pista,
    siempre en el mismo sitio (doc 02 §1.2, punto 1)."""
    ancho = 0.018 * (len(texto) + 3)
    fig.patches.append(
        FancyBboxPatch(
            (0.045, 0.90),
            ancho,
            0.055,
            transform=fig.transFigure,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            facecolor=CRISTAL,
            edgecolor="none",
            zorder=5,
        )
    )
    fig.text(
        0.045 + ancho / 2,
        0.927,
        texto,
        transform=fig.transFigure,
        ha="center",
        va="center",
        fontproperties=Fuentes.texto_medio(),
        fontsize=12,
        color=PISTA,
        zorder=6,
    )


def titulo_y_subtitulo(fig: plt.Figure, titulo: str, subtitulo: str, tema: Tema) -> None:
    colores = colores_tema(tema)
    fig.text(
        0.06,
        0.83,
        titulo,
        transform=fig.transFigure,
        fontproperties=Fuentes.titulo(),
        fontsize=23,
        color=colores["texto_principal"],
        ha="left",
    )
    fig.text(
        0.06,
        0.775,
        subtitulo,
        transform=fig.transFigure,
        fontproperties=Fuentes.texto(),
        fontsize=12.5,
        color=colores["texto_secundario"],
        ha="left",
    )


_ICONO_CACHE: dict[Tema, "Image.Image"] = {}


def _icono(tema: Tema) -> "Image.Image":
    """Icono de marca (`brand/padeldb-icon.png`, navy sobre transparente).
    En tema oscuro se recolorea a Arena (icono en negativo), la regla que
    ya fija doc 02 §1.2 para el icono sobre fondo Pista — no hay un fichero
    `-negative` del icono suelto en `brand/` (solo del logo completo), así
    que el recoloreado se hace aquí en vez de mantener un segundo PNG."""
    if tema in _ICONO_CACHE:
        return _ICONO_CACHE[tema]

    from PIL import Image
    import numpy as np

    path = BRAND_DIR / "padeldb-icon.png"
    if not path.exists():
        raise FileNotFoundError(f"Falta el icono de marca: {path}")
    img = Image.open(path).convert("RGBA")

    if tema == "oscuro":
        arr = np.array(img)
        arena_rgb = tuple(int(ARENA[i : i + 2], 16) for i in (1, 3, 5))
        arr[..., 0] = arena_rgb[0]
        arr[..., 1] = arena_rgb[1]
        arr[..., 2] = arena_rgb[2]
        img = Image.fromarray(arr, "RGBA")

    _ICONO_CACHE[tema] = img
    return img


def icono_marca(fig: plt.Figure, x: float, y: float, tema: Tema, alto_px: float = 24) -> None:
    """Icono de marca a `alto_px` de alto (doc 02 §1.2, punto 6: '24 px')."""
    from matplotlib.offsetbox import AnnotationBbox, OffsetImage
    import numpy as np

    img = _icono(tema)
    zoom = alto_px / img.height
    imagebox = OffsetImage(np.array(img), zoom=zoom)
    ab = AnnotationBbox(imagebox, (x, y), xycoords=fig.transFigure, frameon=False, box_alignment=(0.5, 0.5), zorder=6)
    fig.add_artist(ab)


def pildora_db(fig: plt.Figure, x: float, y: float, tema: Tema) -> None:
    """La píldora DB (doc 02 §1.2): firma compacta para miniaturas pequeñas
    donde el icono no cabe — rectángulo 2:1 cristal con 'DB' en IBM Plex
    Mono negrita en color pista. En el pie normal se usa el icono real
    (`icono_marca`); esta píldora queda disponible para formatos pequeños."""
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
    """Pie fijo (doc 02 §1.2, punto 6): fuente a la izquierda, icono a
    24 px y @padeldb a la derecha; número de registro arriba a la derecha."""
    colores = colores_tema(tema)
    fig.text(
        0.06,
        0.035,
        f"Fuente: {fuente_txt}",
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
    icono_marca(fig, 0.935, 0.036, tema)

    if registro:
        fig.text(
            0.945,
            0.955,
            registro,
            transform=fig.transFigure,
            fontproperties=Fuentes.cifra_regular(),
            fontsize=10,
            color=colores["texto_secundario"],
            ha="right",
        )


def limpiar_ejes(ax: plt.Axes, tema: Tema) -> None:
    colores = colores_tema(tema)
    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelcolor=colores["texto_principal"])
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(Fuentes.texto())
