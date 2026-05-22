# W2 — Bandeja de cotizaciones del taller

> **Backend requerido:** [G2C1/F2](../G2C1/F2_cotizacion.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
Bandeja donde el taller ve cotizaciones pendientes de responder y envía su oferta (monto servicio, repuestos, garantía).

Endpoints consumidos:
- `GET /talleres/mi-taller/cotizaciones?estado=pendiente` — bandeja
- `POST /cotizaciones/{id}/responder` — enviar oferta

---

## Archivos

`web/src/app/dashboards/taller/cotizaciones/`:
```
cotizaciones/
├── cotizaciones.component.ts
├── cotizaciones.component.html
├── cotizaciones.component.scss
├── responder-dialog.component.ts
└── cotizaciones.service.ts
```

## `cotizaciones.service.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface Cotizacion {
  id_cotizacion: number;
  id_incidente: number;
  id_taller: number;
  monto_servicio?: number;
  monto_repuestos?: number;
  garantia_dias?: number;
  nota?: string;
  validez_hasta?: string;
  created_at: string;
  estado?: { id_estado_cotizacion: number; nombre: string };
}

export interface ResponderRequest {
  monto_servicio: number;
  monto_repuestos: number;
  garantia_dias?: number;
  nota?: string;
}

@Injectable({ providedIn: 'root' })
export class CotizacionesService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  bandeja(estado: string = 'pendiente'): Observable<Cotizacion[]> {
    return this.http.get<Cotizacion[]>(
      `${this.base}/talleres/mi-taller/cotizaciones?estado=${estado}`
    );
  }

  responder(idCotizacion: number, body: ResponderRequest): Observable<Cotizacion> {
    return this.http.post<Cotizacion>(
      `${this.base}/cotizaciones/${idCotizacion}/responder`,
      body,
    );
  }
}
```

## `cotizaciones.component.ts`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CotizacionesService, Cotizacion, ResponderRequest } from './cotizaciones.service';

@Component({
  selector: 'app-cotizaciones',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './cotizaciones.component.html',
  styleUrls: ['./cotizaciones.component.scss'],
})
export class CotizacionesComponent implements OnInit {
  private svc = inject(CotizacionesService);

  bandeja: Cotizacion[] = [];
  filtroEstado: 'pendiente' | 'enviada' | 'aceptada' | 'rechazada' | 'expirada' = 'pendiente';
  cargando = true;

  // Estado del modal
  cotEditando: Cotizacion | null = null;
  form: ResponderRequest = { monto_servicio: 0, monto_repuestos: 0 };
  guardando = false;
  errorForm: string | null = null;

  ngOnInit() {
    this.cargar();
  }

  cargar() {
    this.cargando = true;
    this.svc.bandeja(this.filtroEstado).subscribe({
      next: (data) => { this.bandeja = data; this.cargando = false; },
      error: () => { this.cargando = false; },
    });
  }

  abrirResponder(cot: Cotizacion) {
    this.cotEditando = cot;
    this.form = {
      monto_servicio: cot.monto_servicio ?? 0,
      monto_repuestos: cot.monto_repuestos ?? 0,
      garantia_dias: cot.garantia_dias,
      nota: cot.nota,
    };
    this.errorForm = null;
  }

  cancelarEdicion() {
    this.cotEditando = null;
  }

  enviarRespuesta() {
    if (!this.cotEditando) return;
    if (this.form.monto_servicio < 0 || this.form.monto_repuestos < 0) {
      this.errorForm = 'Los montos no pueden ser negativos';
      return;
    }
    this.guardando = true;
    this.svc.responder(this.cotEditando.id_cotizacion, this.form).subscribe({
      next: () => {
        this.guardando = false;
        this.cotEditando = null;
        this.cargar();
      },
      error: (e) => {
        this.errorForm = e.error?.detail ?? 'Error enviando respuesta';
        this.guardando = false;
      },
    });
  }

  esExpirada(cot: Cotizacion): boolean {
    if (!cot.validez_hasta) return false;
    return new Date(cot.validez_hasta) < new Date();
  }
}
```

## `cotizaciones.component.html`

