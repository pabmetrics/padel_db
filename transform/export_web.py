"""export_web (doc 01 §3, §5): gold -> ficheros estáticos de la web.

Escribe todo en `site/public/`, que es lo que Astro sirve tal cual y lo que
lee en el build (`site/src/lib/datos.js`):

- `datos/<tabla>.json` y `.csv`: solo filas `publicable` (doc 01 §3.3: el
  flag es el resultado del control de calidad). `datos/catalogo.json` describe
  cada tabla para la página de datos abiertos (CC BY, doc 01 §7).
- `img/`: el gráfico más reciente de cada nombre de fichero de la cola.
- `cola/hoy.json` y `cola/<fecha>.json`: la cola del día para la tarea
  programada de Cowork (doc 03 §6), con las rutas de los PNG convertidas a
  la URL pública. `hoy.json` es solo la de hoy (lista vacía si no hay), y
  `cola/indice.json` dice qué series tocaban hoy y cuántos candidatos hay.
  No se enlaza desde ningún menú y `_headers` (`X-Robots-Tag: noindex`) la
  deja fuera de los buscadores. `robots.txt` no la bloquea a propósito: el
  fetcher de Cowork respeta robots.txt y no podría leerla.
- `fonts/` y `brand/`: copia de las fuentes y del logo del repo, para que el
  build de Cloudflare Pages no dependa de nada fuera de `site/`.

Este script solo prepara ficheros: no publica nada por sí solo. Cloudflare
Pages reconstruye la web cuando el commit de este job llega a `main`.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))  # este script se ejecuta como `python transform/export_web.py`

from content.copy_factory import calendario  # noqa: E402
from content.copy_factory.nombres import normalizar_nombres  # noqa: E402

GOLD_ROOT = REPO_ROOT / "gold"
QUEUE_ROOT = REPO_ROOT / "queue"
SITE_PUBLIC = REPO_ROOT / "site" / "public"
DATOS = SITE_PUBLIC / "datos"
IMG = SITE_PUBLIC / "img"
COLA = SITE_PUBLIC / "cola"

BASE_URL = "https://padeldb.es"
DIAS_DE_COLA = 14  # la cola caduca a los 7 días (doc 03 §6); se deja margen

TABLAS: dict[str, tuple[str, str]] = {
    "ranking_movimientos_semana": ("Movimientos del ranking", "Puestos ganados o perdidos por jugador en la última semana, con puntos."),
    "forma_reciente": ("Forma reciente", "Partidos, victorias, porcentaje de victorias y racha de cada jugador en las últimas 8 semanas."),
    "perfil_top100": ("Perfil del top 100", "Edad, nacionalidad, altura y lado de pista de los cien primeros de cada ranking."),
    "parejas_duracion": ("Duración de las parejas", "Cuánto lleva cada pareja jugando junta, reconstruido a partir de los partidos."),
    "h2h": ("Cara a cara entre parejas", "Historial de victorias entre cada par de parejas que se han enfrentado."),
    "torneo_sorpresas": ("Sorpresas de torneo", "Derrotas de cabezas de serie por diferencia de semilla."),
    "ganancias_temporada": ("Ganancias de la temporada", "Prize money acumulado por jugador con el detalle por torneo."),
    "puntos_a_defender": ("Puntos a defender", "Puntos del ranking que caducan en las próximas semanas."),
    "pistas_provincia": ("Pistas por provincia", "Elementos de pádel de OpenStreetMap por provincia y por 10.000 habitantes."),
    "licencias_nacional": ("Licencias federativas", "Serie anual de licencias de pádel en España (CSD y FEP, sin mezclar)."),
    "mercado_pais": ("Mercado por país", "Cifras de mercado de los informes de la FIP y de Playtomic, sin mezclar."),
    "trends_geo": ("Interés en Google", "Ratio de interés pádel/tenis en Google Trends por país en expansión."),
}


def _latest_dir(root: Path) -> Path | None:
    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def _escribir_csv(filas: list[dict[str, Any]], destino: Path) -> None:
    columnas = [k for k, v in filas[0].items() if not isinstance(v, (list, dict))]
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def export_gold() -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    catalogo: list[dict[str, Any]] = []
    for tabla, (titulo, descripcion) in TABLAS.items():
        dt_dir = _latest_dir(GOLD_ROOT / tabla)
        if dt_dir is None:
            print(f"  (sin datos para {tabla})")
            continue
        todas = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
        # Las grafías de nombres salen de data/manual/alias_jugadores.csv (CLAUDE.md).
        filas = [normalizar_nombres(r) for r in todas if r.get("publicable", True)]
        fecha = dt_dir.name.split("=", 1)[1]

        (DATOS / f"{tabla}.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
        if filas:
            _escribir_csv(filas, DATOS / f"{tabla}.csv")
        catalogo.append(
            {
                "tabla": tabla,
                "titulo": titulo,
                "descripcion": descripcion,
                "fecha_dato": fecha,
                "filas": len(filas),
                "fuentes": sorted({r["fuente_txt"] for r in filas if r.get("fuente_txt")}),
                "json": f"/datos/{tabla}.json",
                "csv": f"/datos/{tabla}.csv" if filas else None,
            }
        )
        print(f"  {tabla}: {len(filas)}/{len(todas)} filas publicables (fecha {fecha})")

    (DATOS / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")


def export_charts() -> None:
    """El gráfico más reciente de cada nombre de fichero (los nombres no
    llevan fecha, así que la web puede referenciarlos sin listar nada)."""
    IMG.mkdir(parents=True, exist_ok=True)
    dias = sorted(p for p in QUEUE_ROOT.glob("*") if p.is_dir())
    n = 0
    for dia in dias:
        for png in dia.glob("*.png"):
            # Las copias fijas de cada candidato (`0101_forma_reciente_f_16x9.png`)
            # son de la cola, no de la web.
            if png.name[:4].isdigit() and png.name[4:5] == "_":
                continue
            shutil.copy(png, IMG / png.name)
            n += 1
    print(f"  {len(list(IMG.glob('*.png')))} gráficos en site/public/img ({n} copiados)")


def export_cola() -> None:
    """Doc 03 §6: `padeldb.es/cola/<fecha>.json` y `padeldb.es/cola/hoy.json`."""
    COLA.mkdir(parents=True, exist_ok=True)
    dias = sorted(p for p in QUEUE_ROOT.glob("*") if p.is_dir() and (p / "candidates.json").exists())
    dias = dias[-DIAS_DE_COLA:]

    for viejo in COLA.iterdir():
        if viejo.name in {d.name for d in dias} or viejo.name in {f"{d.name}.json" for d in dias} or viejo.name in {"hoy.json", "indice.json"}:
            continue
        shutil.rmtree(viejo) if viejo.is_dir() else viejo.unlink()

    for dia in dias:
        candidatos = json.loads((dia / "candidates.json").read_text(encoding="utf-8"))
        (COLA / dia.name).mkdir(exist_ok=True)
        for c in candidatos:
            for clave in ("png_16x9", "png_4x5"):
                origen = REPO_ROOT / c[clave]
                shutil.copy(origen, COLA / dia.name / origen.name)
                c[clave] = f"{BASE_URL}/cola/{dia.name}/{origen.name}"
        contenido = json.dumps(candidatos, ensure_ascii=False, indent=2)
        (COLA / f"{dia.name}.json").write_text(contenido, encoding="utf-8")

    # hoy.json es la cola de hoy y solo la de hoy: si no hay, lista vacía.
    # Antes era "el último día con candidatos", y la tarea de Cowork habría
    # vuelto a proponer candidatos de días anteriores (ya publicados).
    hoy = date.today()
    del_dia = COLA / f"{hoy.isoformat()}.json"
    candidatos_hoy = json.loads(del_dia.read_text(encoding="utf-8")) if del_dia.exists() else []
    (COLA / "hoy.json").write_text(json.dumps(candidatos_hoy, ensure_ascii=False, indent=2), encoding="utf-8")

    # indice.json deja distinguir a Cowork "hoy no toca ninguna serie" de
    # "tocaba y la cola aún no se ha generado (o ha fallado)".
    indice = {
        "fecha": hoy.isoformat(),
        "actualizado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series_previstas": sorted(calendario.series_del_dia(hoy, calendario.cargar_torneos())),
        "candidatos_hoy": len(candidatos_hoy),
        "publicables_hoy": sum(1 for c in candidatos_hoy if c.get("publicable") and c.get("estado") == "candidato"),
        "dias": [d.name for d in dias],
    }
    (COLA / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  cola: {len(dias)} días; hoy.json = {hoy} ({len(candidatos_hoy)} candidatos); "
          f"series previstas: {indice['series_previstas'] or 'ninguna'}")


def export_assets() -> None:
    for origen, destino, patron in (
        (REPO_ROOT / "fonts", SITE_PUBLIC / "fonts", "*.ttf"),
        (REPO_ROOT / "brand", SITE_PUBLIC / "brand", "*.svg"),
    ):
        destino.mkdir(parents=True, exist_ok=True)
        for f in origen.glob(patron):
            shutil.copy(f, destino / f.name)


def main() -> None:
    print("Gold:")
    export_gold()
    print("Gráficos:")
    export_charts()
    print("Cola:")
    export_cola()
    export_assets()


if __name__ == "__main__":
    main()
