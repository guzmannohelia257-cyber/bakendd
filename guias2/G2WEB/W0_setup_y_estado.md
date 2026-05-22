# W0 — Setup y adaptación al proyecto existente

> **Lee esto ANTES** de empezar W1-W7. Las otras guías asumen un proyecto limpio,
> pero `web/` **ya existe** con código del 1er parcial. Aquí ajustamos diferencias.

---

## 1. Estado actual del proyecto `web/`

### Lo que YA existe (no tocar / reusar)

| Path | Qué es |
|---|---|
| `src/app/app.routes.ts` | Rutas con guards (`authGuard`, `tipoGuard`, `adminGuard`) — **agregar** nuevas rutas aquí, no crear archivo nuevo |
| `src/app/auth/login.component.*` | Login funcional |
| `src/app/shared/services/auth.service.ts` | Login + token + currentUser/currentTaller |
| `src/app/shared/services/http.service.ts` | Cliente HTTP centralizado **— reusar para todos los endpoints nuevos** |
| `src/app/shared/services/admin.service.ts` | Endpoints admin existentes |
| `src/app/shared/services/asignaciones.service.ts` | Lógica de asignaciones existente |
| `src/app/shared/services/notificacion.service.ts` | FCM + notificaciones |
| `src/app/shared/services/taller.service.ts` | CRUD taller |
| `src/app/shared/guards/auth.guard.ts` | Guards de auth |
| `src/app/dashboards/taller/` | Dashboard taller con: `solicitudes`, `solicitud-detalle`, `resenas`, `historial`, `mensajes` |
| `src/app/dashboards/admin/` | Dashboard admin con: `ganancias`, `servicios`, `talleres` |
| `src/environments/environment.ts` | Apunta a `https://back-despliegue-cp05.onrender.com` (NO localhost) |

### Dependencias actuales (`package.json`)

| Paquete | Versión | Usa para |
|---|---|---|
| `@angular/*` | 21.2 | Core (standalone components) |
| `firebase` | 11.0 | FCM push |
| `leaflet` | 1.9 | Mapas (si quieres mostrar talleres en mapa) |
| `rxjs` | 7.8 | Streams |

### LO QUE FALTA INSTALAR (para C1+C2)

```bash
cd web

# Chart.js para KPIs (W6)
npm install chart.js

# Dexie para IndexedDB offline (W7)
npm install dexie

# PWA (W7)
ng add @angular/pwa
```

---

## 2. Diferencias clave vs. las guías W1-W7

### Diferencia #1 — Backend en Render, NO localhost

Las guías W1-W7 mencionan `http://localhost:8000` y `ws://localhost:8000`. **El proyecto real usa Render**:

```typescript
// environment.ts actual
apiUrl: 'https://back-despliegue-cp05.onrender.com',
```

**Cambios necesarios al `environment.ts`**:

```typescript
export const environment = {
  production: false,
  apiUrl: 'https://back-despliegue-cp05.onrender.com',
  wsUrl: 'wss://back-despliegue-cp05.onrender.com',  // ← AGREGAR
  firebase: {
    // ... lo que ya está
  },
};
```

> ⚠️ **WSS, no WS**: Render usa HTTPS → WebSocket debe ser `wss://`.

> ⚠️ **Render duerme tras 15 min**: la primera petición tras inactividad tarda 30-60s. Para defensa, hacer ping `GET /health` 5 min antes para "despertarlo".

### Diferencia #2 — Reusar `http.service.ts` existente

Las guías W1, W2, W3, W6 muestran servicios nuevos con `inject(HttpClient)` directo. **Mejor practica del proyecto: reusar `HttpService`**:

```typescript
// Ejemplo W1 — versión adaptada al proyecto
import { Injectable, inject } from '@angular/core';
import { HttpService } from '../../../shared/services/http.service';

@Injectable({ providedIn: 'root' })
export class ServiciosService {
  private http = inject(HttpService);

  listarCategorias() {
    return this.http.get<Categoria[]>('/categorias');
  }
  // ...
}
```

> Si `HttpService` no expone los verbos que necesitas, primero agregalos ahí. Es el patrón del proyecto.

### Diferencia #3 — Agregar rutas a `app.routes.ts` existente

Las nuevas pantallas van **dentro** del bloque `dashboard/taller` que ya existe:

