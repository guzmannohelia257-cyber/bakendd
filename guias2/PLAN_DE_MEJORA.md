# Plan de Mejora — Segundo Parcial
**Plataforma Inteligente para Talleres Vehiculares (Yary)**

> Documento operativo: alinea el enunciado [ENUNCIADO_MEJORAS_A2.md](./ENUNCIADO_MEJORAS_A2.md) con el código actual y define ciclos, entregables y criterios de aceptación.

> **Guías de implementación BACKEND por ciclo:**
> - [G2C1/](./G2C1/README.md) — Ciclo 1: servicios extendidos, cotización, cancelación
> - [G2C2/](./G2C2/README.md) — Ciclo 2: WebSocket, tracking, KPIs, IA personalizada
> - [G2C3/](./G2C3/README.md) — Ciclo 3: hardening backend + release/backup operacional
>
> **Guías de implementación FRONTEND:**
> - [G2WEB/](./G2WEB/README.md) — Angular (panel del taller, PWA, dashboard, emergencias en vivo)
> - [G2MOBILE/](./G2MOBILE/README.md) — Flutter (cliente final y técnico, tracking, offline)
>
> **Guías de documentación (transversal a los ciclos):**
> - [G2D/](./G2D/README.md) — Marco teórico, UML, manual de usuario, guion demo, FAQ defensa

---

## 0. Estado actual (a 19 de mayo de 2026)

Ya hecho en este branch:

| Bloque | Estado | Evidencia |
|---|---|---|
| Backend FastAPI, modelos, endpoints base | ✅ | `app/` |
| Alembic + baseline migration | ✅ | `alembic/versions/0001…` |
| CORS endurecido, secretos fuera de repo, Redis opcional | ✅ | `app/main.py`, `.gitignore` |
| **Multi-tenant**: `Tenant`, `Plan`, `Suscripcion`, `TenantUser`, `id_tenant` en 9 tablas, FK + índices | ✅ | `app/models/tenant.py`, `0002…`, `0003…` |
| Middleware tenant + filtro global SQLAlchemy + ContextVar | ✅ | `app/core/tenant_*.py` |
| Backfill 1 taller = 1 tenant (idempotente) | ✅ | `scripts/backfill_tenants.py` |
| `id_tenant NOT NULL` en `taller`, filtro sin legacy | ✅ | `0003_tenant_not_null_taller` |
| Endpoints `POST /signup`, `POST /tenants`, `POST /tenants/{id}/talleres/link`, `GET /plans`, `/tenants/me`, … | ✅ | `app/api/tenants.py` |
| **Tests pytest 25/25 PASS** (signup, CRUD, isolation, plans) | ✅ | `tests/` |

**Cobertura del enunciado:** punto **4 (Multi-tenant)** ≈ 90% (falta panel de gestión de miembros y RBAC más fino). Lo demás está por construir.

---

## 1. Mapa enunciado → estado

| # | Funcionalidad del enunciado | Estado | Esfuerzo restante |
|---|---|---|---|
| 1 | Tiempo real (WebSocket + tracking + ETA) | ❌ | ALTO |
| 2 | Modo offline (Flutter + Angular) | ❌ | ALTO |
| 3 | Dashboard de KPIs | ❌ | MEDIO |
| 4 | SaaS Multi-tenant | 🟢 90% | BAJO |
| 5 | Registro de servicios por taller (7 tipos) | 🟡 parcial — existe `taller_servicio` y `categoria_problema`, faltan los 7 tipos del enunciado y el flujo de alta | MEDIO |
| 6 | Cotización (≥2-3 talleres) | ❌ | MEDIO-ALTO |
| 7 | Cancelación con compensación | ❌ | MEDIO |
| IA personalizada al contexto | 🟡 hay `ai_modules/` con Gemini, no está personalizado a talleres bolivianos / categorías oficiales | MEDIO |
| Marco teórico actualizado (WebSocket, multi-tenant, SaaS, KPI, tracking, offline) | ❌ | BAJO (es documentación) |

---

## 2. Calendario y entregables

| Fecha | Hito | Lo que debe estar funcionando |
|---|---|---|
| **19 may** | Inicio (hoy) | Multi-tenant + tests ✅ |
| **29 may** | 1ra presentación | Ciclo 1 completo |
| **7 jun** | 2da presentación | Ciclo 2 completo |
| **9 jun** | Defensa final | Ciclo 3 + ensayo |

