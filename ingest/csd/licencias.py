"""Conector F7 (CSD, Estadística de Deporte Federado) — licencias de pádel.

Descarga en memoria (sin persistir el PDF en el repo) los dos informes que
publica el CSD en la página de licencias federativas:

- "Histórico licencias (actualizado <año>)": serie nacional total por
  federación y año, desde 1941.
- "Licencias por sexo <rango>": desglose hombres/mujeres por año, desde 2007.

El primer intento de acceso (18/09/2026) dio ``CERTIFICATE_VERIFY_FAILED``
con ``httpx``/``certifi`` — no era el sitio (el navegador y
``Invoke-WebRequest`` de PowerShell, que usan el almacén de certificados de
Windows, acceden sin problema): era un desajuste del almacén de confianza
de Python. Se soluciona con ``truststore``, que hace que ``ssl`` use el
almacén nativo del sistema operativo en vez de la lista de Mozilla que trae
``certifi``.

No hay desglose por CCAA en ninguno de los dos informes de esta página —
solo total nacional. Ver docs/campos-licencias-padel.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pdfplumber
import truststore

truststore.inject_into_ssl()

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_ROOT = REPO_ROOT / "bronze" / "csd" / "licencias"
PAGINA_URL = "https://www.csd.gob.es/es/federaciones-y-asociaciones/federaciones-deportivas-espanolas/licencias"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (padeldb.es research bot; contacto hola@padeldb.es)"

FILA_PADEL_RE = re.compile(r"^45\s+P.DEL(?:\s+(.+))?$")
CABECERA_ANIOS_RE = re.compile(r"^FEDERACI.N\s+((?:\d{4}\s*)+)$")
NUMERO_RE = re.compile(r"^[\d.]+$")


def _localizar_pdf(html: str, fragmento_nombre: str) -> str:
    """Busca en la página de licencias el enlace a un PDF cuyo href contenga
    ``fragmento_nombre`` (p.ej. "Hist%C3%B3rico%20licencias" o "sexo"), para
    no depender de una URL fija que cambie de una campaña a otra."""
    for m in re.finditer(r'href="([^"]+\.pdf)"', html):
        href = m.group(1)
        if fragmento_nombre.lower() in href.lower():
            return href if href.startswith("http") else f"https://www.csd.gob.es{href}"
    raise RuntimeError(f"No se ha encontrado un PDF con '{fragmento_nombre}' en {PAGINA_URL}")


def _descargar(url: str) -> bytes:
    r = httpx.get(url, timeout=60, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.content


def _extraer_por_pagina(pdf_bytes: bytes) -> list[tuple[list[int], list[str]]]:
    """Por cada página del PDF, devuelve (años de la cabecera, números de la
    fila 45 PÁDEL). La fila de pádel puede no existir en absoluto en páginas
    de años en los que el deporte no estaba federado (sin fila = lista
    vacía), y cuando existe puede tener menos números que años tiene la
    página (la federación empezó a mitad del rango de esa página) — en
    ambos casos los números que sí hay van alineados con los primeros años
    del rango de esa página, que es como el CSD compone esta tabla."""
    resultado: list[tuple[list[int], list[str]]] = []
    with pdfplumber.open(__import__("io").BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            lineas = texto.split("\n")
            anios: list[int] = []
            numeros: list[str] = []
            for linea in lineas:
                linea = linea.strip()
                m_cab = CABECERA_ANIOS_RE.match(linea)
                if m_cab:
                    anios = [int(a) for a in m_cab.group(1).split()]
                    continue
                m_padel = FILA_PADEL_RE.match(linea)
                if m_padel and m_padel.group(1):
                    numeros = [n for n in m_padel.group(1).split(" ") if NUMERO_RE.match(n)]
            resultado.append((anios, numeros))
    return resultado


def _a_entero(txt: str) -> int:
    return int(txt.replace(".", ""))


def fetch_historico() -> dict[str, Any]:
    """Serie nacional total de licencias de pádel por año (desde que el
    deporte tiene federación propia hasta el último dato publicado)."""
    html = httpx.get(PAGINA_URL, timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True).text
    url = _localizar_pdf(html, "%20licencias%20%28actualizado")
    pdf_bytes = _descargar(url)
    paginas = _extraer_por_pagina(pdf_bytes)

    serie: dict[int, int] = {}
    for anios, numeros in paginas:
        if not numeros:
            continue
        if not anios:
            raise ValueError("Página con fila de pádel pero sin cabecera de años reconocida")
        for anio, num in zip(anios, numeros):
            serie[anio] = _a_entero(num)
    return {"url": url, "serie": serie}


def fetch_por_sexo() -> dict[str, Any]:
    """Desglose hombres/mujeres por año, desde 2007. La tabla intercala una
    columna "sin especificar" solo en el primer año (2007); el resto son
    tríos hombres/mujeres/total que se verifican por suma."""
    html = httpx.get(PAGINA_URL, timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True).text
    url = _localizar_pdf(html, "sexo")
    pdf_bytes = _descargar(url)
    paginas = _extraer_por_pagina(pdf_bytes)
    numeros = [_a_entero(n) for _anios, fila in paginas for n in fila]

    serie: dict[int, dict[str, int]] = {}
    anio = 2007
    i = 0
    while i < len(numeros):
        hombres, mujeres, total = numeros[i], numeros[i + 1], numeros[i + 2]
        if hombres + mujeres == total:
            serie[anio] = {"hombres": hombres, "mujeres": mujeres, "sin_especificar": 0, "total": total}
            i += 3
        else:
            # Único caso esperado: 2007, con una cuarta columna "sin
            # especificar" antes del total.
            sin_especificar, total_real = numeros[i + 2], numeros[i + 3]
            if hombres + mujeres + sin_especificar != total_real:
                raise ValueError(f"Fila de {anio} no cuadra: {numeros[i:i + 4]}")
            serie[anio] = {"hombres": hombres, "mujeres": mujeres, "sin_especificar": sin_especificar, "total": total_real}
            i += 4
        anio += 1
    return {"url": url, "serie": serie}


def write_snapshot(historico: dict[str, Any], por_sexo: dict[str, Any]) -> Path:
    today = datetime.now(timezone.utc).date()
    payload = {
        "source": "csd",
        "endpoint": PAGINA_URL,
        "ingest_ts": datetime.now(timezone.utc).isoformat(),
        "historico": historico,
        "por_sexo": por_sexo,
    }
    sha256 = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    payload["sha256"] = sha256

    out_dir = BRONZE_ROOT / f"dt={today.isoformat()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "data.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file


def main() -> None:
    historico = fetch_historico()
    por_sexo = fetch_por_sexo()
    out_file = write_snapshot(historico, por_sexo)
    print(f"histórico: {len(historico['serie'])} años ({min(historico['serie'])}-{max(historico['serie'])})")
    print(f"por sexo: {len(por_sexo['serie'])} años ({min(por_sexo['serie'])}-{max(por_sexo['serie'])})")
    print(f"-> {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
