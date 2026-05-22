 A.4: Filtros en Historial - COMPLETADO
Cambios Realizados:
1. incidencias.py (Cliente)
✅ Agregué imports: Query, Optional, date
✅ Actualicé GET /incidencias/mis-incidencias con 3 query params opcionales:
estado - Filtrar por: pendiente | en_proceso | atendido | cancelado
desde - Fecha inicial (YYYY-MM-DD)
hasta - Fecha final (YYYY-MM-DD)
✅ Lógica:
Filtra por id_usuario (ownership)
Si hay estado, hace JOIN con EstadoIncidente y filtra por nombre
Si hay desde, filtra created_at >= desde
Si hay hasta, filtra created_at <= hasta
Ordena por created_at DESC (más recientes primero)
2. talleres.py (Taller)
✅ Agregué imports: date
✅ Actualicé GET /talleres/mi-taller/asignaciones con los mismos 3 query params:
estado - Filtrar por: pendiente | aceptada | rechazada | en_camino | completada
desde - Fecha inicial
hasta - Fecha final
✅ Lógica idéntica (filtra por id_taller, estado y fechas)
3. Validación
✅ py_compile sin errores en ambos archivos
Ejemplos de uso:
¿Ok? ¿Continuamos con B.0 (corregir IDs hardcoded)?

Claude Haiku 4.5 • 0.33x