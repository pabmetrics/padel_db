"""La cola: el contrato entre la máquina y la revisión humana (doc 03 §6).

`queue/<fecha>/candidates.json` es una lista de candidatos. La máquina
(`chart_factory` + `copy_factory`) los crea en estado `candidato`; una
persona (o Cowork en su nombre) los aprueba, programa y publica — este
repo nunca publica nada por sí solo (CLAUDE.md).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_ROOT = REPO_ROOT / "queue"

ESTADOS = ("candidato", "aprobado", "programado", "publicado", "medido")


def anadir_candidato(candidato: dict[str, Any]) -> Path:
    """Añade un candidato a `queue/<fecha_dato>/candidates.json`. Si el
    fichero ya existe (varios candidatos el mismo día), se añade a la
    lista en vez de sobreescribirla."""
    fecha = candidato["fecha_dato"]
    out_dir = QUEUE_ROOT / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "candidates.json"

    candidatos: list[dict[str, Any]] = []
    if out_file.exists():
        candidatos = json.loads(out_file.read_text(encoding="utf-8"))

    candidatos = [c for c in candidatos if c.get("registro") != candidato.get("registro")]
    candidatos.append(candidato)
    candidatos.sort(key=lambda c: c.get("registro", ""))

    out_file.write_text(json.dumps(candidatos, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file
