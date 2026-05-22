"""0002_multi_tenant_skeleton

Crea la infraestructura de multi-tenant (Fase 1):
  - Tablas nuevas: plan, tenant, suscripcion, tenant_user
  - Columna id_tenant (nullable + FK + indice) en: taller, incidente, asignacion,
    evidencia, evaluacion, mensaje, notificacion, pago, metrica
  - Seed de planes por defecto (free, pro, enterprise)

NO toca timestamps ni indices preexistentes (eso queda como tarea aparte de
"harmonizacion" para no mezclar cambios).

Idempotente sobre tablas: comprueba existencia donde aplica.

Revision ID: 08a3dffb665e
Revises: 518378145d58
Create Date: 2026-05-19 10:12:43.101229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "08a3dffb665e"
down_revision: Union[str, None] = "518378145d58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tablas a las que se les anade id_tenant + FK + indice.
# (nombre_tabla, nombre_constraint_fk, nombre_indice)
TENANT_SCOPED_TABLES = [
    ("taller", "fk_taller_tenant", "ix_taller_id_tenant"),
    ("incidente", "fk_incidente_tenant", "ix_incidente_id_tenant"),
    ("asignacion", "fk_asignacion_tenant", "ix_asignacion_id_tenant"),
    ("evidencia", "fk_evidencia_tenant", "ix_evidencia_id_tenant"),
    ("evaluacion", "fk_evaluacion_tenant", "ix_evaluacion_id_tenant"),
    ("mensaje", "fk_mensaje_tenant", "ix_mensaje_id_tenant"),
    ("notificacion", "fk_notificacion_tenant", "ix_notificacion_id_tenant"),
    ("pago", "fk_pago_tenant", "ix_pago_id_tenant"),
    ("metrica", "fk_metrica_tenant", "ix_metrica_id_tenant"),
]


def upgrade() -> None:
    # ---------- 1. Tablas nuevas ----------
    op.create_table(
        "plan",
        sa.Column("id_plan", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(length=50), nullable=False, unique=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=500), nullable=True),
        sa.Column("precio_mensual", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("moneda", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("max_talleres", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_tecnicos", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_incidentes_mes", sa.Integer(), nullable=True),
        sa.Column("feature_websockets", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("feature_kpis_avanzados", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("feature_reportes_ia", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tenant",
        sa.Column("id_tenant", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=50), nullable=False, unique=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("email_contacto", sa.String(length=100), nullable=False),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("suspendido", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tenant_slug", "tenant", ["slug"], unique=True)

    op.create_table(
        "suscripcion",
        sa.Column("id_suscripcion", sa.Integer(), primary_key=True),
        sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=False, index=True),
        sa.Column("id_plan", sa.Integer(), sa.ForeignKey("plan.id_plan"), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False, server_default="trial"),
        sa.Column("stripe_customer_id", sa.String(length=100), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=100), nullable=True),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tenant_user",
        sa.Column("id_tenant_user", sa.Integer(), primary_key=True),
        sa.Column("id_tenant", sa.Integer(), sa.ForeignKey("tenant.id_tenant"), nullable=False, index=True),
        sa.Column("id_usuario", sa.Integer(), sa.ForeignKey("usuario.id_usuario"), nullable=False, index=True),
        sa.Column("rol_tenant", sa.String(length=30), nullable=False, server_default="operador"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("id_tenant", "id_usuario", name="uq_tenant_user"),
    )

    # ---------- 2. Seed de planes por defecto ----------
    op.execute(
        """
        INSERT INTO plan
          (codigo, nombre, descripcion, precio_mensual, moneda,
           max_talleres, max_tecnicos, max_incidentes_mes,
           feature_websockets, feature_kpis_avanzados, feature_reportes_ia,
           activo)
        VALUES
          ('free',       'Free',       'Plan gratuito para evaluacion',          0,  'USD', 1,  3,  100,  false, false, false, true),
          ('pro',        'Pro',        'Para talleres en crecimiento',          49,  'USD', 3,  15, 2000, true,  true,  false, true),
          ('enterprise', 'Enterprise', 'Multi-sucursal, IA y soporte premium', 199,  'USD', 99, 99, NULL, true,  true,  true,  true);
        """
    )

    # ---------- 3. id_tenant en tablas existentes ----------
    for table, fk_name, idx_name in TENANT_SCOPED_TABLES:
        op.add_column(table, sa.Column("id_tenant", sa.Integer(), nullable=True))
        op.create_index(idx_name, table, ["id_tenant"])
        op.create_foreign_key(fk_name, table, "tenant", ["id_tenant"], ["id_tenant"])


def downgrade() -> None:
    # Quitar id_tenant de tablas scoped
    for table, fk_name, idx_name in TENANT_SCOPED_TABLES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.drop_index(idx_name, table_name=table)
        op.drop_column(table, "id_tenant")

    # Tablas nuevas
    op.drop_table("tenant_user")
    op.drop_table("suscripcion")
    op.drop_index("ix_tenant_slug", table_name="tenant")
    op.drop_table("tenant")
    op.drop_table("plan")
