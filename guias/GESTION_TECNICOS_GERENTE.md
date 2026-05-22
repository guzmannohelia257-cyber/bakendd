# 🏭 Guía de Gestión de Técnicos - Para Gerentes de Taller

## 📋 Descripción

Esta guía documenta cómo el **Gerente del Taller** (rol=2) puede acceder al panel web Angular para:
- ✅ Ver información de su taller
- ✅ Editar datos del taller
- ✅ Ver lista de técnicos registrados
- ✅ Ver detalles de cada técnico
- ✅ Editar información de técnicos
- ✅ Agregar nuevos técnicos
- ✅ Desactivar/remover técnicos

---

## 🔐 Autenticación

### ⚠️ Importante: Dos Sistemas de Login Separados

La plataforma tiene **dos sistemas de autenticación independientes**:
- **`POST /talleres/login`** → Para autenticar como **Taller** (gerentes en panel web)
- **`POST /usuarios/login`** → Para autenticar como **Usuario/Cliente** (app móvil y admin)

Los tokens NO son intercambiables. El backend valida el tipo de token para cada endpoint.

### Login como Gerente de Taller

**Endpoint (CORRECTO para Gerentes):**
```
POST /talleres/login
```

**Request:**
```bash
curl -X POST "http://localhost:8000/talleres/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "gerente@tallerexcelente.com",
    "password": "taller123!"
  }'
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "taller": {
    "id_taller": 1,
    "nombre": "Taller Excelente",
    "email": "gerente@tallerexcelente.com",
    "telefono": "+57 3105552222",
    "direccion": "Cra 45 #123-45, Medellín",
    "latitud": 6.2442,
    "longitud": -75.5812,
    "capacidad_max": 5,
    "activo": true,
    "verificado": true,
    "created_at": "2026-04-18T22:56:46"
  }
}
```

**Guardar el token:**
```typescript
// En Angular (TypeScript)
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('tipo', 'taller');  // Importante: marcar que es token de taller
localStorage.setItem('taller_id', response.taller.id_taller);
localStorage.setItem('taller_name', response.taller.nombre);
```

---

## 🏭 Endpoints de Taller

### 1️⃣ Obtener Información de Mi Taller

**Endpoint:**
```
GET /talleres/mi-taller
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X GET "http://localhost:8000/talleres/mi-taller" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
  "id_taller": 1,
  "id_gerente": 5,
  "nombre": "Taller Excelente",
  "direccion": "Cra 45 #123-45, Medellín",
  "telefono": "+57 3105552222",
  "email": "gerente@tallerexcelente.com",
  "descripcion": "Taller especializado en reparación de vehículos ligeros",
  "verificado": true,
  "activo": true,
  "created_at": "2026-01-01T10:00:00",
  "updated_at": "2026-04-18T15:30:00"
}
```

---

### 2️⃣ Editar Información de Mi Taller

**Endpoint:**
```
PUT /talleres/mi-taller
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X PUT "http://localhost:8000/talleres/mi-taller" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Taller Super Excelente",
    "direccion": "Cra 45 #123-45 Piso 2, Medellín",
    "telefono": "+57 3105559999",
    "email": "gerente@tallerexcelente.com",
    "descripcion": "Nuevas instalaciones con equipos modernos"
  }'
```

**Response (200 OK):**
```json
{
  "id_taller": 1,
  "id_gerente": 5,
  "nombre": "Taller Super Excelente",
  "direccion": "Cra 45 #123-45 Piso 2, Medellín",
  "telefono": "+57 3105559999",
  "email": "gerente@tallerexcelente.com",
  "descripcion": "Nuevas instalaciones con equipos modernos",
  "verificado": true,
  "activo": true,
  "created_at": "2026-01-01T10:00:00",
  "updated_at": "2026-04-18T16:15:00"
}
```

**Notas:**
- Todos los campos son opcionales
- Solo actualiza los campos que envíes
- El ID del taller y del gerente no se pueden cambiar

---

## 👨‍🔧 Endpoints para Gestionar Técnicos

### 3️⃣ Listar Técnicos de Mi Taller

**Endpoint:**
```
GET /talleres/mi-taller/tecnicos
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X GET "http://localhost:8000/talleres/mi-taller/tecnicos" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
[
  {
    "id_usuario": 4,
    "nombre": "Juan Pérez - Técnico",
    "email": "tecnico.juan@taller.com",
    "telefono": "+57 3105551111",
    "activo": true,
    "created_at": "2026-01-10T08:15:00"
  },
  {
    "id_usuario": 7,
    "nombre": "Carlos Gómez - Técnico",
    "email": "tecnico.carlos@taller.com",
    "telefono": "+57 3105551112",
    "activo": true,
    "created_at": "2026-02-20T12:30:00"
  }
]
```

---

### 4️⃣ Obtener Detalles de un Técnico

**Endpoint:**
```
GET /talleres/mi-taller/tecnicos/{tecnico_id}
```

