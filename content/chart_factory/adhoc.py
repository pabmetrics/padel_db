"""Gráficos a medida pedidos desde Cowork.

Cowork no dibuja: escribe un pedido JSON y este módulo lo valida contra
gold (solo filas `publicable`), lo dibuja con la plantilla de marca y lo
deja en la cola como cualquier otro candidato (registro, texto de
copy_factory, revisión humana). Las cifras salen siempre de gold, nunca
del pedido.

Tipos de pedido:

    {"tipo": "jugadores", "jugadores": ["Alejandro Galan", "..."],
     "metrica": "forma_reciente" | "ganancias"}

    {"tipo": "perfil_top100", "sexo": "M" | "F", "dimension": "altura_cm" | "edad"}

Opcionales en ambos: "titulo" (máx. 10 palabras; por defecto uno
descriptivo), "subtitulo", "serie" (texto de la marca de serie) y
"contexto": una frase que no está en gold y la aporta quien pide el
gráfico ("Lista de España para el Mundial 2026"). Va a `values`, así que
título y texto pueden mencionarla; queda en el candidato para que la
revisión humana la compruebe.

Uso:
    python -m content.chart_factory.adhoc '<json>' --previa DIR   # sin registro ni API
    python -m content.chart_factory.adhoc '<json>'                # a la cola de hoy
    python -m content.chart_factory.adhoc pedido.json             # igual, desde fichero
"""

from __future__ import annotations

import argparse
import difflib
import json
import random
import statistics
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from unidecode import unidecode  # noqa: E402

from content.chart_factory.marca import (  # noqa: E402
    CRISTAL,
    GRIS_PARED,
    MARGEN_DERECHO,
    MARGEN_IZQUIERDO,
    TAMANO_IG,
    TAMANO_X,
    Fuentes,
    colores_tema,
    guardar_figura,
    limpiar_ejes,
    margen_etiquetas_y,
    nueva_figura,
    pie_de_grafico,
    pildora_serie,
    siguiente_registro,
    titulo_y_subtitulo,
)
from content.copy_factory.nombres import cargar_alias  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD = REPO_ROOT / "gold"
DIM_JUGADOR = REPO_ROOT / "silver" / "dim_jugador"

SERIE_POR_DEFECTO = "A medida"
MAX_PALABRAS_TITULO = 10
MAX_JUGADORES = 12
MAX_CARACTERES_CONTEXTO = 120
MIN_POR_TRAMO = 5  # tramos de perfil con menos jugadores se juntan con el vecino
PASO_TRAMO = {"altura_cm": 5, "edad": 3}
ETIQUETA_DIMENSION = {"altura_cm": "altura (cm)", "edad": "edad (años)"}


class PedidoInvalido(ValueError):
    pass


def _ultimo(tabla: Path) -> tuple[str, list[dict]]:
    dirs = sorted(p for p in tabla.glob("*=*") if p.is_dir())
    if not dirs:
        raise PedidoInvalido(f"Sin datos en {tabla.relative_to(REPO_ROOT)}")
    return dirs[-1].name.split("=", 1)[1], json.loads((dirs[-1] / "data.json").read_text(encoding="utf-8"))


def _plano(texto: str) -> str:
    return unidecode(texto).lower().strip()


