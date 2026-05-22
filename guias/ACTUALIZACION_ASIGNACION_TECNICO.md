# Guía: Aceptar Asignación con Técnico

## Resumen

Al aceptar una asignación, el taller puede (opcional) asignar un técnico específico. El backend valida:

1. El técnico pertenece al taller autenticado.
2. El técnico no tiene otra asignación activa (estados: pendiente, aceptada, en_camino).

**Nota de diseño:** los técnicos **no tienen especialidades**. El motor ya filtra talleres por capacidad vía `taller_servicio`, así que si la emergencia llegó al taller es porque el taller puede atenderla. Cualquier técnico del taller puede tomarla.

---

## Flujo

```
Motor asigna → Asignación queda en 'pendiente' sin técnico
Taller abre la solicitud
Taller ve sus técnicos → elige uno (opcional) → PUT /aceptar
Backend valida: pertenece al taller + sin asignación activa
Asignación pasa a 'aceptada' con id_tecnico
```

---

## Endpoints

### 1. Listar técnicos del taller

```
GET /talleres/mi-taller/tecnicos
Authorization: Bearer <token-taller>

Response: 200
[
  {
    "id_tecnico": 1,
    "id_taller": 5,
    "nombre": "Juan García",
    "telefono": "3001234567",
    "disponible": true,
    "latitud": null,
    "longitud": null,
    "activo": true,
    "created_at": "2026-04-15T10:30:00"
  }
]
```

El frontend filtra por `disponible === true` para mostrar el dropdown.

### 2. Detalle de la asignación pendiente

```
GET /talleres/mi-taller/asignaciones/{id_asignacion}

Response: 200 (AsignacionTallerResponse)
{
  "id_asignacion": 42,
  "id_incidente": 100,
  "id_taller": 5,
  "id_tecnico": null,
  "id_estado_asignacion": 1,
  "eta_minutos": null,
  "nota_taller": null,
  "created_at": "2026-04-21T14:30:00",
  "updated_at": "2026-04-21T14:30:00",
  "estado": { "id_estado_asignacion": 1, "nombre": "pendiente" },
  "incidente": {
    "id_incidente": 100,
    "descripcion_usuario": "El auto no enciende",
    "resumen_ia": "Problema eléctrico, posible batería",
    "latitud": 4.7150,
    "longitud": -74.0700,
    "created_at": "2026-04-21T14:25:00",
    "usuario":   { "id_usuario": 10, "nombre": "Pedro Rodríguez", "telefono": "3105551234" },
    "vehiculo":  { "id_vehiculo": 5, "placa": "ABC-123", "marca": "Toyota", "modelo": "Corolla", "anio": 2020, "color": "Blanco" },
    "categoria": { "id_categoria": 3, "nombre": "Batería" },
    "prioridad": { "id_prioridad": 2, "nivel": "Media", "orden": 2 }
  }
}
```

### 3. Aceptar con técnico

```
PUT /talleres/mi-taller/asignaciones/{id_asignacion}/aceptar
Content-Type: application/json

Body:
{
  "id_tecnico": 1,       // opcional
  "eta_minutos": 15,     // opcional, 1..600
  "nota": "Vamos en camino"   // opcional, max 500
}

Response: 200 (AsignacionTallerResponse con id_tecnico asignado y estado 'aceptada')
```

**Errores posibles:**

| Código | detail | Causa |
|--------|--------|-------|
| 400 | `La asignación ya está en estado 'X', no se puede aceptar` | La asignación no está en `pendiente` |
| 404 | `Técnico no encontrado en tu taller` | `id_tecnico` pertenece a otro taller o no existe |
| 400 | `El técnico {id} ya tiene N asignación(es) activa(s). No puede recibir otra hasta completar la actual.` | El técnico ya está ocupado |

### 4. Rechazar

```
PUT /talleres/mi-taller/asignaciones/{id_asignacion}/rechazar

Body:
{ "motivo": "Sin stock de batería" }
```

---

## Ver trabajos del técnico

```
GET /talleres/mi-taller/tecnicos/{tecnico_id}/asignaciones
GET /talleres/mi-taller/tecnicos/{tecnico_id}/asignaciones?estado=en_camino
GET /talleres/mi-taller/tecnicos/{tecnico_id}/asignaciones/{id_asignacion}
```

Devuelven `TecnicoAsignacionResponse` con ubicación GPS del incidente y datos del cliente.

---

## Implementación Angular

### Servicio

