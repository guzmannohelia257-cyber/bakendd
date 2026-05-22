# Handoff — Continuación del Backend Yary (Bloques A, B, C)

Esta guía es para que **otro modelo / desarrollador** retome el proyecto sin rehacer el trabajo de entender el código. Léela en orden.

---

## 0. Contexto técnico

**Stack:**
- FastAPI + SQLAlchemy 2.0 ORM + Pydantic v2
- PostgreSQL (local `postgresql://postgres:12345678@localhost:5432/emergencias_vehiculares`)
- Argon2 para hashing de passwords (`argon2-cffi`)
- JWT con `python-jose`
- Google Gemini 2.5 Pro (multimodal: texto + imagen + audio) vía `google-genai`
- Cloudinary para almacenar evidencias
- Lanzamiento: `uvicorn app.main:app --reload`
- Docs Swagger: `http://localhost:8000/docs`

**Estructura:**
```
app/
  api/         # routers (users, talleres, vehiculos, incidencias, evidencias, diagnostico)
  models/      # ORM (catalogos, usuario, taller, incidente, transaccional)
  schemas/     # Pydantic (user_schema, taller_schema, incidente_schema, vehiculo_schema, evidencia_schema)
  services/    # asignacion (motor), ia_service (Gemini), cloudinary_service
  core/        # config, security (JWT + Argon2 + dependencies)
  db/          # session (engine + SessionLocal + Base + get_db)
  guias/       # documentación interna (.md, schema_postgresql.sql, este archivo)
```

**Entry point:** `app/main.py` — registra routers, monta CORS, crea tablas con `Base.metadata.create_all` (NO hay Alembic).

---

## 1. Convenciones del código (OBLIGATORIO respetarlas)

### 1.1 Claim JWT `tipo` — ¡CUIDADO!

El claim se llama `tipo` y sus valores son `"usuario"` y `"taller"` (NO `"cliente"`). Ver `app/core/security.py:61,115,151`. Cualquier endpoint nuevo debe reusar `get_current_user` (para clientes/admins) o `get_current_taller` (para talleres). **No inventar dependencias nuevas.**

```python
from app.core.security import get_current_user, get_current_taller
```

### 1.2 Tablas de catálogos — lookup por nombre, nunca por ID

El seed de catálogos puede cambiar entre instalaciones. En producción el `id_estado_asignacion` de "aceptada" podría ser 2, 5 o cualquier otro. **Siempre busca por `nombre`:**

```python
estado_aceptada = db.query(EstadoAsignacion).filter_by(nombre="aceptada").first()
if not estado_aceptada:
    raise HTTPException(500, "Catálogo estado 'aceptada' no existe")
asignacion.id_estado_asignacion = estado_aceptada.id_estado_asignacion
```

**Excepción documentada:** `asignacion.py:59,79` usa IDs hardcoded `[1,2,3]` para estados activos. **Esto es un bug latente** que debe corregirse (ver sección 6).

### 1.3 Patrón Pydantic v2

Todos los schemas de respuesta usan `class Config: from_attributes = True` para permitir que SQLAlchemy objects se serialicen directamente. No uses `orm_mode` (es Pydantic v1).

### 1.4 Seguridad del endpoint

Patrón estándar (copiado del código existente):

```python
@router.get("/algo/{id}")
def endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    entidad = db.query(Modelo).filter(
        Modelo.id == id,
        Modelo.id_usuario == current_user.id_usuario,  # SIEMPRE filtrar por ownership
    ).first()
    if not entidad:
        raise HTTPException(404, "No encontrado o no te pertenece")
    ...
```

El `id_usuario` viene SIEMPRE del token, nunca del body o query param. Ver `incidencias.py:171` como ejemplo canónico.

### 1.5 Swagger auth

El `oauth2_scheme.tokenUrl = "/usuarios/login"` (`security.py:27`). En Swagger, el botón "Authorize" por defecto apunta ahí, pero un token de taller (`POST /talleres/login`) también funciona — el `tipo` del claim decide qué endpoints se pueden consumir.

---

## 2. Estado real de cada Caso de Uso

Tabla exhaustiva. ✅ = terminado, 🟡 = parcial/con gaps, ❌ = no implementado.

