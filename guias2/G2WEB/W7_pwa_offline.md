# W7 — PWA + IndexedDB + Outbox (modo offline)

> **Backend requerido:** ninguno especial (cualquier endpoint REST funciona).
> **Esfuerzo:** 1.5 días.

## Objetivo (del enunciado)
> "Permitir visualizar y gestionar solicitudes existentes sin conexión. Encolar solicitudes nuevas realizadas sin internet para sincronizarlas al recuperar conexión."

Componentes:
1. **PWA** — app instalable, service worker cachea assets y respuestas GET.
2. **IndexedDB (Dexie)** — almacén local de entidades + outbox de mutaciones.
3. **HTTP interceptor** — detecta `!navigator.onLine`, encola POST/PUT/PATCH/DELETE.
4. **Sync worker** — drena la outbox al recuperar conexión.
5. **Banner UI** — muestra estado y cuenta de pendientes.

---

## 1. PWA setup

Desde `web/`:
```bash
ng add @angular/pwa
```

Esto genera:
- `ngsw-config.json`
- `manifest.webmanifest`
- Cambios en `angular.json` y `app.config.ts`.

### `ngsw-config.json` (editar)

```json
{
  "$schema": "./node_modules/@angular/service-worker/config/schema.json",
  "index": "/index.html",
  "assetGroups": [
    {
      "name": "app-shell",
      "installMode": "prefetch",
      "resources": {
        "files": ["/favicon.ico", "/index.html", "/manifest.webmanifest", "/*.css", "/*.js"]
      }
    },
    {
      "name": "assets",
      "installMode": "lazy",
      "updateMode": "prefetch",
      "resources": {
        "files": ["/assets/**", "/*.(svg|png|jpg|jpeg|webp|gif|otf|ttf|woff|woff2)"]
      }
    }
  ],
  "dataGroups": [
    {
      "name": "api-catalogos",
      "urls": ["/categorias", "/plans"],
      "cacheConfig": { "maxSize": 50, "maxAge": "1d", "strategy": "freshness", "timeout": "2s" }
    },
    {
      "name": "api-readonly",
      "urls": ["/tenants/me", "/talleres/mi-taller/**", "/incidencias/**"],
      "cacheConfig": { "maxSize": 200, "maxAge": "1h", "strategy": "freshness", "timeout": "3s" }
    }
  ]
}
```

> `freshness` = intenta red primero, fallback a cache. Ideal para datos del taller.

---

## 2. IndexedDB local (Dexie)

```bash
npm install dexie
```

### `web/src/app/shared/offline/local-db.ts`

```typescript
import Dexie, { Table } from 'dexie';

export interface CachedIncidente {
  id_incidente: number;
  id_categoria?: number;
  descripcion_usuario?: string;
  resumen_ia?: string;
  latitud: number;
  longitud: number;
  estado_nombre?: string;
  created_at: string;
  cached_at: string;
}

export interface OutboxItem {
  id?: number;
  client_id: string;        // UUID generado local (idempotencia server-side)
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  url: string;              // path completo, ej /incidencias
  body?: any;
  headers?: Record<string, string>;
  created_at: string;
  attempts: number;
  last_error?: string;
}

export class YaryLocalDB extends Dexie {
  incidentes!: Table<CachedIncidente, number>;
  outbox!: Table<OutboxItem, number>;

  constructor() {
    super('yary-offline');
    this.version(1).stores({
      incidentes: 'id_incidente, created_at',
      outbox: '++id, client_id, created_at',
    });
  }
}

export const localDB = new YaryLocalDB();
```

---

## 3. OutboxService

`web/src/app/shared/offline/outbox.service.ts`:

```typescript
import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { localDB, OutboxItem } from './local-db';

@Injectable({ providedIn: 'root' })
export class OutboxService {
  readonly pendingCount$ = new BehaviorSubject<number>(0);
  private syncing = false;

  constructor() {
    this._refreshCount();
    window.addEventListener('online', () => this.drain());
  }

  async enqueue(item: Omit<OutboxItem, 'id' | 'created_at' | 'attempts' | 'client_id'>): Promise<string> {
    const client_id = crypto.randomUUID();
    await localDB.outbox.add({
      ...item,
      client_id,
      created_at: new Date().toISOString(),
      attempts: 0,
    });
    this._refreshCount();
    return client_id;
  }

  async drain(maxAttempts = 5): Promise<void> {
    if (this.syncing || !navigator.onLine) return;
    this.syncing = true;
    try {
      const items = await localDB.outbox.orderBy('created_at').toArray();
      for (const item of items) {
        try {
          const resp = await fetch(item.url, {
            method: item.method,
            headers: {
              'Content-Type': 'application/json',
              'X-Client-Id': item.client_id,
              ...(item.headers || {}),
            },
            body: item.body ? JSON.stringify(item.body) : undefined,
          });
          if (resp.ok) {
            await localDB.outbox.delete(item.id!);
          } else if (resp.status >= 400 && resp.status < 500) {
            // 4xx: server rechaza, no reintentar
            await localDB.outbox.delete(item.id!);
          } else {
            // 5xx: reintentar
            await localDB.outbox.update(item.id!, {
              attempts: item.attempts + 1,
              last_error: `HTTP ${resp.status}`,
            });
            if (item.attempts + 1 >= maxAttempts) {
              await localDB.outbox.delete(item.id!);
            }
          }
        } catch (e: any) {
          await localDB.outbox.update(item.id!, {
            attempts: item.attempts + 1,
            last_error: e?.message ?? 'network error',
          });
        }
      }
    } finally {
      this.syncing = false;
      this._refreshCount();
    }
  }

  private async _refreshCount() {
    this.pendingCount$.next(await localDB.outbox.count());
  }
}
```

