"""0006_cancelacion

- Anade tarifa_traslado a taller (default 5.0).
- Anade columnas de cancelacion + compensacion a asignacion.
- Asegura que estado_asignacion tenga 'cancelada' y 'llegado'.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e28d2d4b21"
down_revision: Union[str, None] = "b7b5c7b8c2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "taller",
        sa.Column("tarifa_traslado", sa.Numeric(10, 2), nullable=False, server_default="5.00"),
    )

    op.add_column("asignacion", sa.Column("cancelada_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("asignacion", sa.Column("motivo_cancelacion", sa.String(length=500), nullable=True))
    op.add_column("asignacion", sa.Column("cancelada_por", sa.String(length=20), nullable=True))
    op.add_column("asignacion", sa.Column("compensacion_monto", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "asignacion",
        sa.Column("compensacion_pagada", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    for nombre in ("cancelada", "llegado"):
        op.execute(
            sa.text(
                """
            INSERT INTO estado_asignacion (nombre)
            SELECT :n
            WHERE NOT EXISTS (
                SELECT 1 FROM estado_asignacion WHERE nombre = :n
            )
        """
            ).bindparams(n=nombre)
        )


def downgrade() -> None:
    op.drop_column("asignacion", "compensacion_pagada")
    op.drop_column("asignacion", "compensacion_monto")
    op.drop_column("asignacion", "cancelada_por")
    op.drop_column("asignacion", "motivo_cancelacion")
    op.drop_column("asignacion", "cancelada_at")
    op.drop_column("taller", "tarifa_traslado")
