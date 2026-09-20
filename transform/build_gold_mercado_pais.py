"""Gold: mercado_pais (doc 01 §3.3 / doc 02 backlog #9-11: pistas y
jugadores en el mundo, arquetipos de mercado). Doc 02 #8 explícitamente
compara Playtomic vs FIP como el ejemplo de "dos cifras, dos fuentes, sin
mezclar" — este gold es justo esa comparación, ya lista para publicar.

Una fila = un dato de `fact_mercado_pais`, con `fuente` siempre presente
para que ningún gráfico mezcle FIP y Playtomic sin darse cuenta.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_MERCADO_PAIS = REPO_ROOT / "silver" / "fact_mercado_pais" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "mercado_pais"


def build() -> Path:
    filas_silver = json.loads(FACT_MERCADO_PAIS.read_text(encoding="utf-8"))

    hoy = date.today().isoformat()
    rows: list[dict[str, Any]] = []
    for f in filas_silver:
        rows.append({"fecha_dato": hoy, **f, "publicable": True})

    rows.sort(key=lambda r: (r["fuente"], r["pais"]))

    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    pistas_fip = next((r["valor"] for r in rows if r["fuente"] == "fip" and r["pais"] == "GLOBAL" and r["categoria"] == "pistas"), None)
    print(f"mercado_pais: {len(rows)} filas. Pistas mundiales según FIP: {pistas_fip} (no comparable directamente con la cifra de Playtomic, ver docs/campos-mercado-padel.md)")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
