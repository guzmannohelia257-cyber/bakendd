# F1 — Hardening backend (Swagger + cobertura + cleanup)

> **Pre-requisito:** Ciclos 1 y 2 cerrados.
> **Esfuerzo:** 0.5 día.

## Objetivo
Cerrar deuda técnica antes de la defensa:
- Swagger 100% documentado (descripciones, ejemplos, tags consistentes).
- Cobertura ≥ 70% sobre `app/`.
- Quitar endpoints `/diagnostico/*` o `/debug/*` que sean inseguros.
- Cerrar permisos y rate-limit básico en endpoints sensibles.
- Verificar que no quedan secretos hardcoded o `print()` de debug.

---

## 1. Auditoría de endpoints en Swagger

### Script de inventario

`scripts/audit_swagger.py`:

```python
"""
Lista todos los endpoints. Marca los que no tienen:
  - summary
  - description
  - tag
  - response_model
Util para saber que falta documentar antes de la defensa.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def main() -> int:
    faltas = []
    for route in app.routes:
        if not hasattr(route, "endpoint"):
            continue
        methods = getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        if not methods:
            continue

        path = route.path
        summary = getattr(route, "summary", None)
        descripcion = getattr(route, "description", None) or (
            route.endpoint.__doc__ if route.endpoint.__doc__ else None
        )
        tags = getattr(route, "tags", [])
        response_model = getattr(route, "response_model", None)

        problemas = []
        if not summary:
            problemas.append("sin summary")
        if not descripcion:
            problemas.append("sin description/docstring")
        if not tags:
            problemas.append("sin tag")
        if "POST" in methods or "PUT" in methods or "PATCH" in methods:
            if not response_model:
                problemas.append("sin response_model")

        if problemas:
            faltas.append((list(methods)[0], path, problemas))

    if not faltas:
        print("OK: todos los endpoints estan documentados")
        return 0

    print(f"FALTAN {len(faltas)} endpoints:\n")
    for m, p, probs in faltas:
        print(f"  {m:6s} {p}")
        for x in probs:
            print(f"           - {x}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Correr:
```bash
.\venv\Scripts\python.exe -m scripts.audit_swagger
```

### Reglas para arreglar lo que reporte

Cada `@router.get/post/put/patch/delete` debe tener:

```python
@router.post(
    "/recurso/{id}",
    response_model=RecursoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un recurso",                      # ← OBLIGATORIO
    description="Detalle adicional si el summary no alcanza.",
    responses={                                       # ejemplos de error
        409: {"description": "Recurso ya existe"},
        403: {"description": "Permisos insuficientes"},
    },
    tags=["Recursos"],                                # consistente con otros del dominio
)
def crear(...):
    """
    Crea un recurso. Solo dueno del tenant.
    Ejemplo body: { "nombre": "X" }
    """
```

### Tags estandarizados

Mantener estos tags (en este orden en docs):

| Tag | Endpoints |
|---|---|
| `Auth` | login usuario, login taller |
| `Tenants` | /tenants/*, /signup, /plans |
| `Catalogos` | /categorias, /prioridades |
| `Talleres` | /talleres/* |
| `Vehiculos` | /vehiculos/* |
| `Incidentes` | /incidentes/* |
| `Cotizaciones` | /cotizaciones/*, /incidentes/{id}/cotizaciones |
| `Asignaciones` | /asignaciones/* |
| `Evidencias` | /evidencias/* |
| `Notificaciones` | /notificaciones/* |
| `Mensajes` | /mensajes/* |
| `Pagos` | /pagos/* |
| `Tecnicos` | /tecnicos/* |
| `KPIs` | /tenants/me/kpis, /admin/kpis/* |
| `WebSocket` | /ws |
| `Health` | /, /health |
| `Admin` | /admin/* (super-admin) |

---

## 2. Cobertura ≥ 70%

Instalar:
```bash
.\venv\Scripts\pip.exe install pytest-cov==5.0.0
```

Agregar a `requirements.txt`:
```
pytest-cov==5.0.0
```

Correr:
```bash
$env:DEBUG="False"
.\venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-report=term-missing --cov-report=html
```

Esto genera `htmlcov/index.html` (abrir en navegador) con líneas no cubiertas en rojo.

### Política de cobertura

| Capa | Mínimo aceptable |
|---|---|
| `app/api/` | 80% |
| `app/services/` | 75% |
| `app/core/` (tenant_*, security) | **90%** — crítico |
| `app/models/` | n/a (declaraciones, no lógica) |
| `app/ai_modules/` | 60% (parte es LLM, difícil de mockear) |
| `app/realtime/` | 70% |

Si una zona crítica está roja, agregar tests específicos. Ejemplos de "huecos" típicos:

- Rama 403 nunca testeada → agregar test que la dispara.
- Validación de schema 422 nunca testeada → enviar payload inválido.
- Catch de excepción `Exception` nunca alcanzado → opcional, normalmente lo dejas si es defensivo.

### Excluir lo no relevante

`.coveragerc` en la raíz:

```ini
[run]
source = app
omit =
    app/main.py
    app/db/session.py
    app/ai_modules/audio.py
    app/ai_modules/vision.py
    */__init__.py

[report]
exclude_lines =
    pragma: no cover
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
```

---

## 3. Limpieza de código

### A. Endpoints de diagnóstico — decidir mantener o cerrar

Revisar `app/api/diagnostico.py` (si existe). Cualquier endpoint que:
- Exponga estructura interna (variables de entorno, queries crudas)
- Permita ejecutar SQL arbitrario
- Devuelva datos sin auth

→ **eliminar** o gatear con `Depends(_require_super_admin)`.

Ejemplo de fix mínimo (proteger todo el router):

```python
# app/api/diagnostico.py
from fastapi import APIRouter, Depends
from app.api.tenants import _require_super_admin

