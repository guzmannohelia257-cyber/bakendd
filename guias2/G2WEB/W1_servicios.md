# W1 — Pantalla "Mis Servicios" del taller

> **Backend requerido:** [G2C1/F1](../G2C1/F1_servicios_extendidos.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
Pantalla donde el taller autenticado declara qué categorías de problema atiende y su tarifa base.

Endpoints consumidos:
- `GET /categorias` — listar las 7 categorías oficiales
- `GET /talleres/mi-taller/servicios` — estado actual
- `PUT /talleres/mi-taller/servicios` — guardar matriz completa

---

## Estructura de archivos

Crear en `web/src/app/dashboards/taller/servicios/`:
```
servicios/
├── servicios.component.ts
├── servicios.component.html
├── servicios.component.scss
└── servicios.service.ts
```

## `servicios.service.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface Categoria {
  id_categoria: number;
  codigo: string;
  nombre: string;
  descripcion?: string;
  requiere_cotizacion: boolean;
  icono_url?: string;
}

export interface TallerServicio {
  id_taller_servicio?: number;
  id_taller?: number;
  id_categoria: number;
  servicio_movil: boolean;
  tarifa_base?: number;
}

@Injectable({ providedIn: 'root' })
export class ServiciosService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  listarCategorias(): Observable<Categoria[]> {
    return this.http.get<Categoria[]>(`${this.base}/categorias`);
  }

  listarMisServicios(): Observable<TallerServicio[]> {
    return this.http.get<TallerServicio[]>(`${this.base}/talleres/mi-taller/servicios`);
  }

  guardarServicios(servicios: TallerServicio[]): Observable<TallerServicio[]> {
    return this.http.put<TallerServicio[]>(
      `${this.base}/talleres/mi-taller/servicios`,
      { servicios },
    );
  }
}
```

## `servicios.component.ts`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { ServiciosService, Categoria, TallerServicio } from './servicios.service';

interface FilaServicio {
  categoria: Categoria;
  activo: boolean;
  servicio_movil: boolean;
  tarifa_base: number | null;
}

@Component({
  selector: 'app-servicios',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './servicios.component.html',
  styleUrls: ['./servicios.component.scss'],
})
export class ServiciosComponent implements OnInit {
  private svc = inject(ServiciosService);

  filas: FilaServicio[] = [];
  cargando = true;
  guardando = false;
  mensaje: string | null = null;
  error: string | null = null;

  ngOnInit() {
    this.cargar();
  }

  cargar() {
    this.cargando = true;
    forkJoin({
      categorias: this.svc.listarCategorias(),
      mios: this.svc.listarMisServicios(),
    }).subscribe({
      next: ({ categorias, mios }) => {
        const mioPorCat = new Map(mios.map(m => [m.id_categoria, m]));
        this.filas = categorias.map(cat => {
          const m = mioPorCat.get(cat.id_categoria);
          return {
            categoria: cat,
            activo: !!m,
            servicio_movil: m?.servicio_movil ?? false,
            tarifa_base: m?.tarifa_base ?? null,
          };
        });
        this.cargando = false;
      },
      error: (e) => {
        this.error = 'Error cargando datos: ' + (e.error?.detail ?? e.message);
        this.cargando = false;
      },
    });
  }

  guardar() {
    const servicios: TallerServicio[] = this.filas
      .filter(f => f.activo)
      .map(f => ({
        id_categoria: f.categoria.id_categoria,
        servicio_movil: f.servicio_movil,
        tarifa_base: f.tarifa_base ?? undefined,
      }));

    this.guardando = true;
    this.mensaje = null;
    this.error = null;
    this.svc.guardarServicios(servicios).subscribe({
      next: () => {
        this.mensaje = `Guardado: ${servicios.length} servicio(s) activos`;
        this.guardando = false;
      },
      error: (e) => {
        this.error = e.error?.detail ?? 'Error guardando';
        this.guardando = false;
      },
    });
  }
}
```

## `servicios.component.html`

