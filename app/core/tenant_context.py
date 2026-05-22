"""
Contexto de tenant por request.

Un ContextVar se propaga automaticamente entre llamadas async dentro del
mismo request, asi cualquier consulta a la BD puede leer el id_tenant actual
sin pasarlo explicitamente por cada funcion.

Uso tipico desde un endpoint:

    from app.core.tenant_context import current_tenant

    @router.get("/...")
    def listar(...):
        tenant_id = current_tenant.get()  # None si el request no tiene tenant

El middleware (app.core.tenant_middleware) lo setea automaticamente desde el JWT.
"""
from contextvars import ContextVar
from typing import Optional


# None = request publico / sin tenant (cliente final reportando incidente, etc.)
current_tenant: ContextVar[Optional[int]] = ContextVar("current_tenant", default=None)


def set_tenant(tenant_id: Optional[int]) -> object:
    """Setea el tenant en contexto y devuelve un token para resetearlo."""
    return current_tenant.set(tenant_id)


def reset_tenant(token: object) -> None:
    current_tenant.reset(token)  # type: ignore[arg-type]
