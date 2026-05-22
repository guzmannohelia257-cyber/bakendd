"""
Dump del schema actual de la BD (RDS) a un archivo .sql legible.

No reemplaza a pg_dump pero produce DDL suficiente para tener un snapshot
versionado en app/guias/schema_postgresql.sql.

Uso:
    python -m scripts.dump_schema
"""
import os
import sys
from pathlib import Path

# Permitir ejecutar desde la raiz del backend sin instalar como paquete
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.schema import CreateTable, CreateIndex

from app.core.config import get_settings


HEADER_TEMPLATE = """-- ============================================================
-- PLATAFORMA INTELIGENTE DE ATENCION DE EMERGENCIAS VEHICULARES
-- Schema PostgreSQL - SNAPSHOT desde {host}
-- Generado automaticamente por scripts/dump_schema.py
-- NO EDITAR A MANO: regenerar con `python -m scripts.dump_schema`
-- ============================================================

"""


def main() -> int:
    settings = get_settings()
    # Permite override por env var SCHEMA_DUMP_URL (util para apuntar a local)
    url = os.getenv("SCHEMA_DUMP_URL", settings.DATABASE_URL)
    print(f"Conectando a: {url.split('@')[-1]}")

    engine = create_engine(url, future=True)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    inspector = inspect(engine)
    dialect = engine.dialect

    # Ordenar tablas respetando dependencias FK
    sorted_tables = metadata.sorted_tables

    host_label = url.split("@")[-1]
    out_lines: list[str] = [HEADER_TEMPLATE.format(host=host_label)]

    out_lines.append("-- ==========================================")
    out_lines.append(f"-- {len(sorted_tables)} tablas reflejadas")
    out_lines.append("-- ==========================================\n")

    for table in sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
        out_lines.append(f"-- ----- Tabla: {table.name} -----")
        out_lines.append(ddl + ";\n")

        # Indices (excluye los implicitos de PKs)
        indexes = inspector.get_indexes(table.name)
        for idx in indexes:
            cols = ", ".join(idx["column_names"])
            unique = "UNIQUE " if idx.get("unique") else ""
            out_lines.append(
                f'CREATE {unique}INDEX IF NOT EXISTS "{idx["name"]}" '
                f'ON "{table.name}" ({cols});'
            )
        if indexes:
            out_lines.append("")

    out_path = ROOT / "app" / "guias" / "schema_postgresql.sql"
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Schema escrito en: {out_path}")
    print(f"Tablas: {len(sorted_tables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