def resolver_jugadores(nombres: list[str], dim: list[dict] | None = None) -> list[dict]:
    """Nombre del pedido -> fila de `dim_jugador`. Acepta el nombre exacto,
    un alias de `alias_jugadores.csv`, el nombre sin acentos o un
    subconjunto de sus palabras ("Gemma Triay" -> "Gemma Triay Pons") si
    solo encaja un jugador. Nunca por parecido: si no encaja, error con
    sugerencias para que el pedido se corrija (doc 01 §6)."""
    if dim is None:
        dim = _ultimo(DIM_JUGADOR)[1]
    alias = cargar_alias()
    por_plano: dict[str, list[dict]] = {}
    for fila in dim:
        por_plano.setdefault(_plano(fila["nombre_canonico"]), []).append(fila)

    resueltos, errores = [], []
    for nombre in nombres:
        buscado = _plano(alias.get(nombre, nombre))
        candidatos = por_plano.get(buscado, [])
        if not candidatos:
            palabras = set(buscado.split())
            candidatos = [f for clave, filas in por_plano.items() if palabras <= set(clave.split()) for f in filas]
        if len(candidatos) == 1:
            resueltos.append(candidatos[0])
            continue
        if candidatos:
            opciones = ", ".join(sorted(f["nombre_canonico"] for f in candidatos)[:5])
            errores.append(f"{nombre!r} es ambiguo ({opciones})")
        else:
            parecidos = difflib.get_close_matches(buscado, list(por_plano), n=3, cutoff=0.6)
            sugerencia = f" ¿quizá {', '.join(por_plano[p][0]['nombre_canonico'] for p in parecidos)}?" if parecidos else ""
            errores.append(f"{nombre!r} no está en dim_jugador.{sugerencia}")
    if errores:
        raise PedidoInvalido("Jugadores sin resolver: " + "; ".join(errores))
    ids = [f["jugador_id"] for f in resueltos]
    if len(set(ids)) != len(ids):
        raise PedidoInvalido("El pedido repite jugadores")
    return resueltos


def _titulo(pedido: dict, por_defecto: str) -> str:
    titulo = (pedido.get("titulo") or por_defecto).strip()
    if len(titulo.split()) > MAX_PALABRAS_TITULO:
        raise PedidoInvalido(f"Título de más de {MAX_PALABRAS_TITULO} palabras (doc 02 §1.2): {titulo!r}")
    return titulo


def _formato_es(valor: float, decimales: int = 0) -> str:
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


# --- tipo "jugadores" -------------------------------------------------------

def _datos_jugadores(pedido: dict) -> dict:
    nombres = pedido.get("jugadores")
    if not isinstance(nombres, list) or not 2 <= len(nombres) <= MAX_JUGADORES:
        raise PedidoInvalido(f"'jugadores' debe ser una lista de 2 a {MAX_JUGADORES} nombres")
    metrica = pedido.get("metrica", "forma_reciente")
    if metrica not in ("forma_reciente", "ganancias"):
        raise PedidoInvalido("'metrica' debe ser 'forma_reciente' o 'ganancias'")

    jugadores = resolver_jugadores(nombres)
    tabla = "forma_reciente" if metrica == "forma_reciente" else "ganancias_temporada"
    fecha, filas = _ultimo(GOLD / tabla)
    por_id = {f["jugador_id"]: f for f in filas if f["publicable"]}
    _, perfil = _ultimo(GOLD / "perfil_top100")
    ranking = {(f["jugador_nombre"], f["sexo"]): f["ranking"] for f in perfil if f["publicable"]}

    avisos, barras = [], []
    for j in jugadores:
        fila = por_id.get(j["jugador_id"])
        if fila is None:
            avisos.append(f"{j['nombre_canonico']} no tiene fila publicable en gold.{tabla}: fuera del gráfico")
            continue
        barra = {"nombre": fila["jugador_nombre"], "ranking": ranking.get((j["nombre_canonico"], j["sexo"]))}
        if metrica == "forma_reciente":
            barra.update(valor=fila["pct_victorias_8sem"], victorias=fila["victorias_8sem"], partidos=fila["partidos_8sem"])
            if fila["partidos_8sem"] < 8:
                avisos.append(f"{fila['jugador_nombre']}: solo {fila['partidos_8sem']} partidos en 8 semanas")
        else:
            barra.update(valor=fila["ganancias_conocidas_eur"], torneos=fila["n_torneos_con_premio_conocido"])
        barras.append(barra)
    if len(barras) < 2:
        raise PedidoInvalido("Menos de 2 jugadores con datos publicables: no hay gráfico")
    barras.sort(key=lambda b: -b["valor"])

    values: dict[str, Any] = {"n_jugadores": len(barras)}
    for i, b in enumerate(barras, 1):
        values[f"jugador_{i}"] = b["nombre"]
        if metrica == "forma_reciente":
            values |= {f"pct_victorias_{i}": b["valor"], f"victorias_{i}": b["victorias"], f"partidos_{i}": b["partidos"]}
        else:
            values |= {f"ganancias_eur_{i}": b["valor"], f"n_torneos_{i}": b["torneos"]}
        if b["ranking"] is not None:
            values[f"ranking_{i}"] = b["ranking"]

    if metrica == "forma_reciente":
        titulo = "Victorias en las últimas 8 semanas"
        subtitulo = "% de victorias (victorias/partidos) y posición en el ranking"
    else:
        titulo = "Ganancias de la temporada 2026"
        subtitulo = "Ganancias conocidas por torneo y posición en el ranking"
    return {
        "tabla_gold": tabla, "fecha": fecha, "fuente_txt": filas[0]["fuente_txt"], "barras": barras,
        "metrica": metrica, "values": values, "avisos": avisos,
        "titulo": titulo, "subtitulo": f"{subtitulo} · {fecha}",
    }