| CU | Descripción | Estado | Archivo(s) |
|---|---|---|---|
| CU-01 | Registrarse cliente | ✅ | `POST /usuarios/registro` → `api/users.py:41` |
| CU-02 | Sesión (login) | ✅ | `POST /usuarios/login` + `POST /talleres/login` |
| CU-03 | Perfil personal | ✅ | `GET/PUT/DELETE /usuarios/perfil` → `api/users.py:188-323` |
| CU-04 | Vehículos | ✅ | CRUD completo en `api/vehiculos.py` |
| CU-05 | Reportar emergencia | ✅ | `POST /incidencias/` → `api/incidencias.py:126` |
| CU-06 | Evidencias | ✅ | `POST /incidencias/{id}/evidencias` → `api/evidencias.py:46` |
| CU-07 | Pago del servicio | ❌ | — |
| CU-08 | Seguimiento solicitud | ✅ | `GET /incidencias/{id}` devuelve `IncidenteDetalle` con `asignaciones[]` |
| CU-09 | Comunicación con taller (chat) | ❌ | — |
| CU-10 | Evaluar servicio | ✅ | `POST /incidencias/{id}/evaluar` + `GET /mi-taller/evaluaciones` |
| CU-11 | Solicitudes pendientes (cliente) | ✅ | `GET /incidencias/mis-incidencias` |
| CU-12 | Historial incidentes (cliente) | ✅ | `GET /incidencias/mis-incidencias?estado=&desde=&hasta=` con filtros |
| CU-13 | Registro taller | ❌ | Los talleres se crean por seed; no hay endpoint público |
| CU-14 | Perfil del taller | ✅ | `GET/PUT /talleres/mi-taller` → `api/talleres.py:84,89` |
| CU-15 | Servicios ofrecidos (taller) | ❌ | Tabla `taller_servicio` existe pero sin endpoints CRUD |
| CU-16 | Gestionar técnicos | ✅ | CRUD en `api/talleres.py:106-208` |
| CU-17 | Disponibilidad del taller | ✅ | `PUT /mi-taller/disponibilidad` + filtro en motor |
| CU-18 | Solicitudes de asistencia (taller) | ✅ | Listar/aceptar/rechazar en `api/talleres.py:297-399` |
| CU-19 | Asignar técnico | ✅ | `id_tecnico` opcional en `/aceptar` con validación anti-doble-asignación |
| CU-20 | Estado del servicio (en_camino, completada) | ✅ | `PUT /mi-taller/asignaciones/{id}/iniciar-viaje` y `/completar` implementados |
| CU-21 | Comunicación con cliente (chat) | ❌ | Junto con CU-09 |
| CU-22 | Historial atenciones (taller) | ✅ | `GET /mi-taller/asignaciones?estado=&desde=&hasta=` con filtros |
| CU-23 | Reportes desempeño | ❌ | — |
| CU-24 | Pagos y comisiones | ❌ | — |
| CU-25 | Procesar audio | ✅ | Gemini recibe audio directo (`ia_service.py:181-186`) |
| CU-26 | Clasificar incidente | ✅ | `ia_service.py:120` |
| CU-27 | Gestionar prioridad | ✅ | La IA asigna prioridad con reglas de contexto (prompt líneas 49-75) |
| CU-28 | Generar ficha resumen | ✅ | `resumen_ia` en el incidente |
| CU-29 | Casos ambiguos | ⚪ | **Descartado por diseño** — no hay admin. El flag `requiere_revision_manual` se mantiene solo como señal informativa para la UI; el motor siempre corre |
| CU-30 | Motor de asignación | ✅ | `services/asignacion.py` — Haversine + scoring |
| CU-31 | Reasignación automática | ✅ | Al rechazar, el endpoint busca siguiente candidato y crea nueva asignación |
| CU-32 | Push notifications | ❌ | `Taller.push_token` existe pero no se usa; los clientes no tienen columna |
| CU-33 | Trazabilidad | ✅ | `services/trazabilidad.py` + integrado en motor, `/aceptar`, `/rechazar`, `/iniciar-viaje`, `/completar` |
| CU-34 | Métricas de cierre | ❌ | — |
| CU-35-39 | Admin panel | ❌ | — |

---

## 3. Decisiones de diseño ya tomadas (NO cambiar)

1. **Técnicos NO tienen especialidades.** Explícitamente descartado por el usuario — "muchos mecánicos no son estudiados". El motor ya filtra talleres por `taller_servicio.id_categoria`, así que si el trabajo llegó al taller cualquier técnico puede tomarlo.
2. **Un técnico = máximo una asignación activa** (estados pendiente/aceptada/en_camino). Helper `validar_tecnico_disponible()` en `services/asignacion.py:89`.
3. **`id_tecnico` es opcional al `/aceptar`.** Hoy solo se puede asignar técnico mientras la asignación esté en `pendiente`. Si quieres reasignar técnico después, hay que crear endpoint nuevo (no existe).
4. **Técnicos NO tienen login.** Son subentidades del taller. Sus vistas se sirven bajo `/talleres/mi-taller/tecnicos/{id}/...` con token de taller.
5. **El motor se dispara dentro de `clasificar_incidente`.** No lo llames por separado desde endpoints — ya está encadenado (`ia_service.py:242`).
6. **`CandidatoAsignacion.seleccionado`** marca al taller elegido. Cambiar-taller (`incidencias.py:247`) lo manipula. Al rechazar, el taller rechazante se marca `seleccionado=False` (`talleres.py:391-395`).
7. **Baja lógica siempre**, nunca DELETE físico. Todas las entidades tienen `activo: bool`.
8. **Estado inicial de un incidente = `id_estado=1`** (se usa ID hardcoded en `incidencias.py:173`). No ideal, pero hay que dejarlo así o hacer refactor consistente en todos lados.

---

## 4. Datos que ya tienes y que podrían sorprenderte

### 4.1 Columnas útiles ya existentes (no las vuelvas a agregar)

| Tabla | Columna | Uso previsto |
|---|---|---|
| `incidente` | `requiere_revision_manual` | Flag para CU-29 (casos ambiguos) |
| `incidente` | `resumen_ia`, `clasificacion_ia_confianza` | Ficha IA |
| `asignacion` | `costo_estimado NUMERIC(10,2)` | Úsalo para el costo final, NO agregues `costo_final` |
| `asignacion` | `eta_minutos`, `nota_taller` | Ya se llenan en `/aceptar` |
| `taller` | `push_token` | Base para CU-32 (empezar con esta columna antes de migrar a tabla multi-device) |
| `tecnico` | `disponible`, `latitud`, `longitud` | Toggle operativo y GPS del técnico |
| `candidato_asignacion` | `motivo_rechazo` | Para dejar rastro de rechazos específicos |

### 4.2 Tablas de historial YA CREADAS (críticas para CU-33)

**No crees tablas nuevas de eventos**, ya existen:

```python
# app/models/incidente.py:83
class HistorialEstadoIncidente(Base):
    __tablename__ = "historial_estado_incidente"
    id_historial, id_incidente, id_estado_anterior, id_estado_nuevo, observacion, created_at

# app/models/incidente.py:99
class HistorialEstadoAsignacion(Base):
    __tablename__ = "historial_estado_asignacion"
    id_historial, id_asignacion, id_estado_anterior, id_estado_nuevo, observacion, created_at
```

Y los relationships `incidente.historiales` y `asignacion.historiales` ya están mapeados. **Úsalos.**

### 4.3 Credenciales de seed

Correr: `python seed_usuarios_temp.py` (limpia tablas y crea catálogos + usuarios).
Luego: `python seed_estados_prueba.py` (crea incidentes en los 5 estados para demo).

| Rol | Email | Password | Endpoint de login |
|---|---|---|---|
| Cliente | `conductor@ejemplo.com` | `cliente123!` | `POST /usuarios/login` |
| Admin | `admin@plataforma.com` | `admin123!` | `POST /usuarios/login` |
| Taller | `gerente@tallerexcelente.com` | `taller123!` | `POST /talleres/login` |

---

## 5. BLOQUE A — Cerrar el ciclo de vida del incidente

