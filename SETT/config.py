"""
Datos estaticos para el seed: credenciales, catalogos, talleres, tecnicos,
clientes y la definicion declarativa de los 15 escenarios.

Modificar aqui es la unica fuente de verdad para el contenido sembrado.
"""
from __future__ import annotations

# ── Catalogos ────────────────────────────────────────────────────────────────

ROLES = ["cliente", "taller", "tecnico", "admin"]

ESTADOS_INCIDENTE = [
    ("borrador", "Borrador: el cliente aun no confirmo el taller"),
    ("pendiente", "Reportado, sin asignar"),
    ("en_proceso", "Taller asignado, en atencion"),
    ("atendido", "Resuelto"),
    ("cancelado", "Cancelado por el usuario"),
]

# La BD ya tiene 7 estados: pendiente / aceptada / rechazada / en_camino /
# completada / cancelada / llegado. Los listamos todos para cubrirlos.
ESTADOS_ASIGNACION = [
    "pendiente",
    "aceptada",
    "rechazada",
    "en_camino",
    "llegado",
    "completada",
    "cancelada",
]

ESTADOS_PAGO = ["pendiente", "procesando", "completado", "fallido", "reembolsado"]

ESTADOS_COTIZACION = ["pendiente", "enviada", "aceptada", "rechazada", "expirada"]

CATEGORIAS = [
    # (codigo, nombre, descripcion, requiere_cotizacion)
    # Categorias clasicas (usadas por la IA y el flujo basico)
    ("bateria",          "bateria",              "Problemas de bateria",              False),
    ("llanta_pinchada",  "llanta",               "Llanta desinflada o reventada",     False),
    ("choque",           "choque",               "Colision o accidente",              False),
    ("motor",            "motor",                "Fallas del motor",                  False),
    ("llaves",           "llaves",               "Llaves perdidas o bloqueadas",      False),
    ("otros",            "otros",                "Otros problemas",                   False),
    ("incierto",         "incierto",             "Sin clasificar",                    False),
    # Categorias canonicas con codigo (usadas por el dashboard del taller, KPIs y tests)
    ("llantas",          "Servicio de llantas",  "Cambio / reparacion de llantas",    False),
    ("mecanica_general", "Mecanica general",     "Diagnostico y mecanica de taller",  True),
    ("electrico",        "Servicio electrico",   "Sistema electrico del vehiculo",    True),
    ("electronico",      "Servicio electronico", "Computadora y electronica",         True),
    ("chaperia_pintura", "Chaperia y pintura",   "Carroceria y pintura",              True),
    ("grua_auxilio",     "Grua / Auxilio vial",  "Traslado del vehiculo",             False),
    ("rutinario",        "Servicio rutinario",   "Mantenimiento programado",          False),
]

PRIORIDADES = [("baja", 1), ("media", 2), ("alta", 3), ("critica", 4)]

TIPOS_EVIDENCIA = ["imagen", "audio", "texto"]
METODOS_PAGO = ["tarjeta", "transferencia", "efectivo", "qr"]


# ── Planes SaaS ──────────────────────────────────────────────────────────────

PLANES = [
    {
        "codigo": "free",
        "nombre": "Free",
        "descripcion": "Plan gratuito: 1 taller, 5 tecnicos, 50 incidentes/mes",
        "precio_mensual": 0,
        "max_talleres": 1,
        "max_tecnicos": 5,
        "max_incidentes_mes": 50,
        "feature_websockets": False,
        "feature_kpis_avanzados": False,
        "feature_reportes_ia": False,
    },
    {
        "codigo": "pro",
        "nombre": "Pro",
        "descripcion": "Plan Pro: 3 talleres, 20 tecnicos, websockets, KPIs",
        "precio_mensual": 49,
        "max_talleres": 3,
        "max_tecnicos": 20,
        "max_incidentes_mes": 500,
        "feature_websockets": True,
        "feature_kpis_avanzados": True,
        "feature_reportes_ia": False,
    },
    {
        "codigo": "enterprise",
        "nombre": "Enterprise",
        "descripcion": "Plan Enterprise: ilimitado, IA, soporte 24/7",
        "precio_mensual": 199,
        "max_talleres": 999,
        "max_tecnicos": 999,
        "max_incidentes_mes": None,
        "feature_websockets": True,
        "feature_kpis_avanzados": True,
        "feature_reportes_ia": True,
    },
]


