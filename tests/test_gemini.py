"""Cliente de Gemini (content/copy_factory/gemini.py) con respuestas
simuladas: nunca llama a la API real."""

from __future__ import annotations

import httpx
import pytest

from content.copy_factory import gemini


def _cliente(respuestas: list[httpx.Response], llamadas: list[str]) -> httpx.Client:
    def manejar(request: httpx.Request) -> httpx.Response:
        llamadas.append(request.url.path.rsplit("/", 1)[-1])
        assert request.headers["x-goog-api-key"] == "clave-de-prueba"
        return respuestas.pop(0)
    return httpx.Client(transport=httpx.MockTransport(manejar))


def _ok(texto: str) -> httpx.Response:
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": texto}]}}]})


@pytest.fixture(autouse=True)
def _clave(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL_RESPALDO", raising=False)


def test_respuesta_normal():
    llamadas: list[str] = []
    assert gemini.generar("s", "u", cliente=_cliente([_ok('{"x": "hola"}')], llamadas)) == '{"x": "hola"}'
    assert llamadas == ["gemini-flash-latest:generateContent"]


def test_saturado_reintenta_y_pasa_al_modelo_de_respaldo():
    llamadas: list[str] = []
    esperas: list[int] = []
    respuestas = [httpx.Response(503), httpx.Response(429), httpx.Response(503), _ok("ok")]
    assert gemini.generar("s", "u", cliente=_cliente(respuestas, llamadas), dormir=esperas.append) == "ok"
    assert llamadas[-1] == "gemini-flash-lite-latest:generateContent"
    assert esperas == [10, 30]


def test_error_de_clave_para_en_seco():
    llamadas: list[str] = []
    with pytest.raises(gemini.GeminiError, match="403"):
        gemini.generar("s", "u", cliente=_cliente([httpx.Response(403, text="no")], llamadas))
    assert len(llamadas) == 1


def test_respuesta_vacia_prueba_el_otro_modelo_y_el_pensamiento_no_cuenta():
    llamadas: list[str] = []
    vacia = httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "pienso…", "thought": True}]},
                                                      "finishReason": "MAX_TOKENS"}]})
    assert gemini.generar("s", "u", cliente=_cliente([vacia, _ok("bien")], llamadas)) == "bien"
    assert len(llamadas) == 2


def test_sin_clave(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY")
    with pytest.raises(gemini.GeminiSinClave):
        gemini.generar("s", "u")