```typescript
// app.routes.ts — modificar el array children del path 'taller'
{
  path: 'taller',
  canActivate: [tipoGuard(['taller'])],
  children: [
    { path: '', component: DashboardTallerComponent },
    { path: 'solicitudes', component: SolicitudesComponent },  // existente
    // ... otras existentes ...

    // ⬇ AGREGAR estas nuevas:
    {
      path: 'servicios',
      loadComponent: () => import('./dashboards/taller/servicios/servicios.component')
        .then(m => m.ServiciosComponent),
    },
    {
      path: 'cotizaciones',
      loadComponent: () => import('./dashboards/taller/cotizaciones/cotizaciones.component')
        .then(m => m.CotizacionesComponent),
    },
    {
      path: 'cancelaciones',
      loadComponent: () => import('./dashboards/taller/cancelaciones/cancelaciones.component')
        .then(m => m.CancelacionesComponent),
    },
    {
      path: 'emergencias',
      loadComponent: () => import('./dashboards/taller/emergencias/emergencias.component')
        .then(m => m.EmergenciasComponent),
    },
    {
      path: 'kpis',
      loadComponent: () => import('./dashboards/taller/kpis/kpis.component')
        .then(m => m.KpisComponent),
    },
  ]
},
```

### Diferencia #4 — RealtimeService: cargar tras login existente

Las guías W4 muestran cómo crear el `RealtimeService`. **Tu login actual** (`auth.service.ts`) ya devuelve token. Hay que **inyectar la conexión al RealtimeService** después del login:

En `auth.service.ts`, después de guardar el token (típicamente en el `tap` del `login()`):

```typescript
// Imports al top
import { RealtimeService } from './realtime.service';

// En el constructor:
constructor(
  private http: HttpClient,
  private rt: RealtimeService,  // ← AGREGAR
) {}

// En el método login, tras setear token:
login(...): Observable<...> {
  return this.http.post<LoginResponse>('...', body).pipe(
    tap(resp => {
      localStorage.setItem('token', resp.access_token);
      // ... lo demás
      this.rt.connect(resp.access_token);  // ← AGREGAR
    }),
  );
}

logout() {
  // ... lo existente
  this.rt.disconnect();  // ← AGREGAR
}
```

### Diferencia #5 — Service Worker no instalado todavía

W7 asume que `ng add @angular/pwa` ya fue ejecutado. **No está**. Ejecutar:

```bash
cd web
ng add @angular/pwa
```

Esto agrega:
- `ngsw-config.json`
- `src/manifest.webmanifest`
- Cambios en `angular.json` y `app.config.ts`
- Iconos en `src/assets/icons/`

---

## 3. Sidebar / menú del taller

El dashboard del taller actual (`dashboard-taller.component.html`) tiene un menú/sidebar. **Hay que agregar enlaces** a las nuevas pantallas:

```html
<!-- Sidebar del taller (ejemplo) -->
<nav>
  <a routerLink="solicitudes">Solicitudes</a>
  <a routerLink="historial">Historial</a>
  <a routerLink="resenas">Reseñas</a>

  <!-- NUEVOS -->
  <a routerLink="servicios">Mis Servicios</a>
  <a routerLink="cotizaciones">Cotizaciones</a>
  <a routerLink="emergencias">Emergencias en vivo</a>
  <a routerLink="kpis">Indicadores</a>
  <a routerLink="cancelaciones">Compensaciones</a>
</nav>
```

---

## 4. CORS del backend

El backend tiene `CORS_ORIGINS` en `.env`. Verificar que incluya el dominio del frontend desplegado:

```env
# Backend/.env
CORS_ORIGINS=http://localhost:4200,https://yary-front.vercel.app,https://back-despliegue-cp05.onrender.com
```

Si la web Angular está en **Vercel**, agregar la URL exacta a `CORS_ORIGINS` (no `*`).

---

## 5. Limpieza menor

- `web/google-services (1).json` — archivo basura, **borrar** (gitignore ya lo cubre).
- `web/IMPLEMENTACION_ADMIN_WEB.md` y otros .md viejos — ver si valen la pena mover a `guias2/` o eliminar.

---

## 6. Smoke test antes de implementar W1

```bash
cd web
npm install
npm start   # ng serve
# abrir http://localhost:4200
```

Verificar:
- [ ] Login funciona contra Render.
- [ ] Dashboard taller carga.
- [ ] Console no muestra errores.
- [ ] Devtools → Network → ping `/health` responde 200.

Si todo OK, arrancar **W1**.

---

## Checklist W0
- [ ] `npm install` corre limpio.
- [ ] Backend en Render despierto y responde.
- [ ] `chart.js`, `dexie` instalados.
- [ ] `ng add @angular/pwa` ejecutado.
- [ ] `environment.ts` con `wsUrl` agregado.
- [ ] CORS del backend incluye dominio frontend.
- [ ] App arranca con `npm start` sin errores.
- [ ] Patrón decidido: reusar `HttpService` o crear servicios por feature.
- [ ] Entendido cómo agregar rutas al `app.routes.ts` existente.

## Notas de orden
- **W4 (RealtimeService) primero**, antes que W5 (emergencias).
- **W1, W2, W3, W6, W7** son independientes — pueden ir en paralelo.
- Las pantallas pueden compartir el mismo layout del `DashboardTallerComponent`.
