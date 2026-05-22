# 📱 Guía de Perfil de Usuario - App Móvil Flutter

## 📋 Descripción

Esta guía documenta cómo el **Cliente** (rol=1) y **Técnico** (rol=3) pueden acceder desde su app móvil Flutter para:
- ✅ Iniciar sesión con email y contraseña
- ✅ Ver información de su perfil personal
- ✅ Editar su nombre y teléfono
- ✅ Cambiar su contraseña
- ✅ Cerrar sesión

**⚠️ IMPORTANTE: Esta guía es SOLO para App Móvil Flutter (Cliente y Técnico)**

Para **Panel Web Angular** (Taller y Admin), consulta: **LOGIN_POR_ROLES.md**

---

## 🚀 Usuarios de Prueba para Flutter

| Rol | Email | Contraseña | Estado |
|-----|-------|-----------|--------|
| **Cliente** | conductor@ejemplo.com | **cliente123!** | ✅ Listo |
| **Técnico** | (Sin login directo) | (Solo en taller) | ℹ️ Ver nota |

**Para Panel Web (Angular):** Consulta [LOGIN_POR_ROLES.md](LOGIN_POR_ROLES.md)
- Taller: gerente@tallerexcelente.com / **taller123!**
- Admin: admin@plataforma.com / **admin123!**

---

### 📌 Nota sobre Técnicos

Los **técnicos NO se autentican directamente** en la app móvil.

En su lugar:
1. El **Taller** (gerente) maneja técnicos desde el panel web
2. Los 2 técnicos están precargados: **Juan Pérez** y **Carlos Gómez**
3. Se accede a ellos mediante: `GET /talleres/mi-taller/tecnicos` (requiere token de taller)

Ver: [GESTION_TECNICOS_GERENTE.md](GESTION_TECNICOS_GERENTE.md)

---

## 🚀 Inicio Rápido

### Cliente Login

1. **Usar credenciales:**
   ```
   Email: conductor@ejemplo.com
   Contraseña: cliente123!
   ```

2. **Guardar token en SharedPreferences**
3. **Usar GET /usuarios/perfil para obtener datos**
4. **Usar PUT /usuarios/perfil para actualizar**
5. **Logout: Limpiar SharedPreferences y redirigir a login**

✅ **BD completamente poblada y lista para usar. No requiere seed.**

---

## 🔐 Autenticación

### Login como Cliente

**Endpoint:**
```
POST /usuarios/login
```

**Request:**
```bash
curl -X POST "http://localhost:8000/usuarios/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "conductor@ejemplo.com",
    "password": "cliente123!"
  }'
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id_usuario": 1,
    "id_rol": 1,
    "nombre": "Juan Conductor",
    "email": "conductor@ejemplo.com",
    "telefono": "+57 3001234567",
    "activo": true,
    "created_at": "2026-04-18T22:56:46"
  }
}
```

**Guardar el token en SharedPreferences (Flutter):**
```dart
import 'package:shared_preferences/shared_preferences.dart';

// Después del login exitoso
SharedPreferences prefs = await SharedPreferences.getInstance();
await prefs.setString('access_token', response['access_token']);
await prefs.setString('user_id', response['usuario']['id_usuario'].toString());
await prefs.setString('user_rol', response['usuario']['id_rol'].toString());
await prefs.setString('user_email', response['usuario']['email']);
await prefs.setString('user_name', response['usuario']['nombre']);
await prefs.setString('user_telefono', response['usuario']['telefono'] ?? '');

// Guardar como cliente
await prefs.setString('user_type', 'cliente');
```

---

## 👤 Endpoints de Perfil

### 1️⃣ Ver Mi Perfil

**Endpoint:**
```
GET /usuarios/perfil
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X GET "http://localhost:8000/usuarios/perfil" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

**Response (200 OK) - Cliente:**
```json
{
  "id_usuario": 1,
  "id_rol": 1,
  "nombre": "Juan Conductor",
  "email": "conductor@ejemplo.com",
  "telefono": "+57 3001234567",
  "activo": true,
  "created_at": "2026-04-18T22:56:46"
}
```

**Response (200 OK) - Técnico:**
```json
{
  "id_usuario": 2,
  "id_rol": 3,
  "nombre": "Juan Pérez - Técnico",
  "email": "tecnico.juan@taller.com",
  "telefono": "+57 3105551111",
  "activo": true,
  "created_at": "2026-04-18T22:56:46"
}
```

---

### 2️⃣ Editar Mi Perfil

**Endpoint:**
```
PUT /usuarios/perfil
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Campos Editables:**
- `nombre`: Nombre completo (opcional)
- `telefono`: Teléfono de contacto (opcional)
- `password`: Nueva contraseña mínimo 8 caracteres (opcional)