---

## 4. HTTP Interceptor

`web/src/app/shared/offline/offline.interceptor.ts`:

```typescript
import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { from, of, switchMap } from 'rxjs';
import { OutboxService } from './outbox.service';

const MUTATING = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export const offlineInterceptor: HttpInterceptorFn = (req, next) => {
  const outbox = inject(OutboxService);

  if (!navigator.onLine) {
    if (MUTATING.has(req.method)) {
      const headers: Record<string, string> = {};
      req.headers.keys().forEach(k => { headers[k] = req.headers.get(k)!; });

      return from(outbox.enqueue({
        method: req.method as any,
        url: req.urlWithParams,
        body: req.body,
        headers,
      })).pipe(
        switchMap(() => of(new HttpResponse({
          status: 202,
          body: { offline: true, queued: true, message: 'Encolado para sincronizar' },
        }))),
      );
    }
    // GET offline: 204 sin contenido (el SW debería servir del cache normalmente)
    return of(new HttpResponse({ status: 204, body: null }));
  }

  return next(req);
};
```

Registrarlo en `app.config.ts`:

```typescript
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { offlineInterceptor } from './shared/offline/offline.interceptor';
import { authInterceptor } from './shared/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([authInterceptor, offlineInterceptor])),
    // ...
  ],
};
```

---

## 5. Banner UI

`web/src/app/shared/offline/offline-banner.component.ts`:

```typescript
import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OutboxService } from './outbox.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-offline-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="!online" class="banner offline">
      ⚠️ Sin conexión — {{ pending }} acción(es) en cola
    </div>
    <div *ngIf="online && pending > 0" class="banner syncing">
      🔄 Sincronizando {{ pending }} acción(es) pendientes...
    </div>
  `,
  styles: [`
    .banner {
      padding: 0.5rem;
      text-align: center;
      color: white;
      font-weight: 600;
    }
    .offline { background: #dc3545; }
    .syncing { background: #f39c12; }
  `],
})
export class OfflineBannerComponent implements OnInit, OnDestroy {
  private outbox = inject(OutboxService);

  online = navigator.onLine;
  pending = 0;
  private sub?: Subscription;

  ngOnInit() {
    window.addEventListener('online', this._setOnline);
    window.addEventListener('offline', this._setOffline);
    this.sub = this.outbox.pendingCount$.subscribe(n => this.pending = n);
  }

  ngOnDestroy() {
    window.removeEventListener('online', this._setOnline);
    window.removeEventListener('offline', this._setOffline);
    this.sub?.unsubscribe();
  }

  private _setOnline = () => { this.online = true; this.outbox.drain(); };
  private _setOffline = () => { this.online = false; };
}
```

Incluir en `app.html`:
```html
<app-offline-banner />
<router-outlet />
```

(Recordar importar `OfflineBannerComponent` en el componente raíz.)

---

## 6. Espejo de datos read-only (opcional, complementa SW)

En servicios que cargan listas:

```typescript
async cargarIncidentes() {
  try {
    const data = await firstValueFrom(this.http.get<Incidente[]>('/incidencias/mis-incidencias'));
    // Espejar en IndexedDB
    await localDB.transaction('rw', localDB.incidentes, async () => {
      await localDB.incidentes.clear();
      await localDB.incidentes.bulkAdd(
        data.map(i => ({ ...i, cached_at: new Date().toISOString() })),
      );
    });
    return data;
  } catch {
    // Offline: leer cache local
    return await localDB.incidentes.orderBy('created_at').reverse().toArray();
  }
}
```

---

## Validación manual

1. Build production:
   ```bash
   cd web && ng build --configuration production
   ```
2. Servir con HTTPS (el SW solo funciona en HTTPS o localhost):
   ```bash
   npx http-server -S -C cert.pem -K key.pem dist/web/browser
   ```
   O simplemente `npx http-server dist/web/browser -p 8080` (localhost).
3. DevTools → Application → Service Workers → confirmar "activated and running".
4. DevTools → Network → "Offline".
5. Navegar al listado de incidentes: debe cargar del cache.
6. Crear incidente nuevo: debe responder 202 con `{ queued: true }`.
7. DevTools → Application → IndexedDB → `yary-offline` → `outbox`: ver el item.
8. Volver a "Online" → en <2s la outbox se drena.
9. Refrescar lista: el incidente nuevo aparece con `id_incidente` real del servidor.
10. Lighthouse → tab "PWA" → score > 80.

---

## Checklist de cierre W7
- [ ] `ng add @angular/pwa` ejecutado, manifest + SW activos.
- [ ] `ngsw-config.json` cachea catálogos y datos del taller.
- [ ] `dexie` instalado, `localDB` con tablas correctas.
- [ ] HTTP interceptor encola mutaciones cuando `!navigator.onLine`.
- [ ] `OutboxService.drain()` sincroniza al volver conexión.
- [ ] `OfflineBannerComponent` visible.
- [ ] `X-Client-Id` en cada request encolado (para idempotencia server-side).
- [ ] Verificado: build prod, modo avión, crear y sincronizar.
- [ ] Lighthouse PWA score > 80.

## Notas / troubleshooting
- **HTTPS en producción**: el SW solo funciona en HTTPS o localhost. Para demo en LAN usar `mkcert`.
- **Conflictos**: last-write-wins implícito. Para detección formal, agregar columna `version` en server y rechazar con 409.
- **Tokens expirados**: si un POST encolado falla con 401 al sincronizar, el outbox lo descarta (4xx). Mostrar UX "Sesión expirada".
- **Tamaño outbox**: limitar a 100 items o limpiar items con >7 días.
