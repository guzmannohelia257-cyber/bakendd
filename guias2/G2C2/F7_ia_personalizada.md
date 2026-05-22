# F7 — IA personalizada al contexto

> **Pre-requisito:** F1 del Ciclo 1 (categorías oficiales en BD).
> **Esfuerzo:** 1 día.

## Objetivo (del enunciado)
> "La IA integrada debe estar **personalizada al contexto** del proyecto (talleres vehiculares, tipos de servicio, zonas geográficas). No se acepta IA respondiendo en inglés ni sin adaptación."

Lo que vamos a hacer:
1. Prompts en español específicos del dominio.
2. Mapeo estricto a las 7 categorías oficiales del catálogo.
3. Reconocer terminología local (modismos bolivianos).
4. Sugerir prioridad según contexto (carretera vs. ciudad, hora).
5. Cache de respuestas en Redis (no quemar tokens duplicados).

---

## Estado actual
Ya existen `app/ai_modules/vision.py` y `app/ai_modules/audio.py` con Google Gemini. Vamos a refactorizar para:
- Cargar prompts desde archivos `app/ai_modules/prompts/*.md` (versionables).
- Validar que la respuesta del modelo sea uno de los códigos oficiales (rechazar libre).
- Capa de cache.

---

## Estructura

```
app/ai_modules/
├── __init__.py
├── audio.py              (existente - refactor)
├── vision.py             (existente - refactor)
├── classifier.py         NUEVO - logica de clasificacion + validacion
├── cache.py              NUEVO - wrapper Redis especifico
└── prompts/
    ├── clasificar_audio.md
    ├── clasificar_imagen.md
    └── priorizar.md
```

---

## Prompts (Spanish, dominio-specific)

`app/ai_modules/prompts/clasificar_audio.md`:

```markdown
Eres un asistente de emergencias vehiculares en Bolivia. El usuario te
describio un problema con su vehiculo. Tu trabajo es clasificarlo en UNA
de estas 7 categorias OFICIALES y nada mas:

- llantas           : problemas de llantas, neumaticos, vulcanizado, parche, pinchazo,
                      desinflado, "se me bajo la goma", "pinche una llanta"
- mecanica_general  : motor, frenos, transmision, caja, no arranca por mecanica,
                      perdida de potencia, ruidos extranos del motor
- electrico         : sistema electrico, alternador, bateria descargada, no enciende,
                      luces que no prenden, motor de arranque
- electronico       : ECU, computadora del auto, sensores, codigos de falla,
                      escaner OBD, problemas de inyeccion electronica
- chaperia_pintura  : choque, abolladura, pintura rayada, danios por colision,
                      espejos rotos, parachoques
- grua_auxilio     : el vehiculo no se puede mover, necesita remolque,
                      grua, atascado, volcado
- rutinario         : cambio de aceite, alineado, balanceado, revision general,
                      mantenimiento preventivo

REGLAS:
1. Responde SOLO en español.
2. Devuelve JSON valido con esta estructura exacta:
   {
     "codigo": "<uno_de_los_7>",
     "confianza": <float 0.0 a 1.0>,
     "resumen": "<descripcion corta del problema, max 200 caracteres>",
     "prioridad": "baja|media|alta|critica",
     "requiere_revision_manual": <true|false>
   }
3. Si NO puedes clasificar con confianza > 0.5, usa codigo="mecanica_general"
   y requiere_revision_manual=true.
4. Prioridad:
   - critica: vehiculo no se puede mover Y esta en carretera o zona peligrosa
   - alta:    vehiculo no se puede mover en ciudad
   - media:   se mueve pero con problemas
   - baja:    mantenimiento preventivo

Texto del usuario:
"""
{texto_usuario}
"""
```

`app/ai_modules/prompts/clasificar_imagen.md`:

