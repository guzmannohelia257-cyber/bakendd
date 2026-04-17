#!/bin/bash
# Script para poblar usuarios en Linux/Mac

echo ""
echo "============================================================"
echo "POBLANDO USUARIOS DE EJEMPLO..."
echo "============================================================"
echo ""

# Ejecutar el script Python
python -m scripts.seed_usuarios

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "LISTO! Ahora abre Swagger en: http://localhost:8000/docs"
    echo "============================================================"
else
    echo ""
    echo "ERROR: El script no se ejecutó correctamente"
    echo ""
    exit 1
fi