router = APIRouter(
    prefix="/diagnostico",
    tags=["Admin"],
    dependencies=[Depends(_require_super_admin)],  # toda ruta exige admin
)
```

### B. Scripts y archivos huérfanos

Mover a `scripts/legacy/` (gitignored) o eliminar:
- `check_*.py`, `debug_*.py`, `verify_*.py` en raíz del Backend (no son servicio).
- `test_*.py` en raíz que NO son pytest (los reales viven en `tests/`).

### C. Buscar restos de debug

```bash
# desde Backend/
grep -rn "print(" app/ --include="*.py" | grep -v "noqa"
grep -rn "TODO\|FIXME\|XXX\|HACK" app/ --include="*.py"
grep -rn "import pdb\|breakpoint(" app/ --include="*.py"
```

Arreglar o documentar lo que aparezca.

### D. Verificar que no hay secretos en repo

```bash
git log --all --oneline -p -- "*.json" "*.env" "*.pem" | head -200
git ls-files | xargs grep -l "sk_test_\|sk_live_\|AIzaSy" 2>/dev/null
```

Si aparece algo: rotar la credencial inmediatamente.

---

## 4. Performance check ligero

### Slow query log

Activar logs SQL en dev y revisar las queries más lentas:

```python
# En .env (solo dev)
DEBUG=True  # imprime queries
```

Heurística: cualquier endpoint que tarde > 500ms en TestClient con BD local merece atención.

### Indices que pueden faltar

Verificar que estas columnas tienen índice (deberían tras Ciclo 1+2):

```sql
-- desde psql
\d incidente
\d asignacion
\d cotizacion
\d ubicacion_tecnico
```

Buscar `id_tenant` index en todas las tablas tenant-scoped (Alembic 0002 los creó). Si falta alguna por error, agregar:

```python
# alembic revision -m "0008_indices_faltantes"
def upgrade():
    op.create_index("ix_X_id_tenant", "X", ["id_tenant"], if_not_exists=True)
```

---

## 5. Rate limiting básico (opcional pero recomendado)

Para que la defensa no falle si alguien hace F5 frenéticamente:

```bash
pip install slowapi==0.1.9
```

`app/core/rate_limit.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
```

`app/main.py`:

```python
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    from starlette.responses import JSONResponse
    return JSONResponse(status_code=429, content={"detail": "Demasiadas peticiones"})
```

Y en endpoints calientes:

```python
@router.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request, ...):
    ...
```

(En el WebSocket no aplica — bloqueo natural por capacidad de conexiones.)

---

## 6. Pre-flight checklist final

Antes de avanzar a F2 (marco teórico):

- [ ] `python -m scripts.audit_swagger` no reporta faltas críticas.
- [ ] `pytest --cov=app` muestra ≥70% global y ≥90% en `app/core/tenant_*`.
- [ ] No quedan `print()` de debug en `app/`.
- [ ] `git ls-files | grep -E "credentials|firebase|service-account"` solo lista archivos que ya están en `.gitignore`.
- [ ] `app/api/diagnostico.py` (si existe) protegido por super-admin.
- [ ] `alembic upgrade head` desde BD limpia funciona end-to-end.
- [ ] `docker compose up` levanta Redis sin warnings.
- [ ] Endpoints clave responden en <300ms con BD poblada.

---

## 7. Comandos de un solo paso

Script `scripts/preflight.py` para correr todo automáticamente:

```python
"""Pre-flight check pre-defensa."""
import subprocess
import sys


def step(name: str, cmd: list[str]) -> bool:
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd)
    ok = result.returncode == 0
    print(f"-> {'OK' if ok else 'FALLO'}")
    return ok


def main():
    results = {
        "audit_swagger": step("Swagger audit", [sys.executable, "-m", "scripts.audit_swagger"]),
        "pytest_cov":    step("Pytest + cobertura", [
            sys.executable, "-m", "pytest", "tests/",
            "--cov=app", "--cov-report=term-missing",
            "--cov-fail-under=70",
        ]),
        "alembic_check": step("Alembic head check", ["alembic", "current"]),
    }

    print("\n========= RESUMEN =========")
    for name, ok in results.items():
        print(f"  {name:20s} {'OK' if ok else 'FALLO'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Correr en cualquier momento:
```bash
$env:DEBUG="False"
.\venv\Scripts\python.exe -m scripts.preflight
```

---

## Checklist de cierre F1
- [ ] Script de auditoría Swagger creado y arreglados los huecos.
- [ ] `pytest-cov` instalado, `.coveragerc` creado.
- [ ] Cobertura ≥ 70% global verificada.
- [ ] Endpoints de diagnóstico cerrados o protegidos.
- [ ] No quedan `print()`/`pdb`/secretos hardcoded.
- [ ] Rate limit opcional aplicado a `/signup` y `/usuarios/login`.
- [ ] `scripts/preflight.py` corre sin fallar.

## Notas
- **No reorganizar archivos masivamente** a estas alturas. Los diff grandes son riesgo. Solo lo crítico.
- **Si la cobertura no llega a 70%**: priorizar `app/core/tenant_*` (crítico de seguridad) y `app/api/tenants.py`. El resto puede quedar en 60% sin ser desastre — explicarlo en la defensa.
- **Endpoint deprecated**: si hay endpoints viejos que ya no se usan, marcarlos con `deprecated=True` en el decorator. FastAPI los pinta tachados en Swagger.
