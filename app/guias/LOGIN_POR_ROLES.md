# 🔐 Guía de Login por Roles - API Emergencias Vehiculares

## 📋 Estructura de Roles

```
┌─────────────────────────────────────────┐
│  PLATAFORMA DE EMERGENCIAS VEHICULARES  │
└─────────────────────────────────────────┘
        │
        ├── 📱 FLUTTER (App Móvil) 
        │   ├── id_rol=1 → Cliente (Conductor)
        │   └── id_rol=3 → Técnico (El Mecánico)
        │
        └── 🌐 ANGULAR (Web)
            ├── id_rol=2 → Taller
            └── id_rol=4 → Admin del Sistema
```

---

## 🔗 Endpoint Único de Login

```
POST /usuarios/login
Content-Type: application/json
```

**Todos los roles usan el MISMO endpoint**, pero con credenciales diferentes.

---

## 📱 FLUTTER - App Móvil

### 1️⃣ Login: Cliente (Conductor) - id_rol=1

**Request:**
```bash
curl -X POST "http://localhost:8000/usuarios/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "conductor@ejemplo.com",
    "password": "miPassword123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 5,
    "id_rol": 1,
    "nombre": "Juan Conductor",
    "email": "conductor@ejemplo.com",
    "activo": true,
    "created_at": "2026-04-15T10:30:00"
  }
}
```

**Acceso a endpoints:**
- ✅ GET `/usuarios/perfil` - Ver su perfil
- ✅ POST `/incidencias` - **Reportar emergencia (CU-05)**
- ✅ GET `/incidencias/mis-incidentes` - Ver sus incidentes
- ✅ PUT `/usuarios/perfil` - Editar su perfil
- ❌ GET `/talleres` - No tiene acceso
- ❌ GET `/admin/reportes` - No tiene acceso

---

### 2️⃣ Login: Técnico (Mecánico) - id_rol=3

**Request:**
```bash
curl -X POST "http://localhost:8000/usuarios/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tecnico.juan@taller.com",
    "password": "password456!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 12,
    "id_rol": 3,
    "nombre": "Juan Pérez - Técnico",
    "email": "tecnico.juan@taller.com",
    "activo": true,
    "created_at": "2026-01-10T08:15:00"
  }
}
```

**Acceso a endpoints:**
- ✅ GET `/usuarios/perfil` - Ver su perfil
- ✅ GET `/asignaciones/pendientes` - Ver incidentes asignados
- ✅ PUT `/asignaciones/{id}/status` - Actualizar estado
- ✅ POST `/asignaciones/{id}/completar` - Marcar como resuelto
- ❌ GET `/incidencias` - No puede ver todos
- ❌ DELETE `/usuarios` - No puede eliminar usuarios

---

## 🌐 ANGULAR - Panel Web

### 3️⃣ Login: Taller (Gerente) - id_rol=2

**Request:**
```bash
curl -X POST "http://localhost:8000/usuarios/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "gerente@tallerexcelente.com",
    "password": "gerente789!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 8,
    "id_rol": 2,
    "nombre": "Carlos - Gerente Taller",
    "email": "gerente@tallerexcelente.com",
    "activo": true,
    "created_at": "2025-06-20T14:00:00"
  }
}
```

**Acceso a endpoints:**
- ✅ GET `/usuarios/perfil` - Ver su perfil
- ✅ GET `/talleres/mi-taller` - Ver información del taller
- ✅ GET `/asignaciones` - Ver todas las asignaciones del taller
- ✅ POST `/asignaciones/{id}/tecnico` - Asignar técnico
- ✅ GET `/reportes/ganancias` - Ver ganancias del mes
- ✅ PUT `/talleres/{id}` - Editar datos del taller
- ❌ GET `/admin/usuarios` - No puede gestionar usuarios globales
- ❌ DELETE `/incidencias/{id}` - No puede eliminar incidentes

---

### 4️⃣ Login: Administrador - id_rol=4

**Request:**
```bash
curl -X POST "http://localhost:8000/usuarios/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@plataforma.com",
    "password": "admin2026!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 1,
    "id_rol": 4,
    "nombre": "Administrador Sistema",
    "email": "admin@plataforma.com",
    "activo": true,
    "created_at": "2026-01-01T00:00:00"
  }
}
```

**Acceso a endpoints:**
- ✅ GET `/admin/usuarios` - Ver todos los usuarios
- ✅ DELETE `/admin/usuarios/{id}` - Eliminar usuarios
- ✅ GET `/admin/reportes/globales` - Reportes generales
- ✅ GET `/admin/talleres` - Gestionar talleres
- ✅ PUT `/admin/talleres/{id}/verificar` - Verificar talleres
- ✅ POST `/admin/categorias` - Crear categorías
- ✅ GET `/admin/mettricas` - Ver métricas de la plataforma
- ✅ TODO LO DEMÁS - Acceso total