3 semanas calendario, ≈ 14 días hábiles si descontamos fines de semana. Trabajo en 3 ciclos:

```
Ciclo 1 (10 días: 19-29 may) ─► Demo base + features "fáciles" pero visibles
Ciclo 2 (9 días: 30 may-7 jun) ─► Lo técnicamente caro (WS, tracking, offline, KPIs)
Ciclo 3 (2 días: 8-9 jun)       ─► Hardening + documentación + ensayo
```

---

## 3. Ciclo 1 — Fundamentos visibles (19 → 29 mayo)

**Objetivo de la 1ra presentación:** demostrar que el sistema ya es SaaS multi-tenant funcional, con catálogo extendido de talleres, cotizaciones comparativas y cancelación con compensación. La parte "wow" (tiempo real, mapa, offline) se reserva al ciclo 2.

### 1.1 Servicios extendidos por taller (2 días)
**Por qué primero:** todo lo demás (cotización, matching de incidentes, KPIs) depende de tener bien modelados los 7 tipos de servicio.

- [ ] Migración Alembic `0004_categorias_servicios_extendidas`: insertar (o actualizar) las 7 categorías oficiales:
  - llantas, mecánica general, eléctrico, electrónico, chapería y pintura, grúa / auxilio vial, servicio rutinario
- [ ] Campo `tarifa_base` en `taller_servicio` (Numeric(10,2), nullable) — base para cotización
- [ ] Endpoint `PUT /talleres/me/servicios` para que el taller declare/actualice sus servicios y tarifas
- [ ] Endpoint `GET /talleres?categoria=X&lat=…&lng=…` que filtra **solo talleres con esa especialidad**
- [ ] UI Angular: matriz de servicios en el dashboard del taller (checkbox + input de tarifa)
- [ ] UI Flutter: en "reportar emergencia", la IA propone categoría → backend filtra talleres compatibles
- [ ] Tests: alta de servicios, filtro por categoría, validaciones

**Criterios de aceptación:**
- Un taller "Llantería" no aparece como candidato para un incidente "chapería".
- 3 talleres de prueba registrados con servicios distintos demuestran el filtro.

### 1.2 Cotización (3 días)
- [ ] Modelos nuevos:
  - `Cotizacion` (id, id_incidente, id_taller, monto_servicio, monto_repuestos, garantia_dias, validez_hasta, estado, id_tenant)
  - `EstadoCotizacion` catálogo (pendiente / enviada / aceptada / rechazada / expirada)
- [ ] Migración `0005_cotizacion`
- [ ] Endpoints:
  - `POST /incidentes/{id}/cotizaciones/solicitar` (cliente pide a top-3 talleres compatibles)
  - `POST /cotizaciones/{id}/responder` (taller envía precio + repuestos + garantía)
  - `GET /incidentes/{id}/cotizaciones` (cliente compara las recibidas)
  - `POST /cotizaciones/{id}/aceptar` (cliente acepta → crea Asignacion)
- [ ] Notificación push al taller cuando le piden cotización (FCM ya integrado)
- [ ] UI cliente Flutter: pantalla de comparación lado a lado (precio, garantía, rating)
- [ ] UI taller Angular: bandeja de "cotizaciones por responder"
- [ ] Tests: solicitud a 3 talleres, expira en N min, aceptación crea asignación
- [ ] Regla del enunciado: aplica solo a "servicio requiere trabajo interno" → flag en categoría (`requiere_cotizacion`)

**Criterios:**
- Cliente recibe ≥2 cotizaciones para un incidente válido.
- Aceptar una cotización crea automáticamente la `Asignacion` correspondiente y **descarta** las otras.

### 1.3 Cancelación con compensación (2 días)
- [ ] Migración `0006_cancelacion`: añadir a `Asignacion`:
  - `cancelada_at` (timestamp)
  - `motivo_cancelacion` (texto)
  - `compensacion_monto` (Numeric)
  - `compensacion_pagada` (bool)
- [ ] Tabla `TarifaCompensacion` (id_taller, monto_base_traslado) o reutilizar `taller.tarifa_traslado`
- [ ] Endpoint `POST /asignaciones/{id}/cancelar` (cliente cancela; calcula compensación)
- [ ] Lógica: compensación = `tarifa_traslado` del taller (default $5) si la asignación ya pasó a `aceptada` o `en_camino`
- [ ] Notificación al taller: "Cancelación + compensación de $X pendiente"
- [ ] Generar `Pago` automático con `tipo=compensacion`, `monto_total=compensacion_monto`
- [ ] Tests: cancelar antes de aceptar (sin compensación), después de aceptar (con), después de completar (no se puede)

