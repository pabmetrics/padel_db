"""La noticia en datos (14/11/2026): el gráfico del día conectado a lo que
cuenta hoy la prensa.

Lee `silver/fact_noticia` (titulares del día con los jugadores reconocidos,
ver `transform/build_fact_noticia.py`), junta los titulares que hablan de
los mismos jugadores (la misma historia en varios medios), elige la más
fuerte y la convierte en un pedido de gráfico a medida (`adhoc.py`, tipo
"jugadores"): forma de las últimas 8 semanas de esos jugadores, o sus
ganancias si la noticia va de premios.

Las cifras salen de gold, nunca del titular. El titular y su enlace van en
el candidato (`noticia`) para la revisión humana, no en el texto: el
borrador solo recibe un contexto neutro ("Son noticia hoy por…"), porque
un titular de prensa suele valorar ("histórico", "arrollan") y eso no
puede llegar al texto de PadelDB.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SILVER_ROOT = REPO_ROOT / "silver" / "fact_noticia"
FACT_PARTIDO_STATS = REPO_ROOT / "silver" / "fact_partido_stats" / "data.json"
QUEUE_ROOT = REPO_ROOT / "queue"

SERIE = "La noticia en datos"
MAX_POR_DIA = 1
DIAS_SIN_REPETIR = 3  # ni el mismo enlace ni los mismos jugadores en una noticia de estos días
PESO_TIPO = {"parejas": 40, "resultado": 30, "eliminacion": 30, "ranking": 20, "dinero": 20, "otro": 0}
PESO_MEDIO = 25  # cada titular más con la misma historia (más medios = más conversación)
CONTEXTO = {
    "parejas": "Son noticia hoy por un cambio de pareja",
    "resultado": "Son noticia hoy por su último resultado",
    "eliminacion": "Son noticia hoy por una eliminación",
    "ranking": "Son noticia hoy por el ranking",
    "dinero": "Son noticia hoy por los premios",
    "otro": "Son noticia hoy",
}


def cargar(hoy: date, silver_root: Path = SILVER_ROOT) -> list[dict[str, Any]]:
    """Titulares usables de hoy (o de ayer, si el de hoy aún no está)."""
    for dia in (hoy, hoy - timedelta(days=1)):
        f = silver_root / f"dt={dia.isoformat()}" / "data.json"
        if f.exists():
            return [n for n in json.loads(f.read_text(encoding="utf-8")) if n.get("usable")]
    return []


def historias(noticias: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Titulares que comparten algún jugador, juntos (la misma historia
    contada por varios medios, o desde los dos lados: "Triay y Brea caen" y
    "la campanada de Icardo ante Triay y Brea"), de más a menos fuerte: tipo
    de noticia, cuántos titulares la cuentan y lo arriba que están en el
    ranking quienes salen."""
    grupos: list[tuple[set[str], list[dict[str, Any]]]] = []
    for n in noticias:
        ids = {j["jugador_id"] for j in n["jugadores"]}
        juntos = [g for g in grupos if g[0] & ids]
        for g in juntos:
            grupos.remove(g)
        grupos.append((ids.union(*(g[0] for g in juntos)), [t for g in juntos for t in g[1]] + [n]))
    salida = []
    for ids, titulares in grupos:
        principal = max(titulares, key=lambda n: PESO_TIPO.get(n["tipo"], 0))
        vistos: dict[str, dict[str, Any]] = {}
        for t in titulares:
            for j in t["jugadores"]:
                vistos.setdefault(j["jugador_id"], j)
        jugadores = sorted(vistos.values(), key=lambda j: j["posicion"])
        puntos = (PESO_TIPO.get(principal["tipo"], 0) + PESO_MEDIO * (len(titulares) - 1)
                  + sum(_puntos_ranking(j["posicion"]) for j in jugadores))
        salida.append({"ids": ids, "principal": principal, "titulares": titulares, "jugadores": jugadores,
                       "puntos": puntos})
    return sorted(salida, key=lambda h: -h["puntos"])


def _puntos_ranking(posicion: int) -> int:
    """Hasta 20 puntos por jugador: el n.º 1 pesa más que el n.º 90."""
    return max(0, 101 - posicion) // 5


def _ya_contadas(hoy: date, queue_root: Path) -> tuple[set[str], list[set[str]]]:
    enlaces, conjuntos = set(), []
    for dia in range(DIAS_SIN_REPETIR + 1):
        f = queue_root / (hoy - timedelta(days=dia)).isoformat() / "candidates.json"
        if not f.exists():
            continue
        for c in json.loads(f.read_text(encoding="utf-8")):
            if n := c.get("noticia"):
                enlaces.add(n.get("enlace"))
                conjuntos.append(set(n.get("jugador_ids", [])))
    return enlaces, conjuntos