**Por qué es lo primero:** sin esto una emergencia nunca "termina" en el sistema. Todo lo demás (historial, evaluación, pagos, métricas) depende de tener un incidente cerrable.

---

### A.1 — CU-33: Trazabilidad (hacer PRIMERO)

**Por qué primero:** las transiciones de A.2, A.3, B.1 deben escribir historial. Si haces trazabilidad al final, tendrás que volver a tocar cada endpoint.

**Archivos:**
- Crear: `app/services/trazabilidad.py`

**Código completo a crear:**

```python
# app/services/trazabilidad.py
"""
Escribe en historial_estado_asignacion y historial_estado_incidente
cada vez que un estado cambia. CU-33.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.incidente import (
    Asignacion, Incidente,
    HistorialEstadoAsignacion, HistorialEstadoIncidente,
)
from app.models.catalogos import EstadoAsignacion, EstadoIncidente


def registrar_cambio_estado_asignacion(
    db: Session,
    asignacion: Asignacion,
    id_estado_anterior: Optional[int],
    id_estado_nuevo: int,
    observacion: Optional[str] = None,
) -> None:
    """Llamar DESPUÉS de mutar asignacion.id_estado_asignacion pero ANTES del commit final."""
    evento = HistorialEstadoAsignacion(
        id_asignacion=asignacion.id_asignacion,
        id_estado_anterior=id_estado_anterior,
        id_estado_nuevo=id_estado_nuevo,
        observacion=observacion,
    )
    db.add(evento)


def registrar_cambio_estado_incidente(
    db: Session,
    incidente: Incidente,
    id_estado_anterior: Optional[int],
    id_estado_nuevo: int,
    observacion: Optional[str] = None,
) -> None:
    evento = HistorialEstadoIncidente(
        id_incidente=incidente.id_incidente,
        id_estado_anterior=id_estado_anterior,
        id_estado_nuevo=id_estado_nuevo,
        observacion=observacion,
    )
    db.add(evento)


def cambiar_estado_asignacion(
    db: Session,
    asignacion: Asignacion,
    nombre_estado_nuevo: str,
    observacion: Optional[str] = None,
) -> EstadoAsignacion:
    """
    Helper todo-en-uno: busca el nuevo estado por nombre, escribe historial,
    actualiza la asignación. NO hace commit — el caller decide cuándo.
    """
    nuevo = db.query(EstadoAsignacion).filter_by(nombre=nombre_estado_nuevo).first()
    if not nuevo:
        raise ValueError(f"Catálogo estado_asignacion '{nombre_estado_nuevo}' no existe")

    id_anterior = asignacion.id_estado_asignacion
    registrar_cambio_estado_asignacion(db, asignacion, id_anterior, nuevo.id_estado_asignacion, observacion)
    asignacion.id_estado_asignacion = nuevo.id_estado_asignacion
    return nuevo


def cambiar_estado_incidente(
    db: Session,
    incidente: Incidente,
    nombre_estado_nuevo: str,
    observacion: Optional[str] = None,
) -> EstadoIncidente:
    nuevo = db.query(EstadoIncidente).filter_by(nombre=nombre_estado_nuevo).first()
    if not nuevo:
        raise ValueError(f"Catálogo estado_incidente '{nombre_estado_nuevo}' no existe")

    id_anterior = incidente.id_estado
    registrar_cambio_estado_incidente(db, incidente, id_anterior, nuevo.id_estado, observacion)
    incidente.id_estado = nuevo.id_estado
    return nuevo
```

**Después, refactorear endpoints existentes para usarlos:**

- `api/talleres.py:aceptar_asignacion` → reemplazar la lógica que cambia `id_estado_asignacion` por `cambiar_estado_asignacion(db, asignacion, "aceptada", observacion=payload.nota)`.
- Lo mismo en `rechazar_asignacion` con observacion=payload.motivo.
- En `services/asignacion.py:buscar_y_asignar`, después de crear la `Asignacion`, registrar con observación `"Motor de asignación — score X"`.

**Endpoints nuevos para consultar historial** (opcional pero útil para debug):

```python
# api/incidencias.py
@router.get("/{id_incidente}/eventos", summary="Historial de cambios del incidente")
def eventos_incidente(id_incidente: int, db=Depends(get_db), current_user=Depends(get_current_user)):
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()
    if not incidente:
        raise HTTPException(404, "No encontrado")
    return incidente.historiales  # ya mapeado en el modelo
```

---

### A.2 — CU-20: Transiciones `en_camino` y `completada`

**Archivos a tocar:**
- `app/schemas/taller_schema.py` — agregar schemas
- `app/api/talleres.py` — agregar endpoints

**Schemas nuevos (al final del archivo, antes de `MensajeResponse`):**

```python
class IniciarViajeRequest(BaseModel):
    """Opcional: el técnico puede mandar su ubicación al salir."""
    latitud_tecnico: Optional[float] = None
    longitud_tecnico: Optional[float] = None


class CompletarAsignacionRequest(BaseModel):
    resumen_trabajo: Optional[str] = Field(None, max_length=1000,
        description="Descripción del trabajo realizado")
    costo_estimado: Optional[float] = Field(None, ge=0,
        description="Costo final acordado (se guarda en asignacion.costo_estimado)")
```

**Endpoints nuevos en `api/talleres.py`** (después de `/rechazar`, línea ~399):