**Criterios:**
- Cliente puede cancelar y el taller ve el monto a recibir.
- Si llegan al mismo tiempo y el cliente se queda con seguro → taller igual recibe compensación.

### 1.4 Marco teórico — primera entrega (1 día)
- [ ] Sección "Multi-tenant y SaaS" — qué es, modelo elegido (shared-DB + tenant_id), trade-offs
- [ ] Sección "Servicios diferenciados y matching" — diagrama de flujo
- [ ] Sección "Cotización" — caso de uso UML + secuencia
- [ ] Actualizar diagramas de clase con nuevas entidades

### 1.5 Tests del ciclo 1 (continuo)
- [ ] `tests/test_servicios.py` (filtrado por categoría)
- [ ] `tests/test_cotizaciones.py` (flujo completo)
- [ ] `tests/test_cancelacion.py` (3 escenarios)
- Meta: **≥50 tests verdes** al cierre del ciclo.

### Riesgos ciclo 1
- ⚠️ Flutter — actualizar UI puede comer más tiempo que el backend. Mitigación: dejar UI funcional aunque feítos (no perfeccionar estilos hasta ciclo 3).
- ⚠️ Stripe / pagos reales no son requisito — usar `Pago` con estado simulado.

---

## 4. Ciclo 2 — Tiempo real, KPIs y offline (30 mayo → 7 junio)

**Objetivo de la 2da presentación:** la plataforma muestra el lado "premium" — broadcast de emergencia, mapa en vivo, dashboard de gestión y modo sin internet.

### 2.1 Redis + WebSocket infrastructure (1 día)
Pre-requisito para todo lo de tiempo real.
- [ ] Configurar Redis local (docker-compose o instalación nativa)
- [ ] `REDIS_URL` en `.env` (ya soportado)
- [ ] `app/realtime/ws_manager.py` — administra conexiones por canal (`tenant:{id}`, `incidente:{id}`, `taller:{id}`)
- [ ] Auth WS vía JWT en query string (`/ws?token=…`)
- [ ] `app/realtime/pubsub.py` — wrapper Redis pub/sub para que múltiples workers compartan eventos
- [ ] Endpoint `WS /ws` con dispatcher
- [ ] Test de conexión + auth

### 2.2 Broadcast de emergencia + first-accept-wins (2 días)
- [ ] Al crear un incidente:
  - Backend calcula talleres compatibles (categoría + radio en km + disponibles)
  - Publica evento `incidente.nuevo` en canal `taller:{id}` de cada candidato
  - Crea registros `CandidatoAsignacion` (ya existe el modelo)
- [ ] Cuando el primer taller acepta:
  - Transacción con `SELECT … FOR UPDATE` sobre `incidente` para garantizar atomicidad
  - Crea `Asignacion`
  - Publica `incidente.tomado` a los demás candidatos → su UI marca "ya no disponible"
- [ ] UI Angular taller: lista en vivo de emergencias entrantes con botón ACEPTAR
- [ ] UI Flutter cliente: ve cuántos talleres están viendo su pedido + cuando alguien acepta
- [ ] Tests: 3 talleres compiten, solo 1 gana, los otros reciben rechazo

**Criterios:**
- 3 talleres conectados, 1 emergencia, los 3 reciben push en <2s. Uno acepta, los otros 2 reciben evento de "tomado".

### 2.3 Tracking GPS en vivo + ETA (2 días)
- [ ] Tabla `ubicacion_tecnico` (id_usuario, lat, lng, accuracy_m, created_at) — particionar por día si crece
- [ ] Endpoint `POST /tecnicos/me/ubicacion` (batch cada 10-15s desde Flutter)
- [ ] Cada actualización publica `tecnico.posicion` en canal `incidente:{id}` → cliente lo ve en mapa
- [ ] ETA: usar **OSRM público** (`router.project-osrm.org`) o Google Directions con key gratis
- [ ] Geofencing: cuando técnico entra en radio de 100m del incidente → estado pasa a "llegado" automáticamente
- [ ] UI Flutter cliente: mapa (`flutter_map` + OpenStreetMap, sin costo) con marker en movimiento
- [ ] UI Angular taller: mapa con todos sus técnicos activos
- [ ] Tests: alta de ubicación, geofencing, cálculo de ETA simulado

