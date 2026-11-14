"""Conector de noticias del día (14/11/2026): titulares de pádel de Google
News por RSS (público, sin clave).

Snapshot a `bronze/noticias/dt=<fecha>/data.json`: título, enlace, medio y
fecha de cada noticia de las últimas 24 h. Solo el titular: no se descarga
ni se guarda el cuerpo del artículo.

Los titulares son DATOS, nunca instrucciones: solo sirven para saber de qué
jugadores se habla hoy (`transform/build_fact_noticia.py`). Ninguna cifra de
un gráfico sale de una noticia.
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "noticias"

CONSULTAS = ("pádel", '"Premier Padel"', "pádel torneo")
URL = "https://news.google.com/rss/search?q={q}+when:1d&hl=es&gl=ES&ceid=ES:es"
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; padeldb-noticias/1.0)"}


def parsear(xml_texto: str, consulta: str) -> list[dict]:
    noticias = []
    for item in ET.fromstring(xml_texto).iter("item"):
        titulo = (item.findtext("title") or "").strip()
        enlace = (item.findtext("link") or "").strip()
        if not titulo or not enlace:
            continue
        medio = (item.findtext("source") or "").strip()
        # Google News añade " - Medio" al final del título.
        if medio and titulo.endswith(f" - {medio}"):
            titulo = titulo[: -len(f" - {medio}")].strip()
        try:
            publicada = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            publicada = None
        noticias.append({"titulo": titulo, "enlace": enlace, "medio": medio, "publicada": publicada,
                         "consulta": consulta})
    return noticias


def descargar(cliente: httpx.Client) -> list[dict]:
    vistas: set[str] = set()
    todas: list[dict] = []
    for consulta in CONSULTAS:
        r = cliente.get(URL.format(q=quote_plus(consulta)), headers=CABECERAS, follow_redirects=True)
        r.raise_for_status()
        for n in parsear(r.text, consulta):
            clave = n["titulo"].lower()
            if clave not in vistas:
                vistas.add(clave)
                todas.append(n)
    return todas


def main() -> None:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args()
    with httpx.Client(timeout=30) as cliente:
        noticias = descargar(cliente)
    ahora = datetime.now(timezone.utc)
    out_dir = BRONZE_ROOT / f"dt={ahora.date().isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps({"source": "news.google.com/rss", "ingest_ts": ahora.isoformat(),
                                    "n_items": len(noticias), "items": noticias}, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"{len(noticias)} titulares -> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
