"""
Configuración de la sesión de Base de Datos con SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

# Motor SQLAlchemy conectado a PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Mostrar queries SQL en consola si DEBUG=True
    future=True
)

# Factory para crear sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Clase base para todos los modelos ORM
Base = declarative_base()


def get_db():
    """
    Dependency Injection para FastAPI
    Se usa en los endpoints: def endpoint(db: Session = Depends(get_db))
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
