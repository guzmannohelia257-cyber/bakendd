# W5 — Bandeja de emergencias en vivo + first-accept-wins

> **Backend requerido:** [G2C2/F2](../G2C2/F2_broadcast_emergencia.md) implementado.
> **Pre-requisito frontend:** [W4](./W4_websocket_client.md) (RealtimeService).
> **Esfuerzo:** 1 día.

## Objetivo
Dashboard donde el taller ve emergencias entrantes en tiempo real (via WebSocket) y puede aceptarlas con un click. Si otro taller la toma primero, la tarjeta queda gris.

Eventos WS escuchados (canal `taller:{id}` auto-suscrito al login):
- `incidente.nuevo` — emergencia entrante compatible
- `incidente.tomado` — otro taller ya aceptó

Endpoint HTTP:
- `POST /incidentes/{id}/aceptar` — intentar tomar el servicio

---

## Archivos

`web/src/app/dashboards/taller/emergencias/`:
```
emergencias/
├── emergencias.component.ts
├── emergencias.component.html
├── emergencias.component.scss
└── emergencias.service.ts
```

## `emergencias.service.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class EmergenciasService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  aceptar(idIncidente: number) {
    return this.http.post<{ id_asignacion: number; id_taller: number; nuevo_estado: string }>(
      `${this.base}/incidentes/${idIncidente}/aceptar`,
      {},
    );
  }
}
```

## `emergencias.component.ts`

```typescript
import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { RealtimeService, WSEvent } from '../../../shared/services/realtime.service';
import { EmergenciasService } from './emergencias.service';

interface EmergenciaLive {
  id_incidente: number;
  id_categoria?: number;
  latitud: number;
  longitud: number;
  descripcion_usuario?: string;
  resumen_ia?: string;
  created_at: string;

  tomado?: boolean;
  aceptando?: boolean;
  mio?: boolean;     // este taller la acepto
  error?: string;
}

@Component({
  selector: 'app-emergencias',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './emergencias.component.html',
  styleUrls: ['./emergencias.component.scss'],
})
export class EmergenciasComponent implements OnInit, OnDestroy {
  private rt = inject(RealtimeService);
  private svc = inject(EmergenciasService);

  emergencias = signal<EmergenciaLive[]>([]);
  private sub?: Subscription;

  ngOnInit() {
    // El backend ya nos suscribio a taller:{id} en el connected.
    this.sub = this.rt.events$.subscribe(evt => this._handleEvent(evt));
  }

  private _handleEvent(evt: WSEvent) {
    if (evt.event === 'incidente.nuevo') {
      const e: EmergenciaLive = { ...evt.data };
      // Insertar al inicio sin duplicar
      this.emergencias.update(arr => {
        if (arr.some(x => x.id_incidente === e.id_incidente)) return arr;
        return [e, ...arr];
      });
    } else if (evt.event === 'incidente.tomado') {
      this.emergencias.update(arr =>
        arr.map(e =>
          e.id_incidente === evt.data.id_incidente ? { ...e, tomado: true } : e
        ),
      );
    } else if (evt.event === 'incidente.asignado') {
      // Yo gane: marcar mio
      this.emergencias.update(arr =>
        arr.map(e =>
          e.id_incidente === evt.data.id_incidente
            ? { ...e, mio: true, aceptando: false }
            : e
        ),
      );
    }
  }

  aceptar(e: EmergenciaLive) {
    e.aceptando = true;
    e.error = undefined;
    this.svc.aceptar(e.id_incidente).subscribe({
      next: () => {
        e.aceptando = false;
        e.mio = true;
      },
      error: (err) => {
        e.aceptando = false;
        if (err.status === 409) {
          e.tomado = true;
        } else {
          e.error = err.error?.detail ?? 'Error aceptando';
        }
      },
    });
  }