# ── Admin ────────────────────────────────────────────────────────────────────

ADMIN = {
    "nombre": "Administración General",
    "email": "admin.general@gmail.com",
    "password": "admin2026#",
    "telefono": "+591 70000000",
}


# ── Talleres + tenant 1:1 ────────────────────────────────────────────────────
# Cada taller pertenece a un tenant propio (slug derivado del email).

TALLERES = [
    {
        "slug": "autorescate-scz",
        "tenant_nombre": "AutoRescate Santa Cruz Org",
        "plan": "enterprise",
        "nombre": "AutoRescate Santa Cruz",
        "email": "autorescate.scz@gmail.com",
        "password": "taller2026#",
        "telefono": "+591 70011111",
        "direccion": "Av. Cristo Redentor #500, Santa Cruz",
        "latitud": -17.802625,
        "longitud": -63.200045,
        "capacidad_max": 5,
        # Categorias que atiende
        "categorias": [
            "bateria", "llanta", "motor", "choque", "llaves", "otros",
            "incierto", "Mecanica general", "Servicio electrico",
            "Grua / Auxilio vial",
        ],
    },
    {
        "slug": "hermanos-justiniano",
        "tenant_nombre": "Taller Hermanos Justiniano Org",
        "plan": "pro",
        "nombre": "Taller Hermanos Justiniano",
        "email": "hermanos.justiniano@gmail.com",
        "password": "taller2026#",
        "telefono": "+591 70022222",
        "direccion": "2do Anillo y Av. Alemana, Santa Cruz",
        "latitud": -17.781230,
        "longitud": -63.181450,
        "capacidad_max": 4,
        "categorias": [
            "motor", "bateria", "choque", "llaves", "incierto",
            "Mecanica general", "Servicio electronico", "Chaperia y pintura",
        ],
    },
    {
        "slug": "mecanica-elcarmen",
        "tenant_nombre": "Mecánica El Carmen Org",
        "plan": "free",
        "nombre": "Mecánica El Carmen",
        "email": "mecanica.elcarmen@gmail.com",
        "password": "taller2026#",
        "telefono": "+591 70033333",
        "direccion": "Av. Cristo Redentor km 4",
        "latitud": -17.815320,
        "longitud": -63.188120,
        "capacidad_max": 3,
        "categorias": [
            "llanta", "llaves", "choque", "otros", "incierto",
            "Servicio de llantas", "Grua / Auxilio vial", "Servicio rutinario",
        ],
    },
]


# ── Tecnicos (2 por taller) ──────────────────────────────────────────────────
# taller_idx referencia la posicion en TALLERES.

TECNICOS = [
    {"nombre": "Rodrigo Áñez",    "email": "rodrigo.anez@gmail.com",     "password": "tecnico2026#", "telefono": "+591 71011111", "taller_idx": 0},
    {"nombre": "Fernando Suárez", "email": "fernando.suarez@gmail.com",  "password": "tecnico2026#", "telefono": "+591 71011112", "taller_idx": 0},
    {"nombre": "Marco Peña",      "email": "marco.pena@gmail.com",       "password": "tecnico2026#", "telefono": "+591 71022221", "taller_idx": 1},
    {"nombre": "Sergio Vaca",     "email": "sergio.vaca@gmail.com",      "password": "tecnico2026#", "telefono": "+591 71022222", "taller_idx": 1},
    {"nombre": "Iván Roca",       "email": "ivan.roca@gmail.com",        "password": "tecnico2026#", "telefono": "+591 71033331", "taller_idx": 2},
    {"nombre": "Hugo Méndez",     "email": "hugo.mendez@gmail.com",      "password": "tecnico2026#", "telefono": "+591 71033332", "taller_idx": 2},
]


