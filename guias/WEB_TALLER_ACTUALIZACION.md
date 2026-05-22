# Guía de Actualización — Panel Web del Taller (Angular)

Esta guía resume **todo lo nuevo o que cambió en el backend para la web del taller**.

⚠️ **Importante:** Los endpoints de técnico en Flutter (`/iniciar-viaje`, `/completar`) están en otra guía. Esta guía solo cubre lo que hace el taller: **aceptar y designar asignaciones**.

---

## 1. Resumen ejecutivo

**2 endpoints nuevos (WEB):**

| Método | Ruta | Caso de uso |
|---|---|---|
| PUT | `/talleres/mi-taller/disponibilidad` | Toggle pausa/reanuda (CU-17) |
| GET | `/talleres/mi-taller/evaluaciones` | Reseñas del cliente (CU-10) |

**3 endpoints existentes con cambios (backwards-compatible):**

| Ruta | Cambio |
|---|---|
| `POST /talleres/mi-taller/tecnicos` | Requiere `email` y `password` (técnico es Usuario con rol=3) |
| `PUT /talleres/mi-taller/tecnicos/{id}` | `email` y `password` ahora opcionales (editar credenciales) |
| `GET /talleres/mi-taller/asignaciones` | Acepta query params `desde` y `hasta` (además del ya existente `estado`) |

**2 cambios de comportamiento (mismos endpoints):**

- `PUT /asignaciones/{id}/rechazar` ahora dispara **reasignación automática** a otro candidato. Tu UI verá que el incidente "desaparece" de tu bandeja y aparece en otro taller.
- `PUT /asignaciones/{id}/aceptar` ahora registra historial automáticamente. La asignación pasa de `pendiente` → `aceptada`.

**Cambios en campos de respuesta:**

- `TallerResponse.disponible: boolean` - Nuevo estado de disponibilidad
- `TecnicoResponse` ahora usa `id_usuario_taller` (relación) e `id_usuario` (usuario rol=3) en lugar de id_tecnico
- `AsignacionTallerResponse.id_usuario: number | null` - ID del usuario técnico asignado (puede ser null hasta que aceptes)

---

## 2. Interfaces TypeScript actualizadas

Reemplaza/agrega estas interfaces en tu capa de modelos Angular:

```typescript
// src/app/models/taller.model.ts

export interface TallerResponse {
  id_taller: number;
  nombre: string;
  email: string;
  telefono?: string | null;
  direccion?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  capacidad_max: number;
  activo: boolean;
  verificado: boolean;
  disponible: boolean;        // ← NUEVO
  created_at: string;
  updated_at?: string | null;
}

export interface TecnicoResponse {
  id_usuario_taller: number;  // ID de la relación usuario-taller
  id_usuario: number;         // ID del usuario (rol=3)
  nombre: string;
  email: string;              // Siempre presente (usuario rol=3)
  telefono?: string | null;
  disponible: boolean;
  latitud?: number | null;
  longitud?: number | null;
  activo: boolean;
  created_at: string;
}

export interface TecnicoCreate {
  nombre: string;
  email: string;              // ⚠️ OBLIGATORIO (usuario.email NOT NULL)
  password: string;           // ⚠️ OBLIGATORIO (usuario.password_hash NOT NULL)
  telefono?: string;
}

export interface TecnicoUpdate {
  nombre?: string;
  email?: string;              // ← NUEVO
  password?: string;           // ← NUEVO
  telefono?: string;
  disponible?: boolean;
  activo?: boolean;
}
```

```typescript
// src/app/models/asignacion.model.ts

export type EstadoAsignacionNombre =
  | 'pendiente'
  | 'aceptada'
  | 'rechazada'
  | 'en_camino'      // ← NUEVO en el flujo
  | 'completada';    // ← NUEVO en el flujo

export interface AceptarAsignacionRequest {
  id_usuario?: number;         // Técnico usuario (rol=3) a asignar
  eta_minutos?: number;        // 1..600
  nota?: string;               // max 500
}

export interface RechazarAsignacionRequest {
  motivo: string;              // min 3, max 500
}

export interface DisponibilidadUpdate {
  disponible: boolean;
}
```

