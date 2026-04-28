"""
Seed completo de Yary — usa los modelos SQLAlchemy del backend, así respeta
todas las restricciones (FKs, CheckConstraints, hashing real con Argon2,
historiales, métricas).

Pobla:
  - Catálogos (rol, estado_incidente, estado_asignacion, prioridad, categoría, etc.)
  - 1 admin
  - 3 talleres en Santa Cruz con sus servicios (categorías que atienden)
  - 6 técnicos (usuarios rol=3 vinculados a los talleres)
  - 3 clientes con vehículos
  - 5 incidentes que cubren todos los estados de incidente y asignación:
        pendiente / en_proceso / atendido / cancelado
        pendiente / aceptada / rechazada / en_camino / completada
  - Evidencias (URLs de placeholder, sin tocar Cloudinary)
  - Mensajes cliente↔taller
  - Notificaciones
  - Métricas por incidente
  - Pago completado para el incidente atendido + evaluación 5★

Uso local:
    python -m seeders.seed_full

Uso en Render (ver render.yaml): se ejecuta automáticamente en cada deploy
antes de levantar gunicorn.

Idempotente: trunca todas las tablas transaccionales antes de sembrar.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permitir ejecución como script suelto (python seeders/seed_full.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
import app.models  # noqa: F401  – registra todas las tablas en Base.metadata
from app.models.catalogos import (
    CategoriaProblema,
    EstadoAsignacion,
    EstadoIncidente,
    EstadoPago,
    MetodoPago,
    Prioridad,
    Rol,
    TipoEvidencia,
)
from app.models.incidente import (
    Asignacion,
    CandidatoAsignacion,
    Evaluacion,
    Evidencia,
    HistorialEstadoAsignacion,
    HistorialEstadoIncidente,
    Incidente,
)
from app.models.taller import Taller, TallerServicio
from app.models.transaccional import Mensaje, Metrica, Notificacion, Pago
from app.models.usuario import Usuario, Vehiculo
from app.models.usuario_taller import UsuarioTaller

logger = logging.getLogger("seed_full")
logging.basicConfig(level=logging.INFO, format="%(message)s")


# Orden inverso de dependencia para TRUNCATE CASCADE
TABLAS_A_LIMPIAR = [
    "historial_estado_asignacion",
    "historial_estado_incidente",
    "candidato_asignacion",
    "evaluacion",
    "asignacion",
    "evidencia",
    "metrica",
    "notificacion",
    "mensaje",
    "pago",
    "incidente",
    "vehiculo",
    "usuario_taller",
    "taller_servicio",
    "usuario",
    "taller",
    "rol",
    "estado_incidente",
    "categoria_problema",
    "prioridad",
    "estado_asignacion",
    "tipo_evidencia",
    "metodo_pago",
    "estado_pago",
]


# ── Catálogos ─────────────────────────────────────────────────────────────────

ROLES = ["cliente", "taller", "tecnico", "admin"]

ESTADOS_INCIDENTE = [
    ("pendiente", "Reportado, sin asignar"),
    ("en_proceso", "Taller asignado, en atención"),
    ("atendido", "Resuelto"),
    ("cancelado", "Cancelado por el usuario"),
]

CATEGORIAS = [
    ("bateria", "Problemas de batería"),
    ("llanta", "Llanta desinflada o reventada"),
    ("choque", "Colisión o accidente"),
    ("motor", "Fallas del motor"),
    ("llaves", "Llaves perdidas o bloqueadas"),
    ("otros", "Otros problemas"),
    ("incierto", "Sin clasificar"),
]

PRIORIDADES = [("baja", 1), ("media", 2), ("alta", 3), ("critica", 4)]

ESTADOS_ASIGNACION = ["pendiente", "aceptada", "rechazada", "en_camino", "completada"]

TIPOS_EVIDENCIA = ["imagen", "audio", "texto"]
METODOS_PAGO = ["tarjeta", "transferencia", "efectivo", "qr"]
ESTADOS_PAGO = ["pendiente", "procesando", "completado", "fallido", "reembolsado"]


# ── Datos de prueba ───────────────────────────────────────────────────────────

ADMIN = {
    "nombre": "Administrador Sistema",
    "email": "admin@plataforma.com",
    "password": "admin123!",
    "telefono": "+591 70000000",
}

TALLERES = [
    {
        "nombre": "Taller Excelente",
        "email": "gerente@tallerexcelente.com",
        "password": "taller123!",
        "telefono": "+591 70011111",
        "direccion": "Av. Cristo Redentor #500, Santa Cruz",
        "latitud": -17.802625,
        "longitud": -63.200045,
        "capacidad_max": 5,
        # Categorías que atiende
        "categorias": ["bateria", "llanta", "motor", "choque", "llaves", "otros", "incierto"],
    },
    {
        "nombre": "Mecánica Central SC",
        "email": "mecanica.central@talleres.test",
        "password": "taller123!",
        "telefono": "+591 70022222",
        "direccion": "2do Anillo y Av. Alemana, Santa Cruz",
        "latitud": -17.781230,
        "longitud": -63.181450,
        "capacidad_max": 4,
        "categorias": ["motor", "bateria", "choque", "llaves", "incierto"],
    },
    {
        "nombre": "Llantería El Cristo",
        "email": "llanteria.cristo@talleres.test",
        "password": "taller123!",
        "telefono": "+591 70033333",
        "direccion": "Av. Cristo Redentor km 4",
        "latitud": -17.815320,
        "longitud": -63.188120,
        "capacidad_max": 3,
        "categorias": ["llanta", "llaves", "choque", "otros", "incierto"],
    },
]

# 2 técnicos por taller (índice 0..2)
TECNICOS = [
    # Taller 1
    {"nombre": "Juan Pérez",     "email": "tecnico.juan@taller.com",     "password": "tecnico123!", "telefono": "+591 71011111", "taller_idx": 0},
    {"nombre": "Carlos Gómez",   "email": "tecnico.carlos@taller.com",   "password": "tecnico123!", "telefono": "+591 71011112", "taller_idx": 0},
    # Taller 2
    {"nombre": "Luis Rodríguez", "email": "tecnico.luis@taller.com",     "password": "tecnico123!", "telefono": "+591 71022221", "taller_idx": 1},
    {"nombre": "Mario López",    "email": "tecnico.mario@taller.com",    "password": "tecnico123!", "telefono": "+591 71022222", "taller_idx": 1},
    # Taller 3
    {"nombre": "Pedro Vargas",   "email": "tecnico.pedro@taller.com",    "password": "tecnico123!", "telefono": "+591 71033331", "taller_idx": 2},
    {"nombre": "Diego Mamani",   "email": "tecnico.diego@taller.com",    "password": "tecnico123!", "telefono": "+591 71033332", "taller_idx": 2},
]

CLIENTES = [
    {
        "nombre": "Juan Conductor",
        "email": "conductor@ejemplo.com",
        "password": "cliente123!",
        "telefono": "+591 70111001",
        "vehiculo": {"placa": "SCZ-001", "marca": "Toyota", "modelo": "Corolla", "anio": 2021, "color": "Blanco"},
    },
    {
        "nombre": "Ana Pérez",
        "email": "ana.cliente@ejemplo.com",
        "password": "cliente123!",
        "telefono": "+591 70111002",
        "vehiculo": {"placa": "SCZ-002", "marca": "Nissan", "modelo": "Sentra", "anio": 2020, "color": "Rojo"},
    },
    {
        "nombre": "Pedro Ramírez",
        "email": "pedro.cliente@ejemplo.com",
        "password": "cliente123!",
        "telefono": "+591 70111003",
        "vehiculo": {"placa": "SCZ-003", "marca": "Suzuki", "modelo": "Swift", "anio": 2022, "color": "Azul"},
    },
    {
        "nombre": "María Flores",
        "email": "maria.cliente@ejemplo.com",
        "password": "cliente123!",
        "telefono": "+591 70111004",
        "vehiculo": {"placa": "SCZ-004", "marca": "Kia", "modelo": "Picanto", "anio": 2023, "color": "Negro"},
    },
    {
        "nombre": "Carlos Quispe",
        "email": "carlos.cliente@ejemplo.com",
        "password": "cliente123!",
        "telefono": "+591 70111005",
        "vehiculo": {"placa": "SCZ-005", "marca": "Chevrolet", "modelo": "Spark", "anio": 2019, "color": "Gris"},
    },
]

# Cinco escenarios — 1 incidente por cliente, sin solapamiento de activos.
# taller_idx=0 (Taller Excelente) recibe la evaluación para que las estrellas
# aparezcan en el dashboard cuando el usuario loguea como gerente@tallerexcelente.com
INCIDENTES = [
    {
        "cliente_idx": 0,
        "descripcion": "Mi batería está descargada, no enciende el auto.",
        "lat": -17.802625, "lng": -63.200045,
        "categoria": "bateria",
        "prioridad": "media",
        "estado_inc": "pendiente",
        "estado_asig": "pendiente",
        "taller_idx": 0,
        "tecnico_idx": None,
    },
    {
        "cliente_idx": 1,
        "descripcion": "Tengo una llanta reventada, estoy varada en el 2do anillo.",
        "lat": -17.781230, "lng": -63.181450,
        "categoria": "llanta",
        "prioridad": "alta",
        "estado_inc": "pendiente",
        "estado_asig": "aceptada",
        "taller_idx": 2,
        "tecnico_idx": 4,  # Pedro Vargas
    },
    {
        "cliente_idx": 2,
        "descripcion": "Choque leve frente a mi auto, no puedo arrancar.",
        "lat": -17.815320, "lng": -63.188120,
        "categoria": "choque",
        "prioridad": "alta",
        "estado_inc": "pendiente",
        "estado_asig": "rechazada",
        "taller_idx": 1,
        "tecnico_idx": None,
    },
    {
        "cliente_idx": 3,
        "descripcion": "Falla del motor en plena vía. Sale humo del cofre.",
        "lat": -17.795020, "lng": -63.190100,
        "categoria": "motor",
        "prioridad": "critica",
        "estado_inc": "en_proceso",
        "estado_asig": "en_camino",
        "taller_idx": 1,
        "tecnico_idx": 2,  # Luis Rodríguez
    },
    {
        "cliente_idx": 4,
        "descripcion": "Se me perdieron las llaves, no puedo entrar al auto.",
        "lat": -17.808120, "lng": -63.196250,
        "categoria": "llaves",
        "prioridad": "media",
        "estado_inc": "atendido",
        "estado_asig": "completada",
        "taller_idx": 0,   # Taller Excelente recibe la evaluación → estrellas visibles
        "tecnico_idx": 0,  # Juan Pérez
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_tables(db: Session) -> None:
    """Crea las tablas si aún no existen (primer despliegue)."""
    Base.metadata.create_all(bind=engine)
    logger.info("[seed] Tablas verificadas / creadas")


def _truncate_all(db: Session) -> None:
    """TRUNCATE CASCADE de todas las tablas, reiniciando secuencias."""
    for tabla in TABLAS_A_LIMPIAR:
        try:
            db.execute(text(f"TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE;"))
        except Exception as e:
            logger.info(f"[seed] (skip) tabla {tabla} no existe: {e}")
            db.rollback()
            continue
    db.commit()
    logger.info("[seed] Tablas truncadas (secuencias reiniciadas)")


def _seed_catalogos(db: Session) -> None:
    db.add_all([Rol(nombre=n) for n in ROLES])
    db.add_all([EstadoIncidente(nombre=n, descripcion=d) for n, d in ESTADOS_INCIDENTE])
    db.add_all([CategoriaProblema(nombre=n, descripcion=d) for n, d in CATEGORIAS])
    db.add_all([Prioridad(nivel=n, orden=o) for n, o in PRIORIDADES])
    db.add_all([EstadoAsignacion(nombre=n) for n in ESTADOS_ASIGNACION])
    db.add_all([TipoEvidencia(nombre=n) for n in TIPOS_EVIDENCIA])
    db.add_all([MetodoPago(nombre=n) for n in METODOS_PAGO])
    db.add_all([EstadoPago(nombre=n) for n in ESTADOS_PAGO])
    db.commit()
    logger.info("[seed] Catálogos creados")


def _seed_admin(db: Session) -> Usuario:
    rol_admin = db.query(Rol).filter_by(nombre="admin").one()
    admin = Usuario(
        id_rol=rol_admin.id_rol,
        nombre=ADMIN["nombre"],
        email=ADMIN["email"],
        telefono=ADMIN["telefono"],
        password_hash=hash_password(ADMIN["password"]),
        activo=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    logger.info(f"[seed] Admin creado: {admin.email}")
    return admin


def _seed_talleres(db: Session) -> list[Taller]:
    cat_by_name = {c.nombre: c for c in db.query(CategoriaProblema).all()}
    talleres: list[Taller] = []
    for t in TALLERES:
        taller = Taller(
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
        )
        db.add(taller)
        db.flush()  # obtener id_taller

        for cat_nombre in t["categorias"]:
            cat = cat_by_name.get(cat_nombre)
            if not cat:
                continue
            db.add(TallerServicio(
                id_taller=taller.id_taller,
                id_categoria=cat.id_categoria,
                servicio_movil=True,
            ))

        talleres.append(taller)

    db.commit()
    for t in talleres:
        db.refresh(t)
    logger.info(f"[seed] {len(talleres)} talleres + servicios creados")
    return talleres


def _seed_tecnicos(db: Session, talleres: list[Taller]) -> list[Usuario]:
    rol_tecnico = db.query(Rol).filter_by(nombre="tecnico").one()
    tecnicos: list[Usuario] = []
    for t in TECNICOS:
        usuario = Usuario(
            id_rol=rol_tecnico.id_rol,
            nombre=t["nombre"],
            email=t["email"],
            telefono=t["telefono"],
            password_hash=hash_password(t["password"]),
            activo=True,
        )
        db.add(usuario)
        db.flush()

        taller = talleres[t["taller_idx"]]
        db.add(UsuarioTaller(
            id_usuario=usuario.id_usuario,
            id_taller=taller.id_taller,
            disponible=True,
            activo=True,
            latitud=taller.latitud,
            longitud=taller.longitud,
        ))
        tecnicos.append(usuario)

    db.commit()
    for u in tecnicos:
        db.refresh(u)
    logger.info(f"[seed] {len(tecnicos)} técnicos creados (rol=3 + usuario_taller)")
    return tecnicos


def _seed_clientes(db: Session) -> tuple[list[Usuario], list[Vehiculo]]:
    rol_cliente = db.query(Rol).filter_by(nombre="cliente").one()
    clientes: list[Usuario] = []
    vehiculos: list[Vehiculo] = []
    for c in CLIENTES:
        cliente = Usuario(
            id_rol=rol_cliente.id_rol,
            nombre=c["nombre"],
            email=c["email"],
            telefono=c["telefono"],
            password_hash=hash_password(c["password"]),
            activo=True,
        )
        db.add(cliente)
        db.flush()

        v = c["vehiculo"]
        vehiculo = Vehiculo(
            id_usuario=cliente.id_usuario,
            placa=v["placa"], marca=v["marca"], modelo=v["modelo"],
            anio=v["anio"], color=v["color"], activo=True,
        )
        db.add(vehiculo)
        db.flush()

        clientes.append(cliente)
        vehiculos.append(vehiculo)

    db.commit()
    for x in clientes + vehiculos:
        db.refresh(x)
    logger.info(f"[seed] {len(clientes)} clientes + vehículos creados")
    return clientes, vehiculos


def _seed_incidentes(
    db: Session,
    clientes: list[Usuario],
    vehiculos: list[Vehiculo],
    talleres: list[Taller],
    tecnicos: list[Usuario],
) -> None:
    """
    Crea los 5 escenarios de incidente cubriendo todos los estados.
    Para cada uno:
      - Inserta Incidente con su estado final
      - Inserta Métrica con timestamps coherentes
      - Inserta Evidencia (1 imagen + 1 texto)
      - Inserta CandidatoAsignacion (top-3 simulando motor de asignación)
      - Inserta Asignacion con estado final + Historial completo
      - Si está atendido: agrega Pago completado + Evaluación 5★
      - Inserta Mensajes cliente↔taller
      - Inserta Notificacion para cliente y taller
    """
    cat_by_name = {c.nombre: c for c in db.query(CategoriaProblema).all()}
    pri_by_name = {p.nivel: p for p in db.query(Prioridad).all()}
    estado_inc_by = {e.nombre: e for e in db.query(EstadoIncidente).all()}
    estado_asig_by = {e.nombre: e for e in db.query(EstadoAsignacion).all()}
    estado_pago_by = {e.nombre: e for e in db.query(EstadoPago).all()}
    metodo_pago_by = {m.nombre: m for m in db.query(MetodoPago).all()}
    tipo_ev_by = {t.nombre: t for t in db.query(TipoEvidencia).all()}

    ahora = datetime.now(timezone.utc)
    creados = 0

    for idx, esc in enumerate(INCIDENTES):
        cliente = clientes[esc["cliente_idx"]]
        vehiculo = vehiculos[esc["cliente_idx"]]
        taller = talleres[esc["taller_idx"]]
        tecnico = tecnicos[esc["tecnico_idx"]] if esc["tecnico_idx"] is not None else None

        # ── Incidente ──
        incidente = Incidente(
            id_usuario=cliente.id_usuario,
            id_vehiculo=vehiculo.id_vehiculo,
            id_estado=estado_inc_by[esc["estado_inc"]].id_estado,
            id_categoria=cat_by_name[esc["categoria"]].id_categoria,
            id_prioridad=pri_by_name[esc["prioridad"]].id_prioridad,
            latitud=esc["lat"], longitud=esc["lng"],
            descripcion_usuario=esc["descripcion"],
            resumen_ia=f"[Seed] Diagnóstico simulado: {esc['categoria']} con prioridad {esc['prioridad']}",
            clasificacion_ia_confianza=0.9,
            requiere_revision_manual=False,
        )
        db.add(incidente)
        db.flush()

        # ── Historial: creación del incidente ──
        db.add(HistorialEstadoIncidente(
            id_incidente=incidente.id_incidente,
            id_estado_anterior=None,
            id_estado_nuevo=estado_inc_by["pendiente"].id_estado,
            observacion="Incidente reportado (seed)",
        ))

        # Si el estado no es "pendiente", encadenar transiciones
        if esc["estado_inc"] != "pendiente":
            db.add(HistorialEstadoIncidente(
                id_incidente=incidente.id_incidente,
                id_estado_anterior=estado_inc_by["pendiente"].id_estado,
                id_estado_nuevo=estado_inc_by["en_proceso"].id_estado,
                observacion="Técnico en camino (seed)",
            ))
            if esc["estado_inc"] == "atendido":
                db.add(HistorialEstadoIncidente(
                    id_incidente=incidente.id_incidente,
                    id_estado_anterior=estado_inc_by["en_proceso"].id_estado,
                    id_estado_nuevo=estado_inc_by["atendido"].id_estado,
                    observacion="Servicio completado (seed)",
                ))

        # ── Métrica ──
        fecha_inicio = ahora - timedelta(hours=2 + idx)
        metrica = Metrica(
            id_incidente=incidente.id_incidente,
            fecha_inicio=fecha_inicio,
        )
        if esc["estado_asig"] in ("aceptada", "en_camino", "completada"):
            metrica.fecha_asignacion = fecha_inicio + timedelta(minutes=5)
            metrica.tiempo_respuesta_min = 5
        if esc["estado_asig"] in ("en_camino", "completada"):
            metrica.fecha_llegada_tecnico = fecha_inicio + timedelta(minutes=20)
            metrica.tiempo_llegada_min = 15
        if esc["estado_asig"] == "completada":
            metrica.fecha_fin = fecha_inicio + timedelta(minutes=60)
            metrica.tiempo_resolucion_min = 60
            metrica.calificacion_cliente = 5
            metrica.comentario_cliente = "Excelente servicio (seed)"
        db.add(metrica)

        # ── Evidencias (URLs placeholder, sin tocar Cloudinary) ──
        db.add(Evidencia(
            id_incidente=incidente.id_incidente,
            id_tipo_evidencia=tipo_ev_by["texto"].id_tipo_evidencia,
            url_archivo="https://placehold.co/seed-nota.txt",
            descripcion_ia="Nota de texto del cliente (seed)",
        ))
        db.add(Evidencia(
            id_incidente=incidente.id_incidente,
            id_tipo_evidencia=tipo_ev_by["imagen"].id_tipo_evidencia,
            url_archivo="https://placehold.co/600x400/png?text=Seed+Evidencia",
            descripcion_ia="Foto del incidente (seed)",
        ))

        # ── Candidatos (top 3 talleres) ──
        otros_talleres = [t for t in talleres if t.id_taller != taller.id_taller]
        # El elegido va primero como seleccionado=True
        db.add(CandidatoAsignacion(
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            distancia_km=1.5,
            score_total=92.0,
            seleccionado=True,
        ))
        for j, otro in enumerate(otros_talleres[:2]):
            db.add(CandidatoAsignacion(
                id_incidente=incidente.id_incidente,
                id_taller=otro.id_taller,
                distancia_km=3.0 + j,
                score_total=70.0 - j * 5,
                seleccionado=False,
            ))

        # ── Asignación ──
        asignacion = Asignacion(
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_usuario=tecnico.id_usuario if tecnico else None,
            id_estado_asignacion=estado_asig_by[esc["estado_asig"]].id_estado_asignacion,
            eta_minutos=20 if esc["estado_asig"] != "pendiente" else None,
            costo_estimado=85.50 if esc["estado_asig"] == "completada" else None,
            nota_taller=(
                "Servicio completado (seed)" if esc["estado_asig"] == "completada"
                else "Rechazada por falta de capacidad (seed)" if esc["estado_asig"] == "rechazada"
                else None
            ),
        )
        db.add(asignacion)
        db.flush()

        # ── Historial de la asignación ──
        # 1) creación → pendiente
        db.add(HistorialEstadoAsignacion(
            id_asignacion=asignacion.id_asignacion,
            id_estado_anterior=None,
            id_estado_nuevo=estado_asig_by["pendiente"].id_estado_asignacion,
            observacion=f"Motor de asignación seleccionó {taller.nombre} (seed)",
        ))
        # 2) transición a estado final si no es pendiente
        cadena = {
            "pendiente": [],
            "aceptada": ["aceptada"],
            "rechazada": ["rechazada"],
            "en_camino": ["aceptada", "en_camino"],
            "completada": ["aceptada", "en_camino", "completada"],
        }[esc["estado_asig"]]
        prev = "pendiente"
        for siguiente in cadena:
            db.add(HistorialEstadoAsignacion(
                id_asignacion=asignacion.id_asignacion,
                id_estado_anterior=estado_asig_by[prev].id_estado_asignacion,
                id_estado_nuevo=estado_asig_by[siguiente].id_estado_asignacion,
                observacion=f"Transición seed → {siguiente}",
            ))
            prev = siguiente

        # ── Pago + Evaluación si completado ──
        if esc["estado_asig"] == "completada":
            db.add(Pago(
                id_incidente=incidente.id_incidente,
                id_metodo_pago=metodo_pago_by["tarjeta"].id_metodo_pago,
                id_estado_pago=estado_pago_by["pendiente"].id_estado_pago,
                monto_total=85.50,
                comision_plataforma=8.55,
                monto_taller=76.95,
                referencia_externa=f"pi_seed_{incidente.id_incidente}",
            ))
            db.add(Evaluacion(
                id_incidente=incidente.id_incidente,
                id_usuario=cliente.id_usuario,
                id_taller=taller.id_taller,
                estrellas=5,
                comentario="Excelente atención y rapidez (seed)",
            ))

        # ── Mensajes cliente ↔ taller ──
        db.add(Mensaje(
            id_incidente=incidente.id_incidente,
            id_usuario=cliente.id_usuario,
            contenido=f"Hola, necesito ayuda con: {esc['descripcion']}",
            leido=True,
        ))
        if esc["estado_asig"] != "pendiente":
            db.add(Mensaje(
                id_incidente=incidente.id_incidente,
                id_taller=taller.id_taller,
                contenido="Gracias por reportar. Vamos en camino.",
                leido=False,
            ))

        # ── Notificaciones ──
        db.add(Notificacion(
            id_taller=taller.id_taller,
            id_incidente=incidente.id_incidente,
            titulo="Nueva solicitud de asistencia",
            mensaje=f"Tienes una solicitud de {cliente.nombre}",
            leido=esc["estado_asig"] != "pendiente",
        ))
        if esc["estado_asig"] in ("aceptada", "en_camino", "completada"):
            db.add(Notificacion(
                id_usuario=cliente.id_usuario,
                id_incidente=incidente.id_incidente,
                titulo="Solicitud aceptada",
                mensaje=f"{taller.nombre} aceptó tu solicitud",
                leido=esc["estado_asig"] == "completada",
            ))

        creados += 1

    db.commit()
    logger.info(f"[seed] {creados} incidentes con todos los estados creados")


def _resumen(db: Session) -> None:
    print("\n" + "=" * 70)
    print("RESUMEN DEL SEED")
    print("=" * 70)
    tablas_resumen = [
        "rol", "estado_incidente", "categoria_problema", "prioridad",
        "estado_asignacion", "tipo_evidencia", "metodo_pago", "estado_pago",
        "usuario", "taller", "taller_servicio", "usuario_taller", "vehiculo",
        "incidente", "asignacion", "candidato_asignacion",
        "historial_estado_incidente", "historial_estado_asignacion",
        "evidencia", "mensaje", "notificacion", "metrica", "pago", "evaluacion",
    ]
    for t in tablas_resumen:
        try:
            n = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:35s} {n}")
        except Exception:
            pass
    print("=" * 70)
    print("\nCREDENCIALES DE PRUEBA")
    print("-" * 70)
    print(f"  ADMIN  : {ADMIN['email']:40s} / {ADMIN['password']}")
    for t in TALLERES:
        print(f"  TALLER : {t['email']:40s} / {t['password']}")
    for c in CLIENTES:
        print(f"  CLIENTE: {c['email']:40s} / {c['password']}")
    for t in TECNICOS:
        print(f"  TECNICO: {t['email']:40s} / {t['password']}")
    print("=" * 70 + "\n")


def run() -> None:
    from app.core.config import get_settings
    print(f"[seed] DATABASE_URL host: {get_settings().DATABASE_URL.split('@')[-1]}")
    db = SessionLocal()
    try:
        _ensure_tables(db)
        _truncate_all(db)
        _seed_catalogos(db)
        _seed_admin(db)
        talleres = _seed_talleres(db)
        tecnicos = _seed_tecnicos(db, talleres)
        clientes, vehiculos = _seed_clientes(db)
        _seed_incidentes(db, clientes, vehiculos, talleres, tecnicos)
        _resumen(db)
        print("[seed] OK — base poblada con todos los estados")
    except Exception:
        db.rollback()
        logger.exception("[seed] FALLO")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
