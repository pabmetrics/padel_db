"""Tests de la cadena de rendimiento_posts (doc 01 §3.3/§5, ingest_metrics):
marcar un candidato como publicado, cruzarlo con el export de X, y el gold
combinado con la parte web.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from content.copy_factory import cola
from transform import build_fact_rendimiento_x as frx
from transform import build_fact_rendimiento_web as frw
from transform import build_gold_rendimiento_posts as grp


def _escribir_candidato(queue_root: Path, fecha: str, registro: str, estado: str = "candidato") -> None:
    out_dir = queue_root / fecha
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "candidates.json"
    candidatos = json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else []
    candidatos.append(
        {
            "registro": registro,
            "serie": "#RankingLunes",
            "fecha_dato": fecha,
            "values": {"jugador": "Test Jugador", "delta_puestos": 5},
            "fuente_txt": "FIP · elaboración propia",
            "publicable": True,
            "estado": estado,
        }
    )
    out_file.write_text(json.dumps(candidatos, indent=2, ensure_ascii=False), encoding="utf-8")


def test_marcar_publicado_anota_url_y_estado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    monkeypatch.setattr(cola, "QUEUE_ROOT", queue_root)
    _escribir_candidato(queue_root, "2026-09-28", "#0100")

    out_file = cola.marcar_publicado(
        registro="#0100", url_x="https://x.com/padeldb/status/1", fecha_publicado="2026-09-28", hora_publicado="08:30"
    )

    candidatos = json.loads(out_file.read_text(encoding="utf-8"))
    (candidato,) = candidatos
    assert candidato["estado"] == "publicado"
    assert candidato["url_x"] == "https://x.com/padeldb/status/1"
    assert candidato["hora_publicado"] == "08:30"


def test_marcar_publicado_registro_inexistente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    monkeypatch.setattr(cola, "QUEUE_ROOT", queue_root)
    _escribir_candidato(queue_root, "2026-09-28", "#0100")

    with pytest.raises(ValueError):
        cola.marcar_publicado(registro="#9999", url_x="https://x.com/x/status/2", fecha_publicado="2026-09-28")


def test_extraer_metricas_ignora_columnas_vacias() -> None:
    row = {"impressions": "1200", "engagements": "", "likes": "30", "retweets": "5"}
    metricas = frx._extraer_metricas(row)
    assert metricas == {"impresiones": 1200, "me_gusta": 30, "retweets": 5}


def test_fact_rendimiento_x_cruza_por_permalink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_root = tmp_path / "queue"
    csv_dir = tmp_path / "rendimiento_x"
    csv_dir.mkdir()
    monkeypatch.setattr(frx, "QUEUE_ROOT", queue_root)
    monkeypatch.setattr(frx, "CSV_DIR", csv_dir)
    monkeypatch.setattr(frx, "OUT_PATH", tmp_path / "silver" / "fact_rendimiento_x" / "data.json")
    monkeypatch.setattr(frx, "RECONCILIACION_PATH", tmp_path / "recon" / "sin_cruzar.json")

    _escribir_candidato(queue_root, "2026-09-28", "#0100", estado="publicado")
    candidates_file = queue_root / "2026-09-28" / "candidates.json"
    candidatos = json.loads(candidates_file.read_text(encoding="utf-8"))
    candidatos[0]["url_x"] = "https://x.com/padeldb/status/1"
    candidates_file.write_text(json.dumps(candidatos, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_text = (
        "Tweet id,Tweet permalink,time,impressions,engagements,retweets,replies,likes,url clicks\n"
        "1,https://x.com/padeldb/status/1,2026-09-28,1200,90,5,2,30,4\n"
        "2,https://x.com/padeldb/status/999,2026-09-28,300,10,1,0,3,0\n"
    )
    (csv_dir / "2026-09-28.csv").write_text(csv_text, encoding="utf-8")

    out_path = frx.build()
    filas = json.loads(out_path.read_text(encoding="utf-8"))
    assert {f["metrica"]: f["valor"] for f in filas if f["registro"] == "#0100"} == {
        "impresiones": 1200,
        "interacciones": 90,
        "retweets": 5,
        "respuestas": 2,
        "me_gusta": 30,
        "clics_url": 4,
    }

    sin_cruzar = json.loads(frx.RECONCILIACION_PATH.read_text(encoding="utf-8"))
    assert [s["tweet_id"] for s in sin_cruzar] == ["2"]


def test_gold_rendimiento_posts_junta_x_y_web(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fact_x = tmp_path / "silver" / "fact_rendimiento_x" / "data.json"
    fact_x.parent.mkdir(parents=True)
    fact_x.write_text(
        json.dumps(
            [
                {
                    "registro": "#0100",
                    "serie": "#RankingLunes",
                    "fecha_dato": "2026-09-28",
                    "metrica": "impresiones",
                    "valor": 1200,
                }
            ]
        ),
        encoding="utf-8",
    )

    fact_web = tmp_path / "silver" / "fact_rendimiento_web" / "data.json"
    fact_web.parent.mkdir(parents=True)
    fact_web.write_text(
        json.dumps([{"fecha": "2026-09-28", "ruta": "/", "pageviews": 340, "visitas": 210}]),
        encoding="utf-8",
    )

    gold_root = tmp_path / "gold" / "rendimiento_posts"
    monkeypatch.setattr(grp, "FACT_X", fact_x)
    monkeypatch.setattr(grp, "FACT_WEB", fact_web)
    monkeypatch.setattr(grp, "GOLD_ROOT", gold_root)

    out_file = grp.build()
    rows = json.loads(out_file.read_text(encoding="utf-8"))

    fuentes = {r["fuente"] for r in rows}
    assert fuentes == {"x", "web"}
    fila_x = next(r for r in rows if r["fuente"] == "x")
    assert fila_x["registro"] == "#0100" and fila_x["valor"] == 1200
    fila_web = next(r for r in rows if r["fuente"] == "web")
    assert fila_web["ruta"] == "/" and fila_web["metrica"] in ("pageviews", "visitas")