```typescript
// src/app/models/evaluacion.model.ts

export interface EvaluacionResponse {
  id_evaluacion: number;
  id_incidente: number;
  id_taller: number;
  id_tecnico?: number | null;
  estrellas: number;           // 1..5
  comentario?: string | null;
  created_at: string;
}
```

---

## 3. Servicios Angular actualizados

### 3.1 TallerService

```typescript
@Injectable({ providedIn: 'root' })
export class TallerService {
  private api = environment.apiUrl + '/talleres';
  constructor(private http: HttpClient) {}

  obtenerMiTaller(): Observable<TallerResponse> {
    return this.http.get<TallerResponse>(`${this.api}/mi-taller`);
  }

  actualizarMiTaller(data: Partial<TallerResponse>): Observable<TallerResponse> {
    return this.http.put<TallerResponse>(`${this.api}/mi-taller`, data);
  }

  // NUEVO — B.3
  toggleDisponibilidad(disponible: boolean): Observable<TallerResponse> {
    return this.http.put<TallerResponse>(
      `${this.api}/mi-taller/disponibilidad`,
      { disponible }
    );
  }

  // NUEVO — A.3
  obtenerEvaluaciones(): Observable<EvaluacionResponse[]> {
    return this.http.get<EvaluacionResponse[]>(`${this.api}/mi-taller/evaluaciones`);
  }
}
```

### 3.2 AsignacionService (ampliado)

```typescript
@Injectable({ providedIn: 'root' })
export class AsignacionService {
  private api = environment.apiUrl + '/talleres/mi-taller/asignaciones';
  constructor(private http: HttpClient) {}

  listar(filtros?: {
    estado?: EstadoAsignacionNombre;
    desde?: string;             // NUEVO — formato YYYY-MM-DD
    hasta?: string;             // NUEVO
  }): Observable<AsignacionTallerResponse[]> {
    let params = new HttpParams();
    if (filtros?.estado) params = params.set('estado', filtros.estado);
    if (filtros?.desde)  params = params.set('desde', filtros.desde);
    if (filtros?.hasta)  params = params.set('hasta', filtros.hasta);
    return this.http.get<AsignacionTallerResponse[]>(this.api, { params });
  }

  detalle(id: number): Observable<AsignacionTallerResponse> {
    return this.http.get<AsignacionTallerResponse>(`${this.api}/${id}`);
  }

  aceptar(id: number, body: AceptarAsignacionRequest): Observable<AsignacionTallerResponse> {
    return this.http.put<AsignacionTallerResponse>(`${this.api}/${id}/aceptar`, body);
  }

  rechazar(id: number, body: RechazarAsignacionRequest): Observable<AsignacionTallerResponse> {
    return this.http.put<AsignacionTallerResponse>(`${this.api}/${id}/rechazar`, body);
  }
}
```

### 3.3 TecnicoService (ajustado)

Email y password ahora son **obligatorios** al crear técnico (Usuario rol=3):

```typescript
@Injectable({ providedIn: 'root' })
export class TecnicoService {
  private api = environment.apiUrl + '/talleres/mi-taller/tecnicos';
  constructor(private http: HttpClient) {}

  listar(): Observable<TecnicoResponse[]> {
    return this.http.get<TecnicoResponse[]>(this.api);
  }

  crear(data: TecnicoCreate): Observable<TecnicoResponse> {
    return this.http.post<TecnicoResponse>(this.api, data);
  }

  actualizar(id: number, data: TecnicoUpdate): Observable<TecnicoResponse> {
    return this.http.put<TecnicoResponse>(`${this.api}/${id}`, data);
  }

  eliminar(id: number): Observable<{ mensaje: string }> {
    return this.http.delete<{ mensaje: string }>(`${this.api}/${id}`);
  }
}
```

---

## 4. Flujo de vida en la web del taller

Tu dashboard maneja **2 estados**. Los otros los maneja el técnico en su app móvil:

