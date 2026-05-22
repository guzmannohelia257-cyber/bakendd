# W3 — Panel de compensaciones pendientes

> **Backend requerido:** [G2C1/F3](../G2C1/F3_cancelacion.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
Pantalla donde el taller ve sus asignaciones canceladas y la compensación pendiente de cobro. También permite configurar la `tarifa_traslado` propia.

Endpoints consumidos:
- `GET /talleres/mi-taller/asignaciones?estado=cancelada` (existente en backend)
- `PATCH /talleres/mi-taller/tarifa-traslado` (de G2C1/F3)

---

## Archivos

`web/src/app/dashboards/taller/cancelaciones/`:
```
cancelaciones/
├── cancelaciones.component.ts
├── cancelaciones.component.html
├── cancelaciones.component.scss
└── cancelaciones.service.ts
```

## `cancelaciones.service.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface AsignacionCancelada {
  id_asignacion: number;
  id_incidente: number;
  cancelada_at?: string;
  cancelada_por?: string;
  motivo_cancelacion?: string;
  compensacion_monto?: number;
  compensacion_pagada: boolean;
  // ... otros campos del response existente
}

@Injectable({ providedIn: 'root' })
export class CancelacionesService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  misCanceladas(): Observable<AsignacionCancelada[]> {
    return this.http.get<AsignacionCancelada[]>(
      `${this.base}/talleres/mi-taller/asignaciones?estado=cancelada`,
    );
  }

  actualizarTarifa(tarifa: number) {
    return this.http.patch(
      `${this.base}/talleres/mi-taller/tarifa-traslado`,
      { tarifa_traslado: tarifa },
    );
  }

  miTaller() {
    return this.http.get<{ tarifa_traslado: number }>(`${this.base}/talleres/mi-taller`);
  }
}
```

## `cancelaciones.component.ts`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CancelacionesService, AsignacionCancelada } from './cancelaciones.service';

@Component({
  selector: 'app-cancelaciones',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './cancelaciones.component.html',
  styleUrls: ['./cancelaciones.component.scss'],
})
export class CancelacionesComponent implements OnInit {
  private svc = inject(CancelacionesService);

  lista: AsignacionCancelada[] = [];
  tarifaActual = 0;
  nuevaTarifa = 0;
  cargando = true;
  guardandoTarifa = false;
  msgTarifa: string | null = null;

  ngOnInit() {
    this.cargar();
  }

  cargar() {
    this.cargando = true;
    this.svc.misCanceladas().subscribe({
      next: (data) => { this.lista = data; this.cargando = false; },
      error: () => { this.cargando = false; },
    });
    this.svc.miTaller().subscribe({
      next: (t) => {
        this.tarifaActual = +t.tarifa_traslado;
        this.nuevaTarifa = this.tarifaActual;
      },
    });
  }

  guardarTarifa() {
    this.guardandoTarifa = true;
    this.msgTarifa = null;
    this.svc.actualizarTarifa(this.nuevaTarifa).subscribe({
      next: () => {
        this.tarifaActual = this.nuevaTarifa;
        this.msgTarifa = 'Tarifa actualizada';
        this.guardandoTarifa = false;
      },
      error: (e) => {
        this.msgTarifa = e.error?.detail ?? 'Error';
        this.guardandoTarifa = false;
      },
    });
  }

  get totalPendiente(): number {
    return this.lista
      .filter(a => !a.compensacion_pagada && a.compensacion_monto)
      .reduce((sum, a) => sum + Number(a.compensacion_monto), 0);
  }

  get totalCancelaciones(): number {
    return this.lista.length;
  }
}
```

## `cancelaciones.component.html`

