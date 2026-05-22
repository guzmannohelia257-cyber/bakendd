# 🚗 Guía de Gestión de Vehículos - App Móvil Flutter

## 📋 Descripción

Esta guía documenta cómo implementar en **Flutter** el **CU-05: Gestionar Vehículos** desde tu app móvil.

Los clientes pueden:
- ✅ Registrar nuevos vehículos
- ✅ Ver lista de vehículos registrados
- ✅ Ver detalles de cada vehículo
- ✅ Editar información del vehículo
- ✅ Dar de baja un vehículo (baja lógica)

**⚠️ IMPORTANTE:** Sin al menos un vehículo registrado, el cliente **NO podrá reportar una emergencia** (CU-06). La tabla `incidente` requiere `id_vehiculo` como llave foránea.

---

## 🔐 Autenticación

Todos los endpoints requieren **JWT Token** en el header:

```dart
headers: {
  'Authorization': 'Bearer <token_del_cliente>',
  'Content-Type': 'application/json'
}
```

Obtén el token tras hacer login:
```dart
POST http://10.0.2.2:8000/usuarios/login
{
  "email": "conductor@ejemplo.com",
  "password": "cliente123!"
}
```

---

## 🚀 Endpoints

### 1️⃣ Registrar Nuevo Vehículo

**Endpoint:**
```
POST /vehiculos/
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```bash
curl -X POST "http://10.0.2.2:8000/vehiculos/" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "placa": "ABC-1234",
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2022,
    "color": "blanco"
  }'
```

**Response (201 Created):**
```json
{
  "id_vehiculo": 1,
  "id_usuario": 1,
  "placa": "ABC-1234",
  "marca": "Toyota",
  "modelo": "Corolla",
  "anio": 2022,
  "color": "blanco",
  "activo": true,
  "created_at": "2026-04-19T10:30:00"
}
```

**Errores:**
- `409 Conflict`: La placa ya está registrada en tu cuenta
- `401 Unauthorized`: Token inválido o expirado
- `422 Unprocessable Entity`: Validación fallida (placa vacía, año inválido, etc.)

---

### 2️⃣ Listar Mis Vehículos

**Endpoint:**
```
GET /vehiculos/mis-autos
```

**Headers:**
```
Authorization: Bearer <token>
```

**Request:**
```bash
curl -X GET "http://10.0.2.2:8000/vehiculos/mis-autos" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
[
  {
    "id_vehiculo": 1,
    "id_usuario": 1,
    "placa": "ABC-1234",
    "marca": "Toyota",
    "modelo": "Corolla",
    "anio": 2022,
    "color": "blanco",
    "activo": true,
    "created_at": "2026-04-19T10:30:00"
  },
  {
    "id_vehiculo": 2,
    "id_usuario": 1,
    "placa": "XYZ-5678",
    "marca": "Honda",
    "modelo": "Civic",
    "anio": 2023,
    "color": "negro",
    "activo": true,
    "created_at": "2026-04-19T11:15:00"
  }
]
```

---

### 3️⃣ Obtener Detalles de un Vehículo

**Endpoint:**
```
GET /vehiculos/{id_vehiculo}
```

**Request:**
```bash
curl -X GET "http://10.0.2.2:8000/vehiculos/1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "id_vehiculo": 1,
  "id_usuario": 1,
  "placa": "ABC-1234",
  "marca": "Toyota",
  "modelo": "Corolla",
  "anio": 2022,
  "color": "blanco",
  "activo": true,
  "created_at": "2026-04-19T10:30:00"
}
```

**Errores:**
- `404 Not Found`: Vehículo no existe o no pertenece al usuario
- `401 Unauthorized`: Token inválido

---

### 4️⃣ Editar Vehículo

**Endpoint:**
```
PUT /vehiculos/{id_vehiculo}
```

**Request:**
```bash
curl -X PUT "http://10.0.2.2:8000/vehiculos/1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "placa": "XYZ-9999",
    "color": "rojo"
  }'
```

**Response (200 OK):**
```json
{
  "id_vehiculo": 1,
  "id_usuario": 1,
  "placa": "XYZ-9999",
  "marca": "Toyota",
  "modelo": "Corolla",
  "anio": 2022,
  "color": "rojo",
  "activo": true,
  "created_at": "2026-04-19T10:30:00"
}
```

**Errores:**
- `404 Not Found`: Vehículo no encontrado
- `409 Conflict`: La nueva placa ya existe
- `401 Unauthorized`: Token inválido

---

### 5️⃣ Dar de Baja Vehículo (Soft Delete)

**Endpoint:**
```
DELETE /vehiculos/{id_vehiculo}
```

**Request:**
```bash
curl -X DELETE "http://10.0.2.2:8000/vehiculos/1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200 OK):**
```json
{
  "mensaje": "Vehículo eliminado correctamente",
  "detalle": "El vehículo con placa 'ABC-1234' ha sido marcado como inactivo"
}
```