**Request - Cliente cambia nombre y teléfono:**
```bash
curl -X PUT "http://localhost:8000/usuarios/perfil" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Carlos Pérez Conductor",
    "telefono": "+57 3105551234"
  }'
```

**Response (200 OK) - Cliente actualizado:**
```json
{
  "id_usuario": 1,
  "id_rol": 1,
  "nombre": "Juan Carlos Pérez Conductor",
  "email": "conductor@ejemplo.com",
  "telefono": "+57 3105551234",
  "activo": true,
  "created_at": "2026-04-18T22:56:46"
}
```

**Request - Técnico cambia información:**
```bash
curl -X PUT "http://localhost:8000/usuarios/perfil" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Pérez García - Técnico Senior",
    "telefono": "+57 3105559999"
  }'
```

**Response (200 OK) - Técnico actualizado:**
```json
{
  "id_usuario": 2,
  "id_rol": 3,
  "nombre": "Juan Pérez García - Técnico Senior",
  "email": "tecnico.juan@taller.com",
  "telefono": "+57 3105559999",
  "activo": true,
  "created_at": "2026-04-18T22:56:46"
}
```

---

### 3️⃣ Cambiar Contraseña

**Endpoint:**
```
PUT /usuarios/perfil
```

**Request - Solo cambiar contraseña:**
```bash
curl -X PUT "http://localhost:8000/usuarios/perfil" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "password": "miNuevaPassword789"
  }'
```

**Response (200 OK):**
```json
{
  "id_usuario": 1,
  "id_rol": 1,
  "nombre": "Juan Conductor",
  "email": "conductor@ejemplo.com",
  "telefono": "+57 3001234567",
  "activo": true,
  "created_at": "2026-04-18T22:56:46"
}
```

**Importante:**
- ✅ La contraseña se hashea automáticamente con Argon2-cffi
- ✅ La contraseña anterior queda invalidada inmediatamente
- ✅ La nueva contraseña es válida para los próximos logins
- ✅ No devolvemos la contraseña en la respuesta (por seguridad)
- ⚠️ Mínimo 8 caracteres, sin espacios

---

### 4️⃣ Cerrar Sesión (Logout)

**En Flutter (no hay endpoint en el backend):**
```dart
import 'package:shared_preferences/shared_preferences.dart';

Future<void> logout() async {
  SharedPreferences prefs = await SharedPreferences.getInstance();
  await prefs.remove('access_token');
  await prefs.remove('user_id');
  await prefs.remove('user_email');
  await prefs.remove('user_name');
  
  // Navegar a pantalla de login
  Navigator.of(context).pushReplacementNamed('/login');
}
```

---

## 🚀 Ejemplo Completo en Flutter (Dart)

