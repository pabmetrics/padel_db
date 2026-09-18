"""Silver: fact_licencias (doc 01 §3.2) — licencias federativas de pádel.

Dos fuentes independientes, **nunca mezcladas** (misma regla que F5/F6 en
doc 01 §6): F7 (CSD, Estadística de Deporte Federado, bronze/csd/licencias
— foto fija anual) y F8 (FEP, padelfederacion.es, bronze/fep/licencias —
base de datos viva, incluye el año en curso a medio actualizar). Cada fila
lleva `fuente` para no confundirlas nunca en un gráfico. Solo hay dato a
**nivel nacional**, no por CCAA — ver docs/campos-licencias-padel.md.

Una fila = (año, fuente, sexo). `sexo` puede ser "total", "M", "F" o
"sin_especificar" (solo 2007 en el CSD, la única página con esa columna).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRONZE_CSD = REPO_ROOT / "bronze" / "csd" / "licencias"
BRONZE_FEP = REPO_ROOT / "bronze" / "fep" / "licencias"
SILVER_DIR = REPO_ROOT / "silver" / "fact_licencias"

FUENTE_TXT_CSD = "CSD, Estadística de Deporte Federado · elaboración propia"
FUENTE_TXT_FEP = "FEP, Federación Española de Pádel (dato en vivo) · elaboración propia"


def _latest_dir(root: Path) -> Path:
    dirs = sorted((p for p in root.glob("dt=*") if p.is_dir()), key=lambda p: p.name)
    if not dirs:
        raise FileNotFoundError(f"Sin snapshots en {root}")
    return dirs[-1]


def _fila(anio: int, fuente: str, sexo: str, licencias: int, fuente_txt: str) -> dict[str, Any]:
    return {
        "anio": anio,
        "fuente": fuente,
        "federacion": "RFEP",
        "ambito": "nacional",
        "sexo": sexo,
        "licencias": licencias,
        "fuente_txt": fuente_txt,
    }


def _filas_csd() -> list[dict[str, Any]]:
    snapshot = json.loads((_latest_dir(BRONZE_CSD) / "data.json").read_text(encoding="utf-8"))
    historico = snapshot["historico"]["serie"]
    por_sexo = snapshot["por_sexo"]["serie"]

    rows: list[dict[str, Any]] = []
    for anio_str, total in historico.items():
        rows.append(_fila(int(anio_str), "csd", "total", total, FUENTE_TXT_CSD))

    for anio_str, desglose in por_sexo.items():
        anio = int(anio_str)
        rows.append(_fila(anio, "csd", "M", desglose["hombres"], FUENTE_TXT_CSD))
        rows.append(_fila(anio, "csd", "F", desglose["mujeres"], FUENTE_TXT_CSD))
        if desglose.get("sin_especificar"):
            rows.append(_fila(anio, "csd", "sin_especificar", desglose["sin_especificar"], FUENTE_TXT_CSD))
    return rows


def _filas_fep() -> list[dict[str, Any]]:
    if not BRONZE_FEP.exists():
        return []
    snapshot = json.loads((_latest_dir(BRONZE_FEP) / "data.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for anio_str, total in snapshot["serie_anual"].items():
        rows.append(_fila(int(anio_str), "fep", "total", total, FUENTE_TXT_FEP))

    anio_actual = max(int(a) for a in snapshot["serie_anual"])
    genero = snapshot.get("genero_actual", {})
    if genero.get("Masculino"):
        rows.append(_fila(anio_actual, "fep", "M", genero["Masculino"], FUENTE_TXT_FEP))
    if genero.get("Femenino"):
        rows.append(_fila(anio_actual, "fep", "F", genero["Femenino"], FUENTE_TXT_FEP))
    return rows


def build() -> Path:
    rows = _filas_csd() + _filas_fep()
    rows.sort(key=lambda r: (r["anio"], r["fuente"], r["sexo"]))

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    out_file = SILVER_DIR / "data.json"
    out_file.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    for fuente in ("csd", "fep"):
        anios_total = sorted({r["anio"] for r in rows if r["sexo"] == "total" and r["fuente"] == fuente})
        if anios_total:
            print(f"fact_licencias [{fuente}]: años con total {anios_total[0]}-{anios_total[-1]} ({len(anios_total)} años)")
    print(f"fact_licencias: {len(rows)} filas -> {out_file.relative_to(REPO_ROOT)}")
    return out_file


if __name__ == "__main__":
    build()