def pareja_actual(ruta: Path = FACT_PARTIDO_STATS) -> dict[str, str]:
    """jugador_id -> compañero en su último partido de Premier Padel
    (`fact_partido_stats`, se actualiza a diario). No se usa `dim_pareja`:
    sus tramos "activos" salen de torneos sueltos (Mundial, exhibiciones) y
    el 14/11/2026 ni siquiera tenía activa a Tapia/Coello."""
    if not ruta.exists():
        return {}
    filas = [f for f in json.loads(ruta.read_text(encoding="utf-8"))
             if f.get("bloque") == "partido" and f.get("jugador_1_id") and f.get("jugador_2_id")]
    companero: dict[str, str] = {}
    for f in sorted(filas, key=lambda f: f["fecha"]):  # el último partido gana
        companero[f["jugador_1_id"]] = f["jugador_2_id"]
        companero[f["jugador_2_id"]] = f["jugador_1_id"]
    return companero


def con_pareja(jugadores: list[dict[str, Any]], top: dict[str, dict[str, Any]],
               companero: dict[str, str]) -> list[dict[str, Any]]:
    """Cada jugador, con su pareja activa si está en el top 100: la noticia
    de Tapia es también la de Coello, y el titular que nombra a "Jensen"
    (apellido ambiguo, no reconocido) sí nombra a Icardo, su pareja."""
    salida = list(jugadores)
    ids = {j["jugador_id"] for j in salida}
    for j in jugadores:
        otro = companero.get(j["jugador_id"])
        if otro in top and otro not in ids:
            salida.append(top[otro])
            ids.add(otro)
    return salida


def dos_parejas(jugadores: list[dict[str, Any]], companero: dict[str, str]) -> list[list[dict[str, Any]]] | None:
    """Si los jugadores son exactamente dos parejas actuales, esas dos."""
    por_id = {j["jugador_id"]: j for j in jugadores}
    parejas: list[list[dict[str, Any]]] = []
    vistos: set[str] = set()
    for j in jugadores:
        otro = companero.get(j["jugador_id"])
        if j["jugador_id"] in vistos or otro not in por_id:
            continue
        parejas.append([j, por_id[otro]])
        vistos |= {j["jugador_id"], otro}
    return parejas if len(parejas) == 2 and len(vistos) == len(jugadores) else None


def pedidos_de(historia: dict[str, Any], jugadores: list[dict[str, Any]],
               companero: dict[str, str]) -> list[dict[str, Any]]:
    """Pedidos posibles, del mejor al de respaldo: si la noticia enfrenta a
    dos parejas, su cara a cara (con el partido de esta semana si es de
    Premier Padel); si no se han cruzado nunca o no son dos parejas, la
    forma (o las ganancias) de los protagonistas."""
    contexto = CONTEXTO.get(historia["principal"]["tipo"], CONTEXTO["otro"])
    pedidos = []
    if parejas := dos_parejas(jugadores, companero):
        pedidos.append({"tipo": "h2h", "pareja_1": [j["nombre"] for j in parejas[0]],
                        "pareja_2": [j["nombre"] for j in parejas[1]], "serie": SERIE, "contexto": contexto})
    pedidos.append(pedido_de(historia, jugadores))
    return pedidos


def pedido_de(historia: dict[str, Any], jugadores: list[dict[str, Any]]) -> dict[str, Any]:
    tipo = historia["principal"]["tipo"]
    dinero = tipo == "dinero"
    return {
        "tipo": "jugadores",
        "jugadores": [j["nombre"] for j in jugadores],
        "metrica": "ganancias" if dinero else "forma_al_dia",  # con los partidos de esta semana
        "serie": SERIE,
        "titulo": "Son noticia hoy: sus ganancias de 2026" if dinero else "Son noticia hoy: sus victorias en 8 semanas",
        "contexto": CONTEXTO.get(tipo, CONTEXTO["otro"]),
    }


def pedidos_del_dia(hoy: date, top: list[dict[str, Any]], *, silver_root: Path = SILVER_ROOT,
                    queue_root: Path = QUEUE_ROOT, companero: dict[str, str] | None = None
                    ) -> list[tuple[list[dict[str, Any]], dict[str, Any]]]:
    """(pedidos para adhoc, del mejor al de respaldo; noticia para el
    candidato), de la historia más fuerte a la más débil. Quien llama se
    queda con las `MAX_POR_DIA` primeras que salgan bien."""
    enlaces, conjuntos = _ya_contadas(hoy, queue_root)
    por_id = {j["jugador_id"]: j for j in top}
    companero = pareja_actual() if companero is None else companero
    salida = []
    for h in historias(cargar(hoy, silver_root)):
        jugadores = con_pareja(h["jugadores"], por_id, companero)
        ids = {j["jugador_id"] for j in jugadores}
        if len(jugadores) < 2 or any(t["enlace"] in enlaces for t in h["titulares"]) or any(ids & c for c in conjuntos):
            continue
        principal = h["principal"]
        noticia = {
            "titulo": principal["titulo"], "enlace": principal["enlace"], "medio": principal.get("medio"),
            "tipo": principal["tipo"], "tipo_origen": principal.get("tipo_origen"),
            "otros_titulares": [t["titulo"] for t in h["titulares"] if t is not principal][:5],
            "jugador_ids": sorted(ids),
        }
        salida.append((pedidos_de(h, jugadores, companero), noticia))
    return salida
