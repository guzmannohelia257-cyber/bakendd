"""0003_tenant_not_null_taller

Una vez ejecutado el backfill (scripts/backfill_tenants.py), todos los talleres
tienen id_tenant. Esta migracion:

  - Verifica que no queden talleres con id_tenant NULL (fail rapido si hay).
  - Marca taller.id_tenant como NOT NULL.

NO se hace NOT NULL en las transaccionales (incidente, asignacion, etc.) en
esta fase: durante el periodo de transicion permitimos que requests publicos
(cliente final que reporta sin tenant) creen incidentes con id_tenant NULL y
luego se les asigne tenant cuando se asigne a un taller. Cuando se quiera
endurecer eso completamente, se hace en una 0004.

Revision ID: 3aa3e94bded9
Revises: 08a3dffb665e
Create Date: 2026-05-19 10:31:26.397197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3aa3e94bded9"
down_revision: Union[str, None] = "08a3dffb665e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    pending = bind.execute(
        sa.text("SELECT COUNT(*) FROM taller WHERE id_tenant IS NULL")
    ).scalar_one()
    if pending and pending > 0:
        raise RuntimeError(
            f"No se puede aplicar 0003: {pending} taller(es) tienen id_tenant NULL. "
            f"Corre `python -m scripts.backfill_tenants` primero."
        )

    op.alter_column("taller", "id_tenant", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("taller", "id_tenant", existing_type=sa.Integer(), nullable=True)