```markdown
Eres un perito automotriz. Te muestran una foto del problema reportado.

Analiza la imagen y devuelve JSON valido:
{
  "codigo": "<uno de: llantas, mecanica_general, electrico, electronico, chaperia_pintura, grua_auxilio, rutinario>",
  "confianza": <0.0 a 1.0>,
  "descripcion": "<que se ve en la foto, max 300 caracteres, en espanol>",
  "danios_visibles": ["<lista corta>"],
  "requiere_revision_manual": <bool>
}

Reglas:
- Responde SOLO en español.
- Si la foto no es clara o no muestra un problema vehicular,
  confianza=0.2 y requiere_revision_manual=true.
- Si ves una llanta desinflada/pinchada -> codigo="llantas".
- Si ves abolladuras, raspones, vidrio roto -> codigo="chaperia_pintura".
- Si ves humo del motor o liquidos derramados -> codigo="mecanica_general".
- NUNCA inventes categorias fuera de la lista.
```

---

## `app/ai_modules/cache.py`

```python
"""Cache de respuestas IA en Redis para no quemar tokens duplicados."""
import hashlib
import json
from typing import Optional

from app.core.cache import get_redis

PREFIX = "yary:ai:"
TTL_SECONDS = 60 * 60 * 24  # 1 dia


def _key(namespace: str, payload: str) -> str:
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{PREFIX}{namespace}:{h}"


def cache_get(namespace: str, payload: str) -> Optional[dict]:
    r = get_redis()
    if not r:
        return None
    raw = r.get(_key(namespace, payload))
    if raw:
        return json.loads(raw)
    return None


def cache_set(namespace: str, payload: str, value: dict, ttl: int = TTL_SECONDS) -> None:
    r = get_redis()
    if not r:
        return
    r.setex(_key(namespace, payload), ttl, json.dumps(value))
```

---

## `app/ai_modules/classifier.py`

```python
"""
Clasificador principal: encapsula prompts + validacion + cache + fallback.

Si Gemini falla o no esta configurado, usa un clasificador heuristico simple
basado en keywords (suficiente para defender la demo si la API esta caida).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from app.ai_modules import cache as ai_cache
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 7 categorias oficiales
CATEGORIAS_VALIDAS = {
    "llantas", "mecanica_general", "electrico", "electronico",
    "chaperia_pintura", "grua_auxilio", "rutinario",
}

PRIORIDADES_VALIDAS = {"baja", "media", "alta", "critica"}

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


# ---- Cliente Gemini ----

try:
    from google import genai  # type: ignore
    _genai_ok = True
except ImportError:
    _genai_ok = False


def _gemini_client():
    if not _genai_ok:
        return None
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        return None
    return genai.Client(api_key=settings.GEMINI_API_KEY)


# ---- Heuristica fallback (sin IA) ----

_KEYWORDS_FALLBACK = {
    "llantas": ["llanta", "neumatico", "neumático", "goma", "pinchaz", "vulcaniz", "desinflad", "pinche"],
    "mecanica_general": ["motor", "freno", "transmis", "no arranca", "ruido", "potencia"],
    "electrico": ["bateria", "batería", "alternador", "luces", "no enciende", "electric"],
    "electronico": ["escaner", "scanner", "ECU", "sensor", "computador", "inyecc"],
    "chaperia_pintura": ["choque", "chocó", "abollad", "rayad", "pintur", "espejo", "vidrio", "parachoq"],
    "grua_auxilio": ["grua", "grúa", "remolque", "no se mueve", "atascad", "volcad"],
    "rutinario": ["aceite", "alinea", "balance", "mantenim", "revision"],
}


def clasificar_heuristico(texto: str) -> dict:
    """Fallback sin IA: scoring por keywords."""
    t = texto.lower()
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in _KEYWORDS_FALLBACK.items()}
    mejor = max(scores, key=scores.get)
    score_max = scores[mejor]
    return {
        "codigo": mejor if score_max > 0 else "mecanica_general",
        "confianza": min(0.4 + score_max * 0.15, 0.9) if score_max > 0 else 0.2,
        "resumen": texto[:200],
        "prioridad": "media",
        "requiere_revision_manual": score_max == 0,
        "_metodo": "heuristico",
    }


# ---- API publica ----

def clasificar_descripcion(texto_usuario: str) -> dict:
    """
    Devuelve dict validado:
      { codigo, confianza, resumen, prioridad, requiere_revision_manual }
    """
    if not texto_usuario or not texto_usuario.strip():
        return {
            "codigo": "mecanica_general",
            "confianza": 0.0,
            "resumen": "",
            "prioridad": "media",
            "requiere_revision_manual": True,
            "_metodo": "vacio",
        }

    # 1) Cache
    cached = ai_cache.cache_get("clasificar_texto", texto_usuario)
    if cached:
        cached["_metodo"] = "cache"
        return cached

    # 2) Gemini
    client = _gemini_client()
    if client is None:
        result = clasificar_heuristico(texto_usuario)
    else:
        try:
            prompt = _load_prompt("clasificar_audio.md").format(texto_usuario=texto_usuario)
            response = client.models.generate_content(
                model=get_settings().GEMINI_MODEL or "gemini-2.0-flash",
                contents=prompt,
            )
            raw = response.text.strip()
            # Limpiar code fences si los hay
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            result = _validar(parsed)
            result["_metodo"] = "gemini"
        except Exception as exc:
            logger.warning("Gemini fallo (%r) - usando heuristico", exc)
            result = clasificar_heuristico(texto_usuario)

    # 3) Cache de resultado
    ai_cache.cache_set("clasificar_texto", texto_usuario, result)
    return result


def _validar(data: dict) -> dict:
    """
    Garantiza que la respuesta cumple el contrato. Cualquier valor invalido
    se reemplaza por un default seguro.
    """
    codigo = str(data.get("codigo", "")).strip().lower()
    if codigo not in CATEGORIAS_VALIDAS:
        codigo = "mecanica_general"

    try:
        confianza = float(data.get("confianza", 0))
        confianza = max(0.0, min(1.0, confianza))
    except (TypeError, ValueError):
        confianza = 0.5

    resumen = str(data.get("resumen", ""))[:200]

    prioridad = str(data.get("prioridad", "media")).lower()
    if prioridad not in PRIORIDADES_VALIDAS:
        prioridad = "media"

    rev = bool(data.get("requiere_revision_manual", False))
    if confianza < 0.5:
        rev = True

    return {
        "codigo": codigo,
        "confianza": round(confianza, 3),
        "resumen": resumen,
        "prioridad": prioridad,
        "requiere_revision_manual": rev,
    }
```