```python
from app.services.trazabilidad import cambiar_estado_asignacion, cambiar_estado_incidente


@router.put(
    "/mi-taller/asignaciones/{id_asignacion}/iniciar-viaje",
    response_model=AsignacionTallerResponse,
    summary="Técnico sale hacia el cliente (aceptada → en_camino)",
)
def iniciar_viaje(
    id_asignacion: int,
    payload: IniciarViajeRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    asignacion = _get_asignacion_del_taller(db, current_taller.id_taller, id_asignacion)

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if not estado_actual or estado_actual.nombre != "aceptada":
        raise HTTPException(400,
            f"La asignación está en '{estado_actual.nombre if estado_actual else '?'}', "
            f"solo se puede iniciar viaje desde 'aceptada'")

    if asignacion.id_tecnico is None:
        raise HTTPException(400, "Debes asignar un técnico antes de iniciar viaje")

    # Actualizar GPS del técnico si se mandó
    if payload.latitud_tecnico is not None and payload.longitud_tecnico is not None:
        tecnico = db.get(Tecnico, asignacion.id_tecnico)
        if tecnico:
            tecnico.latitud = payload.latitud_tecnico
            tecnico.longitud = payload.longitud_tecnico

    cambiar_estado_asignacion(db, asignacion, "en_camino", observacion="Técnico en camino")

    # Sincronizar estado del incidente
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        estado_inc_actual = db.get(EstadoIncidente, incidente.id_estado)
        if estado_inc_actual and estado_inc_actual.nombre == "pendiente":
            cambiar_estado_incidente(db, incidente, "en_proceso",
                observacion=f"Taller {current_taller.id_taller} en camino")

    db.commit()
    db.refresh(asignacion)
    return asignacion


@router.put(
    "/mi-taller/asignaciones/{id_asignacion}/completar",
    response_model=AsignacionTallerResponse,
    summary="Servicio completado (en_camino → completada)",
)
def completar_asignacion(
    id_asignacion: int,
    payload: CompletarAsignacionRequest,
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    asignacion = _get_asignacion_del_taller(db, current_taller.id_taller, id_asignacion)

    estado_actual = db.get(EstadoAsignacion, asignacion.id_estado_asignacion)
    if not estado_actual or estado_actual.nombre != "en_camino":
        raise HTTPException(400,
            f"La asignación está en '{estado_actual.nombre if estado_actual else '?'}', "
            f"solo se puede completar desde 'en_camino'")

    if payload.costo_estimado is not None:
        asignacion.costo_estimado = payload.costo_estimado
    if payload.resumen_trabajo is not None:
        # resumen_trabajo no tiene columna propia; lo append-eamos a nota_taller
        prev = asignacion.nota_taller or ""
        asignacion.nota_taller = f"{prev}\n[TRABAJO] {payload.resumen_trabajo}".strip()

    cambiar_estado_asignacion(db, asignacion, "completada",
        observacion=payload.resumen_trabajo or "Servicio completado")

    # Cerrar el incidente
    incidente = db.get(Incidente, asignacion.id_incidente)
    if incidente:
        cambiar_estado_incidente(db, incidente, "atendido",
            observacion=f"Taller {current_taller.id_taller} completó el servicio")

    db.commit()
    db.refresh(asignacion)
    return asignacion
```

Importar `Tecnico`, `Incidente`, `EstadoIncidente` arriba del archivo.

**Nota:** si decides agregar columna `resumen_trabajo` propia a `asignacion`, puedes `ALTER TABLE asignacion ADD COLUMN resumen_trabajo TEXT` y luego mapearla en el modelo. Pero para MVP, concatenar a `nota_taller` es suficiente.

---

### A.3 — CU-10: Evaluar servicio

**Tabla nueva en BD** (ejecutar manualmente por ahora, luego añadir a `schema_postgresql.sql`):

```sql
CREATE TABLE IF NOT EXISTS evaluacion (
  id_evaluacion SERIAL PRIMARY KEY,
  id_incidente INT UNIQUE NOT NULL REFERENCES incidente(id_incidente),
  id_usuario   INT NOT NULL REFERENCES usuario(id_usuario),
  id_taller    INT NOT NULL REFERENCES taller(id_taller),
  id_tecnico   INT NULL REFERENCES tecnico(id_tecnico),
  estrellas    SMALLINT NOT NULL CHECK (estrellas BETWEEN 1 AND 5),
  comentario   TEXT,
  created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Modelo nuevo en `app/models/incidente.py`** (al final):

```python
class Evaluacion(Base):
    __tablename__ = "evaluacion"

    id_evaluacion = Column(Integer, primary_key=True, index=True)
    id_incidente = Column(Integer, ForeignKey("incidente.id_incidente"), unique=True, nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False)
    id_tecnico = Column(Integer, ForeignKey("tecnico.id_tecnico"), nullable=True)
    estrellas = Column(Integer, nullable=False)
    comentario = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    incidente = relationship("Incidente")
    usuario = relationship("Usuario")
    taller = relationship("Taller")
    tecnico = relationship("Tecnico")
```

Importarlo en `app/models/__init__.py` para que `Base.metadata.create_all` lo tome en cuenta.

**Schema en `app/schemas/incidente_schema.py`:**

```python
class EvaluacionCreate(BaseModel):
    estrellas: int = Field(..., ge=1, le=5)
    comentario: Optional[str] = Field(None, max_length=500)


class EvaluacionResponse(BaseModel):
    id_evaluacion: int
    id_incidente: int
    id_taller: int
    id_tecnico: Optional[int] = None
    estrellas: int
    comentario: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
```

**Endpoint en `api/incidencias.py`:**

```python
from app.models.incidente import Evaluacion
from app.schemas.incidente_schema import EvaluacionCreate, EvaluacionResponse