```typescript
@Injectable({ providedIn: 'root' })
export class AsignacionService {
  private apiUrl = '/api/talleres';
  constructor(private http: HttpClient) {}

  listarAsignaciones(estado?: string): Observable<AsignacionTallerResponse[]> {
    const url = estado
      ? `${this.apiUrl}/mi-taller/asignaciones?estado=${estado}`
      : `${this.apiUrl}/mi-taller/asignaciones`;
    return this.http.get<AsignacionTallerResponse[]>(url);
  }

  aceptar(id: number, payload: AceptarPayload): Observable<AsignacionTallerResponse> {
    return this.http.put<AsignacionTallerResponse>(
      `${this.apiUrl}/mi-taller/asignaciones/${id}/aceptar`, payload
    );
  }

  rechazar(id: number, motivo: string): Observable<any> {
    return this.http.put(
      `${this.apiUrl}/mi-taller/asignaciones/${id}/rechazar`, { motivo }
    );
  }
}

@Injectable({ providedIn: 'root' })
export class TecnicoService {
  private apiUrl = '/api/talleres';
  constructor(private http: HttpClient) {}

  listar(): Observable<TecnicoResponse[]> {
    return this.http.get<TecnicoResponse[]>(`${this.apiUrl}/mi-taller/tecnicos`);
  }
}

interface AceptarPayload {
  id_tecnico?: number;
  eta_minutos?: number;
  nota?: string;
}
```

### Componente

```typescript
export class AsignacionesComponent implements OnInit {
  asignaciones: AsignacionTallerResponse[] = [];
  tecnicos: TecnicoResponse[] = [];
  seleccionPorAsignacion: Record<number, { id_tecnico?: number; eta?: number; nota?: string }> = {};

  constructor(
    private asignacionSrv: AsignacionService,
    private tecnicoSrv: TecnicoService,
    private toast: ToastService,
  ) {}

  ngOnInit() {
    this.cargar();
  }

  cargar() {
    this.asignacionSrv.listarAsignaciones('pendiente').subscribe(d => this.asignaciones = d);
    this.tecnicoSrv.listar().subscribe(d => this.tecnicos = d.filter(t => t.disponible && t.activo));
  }

  aceptar(a: AsignacionTallerResponse) {
    const sel = this.seleccionPorAsignacion[a.id_asignacion] || {};
    this.asignacionSrv.aceptar(a.id_asignacion, {
      id_tecnico: sel.id_tecnico,
      eta_minutos: sel.eta,
      nota: sel.nota,
    }).subscribe({
      next: () => { this.toast.ok('Asignación aceptada'); this.cargar(); },
      error: err => this.toast.error(err.error?.detail || 'Error al aceptar'),
    });
  }

  rechazar(a: AsignacionTallerResponse) {
    const motivo = prompt('Motivo del rechazo:');
    if (!motivo) return;
    this.asignacionSrv.rechazar(a.id_asignacion, motivo).subscribe({
      next: () => { this.toast.ok('Asignación rechazada'); this.cargar(); },
      error: err => this.toast.error(err.error?.detail || 'Error al rechazar'),
    });
  }
}
```

### Template

```html
<div *ngFor="let a of asignaciones" class="card">
  <h4>{{ a.incidente.usuario.nombre }} — {{ a.incidente.vehiculo.placa }}</h4>
  <p><strong>Categoría:</strong> {{ a.incidente.categoria?.nombre }}</p>
  <p><strong>Prioridad:</strong> {{ a.incidente.prioridad?.nivel }}</p>
  <p><strong>Descripción:</strong> {{ a.incidente.descripcion_usuario }}</p>
  <p><strong>GPS:</strong> {{ a.incidente.latitud }}, {{ a.incidente.longitud }}</p>

  <label>Técnico (opcional)</label>
  <select [(ngModel)]="seleccionPorAsignacion[a.id_asignacion].id_tecnico">
    <option [ngValue]="undefined">-- Sin técnico --</option>
    <option *ngFor="let t of tecnicos" [ngValue]="t.id_tecnico">{{ t.nombre }}</option>
  </select>

  <label>ETA (min)</label>
  <input type="number" min="1" max="600"
         [(ngModel)]="seleccionPorAsignacion[a.id_asignacion].eta">

  <label>Nota</label>
  <textarea [(ngModel)]="seleccionPorAsignacion[a.id_asignacion].nota"></textarea>

  <button class="btn btn-success" (click)="aceptar(a)">Aceptar</button>
  <button class="btn btn-danger"  (click)="rechazar(a)">Rechazar</button>
</div>
```

---

## Reglas de negocio vigentes

- `id_tecnico` es **opcional** al aceptar. Si no se manda, la asignación queda aceptada sin técnico y se puede asignar luego reabriendo el flujo (actualmente solo desde `/aceptar` mientras esté pendiente — si necesitas asignar después hay que crear un endpoint nuevo).
- Un técnico **no puede** tener más de una asignación activa simultánea. Estados activos = `pendiente (1)`, `aceptada (2)`, `en_camino (3)`. Una vez la asignación pasa a `completada (4)` o `rechazada (5)`, el técnico se libera.
- La validación de disponibilidad la hace `validar_tecnico_disponible()` en `app/services/asignacion.py`.

---

## Checklist front

- [ ] Consumir `GET /mi-taller/asignaciones?estado=pendiente` para la bandeja.
- [ ] Cargar técnicos con `GET /mi-taller/tecnicos` y filtrar en cliente por `disponible && activo`.
- [ ] Permitir aceptar con o sin técnico.
- [ ] Mostrar el `detail` del 400/404 tal cual al usuario.
- [ ] Después de aceptar/rechazar, recargar la lista.
- [ ] Vista por técnico: `GET /mi-taller/tecnicos/{id}/asignaciones`.
