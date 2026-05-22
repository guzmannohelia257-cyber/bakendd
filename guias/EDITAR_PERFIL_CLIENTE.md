# 📝 Guía: Editar Perfil del Cliente

## 📌 Overview

El cliente (usuario de rol=1) puede actualizar su perfil con:
- Nombre
- Email (único, validado)
- Teléfono
- Foto de perfil (opcional)

---

## 🔗 Endpoints del Backend

### 1. Obtener Perfil (GET /usuarios/perfil)

**Requiere:** JWT token en header Authorization

```bash
curl -X GET http://localhost:8000/usuarios/perfil \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
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
  "created_at": "2026-04-19T01:30:00"
}
```

### 2. Actualizar Perfil (PUT /usuarios/perfil)

**Requiere:** JWT token + JSON body

```bash
curl -X PUT http://localhost:8000/usuarios/perfil \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Pérez Nuevo",
    "email": "juan.nuevo@ejemplo.com",
    "telefono": "+57 3009999999"
  }'
```

**Response (200 OK):**
```json
{
  "id_usuario": 1,
  "id_rol": 1,
  "nombre": "Juan Pérez Nuevo",
  "email": "juan.nuevo@ejemplo.com",
  "telefono": "+57 3009999999",
  "activo": true,
  "updated_at": "2026-04-19T02:45:00"
}
```

**Errores posibles:**
- `400 Bad Request` - Email ya existe en el sistema
- `401 Unauthorized` - Token inválido o expirado
- `404 Not Found` - Usuario no encontrado

---

## 🎯 Modelo de Datos

### UsuarioResponse (Lectura)
```dart
class UsuarioResponse {
  final int idUsuario;
  final int idRol;
  final String nombre;
  final String email;
  final String? telefono;
  final bool activo;
  final DateTime createdAt;
  final DateTime? updatedAt;

  UsuarioResponse({
    required this.idUsuario,
    required this.idRol,
    required this.nombre,
    required this.email,
    this.telefono,
    required this.activo,
    required this.createdAt,
    this.updatedAt,
  });

  factory UsuarioResponse.fromJson(Map<String, dynamic> json) {
    return UsuarioResponse(
      idUsuario: json['id_usuario'],
      idRol: json['id_rol'],
      nombre: json['nombre'],
      email: json['email'],
      telefono: json['telefono'],
      activo: json['activo'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : null,
    );
  }
}
```

### UsuarioUpdate (Actualización)
```dart
class UsuarioUpdate {
  final String nombre;
  final String email;
  final String? telefono;

  UsuarioUpdate({
    required this.nombre,
    required this.email,
    this.telefono,
  });

  Map<String, dynamic> toJson() => {
    'nombre': nombre,
    'email': email,
    'telefono': telefono,
  };
}
```

---