@router.post(
    "/{id_incidente}/evaluar",
    response_model=EvaluacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluar el servicio recibido",
)
def evaluar_servicio(
    id_incidente: int,
    payload: EvaluacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    incidente = db.query(Incidente).filter(
        Incidente.id_incidente == id_incidente,
        Incidente.id_usuario == current_user.id_usuario,
    ).first()
    if not incidente:
        raise HTTPException(404, "Incidencia no encontrada o no te pertenece")

    estado = db.get(EstadoIncidente, incidente.id_estado)
    if not estado or estado.nombre != "atendido":
        raise HTTPException(400, "Solo puedes evaluar incidentes atendidos")

    existente = db.query(Evaluacion).filter_by(id_incidente=id_incidente).first()
    if existente:
        raise HTTPException(409, "Ya evaluaste este servicio")

    asignacion_completada = db.query(Asignacion).filter(
        Asignacion.id_incidente == id_incidente,
    ).join(EstadoAsignacion).filter(
        EstadoAsignacion.nombre == "completada",
    ).first()
    if not asignacion_completada:
        raise HTTPException(400, "No hay asignación completada para este incidente")

    evaluacion = Evaluacion(
        id_incidente=id_incidente,
        id_usuario=current_user.id_usuario,
        id_taller=asignacion_completada.id_taller,
        id_tecnico=asignacion_completada.id_tecnico,
        estrellas=payload.estrellas,
        comentario=payload.comentario,
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion
```

**Endpoint para que el taller vea sus reviews** (en `api/talleres.py`):

```python
@router.get(
    "/mi-taller/evaluaciones",
    response_model=List[EvaluacionResponse],
    summary="Reseñas recibidas",
)
def mis_evaluaciones(
    db: Session = Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    return db.query(Evaluacion).filter(
        Evaluacion.id_taller == current_taller.id_taller,
    ).order_by(Evaluacion.created_at.desc()).all()
```

**Opcional:** agregar `rating_promedio` a `TallerResponse` calculando `AVG(estrellas)` en el endpoint de perfil.

---

### A.4 — CU-12 / CU-22: Historial con filtros

**Ya existe:**
- `GET /incidencias/mis-incidencias` (cliente)
- `GET /talleres/mi-taller/asignaciones?estado=...` (taller)

**Extender (pequeña cirugía):** agregar query params `desde`, `hasta`, y filtro por estados terminales.

En `api/incidencias.py:listar_mis_incidencias`:

```python
from datetime import date
from fastapi import Query

@router.get("/mis-incidencias", response_model=List[IncidenteDetalle])
def listar_mis_incidencias(
    estado: Optional[str] = Query(None, description="nombre del estado: pendiente|en_proceso|atendido|cancelado"),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(Incidente).filter(Incidente.id_usuario == current_user.id_usuario)
    if estado:
        q = q.join(EstadoIncidente).filter(EstadoIncidente.nombre == estado)
    if desde:
        q = q.filter(Incidente.created_at >= desde)
    if hasta:
        q = q.filter(Incidente.created_at < hasta)
    return q.order_by(Incidente.created_at.desc()).all()
```

Mismo patrón en `api/talleres.py:listar_asignaciones`.

---

## 6. BLOQUE B — Robustez

### B.0 — Corrección previa indispensable

**Bug en `services/asignacion.py`:** las funciones `_contar_asignaciones_activas` (línea 54) y `_contar_asignaciones_activas_tecnico` (línea 69) usan `estados_activos = [1, 2, 3]` hardcoded, asumiendo que esos IDs son pendiente/aceptada/en_camino. Si el seed se corre diferente, esto rompe.

**Arreglar:**

```python
def _ids_estados_activos(db: Session) -> list[int]:
    estados = db.query(EstadoAsignacion).filter(
        EstadoAsignacion.nombre.in_(["pendiente", "aceptada", "en_camino"])
    ).all()
    return [e.id_estado_asignacion for e in estados]
```

Y usar `.in_(_ids_estados_activos(db))` en los dos contadores.

---

### B.1 — CU-31: Reasignación automática al rechazar

**Objetivo:** cuando un taller rechaza, pasar automáticamente al siguiente candidato en lugar de dejar al cliente elegir manualmente (aunque ese flujo manual se mantiene vía `cambiar-taller`).

**Archivo:** `api/talleres.py:rechazar_asignacion`.

**Lógica nueva (al final, antes del return):**

```python
from app.services.trazabilidad import registrar_cambio_estado_asignacion

# Ya desmarcamos el candidato actual. Buscar el siguiente.
# Excluir talleres que ya rechazaron este mismo incidente antes.
rechazos_previos = db.query(Asignacion.id_taller).join(EstadoAsignacion).filter(
    Asignacion.id_incidente == asignacion.id_incidente,
    EstadoAsignacion.nombre == "rechazada",
).all()
ids_rechazantes = {r[0] for r in rechazos_previos}

siguiente = db.query(CandidatoAsignacion).filter(
    CandidatoAsignacion.id_incidente == asignacion.id_incidente,
    ~CandidatoAsignacion.id_taller.in_(ids_rechazantes or [-1]),
).order_by(CandidatoAsignacion.score_total.desc()).first()

if siguiente:
    siguiente.seleccionado = True
    estado_pendiente = db.query(EstadoAsignacion).filter_by(nombre="pendiente").first()
    nueva_asignacion = Asignacion(
        id_incidente=asignacion.id_incidente,
        id_taller=siguiente.id_taller,
        id_estado_asignacion=estado_pendiente.id_estado_asignacion,
    )
    db.add(nueva_asignacion)
    db.flush()
    registrar_cambio_estado_asignacion(
        db, nueva_asignacion, None, estado_pendiente.id_estado_asignacion,
        observacion=f"Reasignación automática tras rechazo de taller {current_taller.id_taller}",
    )
    # TODO CU-32: enviar push al nuevo taller
else:
    # No quedan candidatos — opcionalmente cancelar el incidente
    # cambiar_estado_incidente(db, incidente, "cancelado", observacion="Sin talleres disponibles")
    pass

db.commit()
```

**Edge cases a considerar:**
- Si rechazan todos los candidatos → pasar el incidente a `cancelado` o dejar pendiente de reasignación manual.
- No reasignar a un taller que ya aceptó y luego algo salió mal (revisa antes).

---

### B.2 — CU-29: Casos ambiguos → **DESCARTADO POR DISEÑO**

**Decisión del usuario:** no habrá panel admin ni supervisión humana. El sistema debe operar de forma completamente automática.

**Implicancia:**
- El flag `incidente.requiere_revision_manual = confianza < 0.6` **se mantiene** y se sigue calculando en `ia_service.py:236`. Se expone en `IncidenteDetalle` para que la UI (Flutter/Angular) pueda mostrar un warning al usuario/taller ("⚠️ la IA no estaba segura de la clasificación").
- El motor **siempre corre**, incluso con baja confianza. La IA siempre devuelve una categoría y una prioridad (aunque sea la mejor aproximación), y el motor usa esa clasificación para buscar candidatos.
- Si no hay talleres que atiendan la categoría elegida, el motor retorna `{"error": "No hay talleres disponibles en el área"}` y el incidente queda sin asignar. El cliente puede:
  1. Reintentar `POST /incidencias/{id}/analizar-ia` (reanaliza y re-dispara motor).
  2. O usar `cambiar-taller` manualmente si hay algún candidato previo.

**NO implementar:**
- ❌ Endpoint `GET /admin/incidencias/revision-manual`
- ❌ Endpoint `PUT /admin/incidencias/{id}/clasificar-manual`
- ❌ Archivo `app/api/admin.py`
- ❌ Dependencia `require_admin`
- ❌ Bloqueo del motor cuando `requiere_revision_manual == True`

**Si en el futuro se necesita mejor manejo de casos ambiguos sin admin**, opciones posibles (NO hacer hasta que el usuario lo pida):
- Fallback automático: si el motor no encuentra candidatos en la categoría elegida, reintentar con categoría "otros" o "incierto" (ambas existen en el seed).
- Re-clasificación con `temperature=0` si `confianza < 0.4`.
- Ampliar radio de búsqueda (`RADIO_BUSQUEDA_KM`) cuando la confianza es baja.

---

### B.3 — CU-17: Disponibilidad del taller

**Objetivo:** toggle on/off rápido (pausa de almuerzo, saturación momentánea) sin tocar `activo` (que es baja lógica permanente).

**Paso 1 — Columna nueva:**
```sql
ALTER TABLE taller ADD COLUMN disponible BOOLEAN NOT NULL DEFAULT TRUE;
```

**Paso 2 — Modelo** (`app/models/taller.py`, dentro de la clase `Taller`):
```python
disponible = Column(Boolean, default=True, nullable=False)
```

**Paso 3 — Filtro en motor** (`app/services/asignacion.py:151`):
```python
talleres = db.query(Taller).filter(
    Taller.activo == True,
    Taller.verificado == True,
    Taller.disponible == True,   # <-- agregar
    Taller.latitud.isnot(None),
    Taller.longitud.isnot(None),
).all()
```

**Paso 4 — Endpoint** (`app/api/talleres.py`):
```python
class DisponibilidadUpdate(BaseModel):
    disponible: bool

@router.put("/mi-taller/disponibilidad", response_model=TallerResponse)
def actualizar_disponibilidad(
    payload: DisponibilidadUpdate,
    db=Depends(get_db),
    current_taller: Taller = Depends(get_current_taller),
):
    current_taller.disponible = payload.disponible
    db.commit()
    db.refresh(current_taller)
    return current_taller
```

Agregar `disponible: bool` al schema `TallerResponse`.

---

## 7. BLOQUE C — Comunicación

### C.1 — CU-32: Push notifications con FCM

**Recomendación:** empezar simple usando `Taller.push_token` que ya existe, y agregar `Usuario.push_token`. Después de MVP, migrar a tabla `device_token` si necesitas multi-device.

**Paso 1 — Dependencias:**
```
pip install firebase-admin
```

Agregar a `requirements.txt`: `firebase-admin==6.5.0`.

**Paso 2 — Variable de entorno** (en `.env`):
```
FIREBASE_CREDENTIALS_JSON=/ruta/al/service-account.json
```

**Paso 3 — Columna en usuario:**
```sql
ALTER TABLE usuario ADD COLUMN push_token VARCHAR(255);
```

```python
# app/models/user_model.py (o donde esté Usuario) agregar:
push_token = Column(String(255), nullable=True)
```

**Paso 4 — Servicio:**

```python
# app/services/push_service.py
import logging
from typing import Optional
import firebase_admin
from firebase_admin import credentials, messaging
from app.core.config import get_settings

logger = logging.getLogger("push_service")
settings = get_settings()

_app = None
def _ensure_initialized():
    global _app
    if _app is None and settings.FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_JSON)
        _app = firebase_admin.initialize_app(cred)

def enviar_push(token: Optional[str], titulo: str, body: str, data: Optional[dict] = None) -> bool:
    if not token:
        return False
    _ensure_initialized()
    try:
        msg = messaging.Message(
            notification=messaging.Notification(title=titulo, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        messaging.send(msg)
        return True
    except Exception as e:
        logger.warning(f"[PUSH] Error enviando: {e}")
        return False
```

**Paso 5 — Endpoint para registrar token:**

```python
# api/notificaciones.py (router nuevo)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.security import get_current_user, get_current_taller
...

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

class RegistrarTokenRequest(BaseModel):
    push_token: str

@router.post("/cliente/token")
def registrar_token_cliente(payload, current_user=Depends(get_current_user), db=Depends(get_db)):
    current_user.push_token = payload.push_token
    db.commit()
    return {"ok": True}

@router.post("/taller/token")
def registrar_token_taller(payload, current_taller=Depends(get_current_taller), db=Depends(get_db)):
    current_taller.push_token = payload.push_token
    db.commit()
    return {"ok": True}
```

Registrarlo en `app/main.py`.

**Paso 6 — Disparadores** (agregar llamadas `enviar_push(...)` en):

| Evento | A quién |
|---|---|
| Motor crea asignación | `taller.push_token` del ganador |
| `/aceptar` | `usuario.push_token` del cliente dueño |
| `/rechazar` (y reasignación ok) | `taller.push_token` del nuevo candidato |
| `/iniciar-viaje` | cliente |
| `/completar` | cliente |
| `/evaluar` | taller |

Ejemplo en `aceptar_asignacion`:
```python
incidente = db.get(Incidente, asignacion.id_incidente)
cliente = db.get(Usuario, incidente.id_usuario)
enviar_push(
    cliente.push_token,
    "¡Taller en camino!",
    f"{current_taller.nombre} aceptó tu solicitud. ETA: {payload.eta_minutos or '?'} min",
    data={"id_asignacion": asignacion.id_asignacion, "tipo": "asignacion_aceptada"},
)
```

---

### C.2 — CU-09 / CU-21: Chat cliente ↔ taller

**Recomendación:** polling HTTP simple. WebSocket es overkill para MVP.

**Paso 1 — Tabla:**
```sql
CREATE TABLE IF NOT EXISTS mensaje_chat (
  id_mensaje   SERIAL PRIMARY KEY,
  id_asignacion INT NOT NULL REFERENCES asignacion(id_asignacion),
  emisor_tipo  VARCHAR(20) NOT NULL CHECK (emisor_tipo IN ('usuario','taller')),
  emisor_id    INT NOT NULL,
  contenido    TEXT NOT NULL,
  leido        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_mensaje_asignacion ON mensaje_chat(id_asignacion, created_at);
```

**Paso 2 — Modelo:**
```python
# app/models/incidente.py (o archivo nuevo chat.py)
class MensajeChat(Base):
    __tablename__ = "mensaje_chat"
    id_mensaje = Column(Integer, primary_key=True)
    id_asignacion = Column(Integer, ForeignKey("asignacion.id_asignacion"), nullable=False, index=True)
    emisor_tipo = Column(String(20), nullable=False)  # "usuario" | "taller"
    emisor_id = Column(Integer, nullable=False)
    contenido = Column(Text, nullable=False)
    leido = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

**Paso 3 — Router nuevo `app/api/chat.py`:**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.models.incidente import MensajeChat, Asignacion
from app.models.usuario import Usuario
from app.models.taller import Taller
from app.core.security import oauth2_scheme, verify_token

router = APIRouter(prefix="/chat", tags=["Chat"])


def _get_actor(token: str, db: Session):
    """Retorna (tipo, id, asignaciones_query_filter) sin forzar un solo tipo."""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Token inválido")
    tipo = payload.get("tipo")
    sub = int(payload.get("sub", 0))
    if tipo not in ("usuario", "taller"):
        raise HTTPException(401, "Tipo inválido")
    return tipo, sub


def _verificar_acceso(db: Session, id_asignacion: int, tipo: str, actor_id: int) -> Asignacion:
    asignacion = db.get(Asignacion, id_asignacion)
    if not asignacion:
        raise HTTPException(404, "Asignación no encontrada")
    if tipo == "taller":
        if asignacion.id_taller != actor_id:
            raise HTTPException(403, "No tienes acceso a este chat")
    else:  # usuario
        from app.models.incidente import Incidente
        incidente = db.get(Incidente, asignacion.id_incidente)
        if not incidente or incidente.id_usuario != actor_id:
            raise HTTPException(403, "No tienes acceso a este chat")
    return asignacion


class EnviarMensajeRequest(BaseModel):
    contenido: str


class MensajeResponse(BaseModel):
    id_mensaje: int
    id_asignacion: int
    emisor_tipo: str
    emisor_id: int
    contenido: str
    leido: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/asignaciones/{id_asignacion}/mensajes", response_model=MensajeResponse)
def enviar_mensaje(
    id_asignacion: int,
    payload: EnviarMensajeRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    tipo, actor_id = _get_actor(token, db)
    _verificar_acceso(db, id_asignacion, tipo, actor_id)

    msg = MensajeChat(
        id_asignacion=id_asignacion,
        emisor_tipo=tipo,
        emisor_id=actor_id,
        contenido=payload.contenido,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # TODO push notification a la contraparte
    return msg


@router.get("/asignaciones/{id_asignacion}/mensajes", response_model=List[MensajeResponse])
def listar_mensajes(
    id_asignacion: int,
    desde_id: Optional[int] = Query(None, description="Solo mensajes con id > desde_id"),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    tipo, actor_id = _get_actor(token, db)
    _verificar_acceso(db, id_asignacion, tipo, actor_id)

    q = db.query(MensajeChat).filter(MensajeChat.id_asignacion == id_asignacion)
    if desde_id:
        q = q.filter(MensajeChat.id_mensaje > desde_id)
    return q.order_by(MensajeChat.created_at.asc()).all()


@router.put("/asignaciones/{id_asignacion}/mensajes/marcar-leidos")
def marcar_leidos(
    id_asignacion: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    tipo, actor_id = _get_actor(token, db)
    _verificar_acceso(db, id_asignacion, tipo, actor_id)

    # Marcar leídos los mensajes que NO envió este actor
    db.query(MensajeChat).filter(
        MensajeChat.id_asignacion == id_asignacion,
        MensajeChat.emisor_tipo != tipo,
        MensajeChat.leido == False,
    ).update({MensajeChat.leido: True}, synchronize_session=False)
    db.commit()
    return {"ok": True}
```

Registrar en `app/main.py`.

**Frontend:** polling cada 5s de `GET /chat/asignaciones/{id}/mensajes?desde_id=<último>`.

**Restricción de negocio:** solo permitir chatear mientras la asignación esté activa (no en estados `completada`/`rechazada`). Validar en `_verificar_acceso` si se quiere.

---

## 8. Orden de implementación recomendado

**Ya implementado (no rehacer):**
- ✅ B.0 (lookup por nombre)
- ✅ A.1 (trazabilidad integrada en motor + `/aceptar` + `/rechazar` + `/iniciar-viaje` + `/completar`)
- ✅ A.2 (`iniciar-viaje` + `completar`)
- ✅ A.3 (evaluación + `mis-evaluaciones`)
- ✅ A.4 (filtros historial)
- ✅ B.1 (reasignación automática)
- ✅ B.3 (disponibilidad del taller)
- ⚪ B.2 descartado por diseño (no hay admin)

**Pendiente:**
1. **C.1**: push notifications con FCM.
2. **C.2**: chat cliente ↔ taller (depende de C.1 para notificar mensajes).

---

## 9. Testing end-to-end mínimo

Después de cada bloque, probar este flujo en Swagger:

1. `POST /usuarios/login` con conductor@ejemplo.com → copiar token.
2. `POST /vehiculos/` registrar auto.
3. `POST /incidencias/` reportar emergencia.
4. `POST /incidencias/{id}/evidencias` subir foto.
5. `POST /incidencias/{id}/analizar-ia` → espera categoría y candidatos.
6. Cambiar al login del taller (`POST /talleres/login`).
7. `GET /talleres/mi-taller/asignaciones?estado=pendiente` → ver la solicitud.
8. `PUT /mi-taller/asignaciones/{id}/aceptar` con `{"id_tecnico":1,"eta_minutos":15}`.
9. **(A.2)** `PUT /mi-taller/asignaciones/{id}/iniciar-viaje`.
10. **(A.2)** `PUT /mi-taller/asignaciones/{id}/completar` con costo.
11. Volver al cliente: **(A.3)** `POST /incidencias/{id}/evaluar` `{"estrellas":5}`.
12. Verificar en BD:
    ```sql
    SELECT * FROM historial_estado_asignacion WHERE id_asignacion = X;
    SELECT * FROM historial_estado_incidente WHERE id_incidente = Y;
    SELECT * FROM evaluacion;
    ```

---

## 10. Trampas comunes / cosas que NO hacer

- ❌ No hardcodear IDs de estados. Siempre `filter_by(nombre=...)`.
- ❌ No usar `id_rol=1`, `id_estado=1`, etc., en código nuevo (el código actual lo hace, pero es deuda).
- ❌ No agregar especialidades al técnico. Decisión explícita del usuario.
- ❌ **No crear rol admin ni panel admin.** Decisión explícita: el sistema opera sin supervisión humana.
- ❌ No crear endpoint público de registro de taller sin discutir verificación primero (se abre a spam).
- ❌ No duplicar llamada a `buscar_y_asignar` — ya está dentro de `clasificar_incidente`.
- ❌ No tocar `CandidatoAsignacion.seleccionado` sin entender que afecta `cambiar-taller` y `rechazar_asignacion`.
- ❌ **No bloquear el motor cuando `requiere_revision_manual == True`.** Ese flag es solo informativo para la UI.
- ❌ Cuando agregues columna nueva a un modelo, **acuérdate de correr `ALTER TABLE`** — `create_all` no altera tablas existentes (esto rompió B.3 temporalmente).
- ❌ Cuando crees schema Pydantic en un router, **verifica `from pydantic import BaseModel`** antes de confiar en `class X(BaseModel)` (esto también rompió B.3).
- ❌ No ejecutar `git add -A`. En la raíz hay scripts `.py` sueltos del usuario (seeds, debug) que no son del repo principal.
- ❌ No amendar commits (`--amend`). Crear commits nuevos.
- ❌ No usar `--no-verify`. Si un hook falla, arreglar la causa.
- ❌ No inventar tablas nuevas antes de revisar `schema_postgresql.sql` y los modelos — mucho ya existe.

---

## 11. Archivos que probablemente tocarás

| Archivo | Motivo |
|---|---|
**Ya tocados (A.1–B.3) — no volver a modificar salvo por los bloques C:**
| Archivo | Qué se hizo |
|---|---|
| `app/services/asignacion.py` | B.0 (lookup dinámico `_ids_estados_activos`), B.3 (filtro `disponible`), A.1 (historial en creación) |
| `app/services/trazabilidad.py` | A.1 — helpers `cambiar_estado_asignacion` / `cambiar_estado_incidente` |
| `app/api/talleres.py` | `/aceptar` con trazabilidad, `/rechazar` + B.1, `/iniciar-viaje`, `/completar`, `/mi-taller/evaluaciones`, `/mi-taller/disponibilidad` |
| `app/api/incidencias.py` | A.3 (`/evaluar`), A.4 (filtros `estado/desde/hasta`) |
| `app/models/incidente.py` | `Evaluacion` agregada |
| `app/models/taller.py` | `Taller.disponible` agregada |
| `app/schemas/taller_schema.py` | `IniciarViajeRequest`, `CompletarAsignacionRequest`, `TallerResponse.disponible` |
| `app/schemas/incidente_schema.py` | `EvaluacionCreate/Response` |
| `app/guias/schema_postgresql.sql` | `taller.disponible` documentada |

**Pendientes por bloque C:**
| Archivo | Motivo |
|---|---|
| `app/services/ia_service.py` | **NO tocar** — B.2 descartado |
| `app/services/push_service.py` | **NUEVO** (C.1) |
| `app/api/notificaciones.py` | **NUEVO** (C.1) — endpoint registrar token |
| `app/api/chat.py` | **NUEVO** (C.2) |
| `app/models/incidente.py` | Agregar `MensajeChat` (C.2) |
| `app/models/user_model.py` | Agregar `Usuario.push_token` (C.1) |
| `app/models/__init__.py` | Exportar modelos nuevos |
| `app/main.py` | Registrar routers nuevos (notificaciones, chat) |
| `app/guias/schema_postgresql.sql` | Documentar `mensaje_chat` y `usuario.push_token` |
| `requirements.txt` | `firebase-admin` para C.1 |

---

## 12. Decisiones de producto ya tomadas

**Ya resueltas (no volver a preguntar):**
- ✅ **Sistema 100% automático, sin panel admin ni supervisión humana.** CU-29 (casos ambiguos) se descartó por esto mismo. No crear rutas `/admin/*` ni dependencia `require_admin`.
- ✅ **Costo del servicio:** el taller lo reporta en `/completar` vía `costo_estimado` (ver `CompletarAsignacionRequest`).
- ✅ **Reasignación automática es silenciosa** — no notifica al cliente. En C.1 se puede agregar notificación opcional.
- ✅ **Técnicos sin especialidad** (decisión previa).

**Preguntas abiertas para el Bloque C:**
- ¿FCM es solo móvil (Android/iOS) o también web (FCM-JS para el panel del taller)?
- ¿El chat debe cerrarse automáticamente cuando la asignación pasa a `completada`/`rechazada`, o sigue disponible para disputas?
- ¿Los mensajes del chat persisten para siempre, o se archivan después de N días?
- ¿Se permite agregar un endpoint `PUT /incidencias/{id}/cancelar` para el cliente? (No está en los bloques originales, pero completaría el ciclo de vida.)

Responder estas antes de ejecutar C.1/C.2.

---

## 13. Dónde buscar si algo falla

- **Error 401 "No se pudieron validar credenciales":** revisar claim `tipo` del JWT. Ver `SOLUCION_401_JWT_TIMEZONE.md` y `DIAGNOSTICO_401.md` en `app/guias/` — hubo incidentes previos con timezone en Windows.
- **Swagger no muestra el botón Authorize bien:** es normal, solo un `tokenUrl` está registrado. Usa `/talleres/login` manualmente y copia el token al botón.
- **Motor no asigna nada:** correr `seed_motor_asignacion.py`, verificar que hay `taller_servicio` para la categoría del incidente y que hay talleres con coordenadas dentro de 30 km.
- **Gemini devuelve error:** verificar `GEMINI_API_KEY` en `.env`. Modelo default: `gemini-2.5-pro` (ver `config.py`).

---

**Fin del handoff.** Con esta guía + el repo deberías poder continuar sin necesitar preguntarle al usuario detalles básicos. Suerte.
