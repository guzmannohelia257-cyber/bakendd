# F5 — Offline web Angular

> Esta fase es **100% frontend**. No requiere cambios en el backend.

## Recomendación opcional para el backend
Para soportar idempotencia cuando el cliente reenvía un POST encolado offline, el backend puede honrar el header `X-Client-Id`:

```python
# Ejemplo: en POST /incidencias
client_id = request.headers.get("X-Client-Id")
if client_id:
    existing = db.query(Incidente).filter_by(client_id=client_id).first()
    if existing:
        return existing  # respuesta idempotente
# ... crear con incidente.client_id = client_id
```

Para esto se requiere agregar columna `client_id VARCHAR(36) UNIQUE NULL` a `incidente` en una migración nueva.

**Sin esto**: si un POST se reenvía dos veces, se crean dos incidentes. Para el parcial puede aceptarse y mencionarse como limitación.

## Implementación
Ver guía completa de frontend: [G2WEB/W7_pwa_offline.md](../G2WEB/W7_pwa_offline.md)

Incluye:
- Setup PWA (`ng add @angular/pwa`)
- IndexedDB con Dexie.js
- HTTP interceptor para encolar mutaciones offline
- OutboxService y sincronización al recuperar conexión
- Banner UI de estado offline
- Plan de pruebas manual

## Checklist de cierre F5 (backend)
- [ ] (Opcional) Columna `client_id` agregada a tablas que reciben mutaciones desde mobile/web.
- [ ] (Opcional) Endpoints respetan `X-Client-Id` para deduplicar.
- [ ] La implementación frontend está completada (ver W7).