```html
<div class="servicios-page">
  <h1>Mis servicios</h1>
  <p class="hint">
    Marca las categorías que atiendes. Solo aparecerás en búsquedas de clientes
    para esas categorías. La tarifa base es orientativa.
  </p>

  <div *ngIf="cargando">Cargando...</div>
  <div *ngIf="error" class="error">{{ error }}</div>

  <table *ngIf="!cargando" class="servicios-table">
    <thead>
      <tr>
        <th>Atiende</th>
        <th>Categoría</th>
        <th>Móvil</th>
        <th>Tarifa base (USD)</th>
        <th>Tipo</th>
      </tr>
    </thead>
    <tbody>
      <tr *ngFor="let f of filas">
        <td><input type="checkbox" [(ngModel)]="f.activo"></td>
        <td>
          <strong>{{ f.categoria.nombre }}</strong>
          <div class="muted">{{ f.categoria.descripcion }}</div>
        </td>
        <td>
          <input type="checkbox" [(ngModel)]="f.servicio_movil" [disabled]="!f.activo">
        </td>
        <td>
          <input type="number" [(ngModel)]="f.tarifa_base" [disabled]="!f.activo"
                 min="0" placeholder="0">
        </td>
        <td>
          <span *ngIf="f.categoria.requiere_cotizacion" class="badge cotizacion">
            Cotización previa
          </span>
          <span *ngIf="!f.categoria.requiere_cotizacion" class="badge directo">
            Servicio directo
          </span>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="acciones">
    <button (click)="guardar()" [disabled]="guardando || cargando">
      {{ guardando ? 'Guardando...' : 'Guardar cambios' }}
    </button>
    <span *ngIf="mensaje" class="ok">{{ mensaje }}</span>
  </div>
</div>
```

## `servicios.component.scss`

```scss
.servicios-page {
  padding: 1.5rem;
  max-width: 1100px;
}

.hint {
  color: #666;
  margin-bottom: 1.5rem;
}

.servicios-table {
  width: 100%;
  border-collapse: collapse;

  th, td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #eee;
  }

  thead {
    background: #f5f5f5;
  }

  input[type="number"] {
    width: 120px;
    padding: 4px;
  }
}

.muted {
  font-size: 0.85rem;
  color: #888;
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  &.cotizacion { background: #fff3cd; color: #856404; }
  &.directo { background: #d4edda; color: #155724; }
}

.acciones {
  margin-top: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.ok { color: #28a745; }
.error { color: #dc3545; padding: 1rem; }
```

## Registrar ruta

En `web/src/app/dashboards/taller/taller.routes.ts` (o donde tengas las rutas del taller):

```typescript
import { Routes } from '@angular/router';

export const tallerRoutes: Routes = [
  // ... rutas existentes
  {
    path: 'servicios',
    loadComponent: () =>
      import('./servicios/servicios.component').then(m => m.ServiciosComponent),
  },
];
```

Agregar entrada en el menú lateral / sidebar del taller con icono y texto "Mis servicios".

---

## Validación manual
1. Backend levantado (`uvicorn app.main:app --reload`).
2. Tener un taller registrado y logueado (token guardado).
3. Navegar a `/dashboards/taller/servicios`.
4. Marcar 2-3 categorías, poner tarifas, guardar.
5. Recargar la página → las marcas deben persistir.
6. Probar desde otro cliente (curl o Postman) `GET /talleres/compatibles?id_categoria=X&latitud=Y&longitud=Z` para verificar que solo aparece el taller en esas categorías.

## Checklist de cierre W1
- [ ] Componente standalone funcional.
- [ ] `forkJoin` carga categorías + servicios actuales en paralelo.
- [ ] Checkbox "Atiende" habilita/deshabilita los otros campos.
- [ ] Badge visible para categorías con cotización previa.
- [ ] Mensaje de éxito al guardar.
- [ ] Manejo de error visible al usuario.
- [ ] Ruta agregada al sidebar del taller.
