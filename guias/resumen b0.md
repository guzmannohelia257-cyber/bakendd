✅ B.0 COMPLETADO

Cambios Realizados:
Archivo: asignacion.py

1. ✅ Nueva función _ids_estados_activos()
Obtiene dinámicamente los IDs de estados activos buscando por nombre (no hardcodeado)
Estados: "pendiente", "aceptada", "en_camino"
Ubicación: después de _calcular_distancia_haversine(), línea ~51
2. ✅ Actualizado _contar_asignaciones_activas()
Antes: estados_activos = [1, 2, 3] ❌
Después: estados_activos = _ids_estados_activos(db) ✅
3. ✅ Actualizado _contar_asignaciones_activas_tecnico()
Antes: estados_activos = [1, 2, 3] ❌
Después: estados_activos = _ids_estados_activos(db) ✅
4. ✅ Validación
py_compile sin errores ✅
Impacto: Ahora el motor de asignación es robusto contra cambios de seed de catálogos. Los IDs de estados se resuelven dinámicamente por nombre.

