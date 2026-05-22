"""0004_categorias_y_tarifas

- Anade columnas a categoria_problema: codigo (unique), requiere_cotizacion.
- Anade columna tarifa_base a taller_servicio.
- Upsertea las 7 categorias oficiales del enunciado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f0f9e2b3a1"
down_revision: Union[str, None] = "3aa3e94bded9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIAS = [
    ("llantas", "Servicio de llantas", "Vulcanizado, parches, inflado", False),
    ("mecanica_general", "Mecanica general", "Motor, transmision, frenos", True),
    ("electrico", "Servicio electrico", "Sistema electrico del vehiculo", True),
    ("electronico", "Servicio electronico", "Diagnostico escaner, ECU, sensores", True),
    ("chaperia_pintura", "Chaperia y pintura", "Carroceria, pintura, danos por colision", True),
    ("grua_auxilio", "Grua / Auxilio vial", "Remolque de vehiculos que no arrancan", False),
    ("rutinario", "Servicio rutinario", "Mantenimientos preventivos basicos", False),
]


def upgrade() -> None:
    op.add_column("categoria_problema", sa.Column("codigo", sa.String(length=50), nullable=True))
    op.add_column(
        "categoria_problema",
        sa.Column("requiere_cotizacion", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    for codigo, nombre, desc, requiere in CATEGORIAS:
        op.execute(
            sa.text(
                """
            INSERT INTO categoria_problema (nombre, descripcion, codigo, requiere_cotizacion)
            VALUES (:nombre, :desc, :codigo, :req)
            ON CONFLICT DO NOTHING
        """
            ).bindparams(nombre=nombre, desc=desc, codigo=codigo, req=requiere)
        )

    for codigo, nombre, _desc, requiere in CATEGORIAS:
        op.execute(
            sa.text(
                """
            UPDATE categoria_problema
            SET codigo = :codigo, requiere_cotizacion = :req
            WHERE LOWER(nombre) = LOWER(:nombre) AND (codigo IS NULL OR codigo <> :codigo)
        """
            ).bindparams(codigo=codigo, nombre=nombre, req=requiere)
        )

    op.create_unique_constraint("uq_categoria_codigo", "categoria_problema", ["codigo"])

    op.add_column("taller_servicio", sa.Column("tarifa_base", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("taller_servicio", "tarifa_base")
    op.drop_constraint("uq_categoria_codigo", "categoria_problema", type_="unique")
    op.drop_column("categoria_problema", "requiere_cotizacion")
    op.drop_column("categoria_problema", "codigo")
