"""
Publica eventos de emergencia y aceptacion via pub/sub.
"""
from app.models.incidente import Asignacion, Incidente
from app.models.taller import Taller
from app.services.notify_service import notify_incidente, notify_taller, notify_usuario


def _incidente_payload(incidente: Incidente, taller: Taller | None = None) -> dict:
    base = {
        "id_incidente": incidente.id_incidente,
        "id_categoria": incidente.id_categoria,
        "latitud": incidente.latitud,
        "longitud": incidente.longitud,
        "descripcion_usuario": incidente.descripcion_usuario,
        "resumen_ia": incidente.resumen_ia,
        "created_at": incidente.created_at.isoformat() if incidente.created_at else None,
    }
    if taller is not None:
        base["taller"] = {
            "id_taller": taller.id_taller,
            "nombre": taller.nombre,
            "telefono": taller.telefono,
        }
    return base


async def broadcast_emergencia(incidente: Incidente, candidatos_talleres: list[Taller]) -> None:
    payload = _incidente_payload(incidente)
    for taller in candidatos_talleres:
        await notify_taller(taller.id_taller, "incidente.nuevo", payload)


async def broadcast_incidente_tomado(
    incidente: Incidente, taller_ganador: Taller, otros_candidatos: list[Taller]
) -> None:
    payload = _incidente_payload(incidente, taller_ganador)
    for taller in otros_candidatos:
        await notify_taller(taller.id_taller, "incidente.tomado", payload)


async def notify_cliente_asignado(
    incidente: Incidente, taller: Taller, asignacion: Asignacion
) -> None:
    payload = {
        **_incidente_payload(incidente, taller),
        "id_asignacion": asignacion.id_asignacion,
        "eta_minutos": asignacion.eta_minutos,
    }
    await notify_usuario(incidente.id_usuario, "incidente.asignado", payload)
    await notify_incidente(incidente.id_incidente, "incidente.asignado", payload)
