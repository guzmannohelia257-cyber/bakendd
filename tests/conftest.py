"""
Configuracion global de pytest.

Estrategia:
  - Usa la BD local (emergencias_vehiculares). No requiere BD aparte.
  - Cada test corre dentro de una transaccion + SAVEPOINT que se hace rollback al final,
    asi no contamina la BD.
  - Sobrescribe la dependencia `get_db` de FastAPI para que apunte a la sesion
    transaccional del test.

Si quieres aislamiento total, define TEST_DATABASE_URL en el entorno
apuntando a una BD aparte (debe tener el mismo schema, aplica alembic alli).
"""
from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.taller import Taller
from app.models.tenant import Plan, Suscripcion, Tenant
from app.models.usuario import Usuario, Vehiculo


# Rate limit OFF en tests: si no, varios tests del mismo endpoint disparan 429
# porque el TestClient siempre usa la misma IP (testclient).
limiter.enabled = False


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    url = os.getenv("TEST_DATABASE_URL", settings.DATABASE_URL)
    eng = create_engine(url, future=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """
    Sesion transaccional con SAVEPOINT. Todo lo que el test escriba se hace
    rollback al final, sin contaminar la BD.

    Usa el patron oficial de SQLAlchemy 2.0 con `join_transaction_mode="create_savepoint"`:
    cada session.commit() (incluso los disparados dentro de endpoints via dependency
    override) se traduce en RELEASE SAVEPOINT + nuevo SAVEPOINT, sin tocar la
    transaccion raiz que se hace rollback al final del test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = TestSession()

    try:
        yield session
    finally:
        session.close()
        try:
            transaction.rollback()
        except Exception:
            pass
        connection.close()


@pytest.fixture()
def client(db_session) -> Generator[TestClient, None, None]:
    """TestClient con get_db override apuntando a la sesion transaccional."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ============================================================
# FIXTURES DE DOMINIO
# ============================================================

@pytest.fixture()
def plan_free(db_session) -> Plan:
    return db_session.query(Plan).filter(Plan.codigo == "free").one()


@pytest.fixture()
def tenant_factory(db_session):
    """Crea tenants unicos para evitar choques entre tests."""
    created = []

    def _make(slug_prefix: str = "t", nombre: str | None = None) -> Tenant:
        slug = f"{slug_prefix}-{uuid.uuid4().hex[:8]}"
        t = Tenant(
            slug=slug,
            nombre=nombre or f"Tenant {slug}",
            email_contacto=f"{slug}@test.com",
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        created.append(t)
        return t

    return _make


@pytest.fixture()
def taller_factory(db_session, plan_free):
    """Crea talleres asociados a un tenant para tests."""

    def _make(tenant: Tenant, email: str | None = None, password: str = "secret123") -> Taller:
        email = email or f"taller-{uuid.uuid4().hex[:8]}@test.com"
        t = Taller(
            id_tenant=tenant.id_tenant,
            nombre=f"Taller {tenant.slug}",
            email=email,
            password_hash=hash_password(password),
        )
        db_session.add(t)
        db_session.commit()
        db_session.refresh(t)
        return t

    return _make


@pytest.fixture()
def taller_auth_headers():
    """Construye headers Authorization Bearer para un taller dado."""

    def _make(taller: Taller) -> dict:
        extra = {"id_tenant": taller.id_tenant} if taller.id_tenant else None
        token = create_access_token(subject_id=taller.id_taller, tipo="taller", extra_claims=extra)
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def admin_user_factory(db_session):
    """Crea un usuario con rol=4 (super-admin) para tests que lo requieren."""

    def _make() -> Usuario:
        u = Usuario(
            id_rol=4,
            nombre="Admin Test",
            email=f"admin-{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("admin123"),
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        return u

    return _make


@pytest.fixture()
def admin_headers(admin_user_factory):
    def _make(usuario: Usuario | None = None) -> dict:
        u = usuario or admin_user_factory()
        token = create_access_token(subject_id=u.id_usuario, tipo="usuario")
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def cliente_factory(db_session):
    """Crea usuarios con rol=1 (cliente) para tests."""

    def _make(email: str | None = None, password: str = "secret123") -> Usuario:
        email = email or f"cliente-{uuid.uuid4().hex[:8]}@test.com"
        u = Usuario(
            id_rol=1,
            nombre="Cliente Test",
            email=email,
            password_hash=hash_password(password),
            activo=True,
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        return u

    return _make


@pytest.fixture()
def vehiculo_factory(db_session):
    """Crea vehiculos asociados a un usuario cliente."""

    def _make(usuario: Usuario) -> Vehiculo:
        v = Vehiculo(
            id_usuario=usuario.id_usuario,
            placa=f"TEST-{uuid.uuid4().hex[:5].upper()}",
            marca="Test",
            modelo="Model",
            anio=2020,
            color="Gris",
            activo=True,
        )
        db_session.add(v)
        db_session.commit()
        db_session.refresh(v)
        return v

    return _make


@pytest.fixture()
def cliente_auth_headers():
    """Construye headers Authorization Bearer para un usuario cliente."""

    def _make(cliente: Usuario) -> dict:
        token = create_access_token(subject_id=cliente.id_usuario, tipo="usuario")
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def incidente_factory(db_session):
    """Crea incidentes asociados a un usuario y vehiculo."""

    def _make(
        usuario: Usuario,
        vehiculo: Vehiculo,
        categoria_codigo: str | None = None,
        lat: float = -16.5,
        lng: float = -68.15,
    ):
        from app.models.catalogos import EstadoIncidente
        from app.models.catalogos import CategoriaProblema
        from app.models.incidente import Incidente

        estado = db_session.query(EstadoIncidente).first()
        categoria = None
        if categoria_codigo:
            categoria = (
                db_session.query(CategoriaProblema)
                .filter(CategoriaProblema.codigo == categoria_codigo)
                .first()
            )
        if categoria is None:
            categoria = db_session.query(CategoriaProblema).first()
        inc = Incidente(
            id_usuario=usuario.id_usuario,
            id_vehiculo=vehiculo.id_vehiculo,
            id_estado=estado.id_estado,
            id_categoria=categoria.id_categoria if categoria else None,
            latitud=lat,
            longitud=lng,
        )
        db_session.add(inc)
        db_session.commit()
        db_session.refresh(inc)
        return inc

    return _make


# ============================================================
# FIXTURES PARA CICLO 2
# ============================================================

@pytest.fixture()
def tecnico_factory(db_session):
    """Crea usuario rol=3 vinculado a un taller."""
    from app.models.usuario_taller import UsuarioTaller

    def _make(taller: Taller, email: str | None = None, password: str = "tec12345"):
        email = email or f"tec-{uuid.uuid4().hex[:6]}@test.example.com"
        u = Usuario(
            id_rol=3,
            nombre=f"Tecnico {email}",
            email=email,
            password_hash=hash_password(password),
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)

        vin = UsuarioTaller(id_usuario=u.id_usuario, id_taller=taller.id_taller, activo=True)
        db_session.add(vin)
        db_session.commit()
        return u

    return _make


@pytest.fixture()
def tecnico_auth_headers():
    """
    Headers de tecnico. Si se pasa `taller`, el token incluye id_tenant + id_taller_activo
    (formato post-M9). Si no, token sin tenant (legacy — usar solo en tests que prueben
    explicitamente el caso "token sin tenant" -> 400).
    """
    def _make(tecnico: Usuario, taller: Taller | None = None) -> dict:
        extra = None
        if taller is not None:
            extra = {"id_tenant": taller.id_tenant, "id_taller_activo": taller.id_taller}
        token = create_access_token(
            subject_id=tecnico.id_usuario, tipo="usuario", extra_claims=extra,
        )
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def asignacion_factory(db_session):
    """Crea una asignacion lista para tracking/cancelacion."""
    from app.models.catalogos import EstadoAsignacion
    from app.models.incidente import Asignacion

    def _make(tenant: Tenant, taller: Taller, incidente, tecnico: Usuario | None = None, estado_nombre="aceptada"):
        estado = db_session.query(EstadoAsignacion).filter_by(nombre=estado_nombre).first()
        if not estado:
            estado = EstadoAsignacion(nombre=estado_nombre)
            db_session.add(estado)
            db_session.commit()
            db_session.refresh(estado)

        asig = Asignacion(
            id_tenant=tenant.id_tenant,
            id_incidente=incidente.id_incidente,
            id_taller=taller.id_taller,
            id_usuario=tecnico.id_usuario if tecnico else None,
            id_estado_asignacion=estado.id_estado_asignacion,
        )
        db_session.add(asig)
        db_session.commit()
        db_session.refresh(asig)
        return asig

    return _make


@pytest.fixture(autouse=True)
def _reset_pubsub_local():
    """Asegura que cada test arranca con pubsub en modo local-only."""
    from app.realtime.pubsub import pubsub_broker

    pubsub_broker._redis = None
    yield
