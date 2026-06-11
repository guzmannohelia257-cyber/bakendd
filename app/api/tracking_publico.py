"""
Seguimiento publico en vivo (link compartible a terceros).

Dos endpoints:
  POST /asignaciones/{id}/compartir  -> el taller (autenticado) genera o recupera
                                        el token del link publico de una de SUS
                                        asignaciones.
  GET  /public/track/{token}         -> endpoint PUBLICO (sin auth) que devuelve
                                        ubicacion del tecnico + cliente + ETA,
                                        solo mientras la asignacion siga abierta.

El token es un UUID4 opaco ligado a una sola asignacion. El endpoint publico
omite el filtro de tenant con current_tenant.set(0) dentro de try/finally, igual
que el resto de endpoints publicos (ver app/api/tecnicos.py::talleres_publicos),
y expone unicamente datos minimos (sin telefono, email, costos ni SLA).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_taller, get_current_user
from app.core.tenant_context import current_tenant
from app.db.session import get_db
from app.models.incidente import Asignacion, Incidente
from app.models.taller import Taller
from app.models.ubicacion import UbicacionTecnico
from app.models.usuario import Usuario
from app.schemas.tracking_publico_schema import (
    ClientePublico,
    CompartirResponse,
    EtaPublico,
    TecnicoPublico,
    TrackPublicoResponse,
)
from app.services import tracking_service

router = APIRouter(tags=["Seguimiento publico"])

# Estados en los que la asignacion ya esta cerrada: el link deja de servir.
_ESTADOS_CERRADOS = {"completada", "rechazada"}


@router.post(
    "/asignaciones/{id_asignacion}/compartir",
    response_model=CompartirResponse,
    summary="Genera (o recupera) el token del link publico de seguimiento",
)
def compartir_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db),
    taller: Taller = Depends(get_current_taller),
):
    """
    El taller comparte el seguimiento en vivo de una de sus asignaciones. Si ya
    tiene token, lo reutiliza (el link es estable). El filtro de tenant aplica
    automaticamente por el JWT del taller; ademas validamos que la asignacion sea
    suya.
    """
    asig = (
        db.query(Asignacion)
        .filter(Asignacion.id_asignacion == id_asignacion)
        .first()
    )
    if not asig:
        raise HTTPException(404, "Asignacion no existe")
    if asig.id_taller != taller.id_taller:
        raise HTTPException(403, "La asignacion no pertenece a tu taller")

    if not asig.share_token:
        asig.share_token = uuid.uuid4().hex
        db.commit()
        db.refresh(asig)

    return CompartirResponse(token=asig.share_token)


@router.post(
    "/asignaciones/{id_asignacion}/compartir-cliente",
    response_model=CompartirResponse,
    summary="El cliente (dueno del incidente) genera/recupera el token del link publico",
)
def compartir_asignacion_cliente(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    El cliente comparte el seguimiento en vivo de SU propia emergencia con un
    tercero. Validamos que la asignacion pertenezca a un incidente del usuario.
    El cliente no tiene tenant en contexto (current_tenant=None), asi que el
    filtro global no aplica y puede leer su asignacion sin importar el tenant.
    """
    asig = (
        db.query(Asignacion)
        .filter(Asignacion.id_asignacion == id_asignacion)
        .first()
    )
    if not asig:
        raise HTTPException(404, "Asignacion no existe")

    incidente = db.get(Incidente, asig.id_incidente)
    if not incidente or incidente.id_usuario != current_user.id_usuario:
        raise HTTPException(403, "Esta asignacion no te pertenece")

    if not asig.share_token:
        asig.share_token = uuid.uuid4().hex
        db.commit()
        db.refresh(asig)

    return CompartirResponse(token=asig.share_token)


@router.get(
    "/public/track/{token}",
    response_model=TrackPublicoResponse,
    summary="Seguimiento publico en vivo (sin auth) mediante token compartido",
)
async def track_publico(token: str, db: Session = Depends(get_db)):
    """
    Endpoint PUBLICO (sin auth). Devuelve la ubicacion del tecnico y del cliente
    y el ETA mientras la asignacion siga abierta. Cuando el servicio finaliza
    (completada / rechazada / cancelada) responde 410 y el link deja de servir.
    """
    # Omitimos el filtro de tenant: el request no tiene contexto. El token es
    # unico y apunta a una sola asignacion, asi que no hay fuga entre tenants.
    tok = current_tenant.set(0)
    try:
        asig = (
            db.query(Asignacion)
            .filter(Asignacion.share_token == token)
            .first()
        )
        if not asig:
            raise HTTPException(404, "Enlace no valido")

        estado_nombre = asig.estado.nombre
        cerrada = estado_nombre in _ESTADOS_CERRADOS or asig.cancelada_at is not None
        if cerrada:
            raise HTTPException(410, "El seguimiento de este servicio ya finalizo")

        incidente = asig.incidente
        cli_lat = incidente.latitud
        cli_lng = incidente.longitud
        cli_nombre = incidente.usuario.nombre if incidente.usuario else None
        tec_nombre = asig.usuario_tecnico.nombre if asig.usuario_tecnico else None

        ultimo = (
            db.query(UbicacionTecnico)
            .filter(UbicacionTecnico.id_asignacion == asig.id_asignacion)
            .order_by(UbicacionTecnico.created_at.desc())
            .first()
        )
        tec_lat = ultimo.latitud if ultimo else None
        tec_lng = ultimo.longitud if ultimo else None
        tec_upd = ultimo.created_at if ultimo else None
    finally:
        current_tenant.reset(tok)

    eta = None
    if tec_lat is not None and tec_lng is not None:
        dist_km, eta_seg = await tracking_service.calcular_eta(
            tec_lat, tec_lng, cli_lat, cli_lng
        )
        eta = EtaPublico(distancia_km=round(dist_km, 2), eta_minutos=round(eta_seg / 60))

    return TrackPublicoResponse(
        estado=estado_nombre,
        tecnico=TecnicoPublico(
            nombre=tec_nombre,
            latitud=tec_lat,
            longitud=tec_lng,
            actualizado_at=tec_upd,
        ),
        cliente=ClientePublico(nombre=cli_nombre, latitud=cli_lat, longitud=cli_lng),
        eta=eta,
    )