```html
<div class="cancelaciones-page">
  <h1>Cancelaciones y compensaciones</h1>

  <section class="config">
    <h2>Mi tarifa de traslado</h2>
    <p class="hint">
      Monto base que recibes cuando un cliente cancela.
      <ul>
        <li>Si la asignación estaba <strong>pendiente</strong> → 0%</li>
        <li>Si estaba <strong>aceptada</strong> → 50% de esta tarifa</li>
        <li>Si estaba <strong>en camino</strong> o <strong>llegó</strong> → 100%</li>
      </ul>
    </p>
    <div class="form-tarifa">
      <input type="number" [(ngModel)]="nuevaTarifa" min="0" max="1000">
      <span>USD</span>
      <button (click)="guardarTarifa()" [disabled]="guardandoTarifa || nuevaTarifa === tarifaActual">
        {{ guardandoTarifa ? 'Guardando...' : 'Guardar' }}
      </button>
      <span *ngIf="msgTarifa">{{ msgTarifa }}</span>
    </div>
  </section>

  <section class="stats">
    <div class="kpi">
      <div class="big">{{ totalCancelaciones }}</div>
      <div>Cancelaciones</div>
    </div>
    <div class="kpi destacado">
      <div class="big">${{ totalPendiente | number:'1.2-2' }}</div>
      <div>Pendiente de cobro</div>
    </div>
  </section>

  <h2>Historial</h2>
  <div *ngIf="cargando">Cargando...</div>
  <table *ngIf="!cargando" class="historial">
    <thead>
      <tr>
        <th>Asignación</th>
        <th>Incidente</th>
        <th>Cancelada</th>
        <th>Motivo</th>
        <th>Compensación</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      <tr *ngFor="let a of lista">
        <td>#{{ a.id_asignacion }}</td>
        <td>#{{ a.id_incidente }}</td>
        <td>{{ a.cancelada_at | date:'short' }}</td>
        <td class="motivo">{{ a.motivo_cancelacion }}</td>
        <td>
          <strong>${{ a.compensacion_monto | number:'1.2-2' }}</strong>
        </td>
        <td>
          <span *ngIf="a.compensacion_pagada" class="badge ok">Pagada</span>
          <span *ngIf="!a.compensacion_pagada && a.compensacion_monto" class="badge pending">
            Pendiente
          </span>
          <span *ngIf="!a.compensacion_monto" class="muted">$0</span>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

## `cancelaciones.component.scss`

```scss
.cancelaciones-page { padding: 1.5rem; max-width: 1100px; }

.config {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}
.hint { color: #666; font-size: 0.9rem; }
.form-tarifa {
  display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;
  input { width: 100px; padding: 6px; }
}

.stats {
  display: flex;
  gap: 1rem;
  margin: 1.5rem 0;
  .kpi {
    flex: 1;
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    .big { font-size: 2rem; font-weight: 700; }
    &.destacado { border-color: #f39c12; background: #fff8e1; }
  }
}

.historial {
  width: 100%;
  border-collapse: collapse;
  th, td { padding: 0.6rem; text-align: left; border-bottom: 1px solid #eee; }
  thead { background: #f5f5f5; }
  .motivo { max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  &.ok { background: #d4edda; color: #155724; }
  &.pending { background: #fff3cd; color: #856404; }
}
.muted { color: #888; }
```

## Ruta
```typescript
{
  path: 'cancelaciones',
  loadComponent: () =>
    import('./cancelaciones/cancelaciones.component').then(m => m.CancelacionesComponent),
},
```

---

## Validación manual
1. Crear asignación, ponerla en estado "en_camino".
2. Cliente cancela vía `POST /asignaciones/{id}/cancelar`.
3. Recargar el panel del taller → ver la cancelación con compensación 100% de su `tarifa_traslado`.
4. Cambiar la tarifa, verificar que afecta nuevas cancelaciones.

## Checklist de cierre W3
- [ ] Formulario de tarifa con validación 0-1000.
- [ ] KPIs visibles: total cancelaciones + total pendiente de cobro.
- [ ] Tabla con motivo, compensación, estado.
- [ ] Badge visualmente distinto para pagada / pendiente.
- [ ] Ruta agregada al sidebar.