## 🛠️ Servicio (lib/services/usuario_service.dart)

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class UsuarioService {
  static const String baseUrl = "http://10.0.2.2:8000";
  
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  // Obtener perfil actual
  Future<Map<String, dynamic>> obtenerPerfil() async {
    try {
      print('[USUARIO] Obteniendo perfil...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final response = await http.get(
        Uri.parse('$baseUrl/usuarios/perfil'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      );
      
      print('[USUARIO] Status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final usuario = jsonDecode(response.body);
        print('[USUARIO] Perfil cargado: ${usuario['nombre']}');
        return {'success': true, 'usuario': usuario};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      }
      
      return {'success': false, 'error': 'Error al obtener perfil'};
    } catch (e) {
      print('[USUARIO] Exception: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // Actualizar perfil
  Future<Map<String, dynamic>> actualizarPerfil({
    required String nombre,
    required String email,
    String? telefono,
  }) async {
    try {
      print('[USUARIO] Actualizando perfil...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final body = {
        'nombre': nombre,
        'email': email,
        'telefono': telefono,
      };
      
      print('[USUARIO] Body: $body');
      
      final response = await http.put(
        Uri.parse('$baseUrl/usuarios/perfil'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode(body),
      );
      
      print('[USUARIO] Status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final usuario = jsonDecode(response.body);
        print('[USUARIO] Perfil actualizado');
        
        // Actualizar datos en SharedPreferences
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('user_name', usuario['nombre']);
        await prefs.setString('user_email', usuario['email']);
        
        return {'success': true, 'usuario': usuario};
      } else if (response.statusCode == 400) {
        final error = jsonDecode(response.body);
        return {'success': false, 'error': error['detail'] ?? 'Email ya existe'};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      }
      
      return {'success': false, 'error': 'Error al actualizar perfil'};
    } catch (e) {
      print('[USUARIO] Exception: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
}
```

---

## 📱 Pantalla de Edición (EditarPerfilScreen)

```dart
import 'package:flutter/material.dart';
import '../services/usuario_service.dart';

class EditarPerfilScreen extends StatefulWidget {
  final Map<String, dynamic> usuarioInicial;
  
  const EditarPerfilScreen({required this.usuarioInicial});
  
  @override
  State<EditarPerfilScreen> createState() => _EditarPerfilScreenState();
}

class _EditarPerfilScreenState extends State<EditarPerfilScreen> {
  final usuarioService = UsuarioService();
  final _formKey = GlobalKey<FormState>();
  
  late TextEditingController _nombreController;
  late TextEditingController _emailController;
  late TextEditingController _telefonoController;
  
  bool guardando = false;
  String? errorGeneral;
  
  @override
  void initState() {
    super.initState();
    _nombreController = TextEditingController(
      text: widget.usuarioInicial['nombre'] ?? ''
    );
    _emailController = TextEditingController(
      text: widget.usuarioInicial['email'] ?? ''
    );
    _telefonoController = TextEditingController(
      text: widget.usuarioInicial['telefono'] ?? ''
    );
  }
  
  @override
  void dispose() {
    _nombreController.dispose();
    _emailController.dispose();
    _telefonoController.dispose();
    super.dispose();
  }
  
  void guardarCambios() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() {
      guardando = true;
      errorGeneral = null;
    });
    
    final resultado = await usuarioService.actualizarPerfil(
      nombre: _nombreController.text.trim(),
      email: _emailController.text.trim(),
      telefono: _telefonoController.text.trim().isEmpty 
        ? null 
        : _telefonoController.text.trim(),
    );
    
    if (!mounted) return;
    
    if (resultado['success']) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Perfil actualizado exitosamente'),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 2),
        ),
      );
      
      // Retornar los datos actualizados
      Navigator.pop(context, resultado['usuario']);
    } else {
      setState(() {
        errorGeneral = resultado['error'];
        
        // Si es error de autenticación expirada
        if (resultado['code'] == 'AUTH_EXPIRED') {
          Future.delayed(Duration(seconds: 2), () {
            Navigator.of(context).pushReplacementNamed('/login');
          });
        }
      });
    }
    
    setState(() => guardando = false);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Editar Perfil'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Error general
              if (errorGeneral != null) ...[
                Container(
                  width: double.infinity,
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    border: Border.all(color: Colors.red),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: Colors.red),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          errorGeneral!,
                          style: TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: 16),
              ],
              
              // Campo Nombre
              Text(
                'Nombre Completo',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              TextFormField(
                controller: _nombreController,
                decoration: InputDecoration(
                  hintText: 'Tu nombre completo',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (value) {
                  if (value?.isEmpty ?? true) return 'Ingresa tu nombre';
                  if (value!.length < 3) return 'Mínimo 3 caracteres';
                  return null;
                },
                enabled: !guardando,
              ),
              SizedBox(height: 16),
              
              // Campo Email
              Text(
                'Email',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              TextFormField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  hintText: 'tu@email.com',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.email),
                ),
                validator: (value) {
                  if (value?.isEmpty ?? true) return 'Ingresa tu email';
                  if (!RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                      .hasMatch(value!)) {
                    return 'Email inválido';
                  }
                  return null;
                },
                enabled: !guardando,
              ),
              SizedBox(height: 16),
              
              // Campo Teléfono
              Text(
                'Teléfono (Opcional)',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              TextFormField(
                controller: _telefonoController,
                keyboardType: TextInputType.phone,
                decoration: InputDecoration(
                  hintText: '+57 3001234567',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.phone),
                ),
                validator: (value) {
                  if (value != null && value.isNotEmpty) {
                    if (value.length < 7) {
                      return 'Teléfono muy corto';
                    }
                  }
                  return null;
                },
                enabled: !guardando,
              ),
              SizedBox(height: 24),
              
              // Botones
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: guardando ? null : () => Navigator.pop(context),
                      child: Text('Cancelar'),
                    ),
                  ),
                  SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: guardando ? null : guardarCambios,
                      child: guardando
                          ? SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation(Colors.white),
                              ),
                            )
                          : Text('Guardar Cambios'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## 🖼️ Pantalla de Perfil (Mostrar + Acceso a Edición)

```dart
import 'package:flutter/material.dart';
import '../services/usuario_service.dart';
import 'editar_perfil_screen.dart';

class PerfilScreen extends StatefulWidget {
  @override
  State<PerfilScreen> createState() => _PerfilScreenState();
}

class _PerfilScreenState extends State<PerfilScreen> {
  final usuarioService = UsuarioService();
  
  Map<String, dynamic>? usuario;
  bool cargando = true;
  String? error;
  
  @override
  void initState() {
    super.initState();
    cargarPerfil();
  }
  
  void cargarPerfil() async {
    final resultado = await usuarioService.obtenerPerfil();
    
    if (!mounted) return;
    
    if (resultado['success']) {
      setState(() {
        usuario = resultado['usuario'];
        error = null;
      });
    } else {
      setState(() => error = resultado['error']);
      
      if (resultado['code'] == 'AUTH_EXPIRED') {
        Navigator.of(context).pushReplacementNamed('/login');
      }
    }
    
    setState(() => cargando = false);
  }
  
  void irEditar() async {
    final resultado = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => EditarPerfilScreen(usuarioInicial: usuario!),
      ),
    );
    
    if (resultado != null) {
      setState(() => usuario = resultado);
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
          : error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 64, color: Colors.red),
                      SizedBox(height: 16),
                      Text(error!),
                      SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: cargarPerfil,
                        child: Text('Reintentar'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Avatar
                      Center(
                        child: Column(
                          children: [
                            CircleAvatar(
                              radius: 50,
                              backgroundColor: Colors.blue.shade100,
                              child: Text(
                                usuario!['nombre'][0].toUpperCase(),
                                style: TextStyle(
                                  fontSize: 36,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.blue,
                                ),
                              ),
                            ),
                            SizedBox(height: 16),
                            Text(
                              usuario!['nombre'],
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              'Rol: ${_getRolNombre(usuario!['id_rol'])}',
                              style: TextStyle(color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                      SizedBox(height: 32),
                      
                      // Información
                      _infoCampo('Email', usuario!['email'], Icons.email),
                      SizedBox(height: 16),
                      _infoCampo('Teléfono', usuario!['telefono'] ?? 'No registrado', Icons.phone),
                      SizedBox(height: 16),
                      _infoCampo('Miembro desde', _formatoFecha(usuario!['created_at']), Icons.calendar_today),
                      SizedBox(height: 32),
                      
                      // Botón Editar
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: irEditar,
                          icon: Icon(Icons.edit),
                          label: Text('Editar Perfil'),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
  
  Widget _infoCampo(String label, String valor, IconData icono) {
    return Row(
      children: [
        Icon(icono, color: Colors.blue),
        SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(color: Colors.grey, fontSize: 12),
              ),
              Text(valor, style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ],
    );
  }
  
  String _getRolNombre(int idRol) {
    const roles = {
      1: 'Cliente',
      2: 'Gerente Taller',
      3: 'Técnico',
      4: 'Admin',
    };
    return roles[idRol] ?? 'Desconocido';
  }
  
  String _formatoFecha(String fecha) {
    final dt = DateTime.parse(fecha);
    return '${dt.day}/${dt.month}/${dt.year}';
  }
}
```

---

## 🔄 Integración en Navegación

### En main.dart o router.dart:

```dart
routes: {
  '/perfil': (context) => PerfilScreen(),
  '/editar-perfil': (context) => EditarPerfilScreen(
    usuarioInicial: ModalRoute.of(context)!.settings.arguments as Map<String, dynamic>,
  ),
},
```

---

## ✅ Validaciones

| Campo | Validación |
|-------|-----------|
| **Nombre** | Mín 3 caracteres, máx 50 |
| **Email** | Formato válido, único en BD |
| **Teléfono** | Mín 7 caracteres (opcional) |

---

## 🧪 Prueba Manual (Curl)

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email":"conductor@ejemplo.com","password":"cliente123!"}' \
  | jq -r '.access_token')

# 2. Obtener perfil
curl -X GET http://localhost:8000/usuarios/perfil \
  -H "Authorization: Bearer $TOKEN"

# 3. Actualizar perfil
curl -X PUT http://localhost:8000/usuarios/perfil \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Pérez",
    "email": "juan.nuevo@ejemplo.com",
    "telefono": "+57 3009999999"
  }'
```

---

## 📊 Flujo Completo

```
PerfilScreen
    ↓
  [Ver datos]
    ↓
[Botón "Editar Perfil"]
    ↓
EditarPerfilScreen
    ↓
[Formulario con validaciones]
    ↓
[Guardar → API PUT /usuarios/perfil]
    ↓
✅ Actualizado (regresa a PerfilScreen)
❌ Error (muestra mensaje)
```

---

## 🚀 Estado del Servicio

✅ **Backend:**
- GET /usuarios/perfil → Implementado
- PUT /usuarios/perfil → Implementado
- Validaciones de email único → Implementado
- JWT requerido → Implementado

✅ **Flutter:**
- UsuarioService completo
- PerfilScreen (lectura)
- EditarPerfilScreen (edición)
- Validaciones en cliente
- Manejo de errores

---

**Próximo paso:** Integra estos archivos en tu app Flutter y prueba 🎉