# ── Clientes ─────────────────────────────────────────────────────────────────
# Un cliente DEDICADO por escenario para que los flujos se vean aislados
# en cualquier dashboard. El "key" se referencia luego desde escenarios/*.

CLIENTES = [
    # Incidentes basicos (7 estados de asignacion)
    {"key": "cli_pendiente",      "nombre": "Lucia Pendiente",     "email": "lucia.pendiente.demo@gmail.com",      "password": "cliente2026#", "telefono": "+591 70111001", "vehiculo": {"placa": "SCZ-001", "marca": "Toyota",    "modelo": "Corolla",  "anio": 2021, "color": "Blanco"}},
    {"key": "cli_aceptada",       "nombre": "Mario Aceptada",      "email": "mario.aceptada.demo@gmail.com",       "password": "cliente2026#", "telefono": "+591 70111002", "vehiculo": {"placa": "SCZ-002", "marca": "Nissan",    "modelo": "Sentra",   "anio": 2020, "color": "Rojo"}},
    {"key": "cli_rechazada",      "nombre": "Sofia Rechazada",     "email": "sofia.rechazada.demo@gmail.com",      "password": "cliente2026#", "telefono": "+591 70111003", "vehiculo": {"placa": "SCZ-003", "marca": "Suzuki",    "modelo": "Swift",    "anio": 2022, "color": "Azul"}},
    {"key": "cli_en_camino",      "nombre": "Diego En Camino",     "email": "diego.encamino.demo@gmail.com",       "password": "cliente2026#", "telefono": "+591 70111004", "vehiculo": {"placa": "SCZ-004", "marca": "Kia",       "modelo": "Picanto",  "anio": 2023, "color": "Negro"}},
    {"key": "cli_llegado",        "nombre": "Carla Llegado",       "email": "carla.llegado.demo@gmail.com",        "password": "cliente2026#", "telefono": "+591 70111005", "vehiculo": {"placa": "SCZ-005", "marca": "Chevrolet", "modelo": "Spark",    "anio": 2019, "color": "Gris"}},
    {"key": "cli_atendido",       "nombre": "Ramiro Atendido",     "email": "ramiro.atendido.demo@gmail.com",      "password": "cliente2026#", "telefono": "+591 70111006", "vehiculo": {"placa": "SCZ-006", "marca": "Honda",     "modelo": "Civic",    "anio": 2018, "color": "Plateado"}},
    {"key": "cli_cancelado",      "nombre": "Veronica Cancelado",  "email": "veronica.cancelado.demo@gmail.com",   "password": "cliente2026#", "telefono": "+591 70111007", "vehiculo": {"placa": "SCZ-007", "marca": "Hyundai",   "modelo": "Accent",   "anio": 2017, "color": "Verde"}},
    # Cotizaciones (5 estados)
    {"key": "cli_cot_pendiente",  "nombre": "Andres CotPendiente", "email": "andres.cotpendiente.demo@gmail.com",   "password": "cliente2026#", "telefono": "+591 70111008", "vehiculo": {"placa": "SCZ-008", "marca": "Mazda",     "modelo": "3",        "anio": 2020, "color": "Azul"}},
    {"key": "cli_cot_enviada",    "nombre": "Paola CotEnviada",    "email": "paola.cotenviada.demo@gmail.com",      "password": "cliente2026#", "telefono": "+591 70111009", "vehiculo": {"placa": "SCZ-009", "marca": "Volkswagen","modelo": "Gol",      "anio": 2019, "color": "Blanco"}},
    {"key": "cli_cot_aceptada",   "nombre": "Jorge CotAceptada",   "email": "jorge.cotaceptada.demo@gmail.com",     "password": "cliente2026#", "telefono": "+591 70111010", "vehiculo": {"placa": "SCZ-010", "marca": "Ford",      "modelo": "Fiesta",   "anio": 2021, "color": "Rojo"}},
    {"key": "cli_cot_rechazada",  "nombre": "Elena CotRechazada",  "email": "elena.cotrechazada.demo@gmail.com",    "password": "cliente2026#", "telefono": "+591 70111011", "vehiculo": {"placa": "SCZ-011", "marca": "Renault",   "modelo": "Logan",    "anio": 2022, "color": "Gris"}},
    {"key": "cli_cot_expirada",   "nombre": "Pablo CotExpirada",   "email": "pablo.cotexpirada.demo@gmail.com",     "password": "cliente2026#", "telefono": "+591 70111012", "vehiculo": {"placa": "SCZ-012", "marca": "Peugeot",   "modelo": "208",      "anio": 2018, "color": "Negro"}},
    # Pagos (estados adicionales)
    {"key": "cli_pago_procesando","nombre": "Marta PagoProcesando","email": "marta.pagoprocesando.demo@gmail.com",  "password": "cliente2026#", "telefono": "+591 70111013", "vehiculo": {"placa": "SCZ-013", "marca": "Fiat",      "modelo": "Mobi",     "anio": 2020, "color": "Blanco"}},
    {"key": "cli_pago_fallido",   "nombre": "Cesar PagoFallido",   "email": "cesar.pagofallido.demo@gmail.com",     "password": "cliente2026#", "telefono": "+591 70111014", "vehiculo": {"placa": "SCZ-014", "marca": "Subaru",    "modelo": "Impreza",  "anio": 2019, "color": "Azul"}},
    {"key": "cli_pago_reembolso", "nombre": "Ines PagoReembolso",  "email": "ines.pagoreembolso.demo@gmail.com",    "password": "cliente2026#", "telefono": "+591 70111015", "vehiculo": {"placa": "SCZ-015", "marca": "Mitsubishi","modelo": "Lancer",   "anio": 2017, "color": "Rojo"}},
    {"key": "cli_pago_pendiente", "nombre": "Hugo PagoPendiente",  "email": "hugo.pagopendiente.demo@gmail.com",    "password": "cliente2026#", "telefono": "+591 70111016", "vehiculo": {"placa": "SCZ-016", "marca": "Toyota",    "modelo": "Yaris",    "anio": 2022, "color": "Blanco"}},
]