---

## Integración en el endpoint de incidente

En `app/api/incidencias.py`, al crear el incidente:

```python
from app.ai_modules.classifier import clasificar_descripcion
from app.models.catalogos import CategoriaProblema, Prioridad


def _id_categoria_desde_codigo(db, codigo: str) -> int | None:
    cat = db.query(CategoriaProblema).filter_by(codigo=codigo).first()
    return cat.id_categoria if cat else None


def _id_prioridad_desde_nivel(db, nivel: str) -> int | None:
    p = db.query(Prioridad).filter_by(nivel=nivel).first()
    return p.id_prioridad if p else None


@router.post("/incidentes", ...)
async def crear_incidente(body: IncidenteCreate, db: Session = Depends(get_db), ...):
    # Si el body trae descripcion pero no categoria, clasificar con IA
    if body.descripcion and not body.id_categoria:
        ia = clasificar_descripcion(body.descripcion)
        body.id_categoria = _id_categoria_desde_codigo(db, ia["codigo"])
        id_prioridad = _id_prioridad_desde_nivel(db, ia["prioridad"])
        resumen_ia = ia["resumen"]
        confianza = ia["confianza"]
        rev_manual = ia["requiere_revision_manual"]
    else:
        id_prioridad = None
        resumen_ia = None
        confianza = None
        rev_manual = False

    inc = Incidente(
        id_usuario=current_user.id_usuario,
        id_vehiculo=body.id_vehiculo,
        id_estado=...,
        id_categoria=body.id_categoria,
        id_prioridad=id_prioridad,
        latitud=body.latitud,
        longitud=body.longitud,
        descripcion_usuario=body.descripcion,
        resumen_ia=resumen_ia,
        clasificacion_ia_confianza=confianza,
        requiere_revision_manual=rev_manual,
    )
    # ... resto del flujo (broadcast, etc.)
```

---

## Tests `tests/test_ia_classifier.py`

