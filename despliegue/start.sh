#!/usr/bin/env bash
# Script de arranque para Render.
#
# Comportamiento:
#   - Si SEED_ON_STARTUP=true (default): crea las tablas si no existen,
#     trunca todo y siembra datos de prueba consistentes (todos los estados).
#   - Si SEED_ON_STARTUP=false: arranca directo sin tocar la base.
#
# Pensado para un proyecto universitario donde cada deploy debe partir
# de un estado conocido. Pon SEED_ON_STARTUP=false cuando quieras congelar.
set -e

# IMPORTANTE: preparar el schema SIEMPRE antes de arrancar.
# bootstrap_db.py maneja los 3 casos:
#   - BD vacia  -> create_all() + alembic stamp head  (la 0001 es baseline vacio,
#                  por eso "alembic upgrade head" a secas revienta en una BD nueva)
#   - BD sin alembic_version -> stamp head
#   - BD ya inicializada -> alembic upgrade head (aplica migraciones pendientes)
echo "==> [start.sh] Bootstrap de base de datos"
python despliegue/bootstrap_db.py

if [ "${SEED_ON_STARTUP:-true}" = "true" ]; then
    echo "==> [start.sh] SEED_ON_STARTUP=true → corriendo SETT/run_all.py"
    python -m SETT.run_all
else
    echo "==> [start.sh] SEED_ON_STARTUP=$SEED_ON_STARTUP → no se siembra la base"
fi

echo "==> [start.sh] Levantando gunicorn (uvicorn worker)"
exec gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --timeout 120