---

## 💻 Implementación en Flutter (Dart)

### 1. Service de Vehículos

Crea `lib/services/vehiculo_service.dart`:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class VehiculoService {
  static const String baseUrl = "http://10.0.2.2:8000";
  
  // ============ OBTENER TOKEN ============
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  // ============ REGISTRAR VEHÍCULO ============
  Future<Map<String, dynamic>> registrarVehiculo({
    required String placa,
    String? marca,
    String? modelo,
    int? anio,
    String? color,
  }) async {
    try {
      final token = await _getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final response = await http.post(
        Uri.parse('$baseUrl/vehiculos/'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode({
          'placa': placa,
          'marca': marca,
          'modelo': modelo,
          'anio': anio,
          'color': color,
        }),
      );
      
      if (response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return {'success': true, 'vehiculo': data};
      } else if (response.statusCode == 409) {
        return {'success': false, 'error': 'Esta placa ya está registrada'};
      }
      
      return {'success': false, 'error': 'Error al registrar vehículo'};
    } catch (e) {
      return {'success': false, 'error': 'Error de conexión: $e'};
    }
  }
  
  // ============ LISTAR MIS VEHÍCULOS ============
  Future<Map<String, dynamic>> listarMisVehiculos() async {
    try {
      final token = await _getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final response = await http.get(
        Uri.parse('$baseUrl/vehiculos/mis-autos'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'vehiculos': data};
      }
      
      return {'success': false, 'error': 'Error al cargar vehículos'};
    } catch (e) {
      return {'success': false, 'error': 'Error de conexión: $e'};
    }
  }
  
  // ============ OBTENER DETALLES VEHÍCULO ============
  Future<Map<String, dynamic>> obtenerVehiculo(int idVehiculo) async {
    try {
      final token = await _getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final response = await http.get(
        Uri.parse('$baseUrl/vehiculos/$idVehiculo'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'vehiculo': data};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Vehículo no encontrado'};
      }
      
      return {'success': false, 'error': 'Error al cargar vehículo'};
    } catch (e) {
      return {'success': false, 'error': 'Error de conexión: $e'};
    }
  }
  
  // ============ EDITAR VEHÍCULO ============
  Future<Map<String, dynamic>> editarVehiculo(
    int idVehiculo, {
    String? placa,
    String? marca,
    String? modelo,
    int? anio,
    String? color,
  }) async {
    try {
      final token = await _getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final body = <String, dynamic>{};
      if (placa != null) body['placa'] = placa;
      if (marca != null) body['marca'] = marca;
      if (modelo != null) body['modelo'] = modelo;
      if (anio != null) body['anio'] = anio;
      if (color != null) body['color'] = color;
      
      final response = await http.put(
        Uri.parse('$baseUrl/vehiculos/$idVehiculo'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode(body),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'vehiculo': data};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Vehículo no encontrado'};
      } else if (response.statusCode == 409) {
        return {'success': false, 'error': 'La placa ya está registrada'};
      }
      
      return {'success': false, 'error': 'Error al editar vehículo'};
    } catch (e) {
      return {'success': false, 'error': 'Error de conexión: $e'};
    }
  }
  
  // ============ ELIMINAR VEHÍCULO (Baja Lógica) ============
  Future<Map<String, dynamic>> eliminarVehiculo(int idVehiculo) async {
    try {
      final token = await _getToken();
      if (token == null) return {'success': false, 'error': 'No autenticado'};
      
      final response = await http.delete(
        Uri.parse('$baseUrl/vehiculos/$idVehiculo'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'mensaje': data['detalle']};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Vehículo no encontrado'};
      }
      
      return {'success': false, 'error': 'Error al eliminar vehículo'};
    } catch (e) {
      return {'success': false, 'error': 'Error de conexión: $e'};
    }
  }
}
```

---

### 2. Pantalla de Registro de Vehículo

Crea `lib/screens/registrar_vehiculo_screen.dart`:

```dart
import 'package:flutter/material.dart';
import '../services/vehiculo_service.dart';

class RegistrarVehiculoScreen extends StatefulWidget {
  @override
  State<RegistrarVehiculoScreen> createState() => _RegistrarVehiculoScreenState();
}

class _RegistrarVehiculoScreenState extends State<RegistrarVehiculoScreen> {
  final vehiculoService = VehiculoService();
  
  late TextEditingController placaController;
  late TextEditingController marcaController;
  late TextEditingController modeloController;
  late TextEditingController anioController;
  late TextEditingController colorController;
  
  bool cargando = false;
  String? error;
  
  @override
  void initState() {
    super.initState();
    placaController = TextEditingController();
    marcaController = TextEditingController();
    modeloController = TextEditingController();
    anioController = TextEditingController();
    colorController = TextEditingController();
  }
  
  void registrarVehiculo() async {
    // Validar placa obligatoria
    if (placaController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('La placa es obligatoria'), backgroundColor: Colors.red),
      );
      return;
    }
    
    setState(() => cargando = true);
    
    final resultado = await vehiculoService.registrarVehiculo(
      placa: placaController.text.toUpperCase(),
      marca: marcaController.text.isEmpty ? null : marcaController.text,
      modelo: modeloController.text.isEmpty ? null : modeloController.text,
      anio: anioController.text.isEmpty ? null : int.tryParse(anioController.text),
      color: colorController.text.isEmpty ? null : colorController.text,
    );
    
    setState(() => cargando = false);
    
    if (resultado['success']) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ Vehículo registrado correctamente'), backgroundColor: Colors.green),
      );
      // Limpiar formulario
      placaController.clear();
      marcaController.clear();
      modeloController.clear();
      anioController.clear();
      colorController.clear();
      setState(() => error = null);
      
      // Volver a pantalla anterior
      Future.delayed(Duration(seconds: 1), () {
        Navigator.pop(context, resultado['vehiculo']);
      });
    } else {
      setState(() => error = resultado['error']);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ ${resultado['error']}'), backgroundColor: Colors.red),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Registrar Vehículo'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
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
            
            // Placa (obligatoria)
            Text('Placa del Vehículo *', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: placaController,
              decoration: InputDecoration(
                hintText: 'Ej: ABC-1234',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.directions_car),
              ),
              textCapitalization: TextCapitalization.characters,
            ),
            SizedBox(height: 20),
            
            // Marca
            Text('Marca', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: marcaController,
              decoration: InputDecoration(
                hintText: 'Ej: Toyota',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.local_offer),
              ),
            ),
            SizedBox(height: 20),
            
            // Modelo
            Text('Modelo', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: modeloController,
              decoration: InputDecoration(
                hintText: 'Ej: Corolla',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.directions_car_filled),
              ),
            ),
            SizedBox(height: 20),
            
            // Año
            Text('Año', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: anioController,
              decoration: InputDecoration(
                hintText: 'Ej: 2022',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.calendar_today),
              ),
              keyboardType: TextInputType.number,
            ),
            SizedBox(height: 20),
            
            // Color
            Text('Color', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: colorController,
              decoration: InputDecoration(
                hintText: 'Ej: Blanco',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.palette),
              ),
            ),
            SizedBox(height: 30),
            
            // Botón Registrar
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: cargando ? null : registrarVehiculo,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  padding: EdgeInsets.symmetric(vertical: 14),
                ),
                child: cargando
                    ? SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(color: Colors.white),
                      )
                    : Text(
                        'Registrar Vehículo',
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
    placaController.dispose();
    marcaController.dispose();
    modeloController.dispose();
    anioController.dispose();
    colorController.dispose();
    super.dispose();
  }
}
```

---

### 3. Pantalla de Listado de Vehículos

Crea `lib/screens/mis_vehiculos_screen.dart`:

```dart
import 'package:flutter/material.dart';
import '../services/vehiculo_service.dart';
import 'registrar_vehiculo_screen.dart';
import 'editar_vehiculo_screen.dart';