```python
"""Tests del clasificador IA - validan la capa de validacion + fallback."""


def test_codigo_invalido_se_normaliza_a_mecanica_general():
    from app.ai_modules.classifier import _validar
    r = _validar({"codigo": "INVENTADO", "confianza": 0.9, "resumen": "x", "prioridad": "alta"})
    assert r["codigo"] == "mecanica_general"


def test_confianza_fuera_de_rango_se_clampea():
    from app.ai_modules.classifier import _validar
    r = _validar({"codigo": "llantas", "confianza": 2.5, "resumen": "x", "prioridad": "media"})
    assert r["confianza"] == 1.0
    r2 = _validar({"codigo": "llantas", "confianza": -0.5, "resumen": "x", "prioridad": "media"})
    assert r2["confianza"] == 0.0


def test_confianza_baja_marca_revision_manual():
    from app.ai_modules.classifier import _validar
    r = _validar({"codigo": "llantas", "confianza": 0.3, "resumen": "x", "prioridad": "media"})
    assert r["requiere_revision_manual"] is True


def test_prioridad_invalida_default_media():
    from app.ai_modules.classifier import _validar
    r = _validar({"codigo": "llantas", "confianza": 0.8, "resumen": "x", "prioridad": "extrema"})
    assert r["prioridad"] == "media"


def test_heuristico_detecta_llanta_por_keyword():
    from app.ai_modules.classifier import clasificar_heuristico
    r = clasificar_heuristico("Se me pinche la llanta delantera, no puedo seguir")
    assert r["codigo"] == "llantas"
    assert r["confianza"] > 0.4


def test_heuristico_detecta_chaperia():
    from app.ai_modules.classifier import clasificar_heuristico
    r = clasificar_heuristico("Me chocaron por atras y se abollo el parachoque")
    assert r["codigo"] == "chaperia_pintura"


def test_heuristico_sin_keywords_marca_revision():
    from app.ai_modules.classifier import clasificar_heuristico
    r = clasificar_heuristico("Hola, tengo un problema con mi vehiculo")
    assert r["requiere_revision_manual"] is True


def test_clasificar_descripcion_devuelve_codigo_valido_siempre(monkeypatch):
    """End-to-end: aunque Gemini no este, devuelve algo del catalogo."""
    from app.ai_modules import classifier
    monkeypatch.setattr(classifier, "_gemini_client", lambda: None)

    r = classifier.clasificar_descripcion("Choque feo")
    assert r["codigo"] in classifier.CATEGORIAS_VALIDAS
    assert r["_metodo"] == "heuristico"


def test_cache_se_invoca(monkeypatch):
    """Si hay cache hit, no se llama Gemini."""
    from app.ai_modules import cache as ai_cache, classifier

    calls = {"n": 0}
    def fake_get(ns, p):
        calls["n"] += 1
        return {"codigo": "llantas", "confianza": 0.9, "resumen": "cached", "prioridad": "alta", "requiere_revision_manual": False}
    monkeypatch.setattr(ai_cache, "cache_get", fake_get)

    r = classifier.clasificar_descripcion("se pincho mi llanta")
    assert r["_metodo"] == "cache"
    assert calls["n"] == 1
```

---

## Checklist de cierre F7
- [ ] Directorio `app/ai_modules/prompts/` con `.md` en español, dominio-específicos.
- [ ] `clasificar_descripcion()` siempre devuelve uno de los 7 códigos oficiales.
- [ ] Validador rechaza códigos inventados y los reemplaza por `mecanica_general`.
- [ ] Cache Redis funciona (verificable con un segundo request idéntico que no llama Gemini).
- [ ] Fallback heurístico funciona si Gemini está down o sin API key.
- [ ] Endpoint `POST /incidentes` consume la clasificación si no se especifica `id_categoria`.
- [ ] Tests `tests/test_ia_classifier.py` verdes (≥8).
- [ ] Demo: 5 frases reales en español boliviano clasifican correctamente.

## Notas
- **Costo**: cache de 24h reduce drásticamente el gasto. Para producción, usar embeddings + similitud en vez de hash exacto.
- **Validación estricta**: nunca confiar 100% en LLM. Siempre validar contra catálogo conocido.
- **Multi-modal (audio + foto)**: si quieren ir más allá, combinar audio+foto en un solo prompt para mejorar confianza. Por ahora, dos llamadas separadas con votación final está bien.
- **"IA personalizada" en defensa**: tener listos 3-5 ejemplos demostrables: una frase boliviana ("se me bajó la goma"), un audio, una foto. Mostrar el JSON de respuesta con `codigo`, `confianza`, etc.
