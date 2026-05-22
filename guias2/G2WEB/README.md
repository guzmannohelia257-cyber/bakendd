# G2WEB — Guías de implementación frontend Angular

> Guías para el **panel web del taller** (Angular standalone).
> Carpeta separada de las guías de backend ([G2C1](../G2C1/), [G2C2](../G2C2/)) para que el equipo de front pueda trabajar sin distracciones.

## Pre-requisito
Que el backend correspondiente esté implementado. Cada `Wx.md` apunta al `Fx` de backend que debe estar antes.

> **⚠️ LEER PRIMERO**: [W0_setup_y_estado.md](./W0_setup_y_estado.md) — explica diferencias entre las guías W1-W7 y el estado real del proyecto `web/` (Angular 21.2, backend en Render, `HttpService` ya existente). **Hay que ajustar las guías a la realidad.**

| Web | Backend que la habilita | Producto |
|---|---|---|
| W0 | — | **Setup + adaptación al código existente (OBLIGATORIO LEER)** |
| W1 | [G2C1/F1](../G2C1/F1_servicios_extendidos.md) | Pantalla "Mis Servicios" del taller |
| W2 | [G2C1/F2](../G2C1/F2_cotizacion.md) | Bandeja de cotizaciones pendientes |
| W3 | [G2C1/F3](../G2C1/F3_cancelacion.md) | Columna "Compensaciones pendientes" |
| W4 | [G2C2/F1](../G2C2/F1_redis_websocket_infra.md) | `RealtimeService` (cliente WS Angular) |
| W5 | [G2C2/F2](../G2C2/F2_broadcast_emergencia.md) | Bandeja de emergencias en vivo + botón ACEPTAR |
| W6 | [G2C2/F4](../G2C2/F4_dashboard_kpis.md) | Dashboard KPIs con Chart.js |
| W7 | [G2C2/F5](../G2C2/F5_offline_web_angular.md) | PWA + IndexedDB + outbox |

## Orden de ejecución sugerido

```
W4 (RealtimeService) ─┬─► W5 (emergencias live)
                      └─► (otras pantallas que usen WS)

W1, W2, W3, W6, W7 son independientes entre si.
```

Para la **1ra presentación (29 may)**: W1, W2, W3 listos.
Para la **2da presentación (7 jun)**: W4, W5, W6, W7 listos.

---

## Stack / convenciones del proyecto Angular

| Capa | Tecnología |
|---|---|
| Framework | Angular 17+ standalone components |
| HTTP | `HttpClient` con interceptors |
| Rutas | `provideRouter()` |
| Estado | RxJS + signals (cuando aplique) |
| Tema UI | Angular Material (si ya está) |
| Charts | Chart.js (W6) |
| Offline | Service Worker + Dexie (W7) |
| WebSocket | nativo `WebSocket` API (W4) |

### Estructura recomendada
```
web/src/app/
├── app.config.ts               (providers globales)
├── app.routes.ts               (rutas)
├── auth/                       (login, guards)
├── dashboards/
│   ├── admin/
│   └── taller/
│       ├── servicios/          ← W1
│       ├── cotizaciones/       ← W2
│       ├── cancelaciones/      ← W3
│       ├── emergencias/        ← W5
│       └── kpis/               ← W6
└── shared/
    ├── services/
    │   ├── api.service.ts      (cliente HTTP base)
    │   ├── auth.service.ts
    │   └── realtime.service.ts ← W4
    └── offline/                ← W7
        ├── local-db.ts
        ├── outbox.service.ts
        └── offline.interceptor.ts
```

### Base URL del backend
Configurar en `environment.ts`:
```typescript
export const environment = {
  apiBase: 'http://localhost:8000',
  wsBase: 'ws://localhost:8000',
};
```

Todos los servicios usan `environment.apiBase` (no hardcodear URLs).

### Autenticación
JWT en `localStorage`, enviado en `Authorization: Bearer <token>` por un interceptor:
```typescript
// shared/auth.interceptor.ts
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('token');
  if (token) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }
  return next(req);
};
```

---

## Checklist de cierre por cada Wx
Cada archivo `Wx.md` cierra con su propio checklist. Genéricamente:
- [ ] Component creado y registrado en rutas.
- [ ] Servicio HTTP que consume los endpoints del backend correspondiente.
- [ ] Validaciones del formulario (si aplica).
- [ ] Indicador de carga / error.
- [ ] Verificado manualmente contra backend levantado.
- [ ] Screenshot agregado al manual de usuario ([G2D/D3](../G2D/D3_manual_usuario.md)).
