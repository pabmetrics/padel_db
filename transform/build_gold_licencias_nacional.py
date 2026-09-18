"""Gold: licencias_nacional (doc 01 §3.3 "licencias_ccaa" / doc 02 #5-7 del
backlog: "Licencias de pádel 2000-2025", "Licencias por CCAA y sexo").

Primera versión a nivel **nacional**, no por CCAA — ver
docs/campos-licencias-padel.md sobre por qué (igual que `pistas_provincia`
es provincia y no municipio: se prefiere una cifra verificada a un desglose
sin fuente confirmada).

Una fila = (año, fuente, sexo) con el total de licencias federativas de
pádel en España. Dos fuentes sin mezclar: "csd" (foto fija anual, serie
1980-1985 y 2000-2025, desglose M/F desde 2007) y "fep" (base de datos en
vivo de la federación, serie 2012-año en curso, desglose M/F solo del año
en curso). Ver docs/campos-licencias-padel.md.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FACT_LICENCIAS = REPO_ROOT / "silver" / "fact_licencias" / "data.json"
GOLD_ROOT = REPO_ROOT / "gold" / "licencias_nacional"


def build() -> Path:
    filas_silver = json.loads(FACT_LICENCIAS.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    for f in filas_silver:
        rows.append(
            {
                "fecha_dato": f"{f['anio']}-12-31",
                "anio": f["anio"],
                "fuente": f["fuente"],
                "sexo": f["sexo"],
                "licencias": f["licencias"],
                "fuente_txt": f["fuente_txt"],
                "publicable": True,
            }
        )

    rows.sort(key=lambda r: (r["anio"], r["fuente"], r["sexo"]))

    hoy = date.today().isoformat()
    out_dir = GOLD_ROOT / f"fecha_dato={hoy}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    totales = [r for r in rows if r["sexo"] == "total"]
    if totales:
        primero, ultimo = totales[0], totales[-1]
        print(
            f"licencias_nacional: {len(rows)} filas. Serie total: "
            f"{primero['anio']} ({primero['licencias']}) -> {ultimo['anio']} ({ultimo['licencias']})"
        )
    print(f"-> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
