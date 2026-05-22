"""
Alembic environment.

- Lee DATABASE_URL desde app/core/config.py (no desde alembic.ini), para tener
  una sola fuente de verdad.
- Importa app.models para que Base.metadata conozca todas las tablas.
"""
from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Permitir imports `app.*` desde la raiz del backend
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.session import Base  # noqa: E402
import app.models  # noqa: F401,E402  -> registra todas las tablas en Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inyectar URL desde settings (override de alembic.ini).
# Permite override por env var ALEMBIC_DATABASE_URL para apuntar a otra BD.
settings = get_settings()
db_url = os.getenv("ALEMBIC_DATABASE_URL", settings.DATABASE_URL)
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