# ── Coordenadas Santa Cruz ──────────────────────────────────────────────────

COORDS_SCZ = [
    (-17.802625, -63.200045),  # Cristo Redentor
    (-17.781230, -63.181450),  # 2do anillo
    (-17.815320, -63.188120),  # Av. Cristo km 4
    (-17.795020, -63.190100),
    (-17.808120, -63.196250),
    (-17.787500, -63.175800),
    (-17.823100, -63.205400),
    (-17.793800, -63.192100),
    (-17.811200, -63.179600),
    (-17.776900, -63.166400),
    (-17.819400, -63.193700),
    (-17.788200, -63.205100),
    (-17.802000, -63.182000),
    (-17.815700, -63.198800),
    (-17.794100, -63.179900),
]


# ── Tablas a TRUNCATE (orden inverso de dependencias) ───────────────────────

TABLAS_A_LIMPIAR = [
    "ubicacion_tecnico",
    "historial_estado_asignacion",
    "historial_estado_incidente",
    "candidato_asignacion",
    "evaluacion",
    "asignacion",
    "cotizacion",
    "evidencia",
    "metrica",
    "notificacion",
    "mensaje",
    "pago",
    "incidente",
    "vehiculo",
    "usuario_taller",
    "taller_servicio",
    "taller",
    "tenant_user",
    "suscripcion",
    "tenant",
    "plan",
    "usuario",
    "rol",
    "estado_incidente",
    "estado_asignacion",
    "estado_cotizacion",
    "estado_pago",
    "categoria_problema",
    "prioridad",
    "tipo_evidencia",
    "metodo_pago",
]