| Estado | Acción en web | Endpoint | Quien continúa |
|---|---|---|---|
| `pendiente` | Aceptar / Rechazar + asignar técnico | `/aceptar` · `/rechazar` | Técnico (app móvil) |
| `aceptada` | (solo lectura) | — | Técnico inicia viaje en app |
| `en_camino` | (solo lectura) | — | Técnico completa en app |
| `completada` | (solo lectura) | — | Cliente evalúa |
| `rechazada` | (solo lectura) | — | Sistema reasigna automático |

### Ejemplo de componente (pseudo-código)

```typescript
@Component({ ... })
export class AsignacionDetailComponent {
  asignacion!: AsignacionTallerResponse;
  tecnicos: TecnicoResponse[] = [];

  onAceptar() {
    // El gerente elige técnico en dropdown + define ETA
    this.asignacionSrv.aceptar(this.asignacion.id_asignacion, {
      id_usuario: this.tecnicoSeleccionado.id_usuario,  // Usuario (rol=3)
      eta_minutos: this.eta,
      nota: this.nota,
    }).subscribe({
      next: a => this.asignacion = a,  // estado ahora es "aceptada"
      error: e => this.toast.error(e.error?.detail || 'Error'),
    });
    // El técnico ve en su app móvil y puede iniciar viaje o rechazar
  }

  onRechazar() {
    const motivo = prompt('Motivo del rechazo:');
    if (!motivo || motivo.length < 3) return;
    this.asignacionSrv.rechazar(this.asignacion.id_asignacion, { motivo })
      .subscribe(a => {
        this.asignacion = a;
        // Nota: backend ya disparó reasignación automática a otro taller
        this.toast.info('Rechazada. Buscando otro taller automáticamente.');
      });
  }
}
```

### Errores que el backend devuelve (HTTP codes reales)

| Código | Endpoint | Mensaje (ejemplo) |
|---|---|---|
| 400 | `/aceptar` | `La asignación ya está en estado 'aceptada', no se puede aceptar` |
| 409 | `/aceptar` | `El técnico {id} ya tiene una asignación activa (ID: XXX). Un técnico solo puede tener una asignación a la vez.` |
| 404 | `/aceptar` | `Técnico no encontrado en tu taller` |
| 404 | todos | `Asignación no encontrada o no pertenece a tu taller` |

Muestra el `error.error.detail` tal cual al usuario — el backend devuelve mensajes en español ya listos.

---

## 5. Pantalla nueva: Disponibilidad (CU-17)

En el header o sidebar del dashboard, agrega un toggle visible:

```html
<mat-slide-toggle
  [checked]="taller.disponible"
  (change)="onToggleDisponibilidad($event.checked)">
  {{ taller.disponible ? 'Recibiendo solicitudes' : 'En pausa' }}
</mat-slide-toggle>
```

```typescript
onToggleDisponibilidad(disponible: boolean) {
  this.tallerSrv.toggleDisponibilidad(disponible).subscribe({
    next: t => {
      this.taller = t;
      this.toast.ok(disponible ? 'Taller reanudado' : 'Taller en pausa');
    },
  });
}
```

**Regla de negocio:** cuando `disponible=false`, el motor de asignación del backend **no** incluye a este taller en los candidatos para nuevos incidentes. Las asignaciones ya pendientes no se cancelan; solo no entran nuevas.

---

## 6. Pantalla nueva: Reseñas recibidas (CU-10)

Ruta sugerida: `/dashboard/resenas`.

```typescript
@Component({ ... })
export class ResenasComponent implements OnInit {
  evaluaciones: EvaluacionResponse[] = [];
  promedio = 0;

  ngOnInit() {
    this.tallerSrv.obtenerEvaluaciones().subscribe(evs => {
      this.evaluaciones = evs;
      if (evs.length) {
        this.promedio = evs.reduce((s, e) => s + e.estrellas, 0) / evs.length;
      }
    });
  }
}
```