class MisVehiculosScreen extends StatefulWidget {
  @override
  State<MisVehiculosScreen> createState() => _MisVehiculosScreenState();
}

class _MisVehiculosScreenState extends State<MisVehiculosScreen> {
  final vehiculoService = VehiculoService();
  
  List<dynamic> vehiculos = [];
  bool cargando = true;
  String? error;
  
  @override
  void initState() {
    super.initState();
    cargarVehiculos();
  }
  
  void cargarVehiculos() async {
    setState(() => cargando = true);
    
    final resultado = await vehiculoService.listarMisVehiculos();
    
    if (resultado['success']) {
      setState(() {
        vehiculos = resultado['vehiculos'] ?? [];
        error = null;
      });
    } else {
      setState(() => error = resultado['error']);
    }
    
    setState(() => cargando = false);
  }
  
  void irRegistrar() async {
    final resultado = await Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => RegistrarVehiculoScreen()),
    );
    
    if (resultado != null) {
      cargarVehiculos(); // Recargar lista
    }
  }
  
  void irEditar(Map<String, dynamic> vehiculo) async {
    final resultado = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => EditarVehiculoScreen(vehiculo: vehiculo),
      ),
    );
    
    if (resultado != null) {
      cargarVehiculos(); // Recargar lista
    }
  }
  
  void eliminarVehiculo(int idVehiculo, String placa) async {
    final confirmar = await showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Eliminar Vehículo'),
        content: Text('¿Deseas dar de baja el vehículo $placa?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: Text('Eliminar')),
        ],
      ),
    );
    
    if (confirmar == true) {
      final resultado = await vehiculoService.eliminarVehiculo(idVehiculo);
      
      if (resultado['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('✅ Vehículo eliminado'), backgroundColor: Colors.green),
        );
        cargarVehiculos();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('❌ ${resultado['error']}'), backgroundColor: Colors.red),
        );
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Mis Vehículos'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: cargarVehiculos,
          )
        ],
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
                      ElevatedButton(onPressed: cargarVehiculos, child: Text('Reintentar')),
                    ],
                  ),
                )
              : vehiculos.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.directions_car_filled, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text('No tienes vehículos registrados'),
                          SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: irRegistrar,
                            child: Text('Registrar Primer Vehículo'),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: EdgeInsets.all(16),
                      itemCount: vehiculos.length,
                      itemBuilder: (context, index) {
                        final vehiculo = vehiculos[index];
                        return Card(
                          margin: EdgeInsets.only(bottom: 12),
                          child: ListTile(
                            leading: Icon(Icons.directions_car, color: Colors.blue),
                            title: Text(vehiculo['placa'], style: TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text('${vehiculo['marca']} ${vehiculo['modelo']} (${vehiculo['anio']})'),
                            trailing: PopupMenuButton(
                              itemBuilder: (context) => [
                                PopupMenuItem(
                                  child: Text('Editar'),
                                  onTap: () => irEditar(vehiculo),
                                ),
                                PopupMenuItem(
                                  child: Text('Eliminar', style: TextStyle(color: Colors.red)),
                                  onTap: () => eliminarVehiculo(vehiculo['id_vehiculo'], vehiculo['placa']),
                                ),
                              ],
                            ),
                            onTap: () => irEditar(vehiculo),
                          ),
                        );
                      },
                    ),
      floatingActionButton: FloatingActionButton(
        onPressed: irRegistrar,
        child: Icon(Icons.add),
        tooltip: 'Registrar Nuevo Vehículo',
      ),
    );
  }
}
```

---

### 4. Pantalla de Editar Vehículo

Crea `lib/screens/editar_vehiculo_screen.dart`:

```dart
import 'package:flutter/material.dart';
import '../services/vehiculo_service.dart';