```html
<div class="cotizaciones-page">
  <h1>Cotizaciones</h1>

  <div class="filtros">
    <label>Estado:</label>
    <select [(ngModel)]="filtroEstado" (change)="cargar()">
      <option value="pendiente">Pendientes</option>
      <option value="enviada">Enviadas</option>
      <option value="aceptada">Aceptadas</option>
      <option value="rechazada">Rechazadas</option>
      <option value="expirada">Expiradas</option>
    </select>
  </div>

  <div *ngIf="cargando">Cargando...</div>

  <div *ngIf="!cargando && bandeja.length === 0" class="empty">
    No hay cotizaciones en estado "{{ filtroEstado }}".
  </div>

  <table *ngIf="!cargando && bandeja.length > 0" class="bandeja">
    <thead>
      <tr>
        <th>Incidente</th>
        <th>Solicitada</th>
        <th>Vence</th>
        <th>Monto total</th>
        <th>Garantía</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr *ngFor="let c of bandeja" [class.expirada]="esExpirada(c)">
        <td>#{{ c.id_incidente }}</td>
        <td>{{ c.created_at | date:'short' }}</td>
        <td>{{ c.validez_hasta | date:'short' }}</td>
        <td>
          <span *ngIf="c.monto_servicio !== null && c.monto_servicio !== undefined">
            ${{ (c.monto_servicio || 0) + (c.monto_repuestos || 0) }}
          </span>
          <span *ngIf="c.monto_servicio === null || c.monto_servicio === undefined" class="muted">
            sin cotizar
          </span>
        </td>
        <td>{{ c.garantia_dias ? c.garantia_dias + ' días' : '-' }}</td>
        <td>
          <button *ngIf="filtroEstado === 'pendiente' && !esExpirada(c)"
                  (click)="abrirResponder(c)">
            Responder
          </button>
        </td>
      </tr>
    </tbody>
  </table>

  <!-- Modal de respuesta -->
  <div *ngIf="cotEditando" class="modal-backdrop" (click)="cancelarEdicion()">
    <div class="modal" (click)="$event.stopPropagation()">
      <h2>Responder cotización #{{ cotEditando.id_cotizacion }}</h2>

      <div class="campo">
        <label>Monto del servicio (USD)</label>
        <input type="number" [(ngModel)]="form.monto_servicio" min="0">
      </div>
      <div class="campo">
        <label>Monto de repuestos (USD)</label>
        <input type="number" [(ngModel)]="form.monto_repuestos" min="0">
      </div>
      <div class="campo">
        <label>Garantía (días)</label>
        <input type="number" [(ngModel)]="form.garantia_dias" min="0" max="365">
      </div>
      <div class="campo">
        <label>Nota (opcional)</label>
        <textarea [(ngModel)]="form.nota" maxlength="1000" rows="3"></textarea>
      </div>

      <div *ngIf="errorForm" class="error">{{ errorForm }}</div>

      <div class="acciones">
        <button class="secondary" (click)="cancelarEdicion()" [disabled]="guardando">
          Cancelar
        </button>
        <button (click)="enviarRespuesta()" [disabled]="guardando">
          {{ guardando ? 'Enviando...' : 'Enviar oferta' }}
        </button>
      </div>
    </div>
  </div>
</div>
```

## `cotizaciones.component.scss`

```scss
.cotizaciones-page { padding: 1.5rem; max-width: 1100px; }

.filtros { margin-bottom: 1rem; display: flex; gap: 0.5rem; align-items: center; }

.empty {
  text-align: center;
  padding: 3rem;
  color: #888;
}

.bandeja {
  width: 100%;
  border-collapse: collapse;
  th, td { padding: 0.75rem; border-bottom: 1px solid #eee; text-align: left; }
  thead { background: #f5f5f5; }
  tr.expirada { opacity: 0.5; }
}

.muted { color: #888; }
.error { color: #dc3545; margin: 0.5rem 0; }

.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}

.modal {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  width: 480px;
  max-width: 90vw;

  h2 { margin-top: 0; }
  .campo { margin: 1rem 0; }
  .campo label { display: block; margin-bottom: 0.25rem; font-weight: 600; }
  .campo input, .campo textarea { width: 100%; padding: 6px; box-sizing: border-box; }

  .acciones {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1rem;
  }
  .secondary { background: #e9ecef; color: #333; }
}
```

## Ruta

```typescript
{
  path: 'cotizaciones',
  loadComponent: () =>
    import('./cotizaciones/cotizaciones.component').then(m => m.CotizacionesComponent),
},
```

---

## Validación manual
1. Crear varios incidentes de chapería/mecánica desde el cliente (Postman o mobile).
2. Solicitar cotizaciones: `POST /incidentes/{id}/cotizaciones/solicitar`.
3. Entrar al panel de cualquier taller invitado.
4. Ver la cotización pendiente en la bandeja.
5. Click "Responder", llenar monto, enviar.
6. Cambiar filtro a "Enviadas" → debe aparecer ahí.

## Checklist de cierre W2
- [ ] Bandeja filtrable por estado.
- [ ] Fila expirada visualmente atenuada.
- [ ] Botón "Responder" solo en pendientes no expiradas.
- [ ] Modal con validación de montos no negativos.
- [ ] Recarga automática tras responder.