  abrirEnMaps(e: EmergenciaLive) {
    window.open(
      `https://www.google.com/maps?q=${e.latitud},${e.longitud}`,
      '_blank',
    );
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }
}
```

## `emergencias.component.html`

```html
<div class="emergencias-page">
  <header>
    <h1>Emergencias entrantes</h1>
    <p class="hint">
      Aquí aparecen las solicitudes compatibles con tus servicios en tiempo real.
      El primer taller que acepta gana — los otros verán "ya tomada".
    </p>
  </header>

  <div *ngIf="emergencias().length === 0" class="empty">
    Esperando emergencias...
  </div>

  <div class="grid">
    <div *ngFor="let e of emergencias()" class="card"
         [class.tomada]="e.tomado && !e.mio"
         [class.mia]="e.mio">
      <div class="header">
        <strong>Incidente #{{ e.id_incidente }}</strong>
        <span class="time">{{ e.created_at | date:'shortTime' }}</span>
      </div>

      <div class="resumen">
        {{ e.resumen_ia || e.descripcion_usuario || 'Sin descripción' }}
      </div>

      <div class="ubicacion">
        <button class="link" (click)="abrirEnMaps(e)">
          📍 {{ e.latitud | number:'1.4-4' }}, {{ e.longitud | number:'1.4-4' }}
        </button>
      </div>

      <div class="acciones">
        <button *ngIf="!e.tomado && !e.mio"
                (click)="aceptar(e)"
                [disabled]="e.aceptando"
                class="primary">
          {{ e.aceptando ? 'Aceptando...' : 'ACEPTAR' }}
        </button>

        <div *ngIf="e.tomado && !e.mio" class="status muted">
          Ya fue tomado por otro taller
        </div>

        <div *ngIf="e.mio" class="status ok">
          ✓ Aceptado por tu taller
        </div>

        <div *ngIf="e.error" class="status error">
          {{ e.error }}
        </div>
      </div>
    </div>
  </div>
</div>
```

## `emergencias.component.scss`

```scss
.emergencias-page {
  padding: 1.5rem;
  max-width: 1200px;
}

header {
  margin-bottom: 1.5rem;
}

.empty {
  text-align: center;
  padding: 4rem 1rem;
  color: #888;
  font-style: italic;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: opacity 0.3s;

  &.tomada {
    opacity: 0.4;
    pointer-events: none;
  }

  &.mia {
    border-color: #28a745;
    background: #f0fdf4;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    .time { font-size: 0.8rem; color: #888; }
  }

  .resumen {
    font-size: 0.95rem;
    color: #333;
    min-height: 3em;
  }

  .ubicacion .link {
    background: none;
    border: none;
    color: #007bff;
    cursor: pointer;
    padding: 0;
    font-size: 0.85rem;
  }

  .acciones {
    margin-top: auto;
    button.primary {
      width: 100%;
      background: #dc3545;
      color: white;
      padding: 12px;
      border: none;
      border-radius: 4px;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      &:disabled { background: #aaa; cursor: not-allowed; }
    }

    .status {
      padding: 8px;
      text-align: center;
      &.muted { color: #888; }
      &.ok { color: #28a745; font-weight: 600; }
      &.error { color: #dc3545; }
    }
  }
}
```

## Ruta
```typescript
{
  path: 'emergencias',
  loadComponent: () =>
    import('./emergencias/emergencias.component').then(m => m.EmergenciasComponent),
},
```

> **Importante**: la pantalla de emergencias debe ser la pantalla por defecto del dashboard del taller (`path: ''` o redirigir desde el index).

---

## Sonido / notificación (recomendado)

Para que el operador del taller no pierda emergencias:

```typescript
// emergencias.component.ts
private _handleEvent(evt: WSEvent) {
  if (evt.event === 'incidente.nuevo') {
    this._playBeep();
    // ...
  }
}

private _playBeep() {
  try {
    const audio = new Audio('/assets/beep.mp3');
    audio.play().catch(() => {});  // ignorar si el browser bloquea autoplay
  } catch {}
}
```

Y notificación nativa del SO (pedir permiso una vez):
```typescript
if ('Notification' in window && Notification.permission === 'granted') {
  new Notification('Nueva emergencia', { body: e.resumen_ia });
}
```

---

## Validación manual (demo escenario 4 del [G2D/D4](../G2D/D4_guion_demo.md))
1. 3 navegadores con 3 talleres logueados, cada uno en `/emergencias`.
2. Cliente reporta un incidente compatible con los 3.
3. Las 3 pantallas deben mostrar la tarjeta nueva en <2s.
4. Click ACEPTAR en uno → los otros 2 quedan en gris con "Ya fue tomado".

## Checklist de cierre W5
- [ ] Eventos `incidente.nuevo`, `incidente.tomado`, `incidente.asignado` manejados.
- [ ] No duplica emergencias si llega el evento dos veces.
- [ ] Click ACEPTAR llama al endpoint y maneja 409 graciosamente.
- [ ] Tarjeta tomada visualmente atenuada y sin botón.
- [ ] Tarjeta aceptada por mí en verde.
- [ ] Beep / notification opcional implementados.
- [ ] Pantalla es la default del dashboard del taller.
