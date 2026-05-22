"""0005_cotizacion

Crea catalogo estado_cotizacion + tabla cotizacion (tenant-scoped).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7b5c7b8c2a1"
down_revision: Union[str, None] = "d4f0f9e2b3a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ESTADOS = ["pendiente", "enviada", "aceptada", "rechazada", "expirada"]


def upgrade() -> None:
    op.create_table(
        "estado_cotizacion",
        sa.Column("id_estado_cotizacion", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=50), nullable=False, unique=True),
    )
    for nombre in ESTADOS:
        op.execute(
            sa.text(
                "INSERT INTO estado_cotizacion (nombre) VALUES (:n) ON CONFLICT DO NOTHING"
            ).bindparams(n=nombre)
        )

    op.create_table(
        "cotizacion",
        sa.Column("id_cotizacion", sa.Integer(), primary_key=True),
        sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=False, index=True),
        sa.Column("id_incidente", sa.Integer(), sa.ForeignKey("incidente.id_incidente"), nullable=False, index=True),
        sa.Column("id_taller", sa.Integer(), sa.ForeignKey("taller.id_taller"), nullable=False, index=True),
        sa.Column(
            "id_estado_cotizacion",
            sa.Integer(),
            sa.ForeignKey("estado_cotizacion.id_estado_cotizacion"),
            nullable=False,
        ),
        sa.Column("monto_servicio", sa.Numeric(10, 2), nullable=True),
        sa.Column("monto_repuestos", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("garantia_dias", sa.Integer(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("validez_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("id_incidente", "id_taller", name="uq_cotizacion_incidente_taller"),
    )


def downgrade() -> None:
    op.drop_table("cotizacion")
    op.drop_table("estado_cotizacion")