**Riesgo:** permisos de GPS en Android (foreground service). Mitigación: pedir permisos al inicio de la asignación, no toda la app.

### 2.4 Dashboard de KPIs (2 días)
- [ ] Vista materializada o tabla `kpi_diario_taller` calculada por cron:
  - tiempo_promedio_asignacion_min (avg de `Asignacion.created_at - Incidente.created_at`)
  - tiempo_promedio_llegada_min (de `historial_estado_asignacion` aceptada → en_camino → completada)
  - incidentes_por_categoria (count group by)
  - rating_promedio (avg de `Evaluacion.estrellas`)
  - tasa_aceptacion (asignaciones aceptadas / candidatos)
- [ ] Endpoint `GET /tenants/{id}/kpis?desde=…&hasta=…` (scope por tenant via filtro global ya implementado ✅)
- [ ] Endpoint `GET /admin/kpis/ranking-talleres` (vista global super-admin)
- [ ] UI Angular: dashboard con **Chart.js o ECharts** (4 gráficos según enunciado)
- [ ] Tests: cálculo correcto sobre dataset semilla

### 2.5 Modo offline (3 días — el más caro)

**Angular (web):**
- [ ] `ng add @angular/pwa` (genera service worker, manifest, iconos)
- [ ] **Dexie.js** para IndexedDB: cache de incidentes, mensajes, asignaciones
- [ ] Outbox pattern: cola de mutaciones (POST/PUT) pendientes
- [ ] Interceptor HTTP: si offline → encolar; al reconectar → sync con backend
- [ ] Indicador UI "modo offline" + contador de pendientes
- [ ] Resolución de conflictos: last-write-wins por simplicidad

**Flutter (móvil):**
- [ ] Paquete `sqflite` o `drift` para BD local
- [ ] Repository pattern: lee local → fallback a remoto
- [ ] Outbox table para mutaciones pendientes
- [ ] `connectivity_plus` para detectar conexión
- [ ] Background sync al recuperar conexión
- [ ] Evidencias (fotos/audio): si offline, guardar path local + subir cuando vuelva
- [ ] Indicador UI de estado de sincronización por item

**Tests:**
- Simular offline con `httpx.MockTransport`
- Verificar que un POST encolado se reenvía al volver conexión

**Criterio del enunciado:** "visualizar y gestionar solicitudes existentes sin conexión" + "encolar solicitudes nuevas" → ambos cubiertos.

### 2.6 IA personalizada (1 día — paralelo)
- [ ] Adaptar `ai_modules/vision.py` y `audio.py` para:
  - Responder en español
  - Mapear a las 7 categorías oficiales del proyecto
  - Reconocer terminología local (ej. "se me pinchó la goma", "no enciende", "se quedó sin batería")
  - Sugerir prioridad según contexto (carretera vs ciudad)
- [ ] Cache de prompts en Redis (no quemar tokens)
- [ ] Tests con ejemplos de audio/foto reales del proyecto

---

## 5. Ciclo 3 — Hardening, defensa y entregables (8 → 9 junio)

### 5.1 Día 8 (lunes)
- [ ] Marco teórico completo y revisado — secciones nuevas: WebSocket, KPI, tracking, offline
- [ ] Actualizar diagramas UML: clases, secuencia (emergencia → broadcast → aceptación → tracking → cancelación)
- [ ] Manual de usuario corto: ¿cómo registrar un taller? ¿cómo recibir cotizaciones? ¿modo offline?
- [ ] Recorrer todos los endpoints de Swagger, eliminar deprecated, agregar descripciones
- [ ] Correr **toda la suite de tests** + medir cobertura (meta: ≥70%)

### 5.2 Día 9 (martes — defensa)
- [ ] Demo script: 10 escenarios cronometrados, datos pre-cargados
- [ ] Plan B por si Redis o GPS fallan en vivo: video de respaldo grabado
- [ ] Repaso de preguntas clásicas:
  - "¿Por qué multi-tenant shared-DB y no schema-per-tenant?"
  - "¿Cómo garantizan aislamiento?"
  - "¿Qué pasa si Redis cae?"
  - "¿Cómo escalan los WebSockets?"

---

## 6. Estructura técnica resultante (post-ciclos)