**Path Parameters:**
- `tecnico_id`: ID del técnico (entero)

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X GET "http://localhost:8000/talleres/mi-taller/tecnicos/4" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
  "id_usuario": 4,
  "nombre": "Juan Pérez - Técnico",
  "email": "tecnico.juan@taller.com",
  "telefono": "+57 3105551111",
  "activo": true,
  "id_taller": 1,
  "id_rol": 3,
  "created_at": "2026-01-10T08:15:00"
}
```

---

### 5️⃣ Editar Información de un Técnico

**Endpoint:**
```
PUT /talleres/mi-taller/tecnicos/{tecnico_id}
```

**Path Parameters:**
- `tecnico_id`: ID del técnico (entero)

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X PUT "http://localhost:8000/talleres/mi-taller/tecnicos/4" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Pérez García - Técnico Senior",
    "telefono": "+57 3105551999",
    "activo": true
  }'
```

**Response (200 OK):**
```json
{
  "id_usuario": 4,
  "nombre": "Juan Pérez García - Técnico Senior",
  "email": "tecnico.juan@taller.com",
  "telefono": "+57 3105551999",
  "activo": true,
  "created_at": "2026-01-10T08:15:00"
}
```

**Campos Editables:**
- `nombre`: Nombre completo del técnico
- `telefono`: Teléfono de contacto
- `activo`: true/false para activar o desactivar

---

### 6️⃣ Agregar Nuevo Técnico

**Endpoint:**
```
POST /talleres/mi-taller/tecnicos
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X POST "http://localhost:8000/talleres/mi-taller/tecnicos" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Carlos Gómez - Técnico",
    "email": "tecnico.carlos@taller.com",
    "telefono": "+57 3105551112",
    "password": "password456!"
  }'
```

**Response (201 Created):**
```json
{
  "id_usuario": 7,
  "nombre": "Carlos Gómez - Técnico",
  "email": "tecnico.carlos@taller.com",
  "telefono": "+57 3105551112",
  "activo": true,
  "created_at": "2026-04-18T15:45:00"
}
```

**Validaciones:**
- ✅ Email debe ser único en el sistema
- ✅ Nombre mínimo 3 caracteres
- ✅ Contraseña mínimo 8 caracteres
- ✅ Email debe ser válido
- ✅ Teléfono es opcional

---

### 7️⃣ Desactivar/Remover Técnico

**Endpoint:**
```
DELETE /talleres/mi-taller/tecnicos/{tecnico_id}
```

**Path Parameters:**
- `tecnico_id`: ID del técnico (entero)

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X DELETE "http://localhost:8000/talleres/mi-taller/tecnicos/4" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

**Response (200 OK):**
```json
{
  "mensaje": "Técnico desactivado correctamente del taller"
}
```

**Nota:** 
- Se utiliza **baja lógica** (no se elimina de la BD)
- El técnico queda con `activo=false`
- Se mantiene toda la trazabilidad de incidentes y asignaciones
- Puede ser reactivado editando el técnico con `activo=true`

---

## 🔍 Códigos de Error

### 401 Unauthorized (No Autorizado)
```json
{
  "detail": "No se pudieron validar las credenciales"
}
```
**Causa:** Token expirado o inválido
**Solución:** Hacer login nuevamente

### 403 Forbidden (Prohibido)
```json
{
  "detail": "Solo los gerentes de taller pueden acceder a esta información"
}
```
**Causa:** Tu rol no es Taller (rol=2)
**Solución:** Asegúrate de estar logueado como gerente

### 404 Not Found (No Encontrado)
```json
{
  "detail": "Técnico no encontrado en tu taller"
}
```
**Causa:** El técnico no existe o pertenece a otro taller
**Solución:** Verifica el ID del técnico

### 409 Conflict (Conflicto)
```json
{
  "detail": "El email ya está registrado en el sistema"
}
```
**Causa:** El email ya existe
**Solución:** Usa otro email para el nuevo técnico

---

## 📱 Ejemplo Completo en Angular

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class TallerService {
  private baseUrl = 'http://localhost:8000/talleres';
  
  constructor(private http: HttpClient) {}
  
  // Obtener mi taller
  obtenerMiTaller(): Observable<any> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.get(`${this.baseUrl}/mi-taller`, { headers });
  }
  
  // Editar mi taller
  editarMiTaller(tallerData: any): Observable<any> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.put(`${this.baseUrl}/mi-taller`, tallerData, { headers });
  }
  
  // Listar técnicos
  obtenerTecnicos(): Observable<any[]> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.get<any[]>(`${this.baseUrl}/mi-taller/tecnicos`, { headers });
  }
  
  // Obtener detalles de un técnico
  obtenerTecnico(tecnicoId: number): Observable<any> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.get(`${this.baseUrl}/mi-taller/tecnicos/${tecnicoId}`, { headers });
  }
  
  // Editar técnico
  editarTecnico(tecnicoId: number, tecnicoData: any): Observable<any> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.put(`${this.baseUrl}/mi-taller/tecnicos/${tecnicoId}`, tecnicoData, { headers });
  }
  
  // Agregar nuevo técnico
  agregarTecnico(tecnicoData: any): Observable<any> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.post(`${this.baseUrl}/mi-taller/tecnicos`, tecnicoData, { headers });
  }
  
  // Remover técnico
  removerTecnico(tecnicoId: number): Observable<any> {
    const headers = new HttpHeaders({
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    });
    return this.http.delete(`${this.baseUrl}/mi-taller/tecnicos/${tecnicoId}`, { headers });
  }
  
  // Utilidad: obtener token
  private getToken(): string {
    return localStorage.getItem('access_token') || '';
  }
}
```

---

## 🎨 Componente Angular para Gestionar Técnicos

```typescript
import { Component, OnInit } from '@angular/core';
import { TallerService } from './taller.service';

