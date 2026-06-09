"""
Interpretacion de peticiones en lenguaje natural -> spec de reporte.

Reusa el cliente Gemini de ia_service. Gemini SOLO puede elegir un report_id del
catalogo cerrado (reportes_data_service.CATALOGO); cualquier otra cosa se trata
como peticion vaga y se devuelve una aclaracion con sugerencias. Nunca se genera
SQL ni consultas libres: el report_id devuelto se valida contra el whitelist.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone

from google.genai import types
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tenant_context import current_tenant
from app.models.taller import Taller
from app.services import reportes_data_service as data
from app.services.ia_service import _client

logger = logging.getLogger("reportes_nl")
settings = get_settings()


def _catalogo_texto() -> str:
    lineas = []
    for c in data.CATALOGO:
        params = ", ".join(c["params"]) or "(ninguno)"
        ejs = "; ".join(c.get("ejemplos", []))
        lineas.append(
            f'- report_id="{c["report_id"]}" ({c["titulo"]}): {c["descripcion"]} '
            f"| parametros: {params} | ejemplos: {ejs}"
        )
    return "\n".join(lineas)


def _system_prompt() -> str:
    return f"""Eres un asistente que traduce la peticion de un administrador (en espanol) a UN reporte de un catalogo CERRADO.

CATALOGO DE REPORTES DISPONIBLES (solo puedes elegir uno de estos report_id):
{_catalogo_texto()}

Devuelve SIEMPRE un unico objeto JSON valido, sin markdown, con esta forma exacta:
{{"report_id": <uno del catalogo o null>,
 "titulo": <titulo legible del reporte o null>,
 "params": {{"desde": <YYYY-MM-DD o null>, "hasta": <YYYY-MM-DD o null>, "id_tenant": <int o null>, "sla_minutos": <int o null>, "limite": <int o null>, "anio": <int o null>, "mes": <int o null>}},
 "confianza": <0.0 a 1.0>,
 "aclaracion": <texto breve o null>,
 "sugerencias": <lista de titulos del catalogo o null>}}

REGLAS:
- Elige el report_id cuyo proposito mejor coincida con la peticion. Si ninguno encaja, o la peticion es ambigua o vaga, pon report_id=null, confianza<0.5, una "aclaracion" amable preguntando que necesita, y "sugerencias" con 3-4 titulos del catalogo.
- Resuelve fechas relativas usando HOY. "ultimo mes"/"mes pasado" = 30 dias atras hasta hoy. "mayo" = del 1 al ultimo dia de mayo del anio en curso (o el indicado). "este anio" = desde el 1 de enero. Si no se menciona periodo, deja desde/hasta en null (el backend usa ultimos 30 dias por defecto).
- Para los reportes de ganancias usa "anio" (y "mes" si aplica) en lugar de desde/hasta.
- Si el usuario menciona un taller por nombre, mapea su id_tenant usando la lista TALLERES. Si el nombre es ambiguo o no aparece en la lista, NO inventes id_tenant: dejalo en null y, si el reporte dependia de ese taller, pide aclaracion.
- No incluyas ningun texto fuera del JSON."""


def _es_transitorio(e: Exception) -> bool:
    msg = str(e).lower()
    return any(
        s in msg
        for s in ("503", "unavailable", "overloaded", "resource_exhausted", "429", "high demand")
    )


def _generar_con_reintento(contents, config, intentos: int = 3):
    """Llama a Gemini reintentando ante errores transitorios (503/overloaded/429)
    con backoff incremental. Propaga el ultimo error si no logra responder."""
    ultimo = None
    for i in range(intentos):
        try:
            return _client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=contents, config=config
            )
        except Exception as e:
            ultimo = e
            if _es_transitorio(e) and i < intentos - 1:
                logger.warning("[ReportesNL] Gemini transitorio (intento %d/%d): %s", i + 1, intentos, e)
                time.sleep(1.5 * (i + 1))
                continue
            raise
    if ultimo:
        raise ultimo


def interpretar(db: Session, texto: str) -> dict:
    if _client is None:
        raise RuntimeError(
            "GEMINI_API_KEY no esta configurada en .env. "
            "El asistente de reportes requiere Gemini."
        )

    # Listado de talleres para que el modelo mapee "taller X" -> id_tenant.
    # set(0): super-admin ve todos los talleres sin importar el filtro de tenant.
    tok = current_tenant.set(0)
    try:
        talleres = db.query(Taller).filter(Taller.activo.is_(True)).all()
    finally:
        current_tenant.reset(tok)
    talleres_txt = "\n".join(
        f'- id_tenant={t.id_tenant}: "{t.nombre}"' for t in talleres
    ) or "(sin talleres)"

    hoy = datetime.now(timezone.utc).date().isoformat()
    user_prompt = (
        f"HOY: {hoy}\n\n"
        f"TALLERES:\n{talleres_txt}\n\n"
        f'PETICION DEL ADMINISTRADOR:\n"{texto.strip()}"'
    )

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]
    config = types.GenerateContentConfig(
        system_instruction=_system_prompt(),
        response_mime_type="application/json",
        temperature=0.2,
        max_output_tokens=1024,
    )
    try:
        respuesta = _generar_con_reintento(contents, config)
    except Exception as e:
        logger.exception("[ReportesNL] Error llamando a Gemini: %s", e)
        raise RuntimeError(f"Error al interpretar con IA: {e}") from e

    bruto = (respuesta.text or "").strip()
    match = re.search(r"\{.*\}", bruto, re.DOTALL)
    if not match:
        logger.error("[ReportesNL] Respuesta sin JSON: %s", bruto[:300])
        return _aclaracion_fallback()

    try:
        d = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.error("[ReportesNL] JSON invalido: %s", bruto[:300])
        return _aclaracion_fallback()

    report_id = d.get("report_id")
    confianza = float(d.get("confianza") or 0.0)
    params = d.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    # Validacion dura: report_id debe pertenecer al catalogo y tener confianza.
    if report_id not in data.ids_validos() or confianza < 0.5:
        fb = _aclaracion_fallback()
        if d.get("aclaracion"):
            fb["aclaracion"] = str(d["aclaracion"])[:300]
        if isinstance(d.get("sugerencias"), list) and d["sugerencias"]:
            fb["sugerencias"] = [str(s) for s in d["sugerencias"]][:4]
        fb["confianza"] = confianza
        return fb

    titulo = d.get("titulo") or next(
        (c["titulo"] for c in data.CATALOGO if c["report_id"] == report_id), report_id
    )

    return {
        "report_id": report_id,
        "titulo": titulo,
        "params": params,
        "confianza": confianza,
        "aclaracion": None,
        "sugerencias": None,
    }


def _aclaracion_fallback() -> dict:
    return {
        "report_id": None,
        "titulo": None,
        "params": {},
        "confianza": 0.0,
        "aclaracion": "No estoy seguro de qué reporte necesitas. ¿Puedes elegir uno o reformular la petición?",
        "sugerencias": [c["titulo"] for c in data.CATALOGO[:5]],
    }