def _dibujar_jugadores(d: dict, titulo: str, subtitulo: str, serie: str, tamano, registro: str) -> plt.Figure:
    tema = "claro"
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)
    barras = list(reversed(d["barras"]))  # la mayor arriba
    maximo = max(b["valor"] for b in barras)
    nombres = [b["nombre"] for b in barras]
    ax.barh(range(len(barras)), [b["valor"] for b in barras], height=0.6, zorder=3,
            color=[CRISTAL if b["valor"] == maximo else GRIS_PARED for b in barras])
    ax.set_yticks(range(len(barras)))
    ax.set_yticklabels(nombres, fontsize=12)
    margen_izq = margen_etiquetas_y(fig, nombres, fontsize_pt=12)
    ax.set_xticks([])
    limpiar_ejes(ax, tema)
    ax.set_xlim(0, maximo * 1.45)
    for i, b in enumerate(barras):
        if d["metrica"] == "forma_reciente":
            etiqueta = f"{b['valor']:.0f}% ({b['victorias']}/{b['partidos']})"
        else:
            etiqueta = f"{_formato_es(b['valor'])} €"
        if b["ranking"] is not None:
            etiqueta += f" · #{b['ranking']}"
        ax.text(b["valor"] + maximo * 0.02, i, etiqueta, va="center", ha="left",
                fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])
    pildora_serie(fig, serie, tema)
    top = titulo_y_subtitulo(fig, titulo, subtitulo, tema)
    pie_de_grafico(fig, f"{d['fuente_txt']} — {d['fecha']}", tema, registro)
    fig.subplots_adjust(left=margen_izq, right=1 - MARGEN_DERECHO, top=top, bottom=0.1 if tamano == TAMANO_X else 0.09)
    return fig


# --- tipo "perfil_top100" ---------------------------------------------------

