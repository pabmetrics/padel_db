"""copy_factory (doc 01 §3.4, doc 02 §6) — genera el texto de cada
candidato a partir de la fila gold, con la API de Claude.

Reglas duras del prompt (doc 02 §6, doc 03 §4 "Instrucciones del
proyecto"): solo cifras que estén en los datos, formato numérico español,
nombres de jugadores exactos, sin adjetivos ni especulación, sin pedir
interacción genérica, como mucho un emoji al inicio, siempre con fuente.
"Si dudas del dato, no sale": este módulo no suaviza esas reglas, las hace
fallar con `ValueError` en vez de dejar pasar un texto no verificable — la
revisión humana (doc 03 §5.1) es la última barrera, no la única.

Ajuste 22/09/2026 (a petición del usuario): tono más cercano y cierre con
pregunta a la comunidad cuando el dato lo sostiene (doc 02 §7 ya preveía
esto como plantilla — "Pregunta con dato" — y doc 03 §4 lo permite
explícitamente: "una pregunta a la comunidad es válida"). Sigue prohibido
cualquier adjetivo o interpretación sobre el dato o las personas: la
cercanía es de ritmo y construcción de frase, no de opinión.

Lo que se puede garantizar por código no se le pide al modelo: la línea de
fuente y los hashtags los añade `generar_texto`, el modelo solo escribe el
cuerpo. Las comprobaciones de léxico, emojis y grafía de nombres están en
`verificaciones.py`. Si el texto falla una comprobación, se reintenta una
vez diciéndole al modelo qué falló; si vuelve a fallar, el candidato se
descarta.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

import anthropic  # noqa: E402

from content.copy_factory.nombres import normalizar_nombres  # noqa: E402
from content.copy_factory.verificaciones import comprobar_texto  # noqa: E402

MODEL = "claude-haiku-4-5-20251001"  # modelo económico (doc 01 §4: "el input es una fila de datos")
MAX_TOKENS = 600
MAX_CARACTERES_X_OBJETIVO = 240  # doc 02 §6, plantilla de texto
LIMITE_DURO_X = 280  # límite real de X sin Premium (doc 02 §8)
MAX_INTENTOS = 2

PROMPT_SISTEMA = """Eres el copy_factory de PadelDB (@padeldb_ en X), una cuenta de datos de pádel en español.

Recibes un JSON con "serie", "values" (los únicos datos que existen) y "max_caracteres_x". Escribes solo el cuerpo del texto: la línea de fuente y el pie los añade otro sistema, no los escribas.

Tono: cercano y humano, no robótico ni acartonado — puedes dirigirte al lector, usar un ritmo natural, algún toque de humor seco si encaja. Eso no es lo mismo que opinar: sigue prohibido cualquier adjetivo o valoración sobre personas o sobre el dato.

Reglas duras, sin excepción:
1. Usa solo lo que aparece en "values". Ni cifras, ni hechos, ni contexto que no esté ahí: no añadas nacionalidad, edad, palmarés, pareja, torneo ganado, ni palabras como "mundial" o "récord" si los datos no lo dicen. Si "values" no da para una segunda frase de contexto, no la escribas: una línea corta basta. Nunca rellenes con valoraciones.
2. Formato numérico español: punto de miles, coma decimal (1.254 y 27,8).
3. Nombres de jugadores exactamente como vienen en "values", con sus acentos tal cual, sin acortar ni "corregir" la grafía.
4. Prohibido cualquier adjetivo o adverbio valorativo sobre personas o datos (notable, destacado, impresionante, histórico…) y toda especulación o interpretación (consolida, refleja, demuestra, apunta a, progresión, desempeño, probablemente…). Describe el dato, no lo interpretes. La cercanía va en el ritmo y la construcción de la frase, no en calificar el dato.
5. Sin pedir interacción genérica (nunca "dale like", "sígueme", "comenta", "RT si...", "¿qué opinas?"). En cambio, cuando el dato dé pie a ello, cierra con una pregunta concreta a la comunidad que invite al debate y esté anclada en ese dato — no una pregunta vacía. Por ejemplo, ante una subida en el ranking: "¿Hasta dónde puede llegar esta semana que viene?"; ante una comparativa de dos fuentes: "¿Con qué cifra te quedas?". Inclúyela con frecuencia, no solo cuando sea imprescindible, siempre que quepa en el límite de caracteres.
6. Como mucho un emoji, solo al principio del texto, y solo si aporta.
7. No incluyas la palabra "Fuente" ni ninguna URL.

Texto de X: primera línea con la cifra más sorprendente; si hace falta, una segunda línea con el contexto en una frase; si cabe, cierra con la pregunta de la regla 5. Como máximo "max_caracteres_x" caracteres en total.
Texto de Instagram: más largo (hasta 4-5 líneas cortas), mismo tono cercano y mismas reglas, sin emojis. También puede cerrar con la pregunta de la regla 5.
Hashtags: 2 o 3 (por ejemplo "#padel #PadelDB").

