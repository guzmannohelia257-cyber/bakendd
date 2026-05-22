✅ A.2 COMPLETADO — CU-20: Transiciones en_camino y completada

Cambios implementados:
📄 Schemas nuevos (taller_schema.py):
IniciarViajeRequest — ubicación del técnico (opcional)
CompletarAsignacionRequest — costo final y resumen de trabajo
🔌 Endpoints nuevos (talleres.py):
1. PUT /mi-taller/asignaciones/{id_asignacion}/iniciar-viaje

Validación: asignación debe estar en estado aceptada
Actualiza: posición del técnico si se proporciona
Transición: aceptada → en_camino ✏️ (registrada en historial)
2. PUT /mi-taller/asignaciones/{id_asignacion}/completar

Validación: asignación debe estar en estado en_camino
Actualiza: costo final y resumen de trabajo
Transiciones duales:
Asignación: en_camino → completada ✏️
Incidente: (cualquier estado) → atendido ✏️
Ambas registradas en historial automáticamente
✨ Integración con trazabilidad:
Todos los cambios de estado usan cambiar_estado_asignacion() y cambiar_estado_incidente() del servicio A.1, garantizando audit trail completo.

✅ Validación:
Sintaxis OK (py_compile sin errores)
Imports verificados (Tecnico, Incidente, cambiar_estado_incidente presentes)
¿Próximo paso? A.3 (evaluar servicio) o continuar con otro bloque?

Claude Haiku 4.5 • 0.33x