def tramos(valores: list[float], paso: int, minimo: int = MIN_POR_TRAMO) -> list[tuple[int, int]]:
    """Tramos [desde, hasta] de `paso` unidades; los extremos con menos de
    `minimo` jugadores se juntan hacia dentro para que ningún tramo se lea
    con dos o tres personas."""
    inicio = int(min(valores) // paso * paso)
    limites = list(range(inicio, int(max(valores)) + paso + 1, paso))
    grupos = [[limites[i], limites[i + 1] - 1] for i in range(len(limites) - 1)]
    grupos = [g for g in grupos if any(g[0] <= v <= g[1] for v in valores)]

    def n(g): return sum(g[0] <= v <= g[1] for v in valores)

    while len(grupos) > 1 and n(grupos[0]) < minimo:
        grupos[1][0] = grupos[0][0]
        grupos.pop(0)
    while len(grupos) > 1 and n(grupos[-1]) < minimo:
        grupos[-2][1] = grupos[-1][1]
        grupos.pop()
    # Los extremos, al dato real: "190–196", no el borde teórico "190–199".
    grupos[0][0], grupos[-1][1] = int(min(valores)), int(max(valores))
    return [tuple(g) for g in grupos]


def spearman(x: list[float], y: list[float]) -> float:
    def rangos(v):
        orden = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(orden):
            j = i
            while j + 1 < len(orden) and v[orden[j + 1]] == v[orden[i]]:
                j += 1
            for k in range(i, j + 1):
                r[orden[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    return statistics.correlation(rangos(x), rangos(y))


def _datos_perfil(pedido: dict) -> dict:
    sexo = pedido.get("sexo")
    dimension = pedido.get("dimension", "altura_cm")
    if sexo not in ("M", "F"):
        raise PedidoInvalido("'sexo' debe ser 'M' o 'F'")
    if dimension not in PASO_TRAMO:
        raise PedidoInvalido(f"'dimension' debe ser una de {sorted(PASO_TRAMO)}")
    fecha, filas = _ultimo(GOLD / "perfil_top100")
    filas = [f for f in filas if f["publicable"] and f["sexo"] == sexo]
    con_dato = [f for f in filas if f.get(dimension) is not None]
    if len(con_dato) < 3 * MIN_POR_TRAMO:
        raise PedidoInvalido(f"Solo {len(con_dato)} jugadores del top 100 con {dimension}")

    grupos = tramos([f[dimension] for f in con_dato], PASO_TRAMO[dimension])
    circuito = "masculino" if sexo == "M" else "femenino"
    values: dict[str, Any] = {"circuito": circuito, "n_jugadores": len(con_dato)}
    series = []
    for i, (desde, hasta) in enumerate(grupos, 1):
        posiciones = sorted(f["ranking"] for f in con_dato if desde <= f[dimension] <= hasta)
        mediana = statistics.median(posiciones)
        mediana = int(mediana) if float(mediana).is_integer() else mediana
        series.append({"desde": desde, "hasta": hasta, "posiciones": posiciones, "mediana": mediana})
        values |= {f"tramo_{i}_desde": desde, f"tramo_{i}_hasta": hasta,
                   f"jugadores_tramo_{i}": len(posiciones), f"mediana_ranking_tramo_{i}": mediana}

    rho = spearman([f[dimension] for f in con_dato], [f["ranking"] for f in con_dato])
    fuerza = "débil" if abs(rho) < 0.3 else "moderada" if abs(rho) < 0.5 else "fuerte"
    avisos = [f"para la revisión: correlación de Spearman {dimension}↔posición = {rho:.2f} "
              f"(negativa = más {dimension} va con mejor ranking; relación {fuerza}). No va al texto"]
    if len(con_dato) < len(filas):
        avisos.append(f"{len(filas) - len(con_dato)} jugadores del top 100 sin {dimension}, fuera del gráfico")
    nombre_dim = ETIQUETA_DIMENSION[dimension].split(" ")[0]
    return {
        "tabla_gold": "perfil_top100", "fecha": fecha, "fuente_txt": con_dato[0]["fuente_txt"],
        "series": series, "dimension": dimension, "values": values, "avisos": avisos,
        "titulo": f"{nombre_dim.capitalize()} y ranking en el top 100 {circuito}",
        "subtitulo": f"Cada punto es un jugador; la línea, su posición mediana por tramo de {ETIQUETA_DIMENSION[dimension]} · {fecha}",
    }


def _dibujar_perfil(d: dict, titulo: str, subtitulo: str, serie: str, tamano, registro: str) -> plt.Figure:
    tema = "claro"
    colores = colores_tema(tema)
    fig, ax = nueva_figura(tamano, tema)
    azar = random.Random(0)  # mismo "jitter" en cada ejecución
    for i, s in enumerate(d["series"]):
        xs = [i + azar.uniform(-0.18, 0.18) for _ in s["posiciones"]]
        ax.scatter(xs, s["posiciones"], s=38, color=GRIS_PARED, zorder=3, linewidths=0)
        ax.hlines(s["mediana"], i - 0.3, i + 0.3, color=CRISTAL, linewidth=4, zorder=4)
        ax.text(i + 0.33, s["mediana"], f"#{_formato_es(s['mediana'], 0 if float(s['mediana']).is_integer() else 1)}",
                va="center", ha="left", fontproperties=Fuentes.cifra(), fontsize=11, color=colores["texto_principal"])
    etiquetas = [f"{s['desde']}–{s['hasta']}\n{len(s['posiciones'])} jug." for s in d["series"]]
    ax.set_xticks(range(len(d["series"])))
    ax.set_xticklabels(etiquetas, fontsize=11)
    ax.set_xlim(-0.6, len(d["series"]) - 0.2)
    ax.set_ylim(103, -2)  # nº 1 arriba
    ax.set_yticks([1, 25, 50, 75, 100])
    ax.set_yticklabels(["#1", "#25", "#50", "#75", "#100"], fontsize=11)
    ax.yaxis.grid(True, color=colores["grid"], linewidth=0.6, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)
    limpiar_ejes(ax, tema)
    pildora_serie(fig, serie, tema)
    top = titulo_y_subtitulo(fig, titulo, subtitulo, tema)
    pie_de_grafico(fig, f"{d['fuente_txt']} — {d['fecha']}", tema, registro)
    fig.subplots_adjust(left=MARGEN_IZQUIERDO + 0.04, right=1 - MARGEN_DERECHO, top=top,
                        bottom=0.16 if tamano == TAMANO_X else 0.12)
    return fig


# --- común ------------------------------------------------------------------

TIPOS = {
    "jugadores": (_datos_jugadores, _dibujar_jugadores),
    "perfil_top100": (_datos_perfil, _dibujar_perfil),
}


def _comprobar_textos_del_pedido(titulo: str, subtitulo: str, serie: str, values: dict, fuente_txt: str) -> None:
    """El título lo puede escribir Cowork: pasa por las mismas
    comprobaciones que el texto de X (cifras solo de `values`, sin
    valoraciones ni especulación)."""
    from content.copy_factory.copy_factory import _numeros_en_texto, _numeros_en_values
    from content.copy_factory.verificaciones import ESPECULACION, VALORATIVOS, _buscar, _plano, comprobar_lexico

    # 8 semanas, top 100 y temporada 2026 salen en los títulos por defecto.
    validos = _numeros_en_values(values) | _numeros_en_texto(fuente_txt) | {"8", "100", "2026"}
    # El contexto es un hecho que aporta quien pide: puede nombrar lo que
    # gold no trae ("Mundial"), pero no valorar ni especular.
    contexto = values.get("contexto", "")
    if problemas := _buscar(VALORATIVOS + ESPECULACION, _plano(contexto)):
        raise PedidoInvalido(f"'contexto' valora o especula: {problemas}")
    for texto in (titulo, subtitulo, serie):
        try:
            comprobar_lexico(texto, serie, values, fuente_txt)
        except ValueError as e:
            raise PedidoInvalido(f"{texto!r}: {e}") from None
        inventadas = _numeros_en_texto(texto) - validos
        if inventadas:
            raise PedidoInvalido(f"{texto!r} tiene cifras que no están en los datos: {sorted(inventadas)}")


def build(pedido: dict, out_dir: Path, registro: str) -> dict:
    """Valida el pedido, dibuja 16:9 y 4:5 en `out_dir` y devuelve los
    metadatos del candidato (mismo contrato que los `build()` de cada
    serie, para `candidatos._escribir_candidato`)."""
    if pedido.get("tipo") not in TIPOS:
        raise PedidoInvalido(f"'tipo' debe ser uno de {sorted(TIPOS)}")
    datos_fn, dibujar_fn = TIPOS[pedido["tipo"]]
    d = datos_fn(pedido)
    titulo = _titulo(pedido, d["titulo"])
    subtitulo = (pedido.get("subtitulo") or d["subtitulo"]).strip()
    serie = (pedido.get("serie") or SERIE_POR_DEFECTO).strip()[:30]
    fuente_txt = f"{d['fuente_txt']} — {d['fecha']}"
    contexto = (pedido.get("contexto") or "").strip()
    if len(contexto) > MAX_CARACTERES_CONTEXTO:
        raise PedidoInvalido(f"'contexto' de más de {MAX_CARACTERES_CONTEXTO} caracteres")
    if contexto:
        d["values"] = {"contexto": contexto, **d["values"]}
        d["avisos"].append(f"contexto aportado en el pedido, no sale de gold: {contexto!r}")
    _comprobar_textos_del_pedido(titulo, subtitulo, serie, d["values"], fuente_txt)

    out_dir.mkdir(parents=True, exist_ok=True)
    salidas = {}
    for tamano, sufijo in ((TAMANO_X, "16x9"), (TAMANO_IG, "4x5")):
        fig = dibujar_fn(d, titulo, subtitulo, serie, tamano, registro)
        salidas[sufijo] = out_dir / f"adhoc_{pedido['tipo']}_{sufijo}.png"
        guardar_figura(fig, salidas[sufijo], "claro")
        plt.close(fig)

    return {
        "registro": registro,
        "serie": serie,
        "tabla_gold": d["tabla_gold"],
        "fecha_dato": d["fecha"],
        "values": {"titulo_grafico": titulo, **d["values"]},
        "fuente_txt": fuente_txt,
        "png_16x9": salidas["16x9"],
        "png_4x5": salidas["4x5"],
        "avisos": d["avisos"],
        "pedido": pedido,
    }


def _leer_pedido(arg: str) -> dict:
    ruta = Path(arg)
    texto = ruta.read_text(encoding="utf-8") if arg.strip().endswith(".json") and ruta.exists() else arg
    try:
        pedido = json.loads(texto)
    except json.JSONDecodeError as e:
        raise PedidoInvalido(f"El pedido no es JSON válido: {e}") from None
    if not isinstance(pedido, dict):
        raise PedidoInvalido("El pedido debe ser un objeto JSON")
    return pedido


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gráfico a medida desde un pedido JSON")
    parser.add_argument("pedido", help="JSON del pedido, o ruta a un .json")
    parser.add_argument("--previa", type=Path, metavar="DIR",
                        help="solo dibuja en DIR: sin registro, sin API, sin tocar la cola")
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today(), help="día de la cola")
    args = parser.parse_args(argv)

    try:
        pedido = _leer_pedido(args.pedido)
        if args.previa:
            meta = build(pedido, args.previa, "#PREVIA")
            print(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in meta.items()}, ensure_ascii=False, indent=2))
            return 0

        from content.copy_factory.candidatos import _escribir_candidato
        from content.copy_factory.copy_factory import _cliente

        _cliente()  # falla antes de gastar un registro
        with tempfile.TemporaryDirectory() as tmp:
            # Valida todo antes de consumir el número de registro.
            build(pedido, Path(tmp) / "validacion", "#PREVIA")
            meta = build(pedido, Path(tmp), siguiente_registro())
            _escribir_candidato(meta, args.fecha.isoformat())
    except PedidoInvalido as e:
        print(f"PEDIDO RECHAZADO: {e}")
        return 2
    except ValueError as e:  # copy_factory no logró un texto que pase las comprobaciones
        print(f"SIN TEXTO VÁLIDO: {e}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
