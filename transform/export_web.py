"""export_web — versión mínima para la preview estática (doc 01 §5).

Copia el último snapshot de cada tabla gold y los gráficos más recientes de
la cola a site/public/, con nombres de fichero fijos (sin fecha) para que la
web estática los pueda referenciar sin necesidad de listar directorios ni
tener build step. Cuando llegue la Fase 4 de verdad (Astro + Cloudflare
Pages), este script se sustituye por el export_web definitivo del doc.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_ROOT = REPO_ROOT / "gold"
QUEUE_ROOT = REPO_ROOT / "queue"
SITE_DATA = REPO_ROOT / "site" / "data"
SITE_IMG = REPO_ROOT / "site" / "img"

GOLD_TABLES = [
    "ranking_movimientos_semana",
    "perfil_top100",
    "forma_reciente",
    "parejas_duracion",
    "h2h",
    "torneo_sorpresas",
    "puntos_a_defender",
    "ganancias_temporada",
    "pistas_provincia",
    "licencias_nacional",
]


def _latest_dir(root: Path) -> Path | None:
    dirs = sorted((p for p in root.glob("*=*") if p.is_dir()), key=lambda p: p.name)
    return dirs[-1] if dirs else None


def export_gold() -> None:
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    for tabla in GOLD_TABLES:
        dt_dir = _latest_dir(GOLD_ROOT / tabla)
        if dt_dir is None:
            print(f"  (sin datos para {tabla})")
            continue
        data = json.loads((dt_dir / "data.json").read_text(encoding="utf-8"))
        out_file = SITE_DATA / f"{tabla}.json"
        out_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        fecha = dt_dir.name.split("=", 1)[1]
        print(f"  {tabla}: {len(data)} filas (fecha {fecha}) -> {out_file.relative_to(REPO_ROOT)}")


def export_charts() -> None:
    SITE_IMG.mkdir(parents=True, exist_ok=True)
    dt_dirs = sorted((p for p in QUEUE_ROOT.glob("*") if p.is_dir()), key=lambda p: p.name)
    if not dt_dirs:
        print("  (sin gráficos en la cola)")
        return
    ultimo = dt_dirs[-1]
    for png in ultimo.glob("*.png"):
        shutil.copy(png, SITE_IMG / png.name)
        print(f"  {png.name} -> {(SITE_IMG / png.name).relative_to(REPO_ROOT)}")


def main() -> None:
    print("Gold:")
    export_gold()
    print("Gráficos:")
    export_charts()


if __name__ == "__main__":
    main()
