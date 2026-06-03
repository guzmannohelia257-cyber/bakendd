"""0015_configuracion_plataforma

Mueve la penalizacion del SLA de llegada de configuracion per-tenant a una
configuracion GLOBAL de la plataforma (super-admin), aplicable a TODOS los
talleres.

  - Crea la tabla singleton configuracion_plataforma con:
      * sla_penalizacion_pct (default 15)
      * sla_tolerancia_min   (default 20, antes hardcodeada)
    e inserta la fila default (id=1).
  - Elimina tenant.pct_penalizacion_sla (revierte 0014, ahora global).

Idempotente: comprueba existencia de la tabla / columna antes de operar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "041523340c01"
down_revision: Union[str, None] = "f3041233440c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _has_column(bind, table: str, col: str) -> bool:
    return col in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "configuracion_plataforma"):
        op.create_table(
            "configuracion_plataforma",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("sla_penalizacion_pct", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("sla_tolerancia_min", sa.Integer(), nullable=False, server_default="20"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # Sembrar la fila singleton default (solo si la tabla quedo vacia).
    existe_fila = bind.execute(
        sa.text("SELECT 1 FROM configuracion_plataforma WHERE id = 1")
    ).scalar()
    if not existe_fila:
        op.bulk_insert(
            sa.table(
                "configuracion_plataforma",
                sa.column("id", sa.Integer),
                sa.column("sla_penalizacion_pct", sa.Integer),
                sa.column("sla_tolerancia_min", sa.Integer),
            ),
            [{"id": 1, "sla_penalizacion_pct": 15, "sla_tolerancia_min": 20}],
        )

    # Revertir la columna per-tenant: ahora es global.
    if _has_column(bind, "tenant", "pct_penalizacion_sla"):
        op.drop_column("tenant", "pct_penalizacion_sla")


def downgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "tenant", "pct_penalizacion_sla"):
        op.add_column(
            "tenant",
            sa.Column(
                "pct_penalizacion_sla",
                sa.Integer(),
                nullable=False,
                server_default="15",
            ),
        )

    if _has_table(bind, "configuracion_plataforma"):
        op.drop_table("configuracion_plataforma")
