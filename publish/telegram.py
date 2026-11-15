"""Candidatos del día al Telegram de Pablo (15/11/2026).

No publica nada en ninguna red: manda a un chat privado, por cada candidato
nuevo de la cola, el gráfico (con número, serie, avisos y, si viene de una
noticia, su titular y enlace) y, en un mensaje aparte, solo el texto para X,
para copiarlo de una pulsación y publicarlo a mano. Publicar sigue siendo
cosa de una persona (CLAUDE.md, doc 02 §6).

Lo ya enviado se apunta en `queue/<fecha>/telegram.json` (registros), para
no repetir si el workflow corre dos veces o si un gráfico a medida llega
después. Se miran la cola de hoy y la de ayer: la cola se fecha cuando
empieza a generarse y el envío puede caer pasada la medianoche (pasó el
14/11: cola del 14, envío ya el 15, nada enviado). Sin `PADELDB_TELEGRAM_TOKEN` o `PADELDB_TELEGRAM_CHAT_ID` no hace
nada: el bot es uno propio de PadelDB, distinto del del agente del mini PC
(dos programas con el mismo bot se roban los mensajes).

Uso: python -m publish.telegram [--fecha AAAA-MM-DD]
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_ROOT = REPO_ROOT / "queue"
API = "https://api.telegram.org/bot{token}/{metodo}"
MAX_PIE_FOTO = 1024  # límite de Telegram para el pie de una foto


def pie_de_foto(c: dict[str, Any]) -> str:
    lineas = [f"{c['registro']} · {c['serie']}"]
    if not c.get("publicable", True) or not c.get("borrador_x"):
        lineas.append("⛔ No publicable: sin borrador.")
    for aviso in c.get("avisos", []):
        lineas.append(f"⚠️ {aviso}")
    if n := c.get("noticia"):
        medio = f" ({n['medio']})" if n.get("medio") else ""
        lineas.append(f"📰 {n.get('titulo')}{medio}")
        lineas.append(n.get("enlace", ""))
    texto = "\n".join(lineas)
    return texto if len(texto) <= MAX_PIE_FOTO else texto[: MAX_PIE_FOTO - 1] + "…"


def _enviados(fecha: str, queue_root: Path) -> set[str]:
    f = queue_root / fecha / "telegram.json"
    return set(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else set()


def pendientes(fecha: str, queue_root: Path = QUEUE_ROOT) -> list[dict[str, Any]]:
    f = queue_root / fecha / "candidates.json"
    if not f.exists():
        return []
    ya = _enviados(fecha, queue_root)
    return [c for c in json.loads(f.read_text(encoding="utf-8"))
            if c.get("estado") == "candidato" and c["registro"] not in ya]


def enviar(fecha: str, *, token: str, chat_id: str, cliente: httpx.Client, queue_root: Path = QUEUE_ROOT,
           repo_root: Path = REPO_ROOT) -> int:
    enviados = _enviados(fecha, queue_root)
    n = 0
    for c in pendientes(fecha, queue_root):
        png = repo_root / c["png_16x9"]
        with png.open("rb") as imagen:
            r = cliente.post(API.format(token=token, metodo="sendPhoto"),
                             data={"chat_id": chat_id, "caption": pie_de_foto(c)}, files={"photo": imagen})
        r.raise_for_status()
        if c.get("borrador_x"):
            r = cliente.post(API.format(token=token, metodo="sendMessage"),
                             data={"chat_id": chat_id, "text": c["borrador_x"], "disable_web_page_preview": "true"})
            r.raise_for_status()
        enviados.add(c["registro"])
        n += 1
        # Se apunta tras cada envío: si falla a mitad, el siguiente intento no repite los ya enviados.
        (queue_root / fecha / "telegram.json").write_text(json.dumps(sorted(enviados)), encoding="utf-8")
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fecha", type=date.fromisoformat, default=date.today(),
                        help="se envía lo pendiente de este día y del anterior")
    args = parser.parse_args()
    token, chat_id = os.environ.get("PADELDB_TELEGRAM_TOKEN"), os.environ.get("PADELDB_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram sin configurar (PADELDB_TELEGRAM_TOKEN / PADELDB_TELEGRAM_CHAT_ID): no se envía nada")
        return 0
    with httpx.Client(timeout=60) as cliente:
        try:
            n = sum(enviar(dia.isoformat(), token=token, chat_id=chat_id, cliente=cliente)
                    for dia in (args.fecha - timedelta(days=1), args.fecha))
        except httpx.HTTPStatusError as e:
            # Nunca se imprime la excepción entera: su URL lleva el token.
            print(f"Telegram respondió {e.response.status_code}: {e.response.text[:300]}")
            return 1
        except httpx.HTTPError as e:
            print(f"Telegram no disponible ({type(e).__name__})")
            return 1
    print(f"Telegram: {n} candidatos enviados ({args.fecha})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
