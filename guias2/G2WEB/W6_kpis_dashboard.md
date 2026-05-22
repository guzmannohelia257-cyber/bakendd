# W6 — Dashboard de KPIs con Chart.js

> **Backend requerido:** [G2C2/F4](../G2C2/F4_dashboard_kpis.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
Dashboard con los 4 KPIs del enunciado, dos tarjetas grandes (tiempos promedio) y un gráfico de barras (incidentes por categoría).

Endpoint consumido:
- `GET /tenants/me/kpis?desde=...&hasta=...`

---

## Setup

```bash
cd web
npm install chart.js
```

## Archivos

`web/src/app/dashboards/taller/kpis/`:
```
kpis/
├── kpis.component.ts
├── kpis.component.html
├── kpis.component.scss
└── kpis.service.ts
```

## `kpis.service.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface CategoriaCount {
  codigo: string | null;
  nombre: string;
  total: number;
}

export interface KpiResumen {
  desde: string;
  hasta: string;
  tiempo_promedio_asignacion_min: number;
  tiempo_promedio_llegada_min: number;
  incidentes_por_categoria: CategoriaCount[];
}

@Injectable({ providedIn: 'root' })
export class KpisService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  resumen(desde?: string, hasta?: string): Observable<KpiResumen> {
    let params = new HttpParams();
    if (desde) params = params.set('desde', desde);
    if (hasta) params = params.set('hasta', hasta);
    return this.http.get<KpiResumen>(`${this.base}/tenants/me/kpis`, { params });
  }
}
```

## `kpis.component.ts`

```typescript
import { Component, OnInit, AfterViewInit, inject, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Chart, registerables } from 'chart.js';
import { KpisService, KpiResumen } from './kpis.service';

Chart.register(...registerables);

@Component({
  selector: 'app-kpis',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './kpis.component.html',
  styleUrls: ['./kpis.component.scss'],
})
export class KpisComponent implements OnInit, AfterViewInit {
  private svc = inject(KpisService);

  @ViewChild('chartCat') chartCatRef!: ElementRef<HTMLCanvasElement>;
  private chart?: Chart;

  data: KpiResumen | null = null;
  cargando = true;
  error: string | null = null;

  // Filtros (default ultimos 30 dias)
  desde = '';
  hasta = '';

  ngOnInit() {
    const ahora = new Date();
    const hace30 = new Date(ahora.getTime() - 30 * 24 * 60 * 60 * 1000);
    this.desde = hace30.toISOString().split('T')[0];
    this.hasta = ahora.toISOString().split('T')[0];
    this.cargar();
  }

  ngAfterViewInit() {
    if (this.data) this._renderChart();
  }

  cargar() {
    this.cargando = true;
    this.error = null;
    this.svc.resumen(this.desde, this.hasta).subscribe({
      next: (d) => {
        this.data = d;
        this.cargando = false;
        // Esperar al render
        setTimeout(() => this._renderChart());
      },
      error: (e) => {
        this.error = e.error?.detail ?? 'Error cargando KPIs';
        this.cargando = false;
      },
    });
  }

  private _renderChart() {
    if (!this.data || !this.chartCatRef) return;
    if (this.chart) this.chart.destroy();

    const ctx = this.chartCatRef.nativeElement;
    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: this.data.incidentes_por_categoria.map(c => c.nombre),
        datasets: [{
          label: 'Incidentes',
          data: this.data.incidentes_por_categoria.map(c => c.total),
          backgroundColor: '#4a90e2',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
        },
      },
    });
  }
}
```

## `kpis.component.html`

```html
<div class="kpis-page">
  <header>
    <h1>Indicadores de gestión</h1>
    <div class="filtros">
      <label>Desde:</label>
      <input type="date" [(ngModel)]="desde">
      <label>Hasta:</label>
      <input type="date" [(ngModel)]="hasta">
      <button (click)="cargar()" [disabled]="cargando">
        {{ cargando ? 'Cargando...' : 'Actualizar' }}
      </button>
    </div>
  </header>

  <div *ngIf="error" class="error">{{ error }}</div>

  <div *ngIf="data" class="grid">
    <div class="kpi">
      <div class="big">{{ data.tiempo_promedio_asignacion_min | number:'1.0-1' }}</div>
      <div class="unit">min</div>
      <div class="label">Tiempo promedio de asignación</div>
      <div class="hint">desde reporte hasta aceptación del taller</div>
    </div>

    <div class="kpi">
      <div class="big">{{ data.tiempo_promedio_llegada_min | number:'1.0-1' }}</div>
      <div class="unit">min</div>
      <div class="label">Tiempo promedio de llegada</div>
      <div class="hint">desde aceptación hasta llegada al sitio</div>
    </div>

    <div class="card-grande">
      <h3>Incidentes por tipo</h3>
      <div class="chart-container">
        <canvas #chartCat></canvas>
      </div>
      <div *ngIf="data.incidentes_por_categoria.length === 0" class="empty">
        No hay incidentes en el rango seleccionado.
      </div>
    </div>
  </div>
</div>
```

## `kpis.component.scss`

```scss
.kpis-page {
  padding: 1.5rem;
  max-width: 1200px;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;

  .filtros {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    input[type="date"] { padding: 4px; }
  }
}

.error { color: #dc3545; padding: 1rem; background: #f8d7da; border-radius: 4px; }

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.kpi {
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;

  .big {
    font-size: 3rem;
    font-weight: 700;
    color: #4a90e2;
    line-height: 1;
  }
  .unit {
    font-size: 1rem;
    color: #888;
    margin-top: -0.5rem;
  }
  .label {
    margin-top: 0.5rem;
    font-weight: 600;
  }
  .hint {
    font-size: 0.8rem;
    color: #888;
    margin-top: 0.25rem;
  }
}

.card-grande {
  grid-column: 1 / -1;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1.5rem;

  h3 { margin-top: 0; }
  .chart-container {
    position: relative;
    height: 320px;
  }
  .empty {
    text-align: center;
    color: #888;
    padding: 2rem;
  }
}

@media (max-width: 768px) {
  .grid { grid-template-columns: 1fr; }
}
```

## Ruta

```typescript
{
  path: 'kpis',
  loadComponent: () =>
    import('./kpis/kpis.component').then(m => m.KpisComponent),
},
```

---

## (Opcional) Ranking de talleres

Si el tenant tiene varios talleres (multi-sucursal), agregar tarjeta extra con ranking. Llama a `GET /tenants/me/kpis/ranking-mis-talleres`.

```html
<div class="ranking">
  <h3>Ranking de mis talleres</h3>
  <ol>
    <li *ngFor="let t of ranking">
      <strong>{{ t.nombre }}</strong>
      — score {{ t.score | number:'1.2-2' }}
      ({{ t.completadas }} servicios, ★{{ t.rating_promedio }})
    </li>
  </ol>
</div>
```

---

## Validación manual
1. Tener al menos 5 incidentes en el tenant (en distintas categorías, en distintos estados).
2. Abrir `/dashboards/taller/kpis`.
3. Ver tarjetas con tiempos > 0.
4. Ver gráfico con barras de cada categoría.
5. Cambiar rango de fechas → ver que los datos cambian.

## Checklist de cierre W6
- [ ] Filtro de fechas funcional.
- [ ] Tarjetas con tiempos promedio.
- [ ] Gráfico Chart.js renderizado y responsive.
- [ ] `chart.destroy()` antes de re-render para evitar memory leak.
- [ ] Empty state cuando no hay datos.
- [ ] Responsive en móvil (1 columna).
