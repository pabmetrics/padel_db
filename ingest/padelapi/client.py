"""Cliente mínimo para F2 (padelapi.org).

Auth: Bearer token en la variable de entorno PADEL_API_TOKEN (secreto de
GitHub Actions en producción; variable de entorno local para pruebas).
Nunca hardcodear el token ni escribirlo en bronze.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import Any

import httpx

BASE_URL = "https://padelapi.org/api"
TOKEN_ENV_VAR = "PADEL_API_TOKEN"
MAX_PER_PAGE = 50
# Plan gratuito: 10 peticiones/minuto (doc padelapi). Un pequeño margen sobre
# 6.0s evita ir pegado al límite y encadenar 429 en paginaciones largas.
MIN_SECONDS_BETWEEN_REQUESTS = 6.5


class PadelApiError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise PadelApiError(
            f"Falta la variable de entorno {TOKEN_ENV_VAR} con el Bearer token de padelapi.org"
        )
    return token


class PadelApiClient:
    def __init__(self, *, timeout: float = 30.0) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {_token()}"},
            timeout=timeout,
        )
        self._last_request_at: float = 0.0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PadelApiClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
        if wait > 0:
            time.sleep(wait)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(6):
            self._throttle()
            try:
                response = self._client.get(path, params=params)
            except httpx.TransportError as exc:
                self._last_request_at = time.monotonic()
                if attempt == 5:
                    raise PadelApiError(f"{path}: fallo de red tras varios reintentos ({exc})") from exc
                time.sleep(MIN_SECONDS_BETWEEN_REQUESTS)
                continue
            self._last_request_at = time.monotonic()
            if response.status_code == 429:
                wait = float(response.headers.get("Retry-After", MIN_SECONDS_BETWEEN_REQUESTS * (attempt + 1)))
                time.sleep(wait)
                continue
            if response.status_code == 402:
                raise PadelApiError(
                    f"{path}: 402 Payment Required — endpoint no disponible en el plan gratuito"
                )
            if response.status_code >= 500:
                if attempt == 5:
                    raise PadelApiError(f"{path}: HTTP {response.status_code} tras varios reintentos")
                time.sleep(MIN_SECONDS_BETWEEN_REQUESTS)
                continue
            if response.status_code >= 400:
                raise PadelApiError(f"{path}: HTTP {response.status_code} — {response.text[:300]}")
            return response.json()
        raise PadelApiError(f"{path}: agotados los reintentos tras recibir 429 repetidamente")

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """Itera todas las páginas de un endpoint paginado estilo Laravel (data/links/meta)."""

        page = 1
        query = {**(params or {}), "per_page": MAX_PER_PAGE}
        while True:
            payload = self.get(path, params={**query, "page": page})
            yield from payload.get("data", [])
            meta = payload.get("meta", {})
            if page >= meta.get("last_page", page):
                break
            page += 1