@Component({
  selector: 'app-tecnicos-list',
  templateUrl: './tecnicos-list.component.html',
  styleUrls: ['./tecnicos-list.component.css']
})
export class TecnicosListComponent implements OnInit {
  tecnicos: any[] = [];
  taller: any = {};
  loading = false;
  error = '';
  
  // Formulario para agregar técnico
  mostrarFormulario = false;
  nuevoTecnico = {
    nombre: '',
    email: '',
    telefono: '',
    password: ''
  };
  
  constructor(private tallerService: TallerService) {}
  
  ngOnInit(): void {
    this.cargarDatos();
  }
  
  cargarDatos(): void {
    this.loading = true;
    
    // Obtener información del taller
    this.tallerService.obtenerMiTaller().subscribe({
      next: (data) => {
        this.taller = data;
        this.cargarTecnicos();
      },
      error: (err) => {
        this.error = 'Error al cargar información del taller';
        this.loading = false;
      }
    });
  }
  
  cargarTecnicos(): void {
    this.tallerService.obtenerTecnicos().subscribe({
      next: (data) => {
        this.tecnicos = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al cargar técnicos';
        this.loading = false;
      }
    });
  }
  
  agregarTecnico(): void {
    if (!this.nuevoTecnico.nombre || !this.nuevoTecnico.email || !this.nuevoTecnico.password) {
      this.error = 'Completa todos los campos requeridos';
      return;
    }
    
    this.loading = true;
    this.tallerService.agregarTecnico(this.nuevoTecnico).subscribe({
      next: (data) => {
        this.tecnicos.push(data);
        this.nuevoTecnico = { nombre: '', email: '', telefono: '', password: '' };
        this.mostrarFormulario = false;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al agregar técnico: ' + err.error.detail;
        this.loading = false;
      }
    });
  }
  
  editarTecnico(tecnico: any): void {
    const nombre = prompt('Nuevo nombre:', tecnico.nombre);
    if (!nombre) return;
    
    this.loading = true;
    this.tallerService.editarTecnico(tecnico.id_usuario, { nombre }).subscribe({
      next: (data) => {
        const index = this.tecnicos.findIndex(t => t.id_usuario === tecnico.id_usuario);
        this.tecnicos[index] = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al editar técnico';
        this.loading = false;
      }
    });
  }
  
  removerTecnico(tecnico: any): void {
    if (!confirm(`¿Desactivar a ${tecnico.nombre}?`)) return;
    
    this.loading = true;
    this.tallerService.removerTecnico(tecnico.id_usuario).subscribe({
      next: () => {
        this.tecnicos = this.tecnicos.filter(t => t.id_usuario !== tecnico.id_usuario);
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Error al remover técnico';
        this.loading = false;
      }
    });
  }
}
```

---

## 📋 Flujo de Acceso

```
┌─────────────────────────────────────┐
│ Gerente Inicia Sesión               │
│ (POST /usuarios/login)              │
│ email: gerente@tallerexcelente.com  │
│ password: gerente789!               │
└────────────────┬────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Obtiene JWT Token  │
        │ Valida rol=2       │
        └────────────┬───────┘
                     │
        ┌────────────┴────────────┬──────────────────┐
        ▼                         ▼                  ▼
   ┌─────────────┐      ┌──────────────────┐  ┌──────────────┐
   │ Ver Taller  │      │ Ver Técnicos     │  │Agregar Técnico
   │ GET /taller │      │ GET /tecnicos    │  │ POST /tecnicos
   └─────────────┘      └──────────────────┘  └──────────────┘
        │                         │                 │
        ▼                         ▼                 ▼
   Editar Taller         Editar Técnico        Listar Técnicos
   PUT /taller           PUT /tecnicos/{id}    GET /tecnicos
        │                         │                 │
        └─────────────────────────┴─────────────────┘
                         │
                         ▼
            Remover Técnico (Baja Lógica)
            DELETE /tecnicos/{id}
```

---

## ✅ Checklist de Implementación

- ✅ Login con credenciales de gerente
- ✅ Obtener información del taller
- ✅ Editar datos del taller
- ✅ Ver lista de técnicos
- ✅ Ver detalles de cada técnico
- ✅ Editar información de técnicos
- ✅ Agregar nuevos técnicos
- ✅ Desactivar técnicos
- ✅ Manejar errores de autorización
- ✅ Mantener token en localStorage

---

**¡Panel de Gestión de Técnicos Lista para Implementación!** 🚀
