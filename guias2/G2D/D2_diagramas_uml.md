# D2 — Diagramas UML actualizados

> **Pre-requisito:** Ciclos 1 y 2 cerrados (modelos finales).
> **Esfuerzo:** 0.5 día.

## Objetivo
Tener listo para la defensa:
1. Diagrama de clases consolidado (entidades + multi-tenant + cotización + cancelación + tracking).
2. Diagramas de secuencia de los 4 casos de uso clave nuevos.
3. Diagrama de despliegue actualizado (Redis, IA, mobile/web).

Todos en **PlantUML** (text-as-code → versionable en Git, exportable a PNG/SVG).

---

## Setup

Instalar PlantUML local o usar el render online ([https://www.plantuml.com/plantuml](https://www.plantuml.com/plantuml)).

VSCode extension recomendada: **PlantUML** by jebbs.

Estructura sugerida en el repo:

```
guias2/uml/
├── 01_clases_completo.puml
├── 02_secuencia_emergencia_broadcast.puml
├── 03_secuencia_cotizacion.puml
├── 04_secuencia_tracking.puml
├── 05_secuencia_cancelacion.puml
└── 06_despliegue.puml
```

Crear la carpeta:
```bash
mkdir -p guias2/uml
```

---

## 1. Diagrama de clases consolidado

`guias2/uml/01_clases_completo.puml`:

```plantuml
@startuml
!theme plain
title Diagrama de Clases — Yary (post Ciclo 2)

skinparam classAttributeIconSize 0
hide circle

' ===== MULTI-TENANT =====
package "Multi-tenant" #LightYellow {
    class Tenant {
        +id_tenant: int
        +slug: string
        +nombre: string
        +email_contacto: string
        +activo: bool
        +suspendido: bool
    }
    class Plan {
        +id_plan: int
        +codigo: string
        +precio_mensual: decimal
        +max_talleres: int
        +max_tecnicos: int
        +feature_websockets: bool
        +feature_reportes_ia: bool
    }
    class Suscripcion {
        +id_suscripcion: int
        +estado: string
        +inicio: datetime
        +fin: datetime?
    }
    class TenantUser {
        +id_tenant_user: int
        +rol_tenant: string
    }
}

' ===== ENTIDADES PRINCIPALES =====
package "Núcleo" {
    class Usuario {
        +id_usuario: int
        +id_rol: int
        +nombre: string
        +email: string
    }
    class Taller {
        +id_taller: int
        +id_tenant: int
        +nombre: string
        +latitud: float
        +longitud: float
        +tarifa_traslado: decimal
        +disponible: bool
    }
    class UsuarioTaller {
        +id_usuario_taller: int
        +disponible: bool
        +latitud: float?
        +longitud: float?
    }
    class Vehiculo {
        +id_vehiculo: int
        +placa: string
        +marca/modelo/anio
    }
    class CategoriaProblema {
        +id_categoria: int
        +codigo: string
        +requiere_cotizacion: bool
    }
    class TallerServicio {
        +id_taller_servicio: int
        +servicio_movil: bool
        +tarifa_base: decimal?
    }
}

' ===== TRANSACCIONAL =====
package "Operación" {
    class Incidente {
        +id_incidente: int
        +id_tenant: int?
        +latitud: float
        +longitud: float
        +descripcion_usuario: text
        +resumen_ia: text
        +clasificacion_ia_confianza: float
    }
    class CandidatoAsignacion {
        +id_candidato: int
        +distancia_km: float
        +score_total: float
        +seleccionado: bool
    }
    class Asignacion {
        +id_asignacion: int
        +id_tenant: int
        +eta_minutos: int?
        +costo_estimado: decimal
        +cancelada_at: datetime?
        +compensacion_monto: decimal?
        +compensacion_pagada: bool
    }
    class Evidencia {
        +id_evidencia: int
        +url_archivo: string
        +descripcion_ia: text
    }
    class HistorialEstadoAsignacion {
        +id_historial: int
        +observacion: string
    }
}

' ===== CICLO 1 NUEVOS =====
package "Cotización" #LightBlue {
    class Cotizacion {
        +id_cotizacion: int
        +id_tenant: int
        +monto_servicio: decimal
        +monto_repuestos: decimal
        +garantia_dias: int
        +validez_hasta: datetime
    }
    class EstadoCotizacion {
        +id_estado_cotizacion: int
        +nombre: string
    }
}

' ===== CICLO 2 NUEVOS =====
package "Tiempo Real" #LightGreen {
    class UbicacionTecnico {
        +id_ubicacion: bigint
        +latitud: float
        +longitud: float
        +accuracy_m: float
        +velocidad_kmh: float
        +created_at: datetime
    }
}

' ===== PAGO/MENSAJE/NOTIF =====
package "Comunicación" {
    class Mensaje
    class Notificacion
    class Pago {
        +id_pago: int
        +monto_total: decimal
        +comision_plataforma: decimal
        +monto_taller: decimal
        +referencia_externa: string
    }
    class Evaluacion {
        +estrellas: int
        +comentario: text
    }
}

' ===== RELACIONES =====
Tenant "1" -- "0..*" Taller
Tenant "1" -- "0..*" Suscripcion
Suscripcion "*" -- "1" Plan
Tenant "1" -- "0..*" TenantUser
TenantUser "*" -- "1" Usuario

Usuario "1" -- "0..*" Vehiculo
Usuario "1" -- "0..*" Incidente
Usuario "*" -- "*" Taller : (técnicos via UsuarioTaller)
UsuarioTaller "*" -- "1" Usuario
UsuarioTaller "*" -- "1" Taller

Taller "1" -- "0..*" TallerServicio
TallerServicio "*" -- "1" CategoriaProblema

Incidente "1" -- "0..*" CandidatoAsignacion
CandidatoAsignacion "*" -- "1" Taller
Incidente "1" -- "0..*" Asignacion
Asignacion "*" -- "1" Taller
Asignacion "*" -- "0..1" Usuario : técnico
Asignacion "1" -- "0..*" HistorialEstadoAsignacion
Asignacion "1" -- "0..*" UbicacionTecnico

Incidente "1" -- "0..*" Cotizacion
Cotizacion "*" -- "1" Taller
Cotizacion "*" -- "1" EstadoCotizacion

Incidente "1" -- "0..*" Evidencia
Incidente "1" -- "0..*" Mensaje
Incidente "1" -- "0..*" Notificacion
Incidente "1" -- "0..*" Pago
Incidente "1" -- "0..1" Evaluacion

note bottom of Tenant
  Toda tabla "tenant-scoped" lleva id_tenant.
  Filtro global SQLAlchemy lo aplica automáticamente.
end note

@enduml
```

---

## 2. Secuencia: Emergencia con broadcast first-accept-wins

`guias2/uml/02_secuencia_emergencia_broadcast.puml`:

```plantuml
@startuml
!theme plain
title Secuencia — Emergencia con broadcast first-accept-wins

actor "Cliente\n(Flutter)" as Cliente
participant "API\n/incidentes" as API
participant "MatchingService" as Match
participant "BroadcastService" as Bcast
queue "Redis Pub/Sub" as Redis
participant "WS Manager\n(worker N)" as WS
actor "Taller A" as TallerA
actor "Taller B" as TallerB
actor "Taller C" as TallerC

Cliente -> API : POST /incidentes\n(descripcion, lat, lng)
activate API
API -> API : Clasificar con IA\n(categoria, prioridad)
API -> Match : buscar_compatibles(categoria, radio)
Match --> API : [TallerA, TallerB, TallerC]
API -> API : Crear Incidente\nCrear 3 CandidatoAsignacion
API -> Bcast : broadcast_emergencia(inc, [A,B,C])
Bcast -> Redis : publish "taller:A" { incidente.nuevo }
Bcast -> Redis : publish "taller:B" { incidente.nuevo }
Bcast -> Redis : publish "taller:C" { incidente.nuevo }
API --> Cliente : 201 Created\n(id_incidente)
deactivate API

Redis -> WS : message {taller:A}
WS -> TallerA : ws.send_json(incidente.nuevo)
Redis -> WS : message {taller:B}
WS -> TallerB : ws.send_json(incidente.nuevo)
Redis -> WS : message {taller:C}
WS -> TallerC : ws.send_json(incidente.nuevo)

note over TallerA, TallerC : Los 3 ven la emergencia\nen tiempo real

TallerA -> API : POST /incidentes/{id}/aceptar
activate API
API -> API : SELECT ... FOR UPDATE\n(lock pesimista)
API -> API : Crear Asignacion(taller=A)\nMarcar CandidatoA.seleccionado=true
API -> Bcast : broadcast_incidente_tomado(inc, A, [B,C])
Bcast -> Redis : publish "taller:B" { incidente.tomado }
Bcast -> Redis : publish "taller:C" { incidente.tomado }
Bcast -> Redis : publish "usuario:cliente" { incidente.asignado }
API --> TallerA : 200 OK\n(id_asignacion)
deactivate API

Redis -> WS : forward eventos
WS -> TallerB : ws.send_json(incidente.tomado)
WS -> TallerC : ws.send_json(incidente.tomado)
WS -> Cliente : ws.send_json(incidente.asignado)

note over TallerB, TallerC : UI marca "tomada"\nbotón desactivado

TallerB -> API : POST /incidentes/{id}/aceptar
activate API
API -> API : SELECT ... FOR UPDATE
API -> API : Asignacion ya existe -> 409
API --> TallerB : 409 Conflict
deactivate API

@enduml
```

---

## 3. Secuencia: Cotización comparativa

`guias2/uml/03_secuencia_cotizacion.puml`:

```plantuml
@startuml
!theme plain
title Secuencia — Cotización (≥2 talleres comparativos)

actor Cliente
participant API
participant "CotizacionService" as Svc
database BD
actor "Taller A" as TA
actor "Taller B" as TB
actor "Taller C" as TC

Cliente -> API : POST /incidentes/{id}/cotizaciones/solicitar\n{radio_km, max_talleres=3}
API -> Svc : solicitar(incidente, max=3, validez=2h)
Svc -> Svc : Verificar categoria.requiere_cotizacion=true
Svc -> Svc : Buscar 3 talleres compatibles
Svc -> BD : INSERT 3 Cotizaciones (estado=pendiente)
Svc --> API : [cot_A, cot_B, cot_C]
API --> Cliente : 201 { invitadas: 3 }

== Talleres reciben notificación ==
TA <- API : (push o WS) tienes cotización pendiente
TB <- API : (push o WS) tienes cotización pendiente
TC <- API : (push o WS) tienes cotización pendiente

== Cada taller responde por su cuenta ==
TA -> API : POST /cotizaciones/{idA}/responder\n{monto=200, garantia=30}
API -> Svc : responder(cot_A, ...)
Svc -> BD : UPDATE cot_A (estado=enviada)
API --> TA : 200

TB -> API : POST /cotizaciones/{idB}/responder\n{monto=350, garantia=60}
TC -> API : POST /cotizaciones/{idC}/responder\n{monto=300, garantia=45}

== Cliente compara ==
Cliente -> API : GET /incidentes/{id}/cotizaciones
API --> Cliente : [{monto:200,...}, {monto:350,...}, {monto:300,...}]

note right of Cliente
  Pantalla comparativa:
  ordenar por precio,
  ver garantía + rating
end note

Cliente -> API : POST /cotizaciones/{idA}/aceptar
API -> Svc : aceptar(cot_A, usuario)
Svc -> BD : UPDATE cot_A (estado=aceptada)
Svc -> BD : UPDATE cot_B, cot_C (estado=rechazada)
Svc -> BD : INSERT Asignacion(taller=A, costo=200)
API --> Cliente : 200 { id_asignacion }

@enduml
```

---

## 4. Secuencia: Tracking GPS + geofencing

`guias2/uml/04_secuencia_tracking.puml`:

```plantuml
@startuml
!theme plain
title Secuencia — Tracking GPS en vivo + geofencing

actor "Técnico\n(Flutter)" as Tec
participant API
participant "TrackingService" as TS
queue "Redis Pub/Sub" as Redis
participant WS
actor "Cliente\n(Flutter)" as Cli
database BD

== Técnico inicia viaje ==
Tec -> API : POST /asignaciones/{id}/iniciar-viaje
API -> BD : Asignacion.estado = "en_camino"
API --> Tec : 200

Tec -> Tec : LocationSender.start()\n(cada 12 segundos)

loop cada 12s
    Tec -> Tec : Geolocator.getCurrentPosition()
    Tec -> API : POST /tecnicos/me/ubicacion\n{lat, lng, id_asignacion}
    API -> BD : INSERT UbicacionTecnico
    API -> TS : calcular_eta(tecnico_lat/lng, incidente_lat/lng)
    TS -> TS : OSRM público o Haversine fallback
    TS --> API : {distancia_km, eta_segundos}
    API -> Redis : publish "incidente:{id}" { tecnico.posicion, eta }
    Redis -> WS : forward
    WS -> Cli : ws.send_json(tecnico.posicion + eta)
    Cli -> Cli : mover marker en mapa\nactualizar "ETA: X min"
    API -> TS : llego_geofence(tecnico, incidente)?
    alt distancia ≤ 100m
        API -> BD : Asignacion.estado = "llegado"
        API -> BD : INSERT HistorialEstadoAsignacion
        API -> Redis : publish "incidente:{id}" { asignacion.llegado }
        Redis -> WS : forward
        WS -> Cli : ws.send_json(asignacion.llegado)
        Cli -> Cli : Mostrar dialog "Técnico llegó"
    end
    API --> Tec : 200 { eta, llegado_auto }
end

@enduml
```

---

## 5. Secuencia: Cancelación con compensación

`guias2/uml/05_secuencia_cancelacion.puml`:

```plantuml
@startuml
!theme plain
title Secuencia — Cancelación con compensación al taller

actor Cliente
participant API
participant "CancelacionService" as CS
database BD
actor Taller

note over Cliente : El cliente ya tiene una asignación\nen estado "en_camino"

Cliente -> API : POST /asignaciones/{id}/cancelar\n{motivo: "Llegó mi seguro"}
API -> CS : cancelar(asig, usuario, motivo)
CS -> CS : Validar dueño (usuario.id == incidente.id_usuario)
CS -> CS : Validar estado ≠ completada,cancelada
CS -> CS : factor según estado:\npendiente=0%\naceptada=50%\nen_camino/llegado=100%
CS -> CS : compensacion = taller.tarifa_traslado * factor
CS -> BD : INSERT HistorialEstadoAsignacion
CS -> BD : UPDATE Asignacion\n(estado=cancelada,\ncompensacion_monto,\nmotivo)
alt compensacion > 0
    CS -> BD : INSERT Pago\n(referencia=compensacion-cancelacion-N)
end
CS -> BD : COMMIT
CS --> API : (asignacion, "cancelada")
API --> Cliente : 200 { compensacion_monto: 20.0, nuevo_estado: "cancelada" }

note over Taller : Push / WS le notifica
Taller -> API : GET /asignaciones (lista)
API --> Taller : ... { cancelada, compensacion_pagada=false, monto=20 }
note right of Taller : Taller ve compensación pendiente\nen su panel

@enduml
```

---

## 6. Diagrama de despliegue

`guias2/uml/06_despliegue.puml`:

```plantuml
@startuml
!theme plain
title Diagrama de Despliegue — Yary

node "Cliente móvil" #LightYellow {
    component "Flutter App\n(cliente + técnico)" as Flutter
    database "SQLite local\n(offline cache)" as SQLite
    Flutter -- SQLite
}

node "Cliente web" #LightYellow {
    component "Angular SPA\n(taller/admin)" as Angular
    component "Service Worker\n(PWA)" as SW
    database "IndexedDB\n(offline cache)" as IDB
    Angular -- SW
    Angular -- IDB
}

cloud "Backend AWS / VPS" {
    node "API Server" {
        component "FastAPI\n(N workers uvicorn)" as API
        component "Alembic migrations" as Alembic
    }
    database "PostgreSQL\n(shared-schema multi-tenant)" as PG
    database "Redis\n(pub/sub + cache)" as Redis
    component "Cloudinary\n(evidencias media)" as Cloudinary
}

cloud "Servicios externos" {
    component "Google Gemini\n(IA clasificación)" as Gemini
    component "OSRM público\n(rutas/ETA)" as OSRM
    component "Firebase FCM\n(push)" as FCM
    component "Stripe\n(pagos)" as Stripe
}

Flutter --> API : HTTPS (REST)
Flutter ..> API : WebSocket
Angular --> API : HTTPS (REST)
Angular ..> API : WebSocket

API --> PG : SQLAlchemy
API --> Redis : pub/sub + cache
API --> Cloudinary : upload evidencias
API --> Gemini : clasificación IA
API --> OSRM : routing/ETA
API --> FCM : push notifications
API --> Stripe : pagos / compensaciones
Alembic --> PG : schema versioning

note bottom of API
  Middleware multi-tenant:
  extrae id_tenant del JWT,
  filtro global ORM aplica
  WHERE id_tenant=? automáticamente
end note

note right of Redis
  Si Redis cae:
  - WebSocket degrada a single-worker
  - Cache IA off
  - Sistema sigue vivo
end note

@enduml
```

---

## Cómo renderizar

### Opción 1 — VSCode

1. Instalar extension "PlantUML" (jebbs).
2. Abrir un `.puml`.
3. `Alt+D` para previsualizar.
4. `Ctrl+Shift+P` → "PlantUML: Export Current Diagram" → PNG/SVG.

### Opción 2 — CLI

```bash
# Requiere Java + plantuml.jar (descargar de plantuml.com)
java -jar plantuml.jar guias2/uml/*.puml -o exports/
```

### Opción 3 — Online

[plantuml.com/plantuml](https://www.plantuml.com/plantuml/uml/) — pegar el código, copiar la URL del PNG.

---

## Inclusión en el documento final

Si entregas un PDF/Word:
- Renderizar todos como PNG (300dpi para impresión).
- Insertar en el marco teórico como Figura 1, 2, 3...
- Captions:
  - **Figura 1**: Diagrama de clases consolidado de Yary (post Ciclo 2).
  - **Figura 2**: Secuencia del flujo de emergencia con broadcast.
  - **Figura 3**: Secuencia del flujo de cotización comparativa.
  - **Figura 4**: Secuencia del tracking GPS en vivo con geofencing.
  - **Figura 5**: Secuencia de cancelación con compensación.
  - **Figura 6**: Diagrama de despliegue del sistema.

---

## Checklist de cierre D2
- [ ] Carpeta `guias2/uml/` con los 6 archivos `.puml`.
- [ ] Cada uno renderiza sin errores.
- [ ] PNGs exportados a `guias2/uml/exports/`.
- [ ] Insertados en el marco teórico con captions.
- [ ] Diagrama de clases incluye las **9 entidades nuevas** introducidas (Tenant, Plan, Suscripcion, TenantUser, Cotizacion, EstadoCotizacion, UbicacionTecnico + las dos extensiones de Asignación y Taller).

## Notas
- **Si tu universidad exige diagrama BPMN o DFD**: pedir antes de la defensa, los formatos cambian por carrera. PlantUML también soporta secuencias y actividad.
- **Diagrama de despliegue**: es el que más impresiona en defensa porque muestra todas las piezas movidas. No lo omitas.
- **Mantener actualizado**: cada migración nueva debería actualizar el diagrama de clases. Recordatorio para futuro.
