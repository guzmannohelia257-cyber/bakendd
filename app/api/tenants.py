"""
Endpoints multi-tenant:

  POST   /signup                        - self-service: crea tenant + taller (publico)
  GET    /tenants                       - list (super-admin)
  POST   /tenants                       - create (super-admin)
  GET    /tenants/me                    - el tenant del taller autenticado
  GET    /tenants/{id}                  - detalle (super-admin o miembro)
  PATCH  /tenants/{id}                  - update (super-admin o owner)
  POST   /tenants/{id}/talleres/link    - vincular taller existente al tenant
  GET    /plans                         - list planes disponibles (publico)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_current_taller,
    get_current_user,
    hash_password,
)
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.taller import Taller
from app.models.tenant import Plan, Suscripcion, Tenant
from app.schemas.tenant_schema import (
    PlanResponse,
    SignupRequest,
    SignupResponse,
    SuscripcionResponse,
    TallerLinkRequest,
    TallerLinkResponse,
    TenantCreate,
    TenantCancelacionPctUpdate,
    TenantResponse,
    TenantUpdate,
)
from app.core.rate_limit import limiter


router = APIRouter(tags=["Tenants"])


# Helpers

def _require_super_admin(current_user=Depends(get_current_user)):
    """Solo usuarios con rol=4 (admin global)."""
    if current_user.id_rol != 4:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de super-administrador",
        )
    return current_user


def _get_tenant_or_404(db: Session, id_tenant: int) -> Tenant:
    # Se omite el filtro global de tenant para que el super-admin pueda ver cualquier tenant.
    tok = current_tenant.set(0)
    try:
        tenant = db.query(Tenant).filter(Tenant.id_tenant == id_tenant).first()
    finally:
        current_tenant.reset(tok)
    if tenant is None:
        raise HTTPException(status_code=404, detail=f"Tenant {id_tenant} no existe")
    return tenant


# Planes (público)

@router.get("/plans", response_model=List[PlanResponse], summary="Listar planes disponibles")
def listar_planes(db: Session = Depends(get_db)):
    return db.query(Plan).filter(Plan.activo == True).order_by(Plan.precio_mensual).all()  # noqa: E712


# Signup self-service (público)

@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboarding self-service: crea tenant + primer taller",
)
@limiter.limit("5/minute")
def signup(request: Request, body: SignupRequest, db: Session = Depends(get_db)):
    # 1) Validar el plan solicitado.
    plan = db.query(Plan).filter(Plan.codigo == body.plan_codigo, Plan.activo == True).first()  # noqa: E712
    if plan is None:
        raise HTTPException(status_code=400, detail=f"Plan '{body.plan_codigo}' no existe o esta inactivo")

    # 2) Verificar la unicidad del slug y del email.
    if db.query(Tenant).filter(Tenant.slug == body.tenant_slug).first():
        raise HTTPException(status_code=409, detail="Ese slug de tenant ya esta tomado")
    if db.query(Taller).filter(Taller.email == body.taller_email).first():
        raise HTTPException(status_code=409, detail="Ya existe un taller con ese email")

    # 3) Crear el tenant.
    tenant = Tenant(
        slug=body.tenant_slug,
        nombre=body.tenant_nombre,
        email_contacto=body.taller_email,
        telefono=body.taller_telefono,
    )
    db.add(tenant)
    db.flush()

    # 4) Crear la suscripción al plan.
    db.add(Suscripcion(id_tenant=tenant.id_tenant, id_plan=plan.id_plan, estado="trial"))

    # 5) Crear el taller asociado al tenant.
    taller = Taller(
        id_tenant=tenant.id_tenant,
        nombre=body.taller_nombre,
        email=body.taller_email,
        password_hash=hash_password(body.taller_password),
        telefono=body.taller_telefono,
        direccion=body.taller_direccion,
        latitud=body.taller_latitud,
        longitud=body.taller_longitud,
    )
    db.add(taller)
    db.commit()
    db.refresh(tenant)
    db.refresh(taller)

    # 6) Emitir el token incluyendo el id_tenant.
    access_token = create_access_token(
        subject_id=taller.id_taller,
        tipo="taller",
        extra_claims={"id_tenant": tenant.id_tenant},
    )

    return SignupResponse(
        tenant=TenantResponse.model_validate(tenant),
        id_taller=taller.id_taller,
        taller_email=taller.email,
        access_token=access_token,
    )


# Tenant - CRUD (admin)

@router.get("/tenants", response_model=List[TenantResponse], summary="Listar todos los tenants (super-admin)")
def listar_tenants(
    db: Session = Depends(get_db),
    _admin=Depends(_require_super_admin),
):
    tok = current_tenant.set(0)
    try:
        return db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    finally:
        current_tenant.reset(tok)


@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tenant (super-admin)",
)
def crear_tenant(
    body: TenantCreate,
    db: Session = Depends(get_db),
    _admin=Depends(_require_super_admin),
):
    if db.query(Tenant).filter(Tenant.slug == body.slug).first():
        raise HTTPException(status_code=409, detail="Slug ya tomado")

    tenant = Tenant(
        slug=body.slug,
        nombre=body.nombre,
        email_contacto=body.email_contacto,
        telefono=body.telefono,
    )
    db.add(tenant)
    db.flush()

    id_plan = body.id_plan
    if id_plan is None:
        plan_free = db.query(Plan).filter(Plan.codigo == "free").first()
        id_plan = plan_free.id_plan if plan_free else None

    if id_plan is not None:
        db.add(Suscripcion(id_tenant=tenant.id_tenant, id_plan=id_plan, estado="activa"))

    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/tenants/me", response_model=TenantResponse, summary="Tenant del taller autenticado")
def mi_tenant(
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    if current_taller.id_tenant is None:
        raise HTTPException(status_code=404, detail="Tu taller no esta vinculado a ningun tenant")
    return _get_tenant_or_404(db, current_taller.id_tenant)


@router.get("/tenants/{id_tenant}", response_model=TenantResponse, summary="Detalle de tenant")
def detalle_tenant(
    id_tenant: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    # Solo super-admin o miembro del tenant. Aquí simplificamos: solo si es su propio tenant.
    if current_taller.id_tenant != id_tenant:
        raise HTTPException(status_code=403, detail="Solo puedes ver tu propio tenant")
    return _get_tenant_or_404(db, id_tenant)


@router.patch("/tenants/{id_tenant}", response_model=TenantResponse, summary="Editar tenant")
def actualizar_tenant(
    id_tenant: int,
    body: TenantUpdate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    if current_taller.id_tenant != id_tenant:
        raise HTTPException(status_code=403, detail="Solo puedes editar tu propio tenant")
    tenant = _get_tenant_or_404(db, id_tenant)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get(
    "/tenants/me",
    response_model=TenantResponse,
    summary="Detalle de mi tenant (incluye porcentajes de cancelacion)",
)
def obtener_mi_tenant(
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    return _get_tenant_or_404(db, current_taller.id_tenant)


@router.patch(
    "/tenants/me/cancelacion-pct",
    response_model=TenantResponse,
    summary="Configurar porcentajes de compensacion por cancelacion",
    description=(
        "Admin del tenant ajusta los porcentajes que se cobran sobre "
        "taller.tarifa_traslado segun el estado de la asignacion al cancelar. "
        "Default: pendiente=0%, aceptada=50%, en_camino=100%."
    ),
)
def actualizar_cancelacion_pct(
    body: TenantCancelacionPctUpdate,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    tenant = _get_tenant_or_404(db, current_taller.id_tenant)
    tenant.pct_cancel_pendiente = body.pct_cancel_pendiente
    tenant.pct_cancel_aceptada = body.pct_cancel_aceptada
    tenant.pct_cancel_en_camino = body.pct_cancel_en_camino
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post(
    "/tenants/{id_tenant}/talleres/link",
    response_model=TallerLinkResponse,
    summary="Vincular un taller existente a este tenant (super-admin)",
)
def vincular_taller(
    id_tenant: int,
    body: TallerLinkRequest,
    db: Session = Depends(get_db),
    _admin=Depends(_require_super_admin),
):
    tenant = _get_tenant_or_404(db, id_tenant)

    # Se omite el filtro para localizar el taller aunque pertenezca a otro tenant.
    tok = current_tenant.set(0)
    try:
        taller = db.query(Taller).filter(Taller.id_taller == body.id_taller).first()
    finally:
        current_tenant.reset(tok)
    if taller is None:
        raise HTTPException(status_code=404, detail=f"Taller {body.id_taller} no existe")

    if taller.id_tenant is not None and taller.id_tenant != id_tenant:
        raise HTTPException(
            status_code=409,
            detail=f"El taller ya pertenece al tenant {taller.id_tenant}",
        )

    taller.id_tenant = tenant.id_tenant
    db.commit()
    return TallerLinkResponse(
        id_tenant=tenant.id_tenant,
        id_taller=taller.id_taller,
        mensaje="Taller vinculado correctamente",
    )


# Suscripción

@router.get(
    "/tenants/{id_tenant}/suscripcion",
    response_model=SuscripcionResponse,
    summary="Suscripcion activa del tenant",
)
def suscripcion_actual(
    id_tenant: int,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    if current_taller.id_tenant != id_tenant:
        raise HTTPException(status_code=403, detail="Solo puedes ver tu propia suscripcion")
    tok = current_tenant.set(0)
    try:
        sub = (
            db.query(Suscripcion)
            .filter(Suscripcion.id_tenant == id_tenant)
            .order_by(Suscripcion.created_at.desc())
            .first()
        )
    finally:
        current_tenant.reset(tok)
    if sub is None:
        raise HTTPException(status_code=404, detail="No hay suscripcion para este tenant")
    return sub
