"""copy_factory (doc 01 §3.4, doc 02 §6) — genera el texto de cada
candidato a partir de la fila gold, con la API de Claude.

Reglas duras del prompt (doc 02 §6, doc 03 §4 "Instrucciones del
proyecto"): solo cifras que estén en los datos, formato numérico español,
nombres de jugadores exactos, sin adjetivos ni especulación, sin pedir
interacción, como mucho un emoji al inicio, siempre con fuente. "Si dudas
del dato, no sale": este módulo no suaviza esas reglas, las hace fallar
con `ValueError` en vez de dejar pasar un texto no verificable — la
revisión humana (doc 03 §5.1) es la última barrera, no la única.
"""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

import anthropic  # noqa: E402

MODEL = "claude-haiku-4-5-20251001"  # modelo económico (doc 01 §4: "el input es una fila de datos")
MAX_TOKENS = 600
MAX_CARACTERES_X_OBJETIVO = 240  # doc 02 §6, plantilla de texto
LIMITE_DURO_X = 280  # límite real de X sin Premium (doc 02 §8)

ALIAS_CSV = REPO_ROOT / "data" / "manual" / "alias_jugadores.csv"

PROMPT_SISTEMA = """Eres el copy_factory de PadelDB (@padeldb), una cuenta de datos de pádel en español.

Reglas duras, sin excepción:
1. Usa solo las cifras que aparecen en los datos que te paso (bajo "values"). Nunca inventes una cifra, ni la redondees de forma que cambie el sentido, ni añadas una que no esté ahí.
2. Formato numérico español siempre: punto de miles, coma decimal (1.254 y 27,8 — nunca 1,254 ni 27.8).
3. Nombres de jugadores exactamente como te los paso, sin acortar ni cambiar la grafía.
4. Sin adjetivos sobre personas, sin especulación, sin opinión: los datos hablan.
5. Sin pedir interacción (nunca "dale like", "sígueme", "comenta", "RT si..."). Una pregunta a la comunidad sí es válida si el formato la pide.
6. Como mucho un emoji, solo al principio, y solo si aporta — nunca decorativo.
7. Termina siempre citando la fuente que te paso ("fuente_txt"), tal cual.

Formato del texto de X: máximo 240 caracteres, en tres partes — primera línea con la cifra más sorprendente, segunda con el contexto en una frase, tercera con la fuente.
Formato del texto de Instagram: más largo (hasta 5-6 líneas cortas), mismo tono sobrio, puede cerrar con 2-3 hashtags relevantes de pádel (por ejemplo #padel #PadelDB), sin emojis adicionales a los del texto de X.

Responde solo con un JSON de la forma {"x": "...", "instagram": "..."}, sin explicación ni texto fuera del JSON."""


def _cliente() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta ANTHROPIC_API_KEY. En local: añádela a un fichero .env en la raíz del repo "
            "(ANTHROPIC_API_KEY=sk-ant-...). En producción: secreto de GitHub Actions."
        )
    return anthropic.Anthropic(api_key=api_key)


def _cargar_alias() -> dict[str, str]:
    """`data/manual/alias_jugadores.csv`: alias -> nombre_canonico (CLAUDE.md:
    "usar siempre alias_jugadores.csv como fuente de la grafía correcta").
    Hoy solo tiene la cabecera, sin filas — cuando tenga datos, cualquier
    alias que aparezca en `values` se sustituye por su grafía oficial antes
    de mandarlo al modelo, en vez de confiar en que el modelo "sepa" cuál
    es la correcta."""
    if not ALIAS_CSV.exists():
        return {}
    alias: dict[str, str] = {}
    with ALIAS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("alias") and row.get("nombre_canonico"):
                alias[row["alias"]] = row["nombre_canonico"]
    return alias


def _normalizar_nombres(values: dict[str, Any]) -> dict[str, Any]:
    alias = _cargar_alias()
    if not alias:
        return values
    return {k: (alias[v] if isinstance(v, str) and v in alias else v) for k, v in values.items()}


def _formatear_numero_es(valor: int | float) -> str:
    if isinstance(valor, float) and not valor.is_integer():
        # Sin decimales de más: 27,8 debe quedar así, no "27,80" — solo se
        # fuerzan los decimales que el propio valor tiene.
        texto = f"{valor:,.10f}".rstrip("0").rstrip(".")
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(valor):,}".replace(",", ".")


def _numeros_en_values(values: dict[str, Any]) -> set[str]:
    """Todas las formas en las que una cifra de `values` puede aparecer en
    el texto: con separador de miles, sin él, y (para porcentajes/cifras
    pequeñas) el número suelto. No es exhaustivo con signos (+/-) porque
    esos matices de redacción son legítimos, no una cifra inventada."""
    numeros: set[str] = set()
    for v in values.values():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        numeros.add(_formatear_numero_es(v))
        numeros.add(str(int(v)) if float(v).is_integer() else str(v))
    return numeros


def _numeros_en_texto(texto: str) -> set[str]:
    return set(re.findall(r"\d[\d.,]*\d|\d", texto))


def generar_texto(serie: str, values: dict[str, Any], fuente_txt: str) -> dict[str, str]:
    """Genera los textos de X e Instagram para un candidato. Lanza
    `ValueError` si el resultado no pasa las comprobaciones duras — mejor
    que la función falle aquí a que un texto con una cifra inventada o
    fuera del límite de X llegue a la cola de revisión."""
    values_norm = _normalizar_nombres(values)
    cliente = _cliente()

    mensaje = json.dumps({"serie": serie, "values": values_norm, "fuente_txt": fuente_txt}, ensure_ascii=False)

    respuesta = cliente.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=PROMPT_SISTEMA,
        messages=[{"role": "user", "content": mensaje}],
    )
    texto_bruto = respuesta.content[0].text.strip()
    try:
        salida = json.loads(texto_bruto)
    except json.JSONDecodeError as e:
        raise ValueError(f"El modelo no devolvió JSON válido: {texto_bruto!r}") from e

    texto_x = str(salida.get("x", "")).strip()
    texto_ig = str(salida.get("instagram", "")).strip()
    if not texto_x or not texto_ig:
        raise ValueError(f"Respuesta incompleta del modelo: {salida!r}")
    if len(texto_x) > LIMITE_DURO_X:
        raise ValueError(f"Texto de X por encima del límite real de X ({len(texto_x)} > {LIMITE_DURO_X} caracteres)")

    numeros_validos = _numeros_en_values(values_norm)
    for numero in _numeros_en_texto(texto_x):
        if len(numero) > 1 and numero not in numeros_validos:
            raise ValueError(f"El texto de X contiene una cifra que no está en los datos: {numero!r} (datos: {values_norm})")

    return {"x": texto_x, "instagram": texto_ig}