```html
<div class="resenas">
  <h2>Reseñas ({{ evaluaciones.length }}) — Promedio: {{ promedio | number:'1.1-1' }} ★</h2>
  <div *ngFor="let e of evaluaciones" class="resena-card">
    <div class="estrellas">{{ '★'.repeat(e.estrellas) }}{{ '☆'.repeat(5 - e.estrellas) }}</div>
    <p *ngIf="e.comentario">{{ e.comentario }}</p>
    <small>{{ e.created_at | date:'short' }}</small>
  </div>
</div>
```

El backend retorna `List[EvaluacionResponse]` ordenado por `created_at DESC`.

---

## 7. Formulario de técnicos — credenciales obligatorias

### Crear técnico

Los técnicos ahora se crean como Usuario (rol=3) y **requieren email y contraseña** para poder usarlos en la app móvil:

```html
<form [formGroup]="form" (ngSubmit)="guardar()">
  <input formControlName="nombre" placeholder="Nombre" required />
  
  <!-- ⚠️ Email y Contraseña son OBLIGATORIOS -->
  <input formControlName="email" type="email" placeholder="Email del técnico" required />
  <input formControlName="password" type="password"
         placeholder="Contraseña (mínimo 8 caracteres)" required />
  
  <input formControlName="telefono" placeholder="Teléfono (opcional)" />

  <button mat-raised-button type="submit">Crear Técnico</button>
</form>
```

```typescript
form = this.fb.group({
  nombre: ['', [Validators.required, Validators.minLength(3)]],
  email: ['', [Validators.required, Validators.email]],           // ⚠️ OBLIGATORIO
  password: ['', [Validators.required, Validators.minLength(8)]], // ⚠️ OBLIGATORIO
  telefono: [''],  // Opcional
});

guardar() {
  if (this.form.invalid) {
    this.toast.error('Por favor completa todos los campos requeridos');
    return;
  }

  const v = this.form.value;
  const payload: TecnicoCreate = {
    nombre: v.nombre!,
    email: v.email!,        // Ya validado como required + email
    password: v.password!,  // Ya validado como required + minLength(8)
    telefono: v.telefono || undefined,
  };

  this.tecnicoSrv.crear(payload).subscribe({
    next: t => {
      this.toast.ok(`✅ Técnico ${t.nombre} creado. Puede loguearse con: ${t.email}`);
      this.dialogRef.close(t);
    },
    error: e => {
      // 409 = email duplicado, 400 = email sin password (o viceversa)
      this.toast.error(e.error?.detail || 'Error al crear');
    },
  });
}
```

### Editar técnico

El mismo formulario vale para editar. `password` vacío = no cambia la contraseña. `email` vacío se ignora.

### Listar técnicos

En la tabla de técnicos, agrega una columna "Email/Acceso app":

```html
<td>
  <small class="text-muted">{{ tecnico.email }}</small>
  <br />
  <small class="text-success">✓ Acceso app activo</small>
</td>
```

Todos los técnicos creados **siempre** tienen acceso a la app móvil (email + password obligatorios).

---

## 8. Pantalla de historial con filtros de fecha (A.4)

El endpoint `GET /mi-taller/asignaciones` ahora soporta `desde` y `hasta`:

```typescript
export class HistorialComponent {
  form = this.fb.group({
    estado: [''],
    desde: [''],
    hasta: [''],
  });

  cargar() {
    const { estado, desde, hasta } = this.form.value;
    this.asignacionSrv.listar({
      estado: estado || undefined,
      desde: desde ? this.formatDate(desde) : undefined,  // YYYY-MM-DD
      hasta: hasta ? this.formatDate(hasta) : undefined,
    }).subscribe(list => this.asignaciones = list);
  }
}
```

```html
<form [formGroup]="form" (ngSubmit)="cargar()">
  <mat-select formControlName="estado" placeholder="Estado">
    <mat-option value="">Todos</mat-option>
    <mat-option value="pendiente">Pendiente</mat-option>
    <mat-option value="aceptada">Aceptada</mat-option>
    <mat-option value="en_camino">En camino</mat-option>
    <mat-option value="completada">Completada</mat-option>
    <mat-option value="rechazada">Rechazada</mat-option>
  </mat-select>

  <input matInput [matDatepicker]="d1" formControlName="desde" placeholder="Desde">
  <input matInput [matDatepicker]="d2" formControlName="hasta" placeholder="Hasta">

  <button type="submit">Filtrar</button>
</form>
```

