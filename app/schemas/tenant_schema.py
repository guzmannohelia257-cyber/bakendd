"""
Schemas Pydantic para multi-tenant: Tenant, Plan, Suscripcion, signup.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Plan

class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_plan: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    precio_mensual: float
    moneda: str
    max_talleres: int
    max_tecnicos: int
    max_incidentes_mes: Optional[int] = None
    feature_websockets: bool
    feature_kpis_avanzados: bool
    feature_reportes_ia: bool
    activo: bool


# Tenant

class TenantCreate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    nombre: str = Field(..., min_length=3, max_length=150)
    email_contacto: EmailStr
    telefono: Optional[str] = Field(None, max_length=20)
    id_plan: Optional[int] = Field(None, description="Plan inicial; default = 'free'")


class TenantUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=150)
    email_contacto: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, max_length=20)


class TenantCancelacionPctUpdate(BaseModel):
    """Porcentajes de compensacion por cancelacion (admin del tenant)."""
    pct_cancel_pendiente: int = Field(..., ge=0, le=100)
    pct_cancel_aceptada: int = Field(..., ge=0, le=100)
    pct_cancel_en_camino: int = Field(..., ge=0, le=100)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_tenant: int
    slug: str
    nombre: str
    email_contacto: str
    telefono: Optional[str] = None
    activo: bool
    suspendido: bool
    pct_cancel_pendiente: int = 0
    pct_cancel_aceptada: int = 50
    pct_cancel_en_camino: int = 100
    created_at: datetime
    updated_at: datetime


# Vínculo Taller <-> Tenant

class TallerLinkRequest(BaseModel):
    id_taller: int = Field(..., gt=0)


class TallerLinkResponse(BaseModel):
    id_tenant: int
    id_taller: int
    mensaje: str


# Registro self-service

class SignupRequest(BaseModel):
    """
    Crea de un solo paso: Tenant + Taller asociado.
    El taller queda autenticable con email/password del request.
    """
    # Tenant
    tenant_slug: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    tenant_nombre: str = Field(..., min_length=3, max_length=150)

    # Taller (primer taller del tenant)
    taller_nombre: str = Field(..., min_length=3, max_length=100)
    taller_email: EmailStr
    taller_password: str = Field(..., min_length=8, max_length=128)
    taller_telefono: Optional[str] = Field(None, max_length=20)
    taller_direccion: Optional[str] = Field(None, max_length=255)
    taller_latitud: Optional[float] = Field(None, ge=-90, le=90)
    taller_longitud: Optional[float] = Field(None, ge=-180, le=180)

    plan_codigo: str = Field("free", description="Codigo del plan a contratar")


class SignupResponse(BaseModel):
    tenant: TenantResponse
    id_taller: int
    taller_email: str
    access_token: str
    token_type: str = "bearer"


# Suscripción

class SuscripcionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_suscripcion: int
    id_tenant: int
    id_plan: int
    estado: str
    inicio: datetime
    fin: Optional[datetime] = None
