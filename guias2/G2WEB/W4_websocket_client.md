# W4 — RealtimeService (cliente WebSocket Angular)

> **Backend requerido:** [G2C2/F1](../G2C2/F1_redis_websocket_infra.md) implementado.
> **Bloquea:** W5 (emergencias en vivo).
> **Esfuerzo:** 0.5 día.

## Objetivo
Servicio Angular que mantiene una conexión WebSocket persistente con el backend, reconecta automáticamente, expone eventos como `Observable`, y permite suscribirse/desuscribirse de canales dinámicamente.

Endpoint consumido:
- `WS /ws?token=<JWT>` — handshake con auth en query string

---

## Archivos

`web/src/app/shared/services/realtime.service.ts`

## Código completo

```typescript
import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface WSEvent {
  event: string;
  data?: any;
  channel?: string;
  channels?: string[];
  identity?: { tipo: string; sub_id: number };
  detail?: string;
}

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

@Injectable({ providedIn: 'root' })
export class RealtimeService implements OnDestroy {
  private ws?: WebSocket;
  private token?: string;
  private wsBase = environment.wsBase;

  // Backoff exponencial: 1s, 2s, 4s, 8s, max 30s
  private reconnectAttempts = 0;
  private reconnectTimer?: any;
  private disposed = false;

  // Set local de canales para resubscribir tras reconectar
  private subscribedChannels = new Set<string>();

  readonly events$ = new Subject<WSEvent>();
  readonly state$ = new BehaviorSubject<ConnectionState>('disconnected');

  /** Iniciar conexión con el JWT actual (llamar tras login). */
  connect(token: string): void {
    this.token = token;
    this.disposed = false;
    this._connect();
  }

  /** Cerrar conexión definitivamente (llamar al logout o destroy). */
  disconnect(): void {
    this.disposed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = undefined;
    }
    this.subscribedChannels.clear();
    this.state$.next('disconnected');
  }

  /** Suscribirse a un canal (ej. "incidente:42"). */
  subscribe(channel: string): void {
    this.subscribedChannels.add(channel);
    this._send({ action: 'subscribe', channel });
  }

  unsubscribe(channel: string): void {
    this.subscribedChannels.delete(channel);
    this._send({ action: 'unsubscribe', channel });
  }

  /** Ping manual (el servidor responde pong). */
  ping(): void {
    this._send({ action: 'ping' });
  }

  // ---- privados ----

  private _connect(): void {
    if (!this.token) return;
    if (this.disposed) return;

    this.state$.next(this.reconnectAttempts === 0 ? 'connecting' : 'reconnecting');

    const url = `${this.wsBase}/ws?token=${encodeURIComponent(this.token)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.state$.next('connected');
      // Re-suscribir a todos los canales del set local
      for (const ch of this.subscribedChannels) {
        this._send({ action: 'subscribe', channel: ch });
      }
    };

    this.ws.onmessage = (e) => {
      try {
        const msg: WSEvent = JSON.parse(e.data);
        this.events$.next(msg);
      } catch (err) {
        console.error('WS message no parseable', e.data);
      }
    };

    this.ws.onerror = (e) => {
      console.warn('WS error', e);
    };

    this.ws.onclose = (e) => {
      this.ws = undefined;
      this.state$.next('disconnected');
      if (this.disposed) return;

      // Si el cierre fue 1008 (auth fallida), no reintentar con el mismo token
      if (e.code === 1008) {
        console.error('WS auth fallo - token invalido. No reintento.');
        return;
      }
      this._scheduleReconnect();
    };
  }

  private _scheduleReconnect(): void {
    const delay = Math.min(30_000, 1000 * 2 ** this.reconnectAttempts);
    this.reconnectAttempts++;
    this.state$.next('reconnecting');
    this.reconnectTimer = setTimeout(() => this._connect(), delay);
  }

  private _send(payload: object): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
```

---

## Cómo se conecta

### Después del login

En el componente / servicio de login, **después** de guardar el token:

```typescript
// auth.service.ts (login exitoso)
import { RealtimeService } from '../shared/services/realtime.service';

constructor(private rt: RealtimeService) {}

afterLogin(token: string) {
  localStorage.setItem('token', token);
  this.rt.connect(token);
}

logout() {
  localStorage.removeItem('token');
  this.rt.disconnect();
}
```

### Al inicializar la app (si ya hay token)

`app.config.ts` o `APP_INITIALIZER`:

```typescript
import { APP_INITIALIZER, inject } from '@angular/core';
import { RealtimeService } from './shared/services/realtime.service';

function initRealtime() {
  return () => {
    const rt = inject(RealtimeService);
    const token = localStorage.getItem('token');
    if (token) rt.connect(token);
  };
}

export const appConfig: ApplicationConfig = {
  providers: [
    // ...
    { provide: APP_INITIALIZER, useFactory: initRealtime, multi: true },
  ],
};
```

---

## Cómo se usa en un componente

```typescript
import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Subscription } from 'rxjs';
import { RealtimeService } from '../../shared/services/realtime.service';

@Component({...})
export class MisIncidentesComponent implements OnInit, OnDestroy {
  private rt = inject(RealtimeService);
  private sub?: Subscription;

  ngOnInit() {
    this.rt.subscribe('incidente:42');
    this.sub = this.rt.events$.subscribe(evt => {
      if (evt.event === 'incidente.actualizado' && evt.channel === 'incidente:42') {
        console.log('Mi incidente cambió:', evt.data);
      }
    });
  }

  ngOnDestroy() {
    this.rt.unsubscribe('incidente:42');
    this.sub?.unsubscribe();
  }
}
```

---

## Indicador de estado de conexión

Componente `web/src/app/shared/components/connection-badge.component.ts`:

```typescript
import { Component, inject } from '@angular/core';
import { CommonModule, AsyncPipe } from '@angular/common';
import { RealtimeService } from '../services/realtime.service';

@Component({
  selector: 'app-connection-badge',
  standalone: true,
  imports: [CommonModule, AsyncPipe],
  template: `
    <span class="badge" [class]="(rt.state$ | async)">
      {{ stateLabel(rt.state$ | async) }}
    </span>
  `,
  styles: [`
    .badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: white; }
    .badge.connected { background: #28a745; }
    .badge.connecting, .badge.reconnecting { background: #f39c12; }
    .badge.disconnected { background: #6c757d; }
  `],
})
export class ConnectionBadgeComponent {
  rt = inject(RealtimeService);
  stateLabel(s: string | null) {
    return { connected: 'En vivo', connecting: 'Conectando…', reconnecting: 'Reconectando…', disconnected: 'Desconectado' }[s ?? 'disconnected'];
  }
}
```

Insertar en el header del dashboard:
```html
<app-connection-badge />
```

---

## Validación manual
1. Backend WS levantado.
2. Login en el panel del taller.
3. DevTools → Network → WS → ver conexión a `/ws?token=...`.
4. Cerrar el backend → ver que el badge cambia a "Reconectando…".
5. Reiniciar backend → vuelve a "En vivo".
6. Verificar que un evento publicado desde el backend (`pubsub_broker.publish("taller:N", ...)`) aparece en `events$`.

## Checklist de cierre W4
- [ ] Conexión inicial al login.
- [ ] Reconexión automática con backoff exponencial.
- [ ] No reintenta si el cierre fue 1008 (auth).
- [ ] Re-suscripción automática a canales tras reconectar.
- [ ] Badge visible de estado de conexión.
- [ ] Servicio expone `events$` (Subject) y `state$` (BehaviorSubject).
- [ ] Cleanup al `disconnect()` (logout).
