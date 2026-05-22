"""0001_baseline_empty

Punto de partida para Alembic. La BD productiva ya contiene todas las tablas
historicas creadas via `Base.metadata.create_all` y los SQL en /migrations.
Marcamos este punto con `alembic stamp <rev>` y de aqui en adelante TODO
cambio de schema pasa por una revision Alembic.

Revision ID: 518378145d58
Revises:
Create Date: 2026-05-19 10:05:32.771985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '518378145d58'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
