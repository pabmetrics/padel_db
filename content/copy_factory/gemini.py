"""Cliente mínimo de Gemini (capa gratuita de Google AI Studio), 14/11/2026.

Sustituye a la API de Claude en copy_factory y clasifica titulares en
`noticias.py`: el proyecto se mantiene a coste cero. Todo lo que se le
manda son datos públicos del circuito (filas de gold, titulares de prensa):
la capa gratuita permite a Google usar lo que recibe, así que nunca debe
recibir nada privado.

API REST directa con `httpx` (ya en requirements), sin SDK. Modelos: los
alias `gemini-flash-latest` y, de respaldo, `gemini-flash-lite-latest`
(Google los mueve solo a la versión más nueva). Se pueden cambiar con
`GEMINI_MODEL` / `GEMINI_MODEL_RESPALDO`.

Errores: saturado (5xx) o límite por minuto (429) -> reintenta con espera y
luego prueba el modelo de respaldo; clave o permisos (400/401/403) -> para
en seco, no tiene arreglo reintentando.
"""

from __future__ import annotations

import os
import time

import httpx

BASE = "https://generativelanguage.googleapis.com/v1beta"
ESPERAS_S = (10, 30)
TIMEOUT_S = 90


class GeminiError(RuntimeError):
    pass


class GeminiSinClave(GeminiError):
    pass


def clave() -> str:
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        raise GeminiSinClave(
            "Falta GEMINI_API_KEY. En producción: secreto de GitHub Actions. En local: en el .env del repo "
            "(GEMINI_API_KEY=...), que nunca se sube."
        )
    return k


def modelos() -> list[str]:
    return [os.environ.get("GEMINI_MODEL") or "gemini-flash-latest",
            os.environ.get("GEMINI_MODEL_RESPALDO") or "gemini-flash-lite-latest"]


def generar(sistema: str, usuario: str, *, json_salida: bool = True, max_tokens: int = 4096,
            cliente: httpx.Client | None = None, dormir=time.sleep) -> str:
    """Texto de la respuesta. Con `json_salida`, se pide JSON al modelo
    (`responseMimeType`), pero quien llama lo sigue validando."""
    cuerpo = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"role": "user", "parts": [{"text": usuario}]}],
        # Margen amplio: en los modelos con razonamiento, el "pensamiento"
        # también gasta de este presupuesto.
        "generationConfig": {"maxOutputTokens": max_tokens,
                             **({"responseMimeType": "application/json"} if json_salida else {})},
    }
    cabeceras = {"x-goog-api-key": clave(), "Content-Type": "application/json"}
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=TIMEOUT_S)
    ultimo = "sin intentos"
    try:
        for modelo in modelos():
            for espera in (*ESPERAS_S, None):
                try:
                    r = cliente.post(f"{BASE}/models/{modelo}:generateContent", json=cuerpo, headers=cabeceras)
                except httpx.HTTPError as e:
                    ultimo = f"{modelo}: fallo de red ({type(e).__name__})"
                else:
                    if r.status_code == 200:
                        datos = r.json()
                        partes = ((datos.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                        texto = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
                        if texto:
                            return texto
                        motivo = (datos.get("candidates") or [{}])[0].get("finishReason") or \
                            (datos.get("promptFeedback") or {}).get("blockReason") or "?"
                        ultimo = f"{modelo}: respuesta vacía ({motivo})"
                        break  # bloqueada o vacía: probar el otro modelo
                    if r.status_code in (400, 401, 403):
                        raise GeminiError(f"{modelo}: {r.status_code} (clave, permisos o petición no válida): {r.text[:300]}")
                    if r.status_code == 404:
                        ultimo = f"{modelo}: el modelo no existe (404)"
                        break
                    ultimo = f"{modelo}: {r.status_code}"
                if espera is None:
                    break
                dormir(espera)
    finally:
        if propio:
            cliente.close()
    raise GeminiError(f"Gemini no disponible: {ultimo}")
