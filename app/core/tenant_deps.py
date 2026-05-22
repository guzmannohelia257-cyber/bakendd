"""
Dependencias FastAPI para enforcement de tenant.

Uso:

    from app.core.tenant_deps import require_tenant

    @router.get("/talleres/me/incidentes")
    def listar(tenant_id: int = Depends(require_tenant), db: Session = Depends(get_db)):
        ...

`require_tenant` falla con 400 si el request no trae tenant (o si
TENANT_ENFORCEMENT=True y aun asi falta). Para endpoints publicos (cliente
final) no se usa esta dependencia.
"""
from fastapi import Depends, HTTPException, status

from app.core.config import get_settings
from app.core.tenant_context import current_tenant


def get_optional_tenant() -> int | None:
    """Devuelve el tenant actual o None. No falla."""
    return current_tenant.get()


def require_tenant(tid: int | None = Depends(get_optional_tenant)) -> int:
    """Endpoints exclusivos de tenant: falla si no hay contexto."""
    if tid is None:
        settings = get_settings()
        # En produccion con enforcement activo, mensaje claro.
        detail = (
            "Este endpoint requiere autenticacion de un tenant (taller / organizacion). "
            "Token sin claim id_tenant."
            if settings.TENANT_ENFORCEMENT
            else "Falta contexto de tenant. El token debe incluir id_tenant."
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return tid
