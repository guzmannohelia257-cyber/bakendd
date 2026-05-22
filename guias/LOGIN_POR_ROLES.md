# 🔐 Guía de Login - Panel Web (Angular)

Guía de autenticación **exclusiva para los roles web** de la plataforma: **Taller** y **Admin**.

> Para levantar el servidor:
> ```
> cd "c:\Users\Isael Ortiz\Documents\yary\Backend" ; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
> ```

---

## 📋 Arquitectura de Autenticación

La plataforma tiene **dos sistemas de login separados**, cada uno contra su propia tabla:

```
┌──────────────────────────────────────────────────┐
│  PANEL WEB (Angular)                             │
├──────────────────────────────────────────────────┤
│                                                  │
│  🏭 TALLER  →  POST /talleres/login             │
│               tabla: taller                      │
│               token.tipo = "taller"              │
│                                                  │
│  👨‍💼 ADMIN  →  POST /usuarios/login              │
│               tabla: usuario (id_rol = 4)        │
│               token.tipo = "usuario"             │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Importante:** el token emitido por `/talleres/login` **no funciona** en endpoints de usuario, y viceversa. El servidor valida el claim `tipo` del JWT.

---

## 🏭 1️⃣ Login de Taller (`id_taller`)

El Taller es una entidad independiente con su propia cuenta.

### Request
```bash
curl -X POST "http://localhost:8000/talleres/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "gerente@tallerexcelente.com",
    "password": "taller123!"
  }'
```

### Response (200 OK)
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

### Endpoints accesibles con este token
- ✅ `GET /talleres/mi-taller` — ver info del taller
- ✅ `PUT /talleres/mi-taller` — editar info del taller
- ✅ `GET /talleres/mi-taller/tecnicos` — listar técnicos del taller
- ✅ `GET /talleres/mi-taller/tecnicos/{id}` — detalle de un técnico
- ✅ `POST /talleres/mi-taller/tecnicos` — agregar técnico
- ✅ `PUT /talleres/mi-taller/tecnicos/{id}` — editar técnico
- ✅ `DELETE /talleres/mi-taller/tecnicos/{id}` — baja lógica del técnico
- ❌ `GET /usuarios/perfil` — token de taller no sirve aquí
- ❌ `GET /admin/...` — no tiene permisos de admin

---

## 👨‍💼 2️⃣ Login de Admin (`id_rol = 4`)

El Admin es un registro en la tabla `usuario` con rol administrador.

### Request
```bash
curl -X POST "http://localhost:8000/usuarios/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@plataforma.com",
    "password": "admin123!"
  }'
```

### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 2,
    "id_rol": 4,
    "nombre": "Administrador Sistema",
    "email": "admin@plataforma.com",
    "telefono": "+57 3009999999",
    "activo": true,
    "created_at": "2026-04-18T22:56:46"
  }
}
```

### Endpoints accesibles con este token
- ✅ `GET /usuarios/perfil` — ver su perfil
- ✅ `PUT /usuarios/perfil` — editar su perfil
- ✅ `DELETE /usuarios/perfil` — dar de baja su cuenta
- 🔜 Endpoints de administración global (pendientes de implementar)

---

## 🔑 Flujo de Autenticación (Angular)

### Paso 1️⃣ — Login
```
POST /talleres/login      (taller)
POST /usuarios/login      (admin)
```
**Input:** `email` + `password`
**Output:** `access_token` (JWT)

### Paso 2️⃣ — Guardar token en `localStorage`
```typescript
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('tipo', 'taller'); // o 'admin'
```

### Paso 3️⃣ — Usar token en requests protegidos
```typescript
const token = localStorage.getItem('access_token');
const headers = new HttpHeaders({
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
});
```

