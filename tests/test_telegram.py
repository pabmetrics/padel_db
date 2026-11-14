"""Envío de candidatos a Telegram (publish/telegram.py), con respuestas
simuladas: nunca llama a Telegram."""

from __future__ import annotations

import json

import httpx

from publish import telegram


def _cola(tmp_path, candidatos):
    d = tmp_path / "queue" / "2026-11-16"
    d.mkdir(parents=True)
    (d / "candidates.json").write_text(json.dumps(candidatos, ensure_ascii=False), encoding="utf-8")
    for c in candidatos:
        (tmp_path / c["png_16x9"]).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / c["png_16x9"]).write_bytes(b"png")


def _cand(registro, **extra):
    return {"registro": registro, "serie": "Remontadas", "estado": "candidato", "publicable": True,
            "borrador_x": f"texto {registro}", "avisos": [], "png_16x9": f"queue/2026-11-16/{registro[1:]}.png", **extra}


def test_envia_foto_y_texto_y_no_repite(tmp_path):
    _cola(tmp_path, [_cand("#0300"), _cand("#0301", estado="publicado"),
                     _cand("#0302", publicable=False, borrador_x=None, avisos=["dato dudoso"],
                           noticia={"titulo": "Titular", "medio": "Marca", "enlace": "https://x/1"})])
    llamadas = []

    def manejar(request: httpx.Request) -> httpx.Response:
        llamadas.append((request.url.path.rsplit("/", 1)[-1], request.content))
        return httpx.Response(200, json={"ok": True})

    cliente = httpx.Client(transport=httpx.MockTransport(manejar))
    kw = dict(token="T", chat_id="1", cliente=cliente, queue_root=tmp_path / "queue", repo_root=tmp_path)
    assert telegram.enviar("2026-11-16", **kw) == 2
    # #0300: foto + texto; #0302 (no publicable): solo la foto, con el aviso y la noticia. El publicado no se manda.
    assert [m for m, _ in llamadas] == ["sendPhoto", "sendMessage", "sendPhoto"]
    assert b"text=texto+%230300" in llamadas[1][1]
    assert telegram.enviar("2026-11-16", **kw) == 0  # segunda vez: nada nuevo


def test_pie_de_foto():
    pie = telegram.pie_de_foto(_cand("#0302", avisos=["revisa X"], noticia={"titulo": "T", "medio": "M", "enlace": "https://x"}))
    assert pie.splitlines() == ["#0302 · Remontadas", "⚠️ revisa X", "📰 T (M)", "https://x"]