### Auth Service

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class AuthService {
  static const String baseUrl = "http://localhost:8000";
  
  // ============ LOGIN ============
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/usuarios/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prefs = await SharedPreferences.getInstance();
        
        // Guardar datos
        await prefs.setString('access_token', data['access_token']);
        await prefs.setString('user_id', data['usuario']['id_usuario'].toString());
        await prefs.setString('user_email', data['usuario']['email']);
        await prefs.setString('user_name', data['usuario']['nombre']);
        
        return {'success': true, 'usuario': data['usuario']};
      }
      return {'success': false, 'error': 'Email o contraseña incorrectos'};
    } catch (e) {
      return {'success': false, 'error': 'Error de conexión: $e'};
    }
  }
  
  // ============ VER PERFIL ============
  Future<Map<String, dynamic>> obtenerPerfil() async {
    try {
      final token = await getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final response = await http.get(
        Uri.parse('$baseUrl/usuarios/perfil'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'perfil': data};
      }
      return {'success': false, 'error': 'Error al obtener perfil'};
    } catch (e) {
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // ============ EDITAR PERFIL ============
  Future<Map<String, dynamic>> editarPerfil({
    String? nombre,
    String? telefono,
    String? password,
  }) async {
    try {
      final token = await getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final body = <String, dynamic>{};
      if (nombre != null) body['nombre'] = nombre;
      if (telefono != null) body['telefono'] = telefono;
      if (password != null) body['password'] = password;
      
      final response = await http.put(
        Uri.parse('$baseUrl/usuarios/perfil'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode(body),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Actualizar nombre en SharedPreferences
        if (nombre != null) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('user_name', nombre);
        }
        
        return {'success': true, 'perfil': data};
      }
      return {'success': false, 'error': 'Error al editar perfil'};
    } catch (e) {
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // ============ LOGOUT ============
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('user_id');
    await prefs.remove('user_email');
    await prefs.remove('user_name');
  }
  
  // ============ UTILIDADES ============
  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  Future<bool> isAuthenticated() async {
    final token = await getToken();
    return token != null;
  }
}
```

---

### Pantalla de Perfil

```dart
import 'package:flutter/material.dart';

class PantallaPerfilCliente extends StatefulWidget {
  @override
  State<PantallaPerfilCliente> createState() => _PantallaPerfilClienteState();
}

class _PantallaPerfilClienteState extends State<PantallaPerfilCliente> {
  final authService = AuthService();
  
  late TextEditingController nombreController;
  late TextEditingController telefonoController;
  late TextEditingController passwordController;
  
  Map<String, dynamic> perfil = {};
  bool cargando = false;
  String? error;
  
  @override
  void initState() {
    super.initState();
    nombreController = TextEditingController();
    telefonoController = TextEditingController();
    passwordController = TextEditingController();
    cargarPerfil();
  }
  
  void cargarPerfil() async {
    setState(() => cargando = true);
    
    final resultado = await authService.obtenerPerfil();
    
    if (resultado['success']) {
      setState(() {
        perfil = resultado['perfil'];
        nombreController.text = perfil['nombre'] ?? '';
        telefonoController.text = perfil['telefono'] ?? '';
        error = null;
      });
    } else {
      setState(() => error = resultado['error']);
    }
    
    setState(() => cargando = false);
  }
  
  void guardarCambios() async {
    setState(() => cargando = true);
    
    final resultado = await authService.editarPerfil(
      nombre: nombreController.text,
      telefono: telefonoController.text,
      password: passwordController.text.isEmpty ? null : passwordController.text,
    );
    
    if (resultado['success']) {
      setState(() {
        perfil = resultado['perfil'];
        passwordController.clear();
        error = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ Perfil actualizado correctamente')),
      );
    } else {
      setState(() => error = resultado['error']);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ ${resultado['error']}')),
      );
    }
    
    setState(() => cargando = false);
  }
  
  void cerrarSesion() async {
    final confirmar = await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Cerrar Sesión'),
        content: Text('¿Deseas cerrar sesión?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text('Sí')),
        ],
      ),
    );
    
    if (confirmar) {
      await authService.logout();
      Navigator.pushReplacementNamed(context, '/login');
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Mi Perfil'),
        centerTitle: true,
      ),
      body: cargando
          ? Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: EdgeInsets.all(20),
              child: Column(
                children: [
                  if (error != null)
                    Container(
                      padding: EdgeInsets.all(12),
                      margin: EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: Colors.red.shade100,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(error!, style: TextStyle(color: Colors.red.shade700)),
                    ),
                  
                  // Información de identificación (No editable)
                  Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('ID Usuario:', style: TextStyle(fontWeight: FontWeight.bold)),
                          Text('${perfil['id_usuario']}'),
                          SizedBox(height: 12),
                          Text('Email:', style: TextStyle(fontWeight: FontWeight.bold)),
                          Text('${perfil['email']}'),
                          SizedBox(height: 12),
                          Text('Rol:', style: TextStyle(fontWeight: FontWeight.bold)),
                          Text(perfil['id_rol'] == 1 ? 'Cliente' : perfil['id_rol'] == 3 ? 'Técnico' : 'Otro'),
                          SizedBox(height: 12),
                          Text('Miembro desde:', style: TextStyle(fontWeight: FontWeight.bold)),
                          Text('${perfil['created_at']}'.split('T')[0]),
                        ],
                      ),
                    ),
                  ),
                  SizedBox(height: 24),
                  
                  // Formulario de edición
                  TextField(
                    controller: nombreController,
                    decoration: InputDecoration(
                      labelText: 'Nombre Completo',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.person),
                    ),
                  ),
                  SizedBox(height: 16),
                  
                  TextField(
                    controller: telefonoController,
                    decoration: InputDecoration(
                      labelText: 'Teléfono',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.phone),
                    ),
                    keyboardType: TextInputType.phone,
                  ),
                  SizedBox(height: 16),
                  
                  TextField(
                    controller: passwordController,
                    decoration: InputDecoration(
                      labelText: 'Nueva Contraseña (opcional)',
                      hintText: 'Deja en blanco para no cambiar',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.lock),
                    ),
                    obscureText: true,
                  ),
                  SizedBox(height: 24),
                  
                  // Botones
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: guardarCambios,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        padding: EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: Text(
                        'Guardar Cambios',
                        style: TextStyle(fontSize: 16, color: Colors.white),
                      ),
                    ),
                  ),
                  SizedBox(height: 12),
                  
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: cerrarSesion,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        padding: EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: Text(
                        'Cerrar Sesión',
                        style: TextStyle(fontSize: 16, color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
  
  @override
  void dispose() {
    nombreController.dispose();
    telefonoController.dispose();
    passwordController.dispose();
    super.dispose();
  }
}
```

---

## 🔍 Códigos de Error

### 401 Unauthorized
```json
{
  "detail": "No se pudieron validar las credenciales"
}
```
**Causa:** Token expirado o inválido
**Solución:** Hacer login nuevamente

### 403 Forbidden
```json
{
  "detail": "El usuario ha sido desactivado"
}
```
**Causa:** La cuenta fue desactivada (baja lógica)
**Solución:** Contactar con soporte

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "msg": "value_error.email"
    }
  ]
}
```
**Causa:** Email inválido o contraseña muy corta
**Solución:** Verifica los datos ingresados



## 📊 Matriz de Acceso

| Endpoint | Método | Requiere Auth | Acceso | Descripción |
|----------|--------|---------------|---------|-----------| 
| `/usuarios/login` | POST | ❌ No | Cliente, Técnico | Iniciar sesión |
| `/usuarios/perfil` | GET | ✅ Sí | Cliente, Técnico | Ver perfil actual |
| `/usuarios/perfil` | PUT | ✅ Sí | Cliente, Técnico | Editar nombre, teléfono, contraseña |
| `/usuarios/perfil` | DELETE | ✅ Sí | Cliente, Técnico | Deactivar cuenta (baja lógica) |
| `/usuarios/perfil` | DELETE | ✅ Sí | Cliente, Técnico | Deactivar cuenta (baja lógica) |

---

## 🎯 Solución: URL Correcta en Flutter

**⚠️ IMPORTANTE:** Si usas un emulador Android, `localhost` no funciona.

### Para Emulador Android:
```dart
static const String baseUrl = "http://10.0.2.2:8000";
```

### Para Dispositivo Físico:
```dart
// Reemplaza 192.168.1.100 con tu IP real
static const String baseUrl = "http://192.168.1.100:8000";
```

---

## ✅ Flujo Completo

```
1️⃣ LOGIN
   POST /usuarios/login
   ↓
   Token guardado en SharedPreferences
   ↓
2️⃣ VER PERFIL
   GET /usuarios/perfil
   (Mostrar en pantalla)
   ↓
3️⃣ EDITAR PERFIL
   PUT /usuarios/perfil
   (Actualizar campos)
   ↓
4️⃣ CERRAR SESIÓN
   Limpiar SharedPreferences
   Navegar a login
```

---

## 🎯 Casos de Uso

### Caso 1: Cliente quiere cambiar su nombre
```dart
await authService.editarPerfil(nombre: "Juan Carlos Pérez Nuevo");
```

### Caso 2: Cliente quiere cambiar teléfono
```dart
await authService.editarPerfil(telefono: "+57 3105559999");
```

### Caso 3: Cliente quiere cambiar contraseña
```dart
await authService.editarPerfil(password: "miNuevaPassword123!");
```

### Caso 4: Cliente quiere cambiar todo
```dart
await authService.editarPerfil(
  nombre: "Juan Carlos Pérez",
  telefono: "+57 3105559999",
  password: "miNuevaPassword123!"
);
```

---

## 📌 Diferencia: App Móvil vs Panel Web

**Esta Guía (PERFIL_CLIENTE_MOBILE.md)** → App Móvil Flutter
- Roles: Cliente (rol=1)
- Endpoint: `POST /usuarios/login`
- Credencial: conductor@ejemplo.com / cliente123!

**Otra Guía (LOGIN_POR_ROLES.md)** → Panel Web Angular
- Roles: Taller (rol=2) y Admin (rol=4)
- Endpoints: `POST /talleres/login` y `POST /usuarios/login`
- Credenciales: gerente@tallerexcelente.com / taller123! y admin@plataforma.com / admin123!