```
Backend/
├── alembic/versions/
│   ├── 0001_baseline_empty.py            ✅
│   ├── 0002_multi_tenant_skeleton.py     ✅
│   ├── 0003_tenant_not_null_taller.py    ✅
│   ├── 0004_categorias_servicios.py      🟡 Ciclo 1
│   ├── 0005_cotizacion.py                🟡 Ciclo 1
│   ├── 0006_cancelacion.py               🟡 Ciclo 1
│   ├── 0007_ubicacion_tecnico.py         🟡 Ciclo 2
│   └── 0008_kpi_diario.py                🟡 Ciclo 2
├── app/
│   ├── api/
│   │   ├── tenants.py        ✅
│   │   ├── cotizaciones.py   🟡 Ciclo 1
│   │   ├── kpis.py           🟡 Ciclo 2
│   │   └── (existentes…)
│   ├── realtime/             🟡 Ciclo 2
│   │   ├── ws_manager.py
│   │   ├── pubsub.py
│   │   └── handlers.py
│   ├── core/                 ✅ tenant_context/middleware/filter
│   └── services/             ➕ cotizacion_service, cancelacion_service, kpi_service
└── tests/
    ├── test_plans.py            ✅
    ├── test_signup.py           ✅
    ├── test_tenants_crud.py     ✅
    ├── test_tenant_isolation.py ✅
    ├── test_servicios.py        🟡 Ciclo 1
    ├── test_cotizaciones.py     🟡 Ciclo 1
    ├── test_cancelacion.py      🟡 Ciclo 1
    ├── test_ws.py               🟡 Ciclo 2
    ├── test_kpis.py             🟡 Ciclo 2
    └── test_offline_sync.py     🟡 Ciclo 2
```

---

## 7. Distribución sugerida si son grupo

| Rol | Ciclo 1 | Ciclo 2 |
|---|---|---|
| Backend dev 1 | Servicios + Cotización (1.1, 1.2) | WS infra + broadcast (2.1, 2.2) |
| Backend dev 2 | Cancelación + tests (1.3, 1.5) | Tracking + KPIs (2.3, 2.4) |
| Frontend Angular | Dashboard servicios + bandeja cotizaciones | Dashboard KPIs + PWA offline |
| Flutter | UI cotización + cancelación | Mapa tracking + SQLite offline |
| Tech lead / docs | Marco teórico + UML | Marco teórico final + manual |

Si son solo o 2 personas: **recortar IA personalizada y dejar KPIs más simples** (solo 2 indicadores). Lo del enunciado es no-negociable; el resto se prioriza.

---

## 8. Riesgos transversales

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Permisos GPS Android en background | Alta | Solo en foreground durante asignación activa |
| Offline + conflictos de sincronización | Alta | Last-write-wins, sin CRDT |
| WS no soportado por proxy / corp firewall en demo | Media | Probar polling fallback (long-polling) |
| Limite gratis Google Maps / Gemini | Media | OSRM + cache de prompts |
| Reloj se acaba | **Alta** | Reducir scope antes que entregar a medias — priorizar 1,3,4,5,6,7 sobre tracking si toca |
| Bug regresivo por filtro tenant en endpoints viejos | Media | Tests por endpoint + super-admin (tid=0) como escape hatch |

---

## 9. Checklist final pre-defensa (9 jun, mañana)

- [ ] `alembic upgrade head` aplica limpio en BD vacía
- [ ] `pytest` → todos verdes
- [ ] 3 tenants de demo cargados con servicios distintos
- [ ] Cliente de prueba con vehículo registrado
- [ ] Token de admin global a la mano
- [ ] Demo de WebSocket en 2 navegadores + 1 móvil simultáneos
- [ ] Mapa cargando offline (al menos tiles cacheados)
- [ ] Marco teórico impreso + diagramas UML actualizados
- [ ] Backup en USB del último commit + dump de BD

---

## 10. Convenciones del proyecto (recordatorio)

- Toda modificación de schema pasa por **Alembic** (no más `create_all`).
- Toda tabla con datos del taller debe llevar `id_tenant` (FK + index).
- Los endpoints públicos (cliente final) NO usan `require_tenant`.
- Los endpoints del panel de taller SÍ requieren tenant (filtro automático garantiza aislamiento).
- Tests nuevos van bajo `tests/` con fixtures de `conftest.py`. Cada test usa SAVEPOINT (rollback automático).
- Secretos NUNCA en repo: usar `.env` (gitignored) + `.env.example` plantilla.

---

**Última actualización:** 19 de mayo de 2026.
