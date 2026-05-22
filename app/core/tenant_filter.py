"""
Filtro global SQLAlchemy por tenant.

Cuando una query toca un modelo que declara columna `id_tenant`, se le anade
automaticamente `WHERE id_tenant = <current_tenant>` (o `IS NULL` durante el
periodo de migracion para no romper datos legacy sin tenant).

Comportamiento por estado:
  - current_tenant.get() is None  -> no se filtra (request publico).
  - current_tenant.get() == 0     -> super-admin: ve TODO. (escape hatch)
  - current_tenant.get() == N     -> filtra por N. Si include_legacy=True,
                                     incluye tambien filas con id_tenant IS NULL
                                     (util mientras backfilleas).

Aplicar una sola vez al arrancar la app:

    from app.core.tenant_filter import install_tenant_filter
    install_tenant_filter(include_legacy=True)
"""
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.core.tenant_context import current_tenant


_INSTALLED = False


def install_tenant_filter(include_legacy: bool = True) -> None:
    """
    Registra un listener `do_orm_execute` que inyecta WHERE id_tenant=...
    a cada SELECT/UPDATE/DELETE que use modelos con columna id_tenant.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    @event.listens_for(Session, "do_orm_execute")
    def _add_tenant_filter(execute_state: Any) -> None:  # noqa: ANN001
        if not (
            execute_state.is_select
            or execute_state.is_update
            or execute_state.is_delete
        ):
            return

        tid = current_tenant.get()
        # None = sin scope (request publico). 0 = super-admin (sin filtro).
        if tid is None or tid == 0:
            return

        # Importacion diferida para evitar ciclos
        from app.db.session import Base

        for mapper in Base.registry.mappers:
            cls = mapper.class_
            if "id_tenant" not in mapper.columns:
                continue

            col = mapper.columns["id_tenant"]
            if include_legacy:
                criterion = (col == tid) | (col.is_(None))
            else:
                criterion = col == tid

            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(cls, criterion, include_aliases=True)
            )
