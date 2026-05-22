"""
Talleres + tenant 1:1 + suscripcion al plan correspondiente + taller_servicio.

Cada taller pertenece a un tenant propio (slug derivado). Esto satisface el
constraint NOT NULL en taller.id_tenant.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.taller import Taller, TallerServicio
from app.models.tenant import Suscripcion, Tenant
from SETT.config import TALLERES
from SETT.utils import Ctx, logger


def run(db: Session, ctx: Ctx) -> None:
    for t in TALLERES:
        tenant = Tenant(
            slug=t["slug"],
            nombre=t["tenant_nombre"],
            email_contacto=t["email"],
            telefono=t["telefono"],
            activo=True,
            suspendido=False,
        )
        db.add(tenant)
        db.flush()

        plan = ctx.plan[t["plan"]]
        suscripcion = Suscripcion(
            id_tenant=tenant.id_tenant,
            id_plan=plan.id_plan,
            estado="activa",
            inicio=datetime.now(timezone.utc),
        )
        db.add(suscripcion)

        taller = Taller(
            id_tenant=tenant.id_tenant,
            nombre=t["nombre"],
            email=t["email"],
            password_hash=hash_password(t["password"]),
            telefono=t["telefono"],
            direccion=t["direccion"],
            latitud=t["latitud"],
            longitud=t["longitud"],
            capacidad_max=t["capacidad_max"],
            activo=True,
            verificado=True,
            disponible=True,
            tarifa_traslado=5.00,
        )
        db.add(taller)
        db.flush()

        for cat_nombre in t["categorias"]:
            cat = ctx.categoria.get(cat_nombre)
            if not cat:
                logger.info(f"[entidades]   (skip categoria '{cat_nombre}')")
                continue
            db.add(TallerServicio(
                id_taller=taller.id_taller,
                id_categoria=cat.id_categoria,
                servicio_movil=True,
                tarifa_base=80.00,
            ))

        ctx.talleres.append(taller)

    db.commit()
    for t in ctx.talleres:
        db.refresh(t)

    logger.info(f"[entidades] {len(ctx.talleres)} talleres + tenants + servicios")
