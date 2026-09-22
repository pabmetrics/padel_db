"""Conector de métricas web (doc 01 §3.4/§5, `ingest_metrics`) — tráfico de
padeldb.es vía Cloudflare Web Analytics.

padeldb.es usa Cloudflare Web Analytics en modo "Automatic setup": al estar
el dominio proxied (nube naranja), Cloudflare inyecta el script de medición
en el borde de red sin tocar el HTML (ver bitácora 22/09/2026 en
`docs/padel-datos-04-seguimiento.md`). Esos datos se leen con la API
GraphQL de Cloudflare (dataset RUM), no con un export manual: a diferencia
de X, aquí sí hay una vía gratuita y automatizable.

Auth: token en la variable de entorno CLOUDFLARE_API_TOKEN (permiso
"Account Analytics: Read" o "Zone Analytics: Read" sobre la zona de
padeldb.es) y el identificador de zona en CLOUDFLARE_ZONE_TAG (Cloudflare
dashboard → padeldb.es → panel derecho, "Zone ID"). Secretos de GitHub
Actions en producción; variables de entorno locales para pruebas.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "webanalytics" / "pageviews"
GRAPHQL_URL = "https://api.cloudflare.com/client/v4/graphql"
TOKEN_ENV_VAR = "CLOUDFLARE_API_TOKEN"
ZONE_ENV_VAR = "CLOUDFLARE_ZONE_TAG"

QUERY = """
query PadelDBPageviews($zoneTag: string, $since: Time, $until: Time) {
  viewer {
    zones(filter: {zoneTag: $zoneTag}) {
      rumPageloadEventsAdaptiveGroups(
        limit: 5000
        filter: {datetime_geq: $since, datetime_lt: $until}
      ) {
        count
        sum { visits }
        dimensions {
          date: datetimeDay
          requestPath: requestPath
        }
      }
    }
  }
}
"""


class CloudflareError(RuntimeError):
    pass


def _auth() -> tuple[str, str]:
    token = os.environ.get(TOKEN_ENV_VAR)
    zone_tag = os.environ.get(ZONE_ENV_VAR)
    if not token or not zone_tag:
        raise CloudflareError(
            f"Faltan {TOKEN_ENV_VAR} y/o {ZONE_ENV_VAR} (token y zona de Cloudflare para padeldb.es)"
        )
    return token, zone_tag


def fetch_pageviews_semana(*, dias_atras: int = 7) -> dict[str, Any]:
    """Pageviews y visitas de los últimos `dias_atras` días, por día y
    ruta. `dias_atras=7` cubre la semana natural del rito del domingo
    (doc 03 §5.3)."""
    token, zone_tag = _auth()
    until = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since = until - timedelta(days=dias_atras)

    r = httpx.post(
        GRAPHQL_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "query": QUERY,
            "variables": {
                "zoneTag": zone_tag,
                "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "until": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        },
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("errors"):
        raise CloudflareError(f"GraphQL de Cloudflare devolvió errores: {payload['errors']}")

    zonas = payload["data"]["viewer"]["zones"]
    grupos = zonas[0]["rumPageloadEventsAdaptiveGroups"] if zonas else []
    return {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "grupos": grupos,
    }


def write_snapshot(datos: dict[str, Any]) -> Path:
    today = datetime.now(timezone.utc).date()
    payload = {
        "source": "cloudflare_web_analytics",
        "endpoint": GRAPHQL_URL,
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        **datos,
    }
    sha256 = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    payload["sha256"] = sha256

    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    datos = fetch_pageviews_semana()
    out_file = write_snapshot(datos)
    print(f"pageviews: {len(datos['grupos'])} grupos día×ruta ({datos['since']} — {datos['until']})")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
