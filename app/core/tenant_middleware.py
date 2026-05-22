"""
Middleware que extrae el id_tenant del JWT y lo guarda en el ContextVar
`current_tenant` para que las consultas SQLAlchemy puedan filtrar.

Logica:
  - Si el header Authorization trae un JWT valido y contiene `id_tenant`,
    lo setea en el contexto.
  - Si no hay token o no trae tenant, deja contexto en None (request publico).
  - NUNCA bloquea un request por ausencia de tenant (el enforcement se hace
    en las dependencias de cada endpoint, no aqui).

Activable via `TENANT_ENFORCEMENT=True`: los endpoints protegidos exigen tenant.
"""
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import verify_token
from app.core.tenant_context import current_tenant


def _extract_tenant_from_request(request: Request) -> Optional[int]:
    auth: Optional[str] = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        # Permitir override por header explicito (util en tests / cross-service)
        header_tid = request.headers.get("x-tenant-id")
        if header_tid and header_tid.isdigit():
            return int(header_tid)
        return None

    token = auth.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        return None

    tid = payload.get("id_tenant")
    if isinstance(tid, int):
        return tid
    if isinstance(tid, str) and tid.isdigit():
        return int(tid)
    return None


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = _extract_tenant_from_request(request)
        token = current_tenant.set(tenant_id)
        try:
            response = await call_next(request)
        finally:
            current_tenant.reset(token)
        return response