---

## 9. Comportamientos nuevos del backend que afectan la UI

### 9.1 Reasignación automática al rechazar (B.1)

Cuando llamas `rechazar_asignacion(id, {motivo})`:
- Tu asignación queda en estado `rechazada`.
- El backend **automáticamente** crea una nueva asignación para el siguiente mejor candidato (otro taller) con el mismo incidente.
- Desde tu perspectiva: la asignación ya no aparece en tu lista de pendientes. Punto.
- Importante: no muestres "buscando otro taller" falsamente prolongado — el backend ya lo hizo síncrono antes de responder tu PUT.

### 9.2 Historial automático (A.1)

Todas las transiciones ahora se guardan en `historial_estado_asignacion`. No tienes que hacer nada — es solo para auditoría backend. Si en el futuro quieres mostrar una línea de tiempo al gerente, el backend ya tiene los datos.

---

## 10. Catálogos — endpoint de estados (opcional pero útil)

En vez de hardcodear los strings de estado en tu UI, puedes pedirlos al backend:

```
GET /incidencias/estados        → estados de incidente
```

Para estados de asignación no hay endpoint dedicado hoy; si lo necesitas, están siempre con estos nombres: `pendiente, aceptada, rechazada, en_camino, completada`.

---

## 11. Checklist de implementación

### Código

- [ ] Actualizar interfaces TS (`TallerResponse.disponible`, `id_usuario_taller`, `id_usuario`)
- [ ] Remover `id_tecnico` de interfaces (tabla eliminada)
- [ ] Crear `TallerService.toggleDisponibilidad()` y `obtenerEvaluaciones()`
- [ ] Ampliar `AsignacionService` con query params `desde`/`hasta`
- [ ] Actualizar `TecnicoService.crear()` para requerir email y password

### Pantallas

- [ ] Header/sidebar: toggle de disponibilidad
- [ ] Detalle de asignación: botones "Aceptar" y "Rechazar" + dropdown de técnico para pendiente
- [ ] Estados aceptada/en_camino/completada: mostrar como solo lectura (técnico en app móvil)
- [ ] Página de reseñas con promedio de estrellas
- [ ] Formulario de técnico: campos email + password **obligatorios**
- [ ] Tabla de técnicos: mostrar email (todos tienen acceso a app)
- [ ] Historial: filtros por fecha (`desde`, `hasta`)
- [ ] Badge visual en asignaciones: colores diferenciados para pendiente/aceptada/etc

### Testing manual

- [ ] Crear un técnico con email+password **obligatorios** → funciona ✅
- [ ] Intentar crear técnico sin email → backend rechaza ✅
- [ ] Intentar crear técnico sin password → backend rechaza ✅
- [ ] Intentar crear dos técnicos con mismo email → 409 Conflict ✅
- [ ] Aceptar asignación con técnico → estado pasa a `aceptada` ✅
- [ ] Intentar asignar técnico con asignación activa → 409 Conflict ✅
- [ ] Rechazar asignación → desaparece de bandeja (reasignado a otro taller) ✅
- [ ] Toggle disponibilidad `false` → motor no envía nuevas solicitudes ✅
- [ ] Página de reseñas muestra estrellas y comentarios ✅
- [ ] Estados `aceptada`, `en_camino`, `completada` son solo lectura en web ✅
- [ ] Los endpoints `/iniciar-viaje` y `/completar` están en la guía de Flutter (no en web) ✅

---

## 12. Credenciales de prueba

Puedes probar todo con los datos de seed:

| Dato | Valor |
|---|---|
| Email gerente | `gerente@tallerexcelente.com` |
| Password | `taller123!` |
| Endpoint login | `POST /talleres/login` |

Para el técnico con credenciales (crear uno desde el dashboard primero), o usar uno que tú crees.

---

## 13. Preguntas frecuentes

