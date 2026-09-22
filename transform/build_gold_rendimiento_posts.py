"""Gold: rendimiento_posts (doc 01 §3.3, "Impresiones e interacciones por
serie, día y hora (bucle de mejora)"). Última tabla gold de Fase 4.

Formato largo (fecha_dato, metrica, valor + dimensiones), como el resto de
gold, para poder juntar dos fuentes que no comparten grano sin forzar un
cruce que no existe:

- `fuente="x"`: una fila por (registro, métrica) — impresiones,
  interacciones, retweets, respuestas, me_gusta, clics_url — desde
  `fact_rendimiento_x` (CSV manual de analytics.x.com cruzado con la cola).
- `fuente="web"`: una fila por (ruta, día, métrica) — pageviews, visitas —
  desde `fact_rendimiento_web` (Cloudflare Web Analytics, automático).

No es una tabla `publicable` en el sentido de doc 01 §3.3/§9 (no sale en
`export_web.py`: es rendimiento interno de la cuenta y de la web, no un
dato abierto del circuito de pádel), pero se mantiene el flag por
consistencia con el resto de gold — aquí solo marca filas con un valor
numérico válido.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_X = REPO_ROOT / "silver" / "fact_rendimiento_x" / "data.json"
FACT_WEB = REPO_ROOT / "silver" / "fact_rendimiento_web" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "rendimiento_posts"


def _mostrar(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _filas_x() -> list[dict[str, Any]]:
    if not FACT_X.exists():
        return []
    filas = json.loads(FACT_X.read_text(encoding="utf-8"))
    return [
        {
            "fecha_dato": f["fecha_dato"],
            "fuente": "x",
            "registro": f["registro"],
            "serie": f["serie"],
            "ruta": None,
            "metrica": f["metrica"],
            "valor": f["valor"],
            "fuente_txt": "X analytics (analytics.x.com) · exportado a mano · elaboración propia",
            "publicable": isinstance(f["valor"], int) and f["valor"] >= 0,
        }
        for f in filas
    ]


def _filas_web() -> list[dict[str, Any]]:
    if not FACT_WEB.exists():
        return []
    filas = json.loads(FACT_WEB.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for f in filas:
        if not f.get("fecha"):
            continue
        fecha_dato = f["fecha"][:10]
        for metrica, valor in (("pageviews", f.get("pageviews")), ("visitas", f.get("visitas"))):
            if valor is None:
                continue
            rows.append(
                {
                    "fecha_dato": fecha_dato,
                    "fuente": "web",
                    "registro": None,
                    "serie": None,
                    "ruta": f["ruta"],
                    "metrica": metrica,
                    "valor": int(valor),
                    "fuente_txt": "Cloudflare Web Analytics · padeldb.es · elaboración propia",
                    "publicable": int(valor) >= 0,
                }
            )
    return rows


def build() -> Path:
    rows = _filas_x() + _filas_web()
    rows.sort(key=lambda r: (r["fecha_dato"], r["fuente"], r.get("registro") or "", r.get("ruta") or "", r["metrica"]))

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    n_x = sum(1 for r in rows if r["fuente"] == "x")
    n_web = sum(1 for r in rows if r["fuente"] == "web")
    print(f"rendimiento_posts: {len(rows)} filas ({n_x} de X, {n_web} de web)")
    print(f"-> {_mostrar(out_file)}")
    return out_file


if __name__ == "__main__":
    build()
