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


def marcar_publicado(*, registro: str, url_x: str, fecha_publicado: str, hora_publicado: str | None = None) -> Path:
    """Anota que un candidato se ha publicado de verdad en X (doc 03 §5.2:
    "publicado #0042 a las 8:30"). Es el paso manual que hace posible
    `ingest_metrics`/`gold.rendimiento_posts`: sin `url_x` no hay forma de
    cruzar el export de analíticas de X con el registro/serie del gráfico.

    Busca el candidato por `registro` en todas las carpetas de `queue/`
    (no solo en la de `fecha_publicado`, que puede no coincidir con
    `fecha_dato` si el post se programó para otro día)."""
    for candidates_file in sorted(QUEUE_ROOT.glob("*/candidates.json")):
        candidatos = json.loads(candidates_file.read_text(encoding="utf-8"))
        for candidato in candidatos:
            if candidato.get("registro") == registro:
                candidato["estado"] = "publicado"
                candidato["url_x"] = url_x
                candidato["fecha_publicado"] = fecha_publicado
                candidato["hora_publicado"] = hora_publicado
                candidates_file.write_text(
                    json.dumps(candidatos, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                return candidates_file
    raise ValueError(f"No se ha encontrado el candidato {registro} en ninguna carpeta de queue/")


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Anotar un candidato como publicado en X")
    parser.add_argument("--registro", required=True, help='p. ej. "#0042"')
    parser.add_argument("--url", required=True, dest="url_x", help="enlace permanente del post en X")
    parser.add_argument("--fecha", required=True, dest="fecha_publicado", help="YYYY-MM-DD")
    parser.add_argument("--hora", default=None, dest="hora_publicado", help="HH:MM, opcional")
    args = parser.parse_args()

    out_file = marcar_publicado(
        registro=args.registro,
        url_x=args.url_x,
        fecha_publicado=args.fecha_publicado,
        hora_publicado=args.hora_publicado,
    )
    print(f"{args.registro} -> publicado, anotado en {out_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    _cli()