class EditarVehiculoScreen extends StatefulWidget {
  final Map<String, dynamic> vehiculo;
  
  const EditarVehiculoScreen({required this.vehiculo});
  
  @override
  State<EditarVehiculoScreen> createState() => _EditarVehiculoScreenState();
}

class _EditarVehiculoScreenState extends State<EditarVehiculoScreen> {
  final vehiculoService = VehiculoService();
  
  late TextEditingController placaController;
  late TextEditingController marcaController;
  late TextEditingController modeloController;
  late TextEditingController anioController;
  late TextEditingController colorController;
  
  bool cargando = false;
  String? error;
  
  @override
  void initState() {
    super.initState();
    placaController = TextEditingController(text: widget.vehiculo['placa']);
    marcaController = TextEditingController(text: widget.vehiculo['marca'] ?? '');
    modeloController = TextEditingController(text: widget.vehiculo['modelo'] ?? '');
    anioController = TextEditingController(text: widget.vehiculo['anio']?.toString() ?? '');
    colorController = TextEditingController(text: widget.vehiculo['color'] ?? '');
  }
  
  void guardarCambios() async {
    setState(() => cargando = true);
    
    final resultado = await vehiculoService.editarVehiculo(
      widget.vehiculo['id_vehiculo'],
      placa: placaController.text,
      marca: marcaController.text.isEmpty ? null : marcaController.text,
      modelo: modeloController.text.isEmpty ? null : modeloController.text,
      anio: anioController.text.isEmpty ? null : int.tryParse(anioController.text),
      color: colorController.text.isEmpty ? null : colorController.text,
    );
    
    setState(() => cargando = false);
    
    if (resultado['success']) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ Vehículo actualizado'), backgroundColor: Colors.green),
      );
      Navigator.pop(context, resultado['vehiculo']);
    } else {
      setState(() => error = resultado['error']);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ ${resultado['error']}'), backgroundColor: Colors.red),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Editar Vehículo'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
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
            
            Text('Placa', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: placaController,
              decoration: InputDecoration(border: OutlineInputBorder(), prefixIcon: Icon(Icons.directions_car)),
              textCapitalization: TextCapitalization.characters,
            ),
            SizedBox(height: 20),
            
            Text('Marca', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: marcaController,
              decoration: InputDecoration(border: OutlineInputBorder(), prefixIcon: Icon(Icons.local_offer)),
            ),
            SizedBox(height: 20),
            
            Text('Modelo', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: modeloController,
              decoration: InputDecoration(border: OutlineInputBorder(), prefixIcon: Icon(Icons.directions_car_filled)),
            ),
            SizedBox(height: 20),
            
            Text('Año', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: anioController,
              decoration: InputDecoration(border: OutlineInputBorder(), prefixIcon: Icon(Icons.calendar_today)),
              keyboardType: TextInputType.number,
            ),
            SizedBox(height: 20),
            
            Text('Color', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            TextField(
              controller: colorController,
              decoration: InputDecoration(border: OutlineInputBorder(), prefixIcon: Icon(Icons.palette)),
            ),
            SizedBox(height: 30),
            
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: cargando ? null : guardarCambios,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  padding: EdgeInsets.symmetric(vertical: 14),
                ),
                child: cargando
                    ? SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white))
                    : Text('Guardar Cambios', style: TextStyle(fontSize: 16, color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  @override
  void dispose() {
    placaController.dispose();
    marcaController.dispose();
    modeloController.dispose();
    anioController.dispose();
    colorController.dispose();
    super.dispose();
  }
}
```

---

## 🧪 Pruebas desde Flutter

### 1. Registrar un vehículo
```dart
import 'services/vehiculo_service.dart';

final resultado = await VehiculoService().registrarVehiculo(
  placa: 'ABC-1234',
  marca: 'Toyota',
  modelo: 'Corolla',
  anio: 2022,
  color: 'blanco',
);

if (resultado['success']) {
  print('✅ Vehículo: ${resultado['vehiculo']}');
} else {
  print('❌ Error: ${resultado['error']}');
}
```

### 2. Listar vehículos
```dart
final resultado = await VehiculoService().listarMisVehiculos();

if (resultado['success']) {
  final vehiculos = resultado['vehiculos'];
  for (var v in vehiculos) {
    print('🚗 ${v['placa']} - ${v['marca']} ${v['modelo']}');
  }
}
```

### 3. Editar vehículo
```dart
final resultado = await VehiculoService().editarVehiculo(
  1,  // id_vehiculo
  color: 'rojo',
);

if (resultado['success']) {
  print('✅ Vehículo actualizado');
}
```

### 4. Eliminar vehículo
```dart
final resultado = await VehiculoService().eliminarVehiculo(1);

if (resultado['success']) {
  print('✅ ${resultado['mensaje']}');
}
```

---

## 📝 Validaciones en Flutter

### Placa
- ✅ Obligatoria
- ✅ Máximo 20 caracteres
- ✅ Convertir a mayúsculas

### Año
- ✅ Número válido (1900-2100)
- ✅ Opcional

### Color
- ✅ Máximo 30 caracteres
- ✅ Opcional

---

## 🔒 Seguridad

✅ **Token JWT obligatorio** en todos los endpoints  
✅ **Backend valida** que el vehículo pertenezca al usuario  
✅ **Placa única** por usuario  
✅ **Baja lógica** → No se pierden datos  

---

## 📋 Flujo Completo

```
1️⃣ Cliente inicia sesión
   → Obtiene JWT token
   ↓
2️⃣ Cliente navega a "Mis Vehículos"
   GET /vehiculos/mis-autos (con token)
   ↓
3️⃣ Cliente presiona "Registrar Vehículo"
   → Pantalla de registro
   ↓
4️⃣ Cliente ingresa placa, marca, modelo, año, color
   → POST /vehiculos/ (con token)
   ↓
5️⃣ Backend valida y guarda en BD
   ← Response: {id_vehiculo, ...}
   ↓
6️⃣ App actualiza lista de vehículos
   → Cliente ve su vehículo en la lista
   ↓
7️⃣ Cliente puede reportar emergencias con este vehículo
   → CU-06: Reportar Incidencia
```

---

## 🚀 Próximo Paso: CU-06 Reportar Incidencia

Con los vehículos registrados, el cliente ahora puede reportar emergencias.

Consulta: **REPORTAR_INCIDENCIA_FLUTTER.md** (próximamente)

---

**¡Guía Completa para Gestionar Vehículos desde Flutter!** 🚗✅
