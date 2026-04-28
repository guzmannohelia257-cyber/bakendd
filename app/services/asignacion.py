"""
Motor de Asignación Inteligente.

Después de que la IA clasifica un incidente, este servicio:
1. Busca talleres cercanos (radio configurable)
2. Filtra por especialidad (categoría del incidente)
3. Calcula score para cada candidato (distancia + capacidad + disponibilidad)
4. Guarda top 3-5 en candidato_asignacion
5. Marca el mejor como seleccionado=true
6. Crea una asignación automática con el taller seleccionado
"""
import math
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.incidente import Incidente, CandidatoAsignacion, Asignacion, Evaluacion
from app.models.taller import Taller, TallerServicio
from app.models.usuario_taller import UsuarioTaller
from app.models.catalogos import EstadoAsignacion

logger = logging.getLogger("asignacion_service")

# Configuración
RADIO_BUSQUEDA_KM = 30  # Buscar talleres dentro de 30 km
MIN_CANDIDATOS = 3      # Mínimo de candidatos a guardar
MAX_CANDIDATOS = 10     # Máximo de candidatos a guardar (más opciones para el cliente)


def _calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en km entre dos coordenadas (lat, lon) usando la fórmula de Haversine.
    
    Args:
        lat1, lon1: Coordenadas del incidente
        lat2, lon2: Coordenadas del taller
    
    Returns:
        Distancia en km
    """
    R = 6371  # Radio de la Tierra en km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def _ids_estados_activos(db: Session) -> list:
    """
    Obtiene dinámicamente los IDs de los estados ACTIVOS buscando por nombre.
    Esto evita hardcodear [1,2,3] que pueden cambiar según el seed.
    
    Estados activos: pendiente, aceptada, en_camino
    """
    from app.models.catalogos import EstadoAsignacion
    
    estados = db.query(EstadoAsignacion).filter(
        EstadoAsignacion.nombre.in_(["pendiente", "aceptada", "en_camino"])
    ).all()
    
    return [e.id_estado_asignacion for e in estados]


def _contar_asignaciones_activas(db: Session, id_taller: int) -> int:
    """
    Cuenta cuántos incidentes activos tiene asignados un taller.
    (Estados pendiente, aceptada, en_camino)
    """
    estados_activos = _ids_estados_activos(db)
    
    count = db.query(Asignacion).filter(
        Asignacion.id_taller == id_taller,
        Asignacion.id_estado_asignacion.in_(estados_activos)
    ).count()
    
    return count


def _contar_asignaciones_activas_usuario_tecnico(db: Session, id_usuario: int) -> int:
    """
    Cuenta cuántos incidentes ACTIVOS tiene asignados un usuario técnico específico.
    (Estados pendiente, aceptada, en_camino)
    
    Un técnico NO puede tener más de 1 asignación activa simultáneamente.
    
    Returns:
        Número de asignaciones activas del usuario técnico
    """
    estados_activos = _ids_estados_activos(db)
    
    count = db.query(Asignacion).filter(
        Asignacion.id_usuario == id_usuario,
        Asignacion.id_estado_asignacion.in_(estados_activos)
    ).count()
    
    return count


def _obtener_rating_promedio_taller(db: Session, id_taller: int) -> float | None:
    """Calcula el promedio de estrellas del taller desde sus evaluaciones."""
    rating = db.query(func.avg(Evaluacion.estrellas)).filter(
        Evaluacion.id_taller == id_taller
    ).scalar()

    return round(float(rating), 2) if rating is not None else None


def validar_usuario_tecnico_disponible(db: Session, id_usuario: int) -> bool:
    """
    Valida que un usuario técnico NO tiene asignaciones ACTIVAS.
    
    Uso:
    - Antes de asignar una emergencia a un técnico
    - Levanta excepción si el técnico ya está ocupado
    
    Args:
        db: Sesión de BD
        id_usuario: ID del usuario técnico a validar
    
    Returns:
        True si el técnico está disponible (sin asignaciones activas)
    
    Raises:
        ValueError: Si el técnico ya tiene una asignación activa
    """
    asignaciones_activas = _contar_asignaciones_activas_usuario_tecnico(db, id_usuario)
    
    if asignaciones_activas > 0:
        raise ValueError(
            f"El técnico {id_usuario} ya tiene {asignaciones_activas} "
            f"asignación(es) activa(s). No puede recibir otra hasta completar la actual."
        )
    
    return True


def buscar_y_asignar(db: Session, incidente: Incidente) -> dict:
    """
    Ejecuta el motor de asignación inteligente.
    
    Flujo:
    1. Valida que el incidente tenga categoría asignada por IA
    2. Busca talleres cercanos que atiendan esa categoría
    3. Calcula score para cada candidato
    4. Guarda top 3-5 en candidato_asignacion
    5. Marca el mejor como seleccionado
    6. Crea asignación automática con el taller seleccionado
    
    Args:
        db: Sesión de BD
        incidente: Incidente ya clasificado por IA
    
    Returns:
        dict con resumen de la asignación
    """
    
    # 1️⃣ Validar precondiciones
    if not incidente.id_categoria:
        logger.warning(f"[ASIGN] Incidente {incidente.id_incidente} sin categoría. Saltando.")
        return {"error": "Incidente sin categoría asignada por IA"}
    
    if not incidente.latitud or not incidente.longitud:
        logger.warning(f"[ASIGN] Incidente {incidente.id_incidente} sin ubicación. Saltando.")
        return {"error": "Incidente sin coordenadas GPS"}
    
    # 2️⃣ Buscar talleres cercanos que atiendan esa categoría
    candidatos_potenciales: List[tuple[Taller, float]] = []
    
    # Obtener TODOS los talleres activos y verificados
    talleres = db.query(Taller).filter(
        Taller.activo == True,
        Taller.verificado == True,
        Taller.disponible == True,
        Taller.latitud.isnot(None),
        Taller.longitud.isnot(None)
    ).all()
    
    for taller in talleres:
        # Verificar que el taller atienda esta categoría
        servicio = db.query(TallerServicio).filter(
            TallerServicio.id_taller == taller.id_taller,
            TallerServicio.id_categoria == incidente.id_categoria
        ).first()
        
        if not servicio:
            continue  # Este taller no atiende esta categoría
        
        # Calcular distancia
        distancia = _calcular_distancia_haversine(
            incidente.latitud, incidente.longitud,
            taller.latitud, taller.longitud
        )
        
        # Filtrar por radio de búsqueda
        if distancia > RADIO_BUSQUEDA_KM:
            continue
        
        candidatos_potenciales.append((taller, distancia))
    
    if not candidatos_potenciales:
        logger.warning(
            f"[ASIGN] Incidente {incidente.id_incidente}: "
            f"No hay talleres cercanos que atiendan {incidente.id_categoria}"
        )
        return {"error": "No hay talleres disponibles en el área"}
    
    logger.info(
        f"[ASIGN] Incidente {incidente.id_incidente}: "
        f"Encontrados {len(candidatos_potenciales)} talleres potenciales"
    )
    
    # 3️⃣ Calcular score para cada candidato
    candidatos_con_score = []
    
    for taller, distancia in candidatos_potenciales:
        # Contar asignaciones activas
        asignaciones_activas = _contar_asignaciones_activas(db, taller.id_taller)
        
        # Calcular capacidad disponible (0..1, donde 1 es máxima disponibilidad)
        capacidad_disponible = 1.0 - (asignaciones_activas / max(taller.capacidad_max, 1))
        capacidad_disponible = max(0, min(1, capacidad_disponible))  # Clamp [0, 1]
        
        # Contar técnicos disponibles asociados a este taller específico
        tecnicos_disponibles = db.query(func.count(UsuarioTaller.id_usuario)).filter(
            UsuarioTaller.id_taller == taller.id_taller,
            UsuarioTaller.activo == True,
            UsuarioTaller.disponible == True,
        ).scalar()
        
        # Score normalizado (0..100)
        # 40% distancia (más cercano = mejor), 30% capacidad, 30% disponibilidad
        score_distancia = max(0, 1.0 - (distancia / RADIO_BUSQUEDA_KM))  # [0..1]
        score_capacidad = capacidad_disponible  # [0..1]
        score_disponibilidad = min(1.0, tecnicos_disponibles / 2)  # [0..1]
        
        score_total = (
            score_distancia * 0.40 +
            score_capacidad * 0.30 +
            score_disponibilidad * 0.30
        ) * 100

        rating_promedio = _obtener_rating_promedio_taller(db, taller.id_taller)
        
        candidatos_con_score.append({
            "taller": taller,
            "distancia_km": round(distancia, 2),
            "score_total": round(score_total, 2),
            "rating_promedio": rating_promedio,
            "asignaciones_activas": asignaciones_activas,
            "tecnicos_disponibles": tecnicos_disponibles,
        })
    
    # 4️⃣ Ordenar por score descendente
    candidatos_con_score.sort(key=lambda x: x["score_total"], reverse=True)
    
    # Limitar a MAX_CANDIDATOS
    top_candidatos = candidatos_con_score[:MAX_CANDIDATOS]
    
    logger.info(
        f"[ASIGN] Incidente {incidente.id_incidente}: "
        f"Top {len(top_candidatos)} candidatos calculados"
    )
    
    # 5️⃣ Guardar en BD
    candidatos_guardados = []
    mejor_candidato = None
    
    for i, cand in enumerate(top_candidatos):
        es_seleccionado = (i == 0)  # El primero es el seleccionado
        
        candidato_db = CandidatoAsignacion(
            id_incidente=incidente.id_incidente,
            id_taller=cand["taller"].id_taller,
            distancia_km=cand["distancia_km"],
            score_total=cand["score_total"],
            seleccionado=es_seleccionado,
        )
        
        db.add(candidato_db)
        candidatos_guardados.append(candidato_db)
        
        if es_seleccionado:
            mejor_candidato = cand
    
    db.commit()
    
    # Refrescar los candidatos para obtener IDs
    for cand in candidatos_guardados:
        db.refresh(cand)
    
    logger.info(
        f"[ASIGN] Incidente {incidente.id_incidente}: "
        f"Guardados {len(candidatos_guardados)} candidatos"
    )
    
    # 6️⃣ Crear asignación automática con el mejor candidato
    if mejor_candidato:
        # Obtener estado "pendiente" de asignación (ID=1 típicamente)
        estado_pendiente = db.query(EstadoAsignacion).filter_by(nombre="pendiente").first()
        if not estado_pendiente:
            estado_pendiente_id = 1
        else:
            estado_pendiente_id = estado_pendiente.id_estado_asignacion
        
        asignacion = Asignacion(
            id_incidente=incidente.id_incidente,
            id_taller=mejor_candidato["taller"].id_taller,
            id_estado_asignacion=estado_pendiente_id,
            eta_minutos=None,  # Se calcula después
        )

        db.add(asignacion)
        db.flush()  # obtener id_asignacion antes del historial

        # A.1: registrar creación de la asignación en el historial
        from app.services.trazabilidad import registrar_cambio_estado_asignacion
        registrar_cambio_estado_asignacion(
            db, asignacion, None, estado_pendiente_id,
            observacion=(
                f"Motor de asignación — taller {mejor_candidato['taller'].nombre} "
                f"(score: {mejor_candidato['score_total']}, "
                f"distancia: {mejor_candidato['distancia_km']} km)"
            ),
        )

        db.commit()
        db.refresh(asignacion)

        logger.info(
            f"[ASIGN] Incidente {incidente.id_incidente}: "
            f"Asignado automáticamente al taller {mejor_candidato['taller'].nombre} "
            f"(score: {mejor_candidato['score_total']}, distancia: {mejor_candidato['distancia_km']} km)"
        )
        
        return {
            "exito": True,
            "id_asignacion": asignacion.id_asignacion,
            "id_taller_seleccionado": mejor_candidato["taller"].id_taller,
            "taller_seleccionado": mejor_candidato["taller"].nombre,
            "score": mejor_candidato["score_total"],
            "distancia_km": mejor_candidato["distancia_km"],
            "candidatos_total": len(candidatos_guardados),
        }
    
    return {"error": "No se pudo crear asignación"}