**¿Qué pasa si acepto sin elegir técnico (id_usuario)?**
Se puede. `id_usuario` es opcional en `/aceptar`. Pero después el técnico no podrá ver la asignación en su app. → Recomendación: hacer el dropdown de técnico **obligatorio en la UI**.

**¿Qué pasa si un técnico tiene otra asignación activa y lo asigno acá?**
Backend devuelve 409 Conflict: "El técnico ya tiene una asignación activa (ID: XXX). Un técnico solo puede tener una asignación a la vez.". Muestra ese mensaje y dejá que el gerente elija otro.

**¿Puedo crear un técnico sin email y contraseña?**
⚠️ **No**. El backend requiere ambos campos obligatoriamente (usuario.email NOT NULL, usuario.password_hash NOT NULL). En tu formulario Angular, usa `Validators.required` para ambos.

**¿Puedo editar una asignación ya aceptada para cambiar el técnico?**
No hay endpoint para eso. Si necesitas cambiar técnico, rechaza y espera reasignación.

**¿Cuánto demora la reasignación automática?**
Instantánea — sucede dentro del mismo request de `/rechazar`. Cuando tu PUT responde 200, la nueva asignación para otro taller ya existe.

**¿Cómo se comporta el toggle disponibilidad si tengo asignaciones activas?**
Las asignaciones activas (`pendiente`, `aceptada`, `en_camino`) no se cancelan. Solo se bloquean las NUEVAS entrantes.

---

## 14. Endpoints del técnico en Flutter

Los endpoints `/iniciar-viaje` y `/completar` **no están en esta guía** — están en la documentación de Flutter porque los maneja el técnico desde su app móvil, no desde el panel web del taller.

La web del taller solo:
- ✅ Acepta o rechaza asignaciones (pendiente)
- ✅ Asigna técnico a la asignación
- 📱 El técnico continúa en su app (inicia viaje y completa)

---

## 14. Detalles técnicos críticos para Angular

### 1. TecnicoResponse: Remover id_tecnico

```typescript
// ❌ INCORRECTO (tabla eliminada)
export interface TecnicoResponse {
  id_tecnico: number;        // ⚠️ Ya no existe en BD
  id_usuario_taller: number;
  id_usuario: number;
  ...
}

// ✅ CORRECTO
export interface TecnicoResponse {
  id_usuario_taller: number;  // Usar para CRUD del taller
  id_usuario: number;         // Usar para asignar a incidentes
  nombre: string;
  email: string;              // Siempre presente (obligatorio)
  ...
}
```

### 2. TecnicoCreate: Email y Password OBLIGATORIOS

```typescript
// ❌ INCORRECTO (opcional = error 400)
export interface TecnicoCreate {
  nombre: string;
  email?: string;     // Opcional
  password?: string;  // Opcional
}

// ✅ CORRECTO
export interface TecnicoCreate {
  nombre: string;
  email: string;      // OBLIGATORIO
  password: string;   // OBLIGATORIO
  telefono?: string;  // Opcional
}
```

### 3. Validadores del Formulario

```typescript
form = this.fb.group({
  nombre: ['', [Validators.required, Validators.minLength(3)]],
  email: ['', [Validators.required, Validators.email]],           // ⚠️ REQUIRED
  password: ['', [Validators.required, Validators.minLength(8)]], // ⚠️ REQUIRED
  telefono: [''],  // Opcional
});
```

**Si omites `Validators.required` en email/password:**
- Frontend te deja enviar sin ellos
- Backend rechaza con 400/422 error
- Usuario confundido: "¿Por qué falla si rellené el formulario?"

### 4. Usar id_usuario al Aceptar Asignación

```typescript
// ❌ INCORRECTO
this.asignacionSrv.aceptar(idAsignacion, {
  id_tecnico: tecnico.id_tecnico,  // No existe
  ...
})

// ✅ CORRECTO
this.asignacionSrv.aceptar(idAsignacion, {
  id_usuario: tecnico.id_usuario,  // ID real del usuario (rol=3)
  eta_minutos: 25,
  nota: "..."
})
```
