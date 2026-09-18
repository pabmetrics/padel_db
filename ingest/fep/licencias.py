"""Conector F8 (FEP, padelfederacion.es) — licencias en vivo.

La página `Datos_Federacion.asp?Id=0` (la ficha de la propia FEP dentro del
listado de federaciones autonómicas) no es la sección de noticias que se
exploró y se descartó en una sesión anterior (docs/campos-pistas-territorio.md):
incrusta un bloque Highcharts con datos que según la propia página están
"actualizados online con la BBDD FEP" — serie de licencias por año
(2012-año en curso) y el desglose actual por género y por edad. Es la única
fuente de este proyecto con el **año en curso** (parcial, sube durante el
año) y con desglose por edad.

No se cruza ni se promedia con F7 (CSD): son dos fuentes independientes que
pueden no coincidir exactamente (el CSD publica una foto fija anual: la FEP,
una base de datos viva) — ver docs/campos-licencias-padel.md, misma regla
que ya aplica el proyecto a F5 vs F6 (doc 01 §6, "F5 y F6 no se mezclan").
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import truststore

truststore.inject_into_ssl()

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "fep" / "licencias"
URL = "https://www.padelfederacion.es/Datos_Federacion.asp?Id=0"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (padeldb.es research bot; contacto hola@padeldb.es)"

SERIE_RE = re.compile(r"\[\s*'(\d{4})'\s*,\s*(\d+)\s*\]")
GENERO_RE = re.compile(r"\[\s*'(Masculino|Femenino)'\s*,\s*(\d+)\s*\]")
EDAD_RE = re.compile(r"\[\s*'([^']+)'\s*,\s*(\d+)\s*\]")
TOTAL_JUGADOR_RE = re.compile(r"N.mero de Licencias Jugador/a:\s*<strong>([\d.]+)</strong>")
TOTAL_TECNICO_RE = re.compile(r"N.mero de Licencias T.cnico Nacional:\s*<strong>([\d.]+)</strong>")
TOTAL_ARBITRO_RE = re.compile(r"N.mero de Licencias Juez-.rbitro Nacional:\s*<strong>([\d.]+)</strong>")
TOTAL_CLUBES_RE = re.compile(r"N.mero de Clubes Federados:\s*<strong>([\d.]+)</strong>")


def _a_entero(txt: str) -> int:
    return int(txt.replace(".", ""))


def _bloque(html: str, inicio: str, fin: str) -> str:
    i = html.index(inicio)
    j = html.index(fin, i)
    return html[i:j]


def fetch() -> dict[str, Any]:
    html = httpx.get(URL, timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True).text

    serie_bloque = _bloque(html, "container'", "container2'")
    serie = {int(anio): _a_entero(n) for anio, n in SERIE_RE.findall(serie_bloque)}

    genero_bloque = _bloque(html, "container2'", "container3'")
    genero = {sexo: _a_entero(n) for sexo, n in GENERO_RE.findall(genero_bloque)}

    edad_bloque = html[html.index("container3'"):]
    edad_bloque = edad_bloque[: edad_bloque.index("});", edad_bloque.index("data:"))]
    edad = {tramo: _a_entero(n) for tramo, n in EDAD_RE.findall(edad_bloque)}

    resumen = {
        "licencias_jugador": _a_entero(TOTAL_JUGADOR_RE.search(html).group(1)),
        "licencias_tecnico_nacional": _a_entero(TOTAL_TECNICO_RE.search(html).group(1)),
        "licencias_juez_arbitro_nacional": _a_entero(TOTAL_ARBITRO_RE.search(html).group(1)),
        "clubes_federados": _a_entero(TOTAL_CLUBES_RE.search(html).group(1)),
    }

    return {"url": URL, "resumen": resumen, "serie_anual": serie, "genero_actual": genero, "edad_actual": edad}


def write_snapshot(data: dict[str, Any]) -> Path:
    today = datetime.now(timezone.utc).date()
    sha256 = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    payload = {
        "source": "fep",
        "endpoint": URL,
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256,
        **data,
    }
    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    data = fetch()
    out_file = write_snapshot(data)
    print(f"resumen: {data['resumen']}")
    print(f"serie anual: {len(data['serie_anual'])} años ({min(data['serie_anual'])}-{max(data['serie_anual'])})")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
