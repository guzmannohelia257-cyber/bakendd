"""Logica de negocio de cotizaciones."""
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalogos import CategoriaProblema, EstadoAsignacion
from app.models.cotizacion import Cotizacion, EstadoCotizacion
from app.models.incidente import Asignacion, Incidente
from app.models.taller import Taller, TallerServicio
from app.models.usuario import Usuario


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _get_estado(db: Session, nombre: str) -> EstadoCotizacion:
    estado = db.query(EstadoCotizacion).filter(EstadoCotizacion.nombre == nombre).first()
    if not estado:
        raise HTTPException(500, f"Catalogo estado_cotizacion sin '{nombre}'")
    return estado


def solicitar_cotizaciones(
    db: Session,
    incidente: Incidente,
    usuario: Usuario,
    radio_km: float = 20.0,
    max_talleres: int = 3,
    validez_horas: int = 2,
) -> list[Cotizacion]:
    if incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede pedir cotizaciones")

    if incidente.id_categoria is None:
        raise HTTPException(400, "El incidente aun no tiene categoria clasificada")

    categoria = db.query(CategoriaProblema).get(incidente.id_categoria)
    if not categoria:
        raise HTTPException(400, "Categoria invalida")
    if not categoria.requiere_cotizacion:
        raise HTTPException(
            400,
            f"La categoria '{categoria.codigo}' no requiere cotizacion: el servicio se solicita directo",
        )

    candidatos = (
        db.query(Taller, TallerServicio)
        .join(TallerServicio, TallerServicio.id_taller == Taller.id_taller)
        .filter(
            TallerServicio.id_categoria == incidente.id_categoria,
            Taller.activo == True,  # noqa: E712
            Taller.disponible == True,  # noqa: E712
            Taller.latitud.isnot(None),
            Taller.longitud.isnot(None),
        )
        .all()
    )

    con_distancia = []
    for taller, _servicio in candidatos:
        d = _haversine_km(incidente.latitud, incidente.longitud, taller.latitud, taller.longitud)
        if d <= radio_km:
            con_distancia.append((d, taller))
    con_distancia.sort(key=lambda x: x[0])

    seleccionados = [t for _d, t in con_distancia[:max_talleres]]
    if len(seleccionados) < 2:
        raise HTTPException(
            422,
            "No hay suficientes talleres compatibles (encontrados: "
            f"{len(seleccionados)}, minimo: 2). Amplia el radio o intenta de nuevo.",
        )

    ya_solicitado = (
        db.query(Cotizacion)
        .filter(Cotizacion.id_incidente == incidente.id_incidente)
        .first()
    )
    if ya_solicitado:
        raise HTTPException(409, "Ya solicitaste cotizaciones para este incidente")

    pendiente = _get_estado(db, "pendiente")
    validez = datetime.now(timezone.utc) + timedelta(hours=validez_horas)

    creadas = []
    for taller in seleccionados:
        cot = Cotizacion(
            id_tenant=taller.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_estado_cotizacion=pendiente.id_estado_cotizacion,
            validez_hasta=validez,
        )
        db.add(cot)
        creadas.append(cot)

    db.commit()
    for c in creadas:
        db.refresh(c)

    return creadas


def responder_cotizacion(
    db: Session,
    cotizacion: Cotizacion,
    taller: Taller,
    monto_servicio: float,
    monto_repuestos: float,
    garantia_dias: int | None,
    nota: str | None,
) -> Cotizacion:
    if cotizacion.id_taller != taller.id_taller:
        raise HTTPException(403, "Esta cotizacion no te pertenece")
    if cotizacion.estado.nombre not in ("pendiente",):
        raise HTTPException(
            409, f"No puedes responder una cotizacion en estado '{cotizacion.estado.nombre}'"
        )
    if cotizacion.validez_hasta and cotizacion.validez_hasta < datetime.now(timezone.utc):
        _marcar_expirada(db, cotizacion)
        raise HTTPException(410, "Esta cotizacion ya expiro")

    cotizacion.monto_servicio = monto_servicio
    cotizacion.monto_repuestos = monto_repuestos
    cotizacion.garantia_dias = garantia_dias
    cotizacion.nota = nota
    cotizacion.id_estado_cotizacion = _get_estado(db, "enviada").id_estado_cotizacion
    db.commit()
    db.refresh(cotizacion)
    return cotizacion


def aceptar_cotizacion(
    db: Session,
    cotizacion: Cotizacion,
    usuario: Usuario,
) -> Asignacion:
    incidente = db.query(Incidente).get(cotizacion.id_incidente)
    if incidente.id_usuario != usuario.id_usuario:
        raise HTTPException(403, "Solo el dueno del incidente puede aceptar cotizaciones")

    if cotizacion.estado.nombre != "enviada":
        raise HTTPException(
            409, f"No puedes aceptar una cotizacion en estado '{cotizacion.estado.nombre}'"
        )

    cotizacion.id_estado_cotizacion = _get_estado(db, "aceptada").id_estado_cotizacion

    otras = (
        db.query(Cotizacion)
        .filter(
            Cotizacion.id_incidente == cotizacion.id_incidente,
            Cotizacion.id_cotizacion != cotizacion.id_cotizacion,
        )
        .all()
    )
    estado_rechazada = _get_estado(db, "rechazada")
    for o in otras:
        if o.estado.nombre in ("pendiente", "enviada"):
            o.id_estado_cotizacion = estado_rechazada.id_estado_cotizacion

    estado_asig_aceptada = (
        db.query(EstadoAsignacion).filter(EstadoAsignacion.nombre == "aceptada").first()
    )
    if not estado_asig_aceptada:
        raise HTTPException(500, "Catalogo estado_asignacion sin 'aceptada'")

    asig = Asignacion(
        id_tenant=cotizacion.id_tenant,
        id_incidente=cotizacion.id_incidente,
        id_taller=cotizacion.id_taller,
        id_estado_asignacion=estado_asig_aceptada.id_estado_asignacion,
        costo_estimado=cotizacion.monto_total,
        nota_taller=cotizacion.nota,
    )
    db.add(asig)
    db.commit()
    db.refresh(asig)
    return asig


def _marcar_expirada(db: Session, cot: Cotizacion) -> None:
    cot.id_estado_cotizacion = _get_estado(db, "expirada").id_estado_cotizacion
    db.commit()