Si recibes "error_intento_anterior", tu respuesta anterior incumplió una regla: reescríbela corrigiendo exactamente eso.

Responde solo con un JSON {"x": "...", "instagram": "...", "hashtags": "#... #..."}, sin explicación ni texto fuera del JSON."""


def _cliente() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta ANTHROPIC_API_KEY. En local: añádela a un fichero .env en la raíz del repo "
            "(ANTHROPIC_API_KEY=sk-ant-...). En producción: secreto de GitHub Actions."
        )
    return anthropic.Anthropic(api_key=api_key)


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


def _quitar_valla_markdown(texto: str) -> str:
    """El modelo a veces envuelve el JSON en una valla de código markdown
    (` ```json ... ``` `) pese a que el prompt pide "solo un JSON, sin
    texto fuera" — se ha visto en la primera llamada real. Se quita antes
    de parsear en vez de depender de que el modelo nunca lo haga."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```[a-zA-Z]*\n?", "", texto)
        texto = re.sub(r"\n?```$", "", texto)
    return texto.strip()


def _validar_y_ensamblar(salida: dict[str, Any], serie: str, values: dict[str, Any], fuente_txt: str) -> dict[str, str]:
    cuerpo_x = str(salida.get("x", "")).strip()
    cuerpo_ig = str(salida.get("instagram", "")).strip()
    hashtags = str(salida.get("hashtags", "")).strip()
    if not cuerpo_x or not cuerpo_ig:
        raise ValueError(f"Respuesta incompleta del modelo: {salida!r}")
    if not re.fullmatch(r"(?:#\w+\s*){1,3}", hashtags):
        raise ValueError(f"Hashtags no válidos (2-3, formato #palabra): {hashtags!r}")

    pie = f"Fuente: {fuente_txt}"
    texto_x = f"{cuerpo_x}\n\n{pie}"
    texto_ig = f"{cuerpo_ig}\n\n{pie}\n\n{hashtags}"
    if len(texto_x) > LIMITE_DURO_X:
        raise ValueError(f"Texto de X por encima del límite real de X ({len(texto_x)} > {LIMITE_DURO_X} caracteres)")

    # Los números válidos son los de `values` y también los que ya
    # aparecen en `fuente_txt` (p. ej. la fecha, "2026-09-16"): el texto
    # cita la fuente tal cual, así que esas cifras no son una invención.
    numeros_validos = _numeros_en_values(values) | _numeros_en_texto(fuente_txt)
    for nombre_texto, cuerpo, completo in (("X", cuerpo_x, texto_x), ("Instagram", cuerpo_ig, texto_ig)):
        if re.search(r"fuente", cuerpo, re.IGNORECASE):
            raise ValueError(f"El cuerpo del texto de {nombre_texto} menciona la fuente: la añade el sistema")
        for numero in _numeros_en_texto(completo):
            if numero not in numeros_validos:
                raise ValueError(
                    f"El texto de {nombre_texto} contiene una cifra que no está en los datos: {numero!r} (datos: {values})"
                )
        comprobar_texto(cuerpo, serie, values, fuente_txt)

    return {"x": texto_x, "instagram": texto_ig}


def generar_texto(serie: str, values: dict[str, Any], fuente_txt: str) -> dict[str, str]:
    """Genera los textos de X e Instagram para un candidato. Lanza
    `ValueError` si el resultado no pasa las comprobaciones duras tras
    `MAX_INTENTOS` intentos — mejor que la función falle aquí a que un
    texto con una cifra inventada o una valoración llegue a la cola."""
    values_norm = normalizar_nombres(values)
    cliente = _cliente()

    pie = f"Fuente: {fuente_txt}"
    mensaje: dict[str, Any] = {
        "serie": serie,
        "values": values_norm,
        "max_caracteres_x": MAX_CARACTERES_X_OBJETIVO - len(pie) - 2,
    }

    ultimo_error: ValueError | None = None
    for _ in range(MAX_INTENTOS):
        respuesta = cliente.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=PROMPT_SISTEMA,
            messages=[{"role": "user", "content": json.dumps(mensaje, ensure_ascii=False)}],
        )
        texto_bruto = _quitar_valla_markdown(respuesta.content[0].text.strip())
        try:
            salida = json.loads(texto_bruto)
            if not isinstance(salida, dict):
                raise ValueError(f"El modelo no devolvió un objeto JSON: {texto_bruto!r}")
            return _validar_y_ensamblar(salida, serie, values_norm, fuente_txt)
        except json.JSONDecodeError:
            ultimo_error = ValueError(f"El modelo no devolvió JSON válido: {texto_bruto!r}")
        except ValueError as e:
            ultimo_error = e
        mensaje["error_intento_anterior"] = str(ultimo_error)

    raise ValueError(f"Sin texto válido tras {MAX_INTENTOS} intentos: {ultimo_error}")