### Paso 4️⃣ — Llamar endpoint protegido
```bash
curl -X GET "http://localhost:8000/talleres/mi-taller" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 📊 Matriz de Permisos (Web)

| Endpoint | Taller | Admin |
|----------|--------|-------|
| `POST /talleres/login` | ✅ | ❌ |
| `POST /usuarios/login` | ❌ | ✅ |
| `GET /talleres/mi-taller` | ✅ | ❌ |
| `PUT /talleres/mi-taller` | ✅ | ❌ |
| `GET /talleres/mi-taller/tecnicos` | ✅ | ❌ |
| `POST /talleres/mi-taller/tecnicos` | ✅ | ❌ |
| `PUT /talleres/mi-taller/tecnicos/{id}` | ✅ | ❌ |
| `DELETE /talleres/mi-taller/tecnicos/{id}` | ✅ | ❌ |
| `GET /usuarios/perfil` | ❌ | ✅ |
| `PUT /usuarios/perfil` | ❌ | ✅ |
| `DELETE /usuarios/perfil` | ❌ | ✅ |

> El admin **no** comparte endpoints con el taller: cada uno tiene su propio dominio de acceso.

---

## ⚠️ Errores Comunes

### 401 — Email o contraseña incorrectos
```json
{ "detail": "Email o contraseña incorrectos" }
```
**Causa:** Credenciales inválidas.
**Solución:** Verificar el email y el password.

### 401 — Token cruzado
```json
{ "detail": "No se pudieron validar las credenciales" }
```
**Causa:** Usaste un token de `/talleres/login` en un endpoint de `/usuarios/...`, o al revés.
**Solución:** Hacer login contra el endpoint correcto según el rol.

### 403 — Cuenta desactivada
```json
{ "detail": "El taller ha sido desactivado" }
```
o
```json
{ "detail": "Tu cuenta ha sido desactivada" }
```
**Causa:** El registro tiene `activo = false`.
**Solución:** Reactivar desde BD o contactar soporte.

### 401 — Token expirado
```json
{ "detail": "No se pudieron validar las credenciales" }
```
**Causa:** El JWT tiene más de `ACCESS_TOKEN_EXPIRE_MINUTES` (30 min por defecto).
**Solución:** Hacer login nuevamente.

---

## 🚀 Ejemplo en Angular — Servicio de Autenticación

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  // ============ LOGIN TALLER ============
  loginTaller(email: string, password: string): Observable<any> {
    return this.http
      .post<any>(`${this.baseUrl}/talleres/login`, { email, password })
      .pipe(tap(res => {
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('tipo', 'taller');
        localStorage.setItem('taller', JSON.stringify(res.taller));
      }));
  }

  // ============ LOGIN ADMIN ============
  loginAdmin(email: string, password: string): Observable<any> {
    return this.http
      .post<any>(`${this.baseUrl}/usuarios/login`, { email, password })
      .pipe(tap(res => {
        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('tipo', 'admin');
        localStorage.setItem('usuario', JSON.stringify(res.usuario));
      }));
  }

  // ============ HEADERS AUTENTICADOS ============
  authHeaders(): HttpHeaders {
    const token = localStorage.getItem('access_token') || '';
    return new HttpHeaders({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    });
  }

  // ============ LOGOUT ============
  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('tipo');
    localStorage.removeItem('taller');
    localStorage.removeItem('usuario');
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }

  getTipo(): 'taller' | 'admin' | null {
    return localStorage.getItem('tipo') as any;
  }
}
```

---

## 📅 Vigencia del Token

- **Duración:** 30 minutos (configurable en `.env` con `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Almacenamiento:** `localStorage` en el navegador
- **Renovación:** hacer login nuevamente (no hay refresh token)
- **Claim `tipo`:** el backend valida que el token sea del tipo correcto para cada endpoint

---

## 📌 Cuentas de Prueba (seed inicial)

| Rol | Endpoint de login | Email | Password |
|---|---|---|---|
| 🏭 Taller | `POST /talleres/login` | `gerente@tallerexcelente.com` | `taller123!` |
| 👨‍💼 Admin | `POST /usuarios/login` | `admin@plataforma.com` | `admin123!` |

---

**Listo para integrar en el panel Angular.** 🌐
