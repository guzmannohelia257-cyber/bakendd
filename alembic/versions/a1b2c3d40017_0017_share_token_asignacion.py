"""0017_share_token_asignacion

Agrega share_token a asignacion: token opaco (UUID4 hex) que permite compartir
el seguimiento en vivo (ubicacion del tecnico + cliente + ruta) con un tercero
a traves de un link publico (GET /public/track/{token}).

Nullable: solo se genera cuando el taller comparte una asignacion. Indice unico
para localizar la asignacion por token sin escaneo.

Idempotente: solo agrega la columna/indice si la tabla existe y la columna no.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d40017"
down_revision: Union[str, None] = "c1d2e3f40016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, col: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return col in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("asignacion") and not _has_column(
        bind, "asignacion", "share_token"
    ):
        op.add_column(
            "asignacion",
            sa.Column("share_token", sa.String(length=64), nullable=True),
        )
        op.create_index(
            "ix_asignacion_share_token",
            "asignacion",
            ["share_token"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "asignacion", "share_token"):
        op.drop_index("ix_asignacion_share_token", table_name="asignacion")
        op.drop_column("asignacion", "share_token")