---

## 🔑 Flujo Completo de Autenticación

### Paso 1️⃣: Login
```
POST /usuarios/login
```
**Input:** email + password
**Output:** access_token (JWT)

### Paso 2️⃣: Guardar Token
```javascript
// En Flutter (Dart):
SharedPreferences prefs = await SharedPreferences.getInstance();
prefs.setString('access_token', response['access_token']);

// En Angular (TypeScript):
localStorage.setItem('access_token', response.access_token);
```

### Paso 3️⃣: Usar Token en Requests
```javascript
// Flutter (Dart):
String token = prefs.getString('access_token') ?? '';
var headers = {
  'Authorization': 'Bearer $token',
  'Content-Type': 'application/json'
};

// Angular (TypeScript):
const token = localStorage.getItem('access_token');
let headers = new HttpHeaders({
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
});
```

### Paso 4️⃣: Llamar Endpoint Protegido
```bash
curl -X GET "http://localhost:8000/usuarios/perfil" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 📊 Matriz de Permisos

| Endpoint | Cliente | Técnico | Taller | Admin |
|----------|---------|---------|--------|-------|
| POST /usuarios/login | ✅ | ✅ | ✅ | ✅ |
| GET /usuarios/perfil | ✅ | ✅ | ✅ | ✅ |
| PUT /usuarios/perfil | ✅ | ✅ | ✅ | ✅ |
| DELETE /usuarios/perfil | ✅ | ✅ | ✅ | ✅ |
| **POST /incidencias** | ✅ | ❌ | ❌ | ❌ |
| GET /incidencias/mis-incidentes | ✅ | ❌ | ❌ | ❌ |
| GET /asignaciones/pendientes | ❌ | ✅ | ✅ | ✅ |
| PUT /asignaciones/{id}/status | ❌ | ✅ | ✅ | ✅ |
| GET /reportes/ganancias | ❌ | ❌ | ✅ | ✅ |
| GET /admin/reportes | ❌ | ❌ | ❌ | ✅ |
| GET /admin/usuarios | ❌ | ❌ | ❌ | ✅ |
| DELETE /admin/usuarios/{id} | ❌ | ❌ | ❌ | ✅ |

---

## ⚠️ Errores Comunes

### 1️⃣ Email no registrado
```json
{
  "detail": "Email o contraseña incorrectos"
}
```
**Causa:** El usuario no existe en la BD
**Solución:** Crear el usuario primero con POST /usuarios/registro

### 2️⃣ Contraseña incorrecta
```json
{
  "detail": "Email o contraseña incorrectos"
}
```
**Causa:** Hash no coincide
**Solución:** Verificar que escribiste bien la contraseña

### 3️⃣ Usuario inactivo (dado de baja)
```json
{
  "detail": "El usuario ha sido desactivado"
}
```
**Causa:** activo=False
**Solución:** Contactar administrador para reactivar

### 4️⃣ Token expirado
```json
{
  "detail": "No se pudieron validar las credenciales"
}
```
**Causa:** El token tiene más de 30 minutos (configurable)
**Solución:** Hacer login nuevamente

---

## 🚀 Ejemplo Completo en Flutter

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String baseUrl = "http://localhost:8000";
  
  Future<bool> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/usuarios/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'password': password,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prefs = await SharedPreferences.getInstance();
        
        // Guardar token
        await prefs.setString('access_token', data['access_token']);
        await prefs.setString('user_id', data['usuario']['id_usuario'].toString());
        await prefs.setString('user_rol', data['usuario']['id_rol'].toString());
        await prefs.setString('user_name', data['usuario']['nombre']);
        
        return true;
      }
      return false;
    } catch (e) {
      print('Error en login: $e');
      return false;
    }
  }
  
  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('user_id');
    await prefs.remove('user_rol');
    await prefs.remove('user_name');
  }
}
```

---

## 🚀 Ejemplo Completo en Angular

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private baseUrl = 'http://localhost:8000';
  
  constructor(private http: HttpClient) {}
  
  login(email: string, password: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/usuarios/login`, {
      email,
      password
    });
  }
  
  saveToken(token: string, userData: any) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_id', userData.id_usuario);
    localStorage.setItem('user_rol', userData.id_rol);
    localStorage.setItem('user_name', userData.nombre);
  }
  
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }
  
  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_rol');
    localStorage.removeItem('user_name');
  }
  
  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
```

---

## 📅 Vigencia del Token

- **Duración:** 30 minutos (configurable en `.env`)
- **Almacenamiento:** JWT en memory (cliente)
- **Renovación:** Hacer login nuevamente
- **Almacenamiento seguro:** `localStorage` (Angular), `SharedPreferences` (Flutter)

---

**¡Listo para implementar en tus frontends!** 🎉
