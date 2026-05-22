# 🚨 Guía: Reportar Incidencia (CU-06)

## 📌 Overview

El cliente (rol=1) puede reportar una incidencia (emergencia/problema) vinculada a uno de sus vehículos. La incidencia incluye:
- Vehículo afectado
- Categoría del problema
- Descripción del incidente
- Ubicación GPS
- Prioridad
- Fotos/Audio (CU-07)

---

## 🔗 Endpoints del Backend

### 1. Obtener Categorías (GET /incidencias/categorias)

**Requiere:** JWT token (cualquier usuario)

```bash
curl -X GET http://localhost:8000/incidencias/categorias \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**
```json
[
  {
    "id_categoria": 1,
    "nombre": "Falla Mecánica",
    "descripcion": "Problemas con el motor, transmisión, etc.",
    "icono_url": "icon-mechanics.png"
  },
  {
    "id_categoria": 2,
    "nombre": "Falla Eléctrica",
    "descripcion": "Problemas con batería, alternador, etc.",
    "icono_url": "icon-electrical.png"
  },
  {
    "id_categoria": 3,
    "nombre": "Accidente",
    "descripcion": "Choque, colisión, impacto",
    "icono_url": "icon-accident.png"
  },
  {
    "id_categoria": 4,
    "nombre": "Descompostura",
    "descripcion": "El vehículo no arranca",
    "icono_url": "icon-breakdown.png"
  }
]
```

### 2. Obtener Prioridades (GET /incidencias/prioridades)

**Requiere:** JWT token (cualquier usuario)

```bash
curl -X GET http://localhost:8000/incidencias/prioridades \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**
```json
[
  {
    "id_prioridad": 1,
    "nivel": "baja",
    "tiempo_respuesta_minutos": 120
  },
  {
    "id_prioridad": 2,
    "nivel": "media",
    "tiempo_respuesta_minutos": 60
  },
  {
    "id_prioridad": 3,
    "nivel": "alta",
    "tiempo_respuesta_minutos": 30
  },
  {
    "id_prioridad": 4,
    "nivel": "critica",
    "tiempo_respuesta_minutos": 15
  }
]
```

### 3. Crear Incidencia (POST /incidencias)

**Requiere:** JWT token + JSON body

```bash
curl -X POST http://localhost:8000/incidencias \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id_vehiculo": 1,
    "id_categoria": 1,
    "id_prioridad": 3,
    "descripcion": "El motor hace ruido extraño y humo blanco",
    "latitud": 4.7110,
    "longitud": -74.0721,
    "observaciones": "Estoy en la avenida principal cerca de la estación"
  }'
```

**Response (201 Created):**
```json
{
  "id_incidente": 1,
  "id_usuario": 1,
  "id_vehiculo": 1,
  "id_categoria": 1,
  "id_prioridad": 3,
  "id_estado": 1,
  "descripcion": "El motor hace ruido extraño y humo blanco",
  "observaciones": "Estoy en la avenida principal cerca de la estación",
  "latitud": 4.7110,
  "longitud": -74.0721,
  "created_at": "2026-04-19T03:15:22",
  "estado": {
    "id_estado": 1,
    "nombre": "pendiente"
  }
}
```

### 4. Listar Mis Incidencias (GET /incidencias/mis-incidencias)

**Requiere:** JWT token

```bash
curl -X GET http://localhost:8000/incidencias/mis-incidencias \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**
```json
[
  {
    "id_incidente": 1,
    "id_usuario": 1,
    "id_vehiculo": 1,
    "id_categoria": 1,
    "id_prioridad": 3,
    "id_estado": 1,
    "descripcion": "El motor hace ruido extraño y humo blanco",
    "observaciones": "Estoy en la avenida principal cerca de la estación",
    "latitud": 4.7110,
    "longitud": -74.0721,
    "created_at": "2026-04-19T03:15:22",
    "estado": {
      "id_estado": 1,
      "nombre": "pendiente"
    },
    "categoria": {
      "id_categoria": 1,
      "nombre": "Falla Mecánica"
    },
    "vehiculo": {
      "id_vehiculo": 1,
      "placa": "TEST001",
      "marca": "Toyota"
    }
  }
]
```

### 5. Obtener Detalles de Incidencia (GET /incidencias/{id})

```bash
curl -X GET http://localhost:8000/incidencias/1 \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):** (misma estructura que arriba)

---

## 🎯 Modelos de Datos

### CategoriaProblema
```dart
class CategoriaProblema {
  final int idCategoria;
  final String nombre;
  final String? descripcion;
  final String? iconoUrl;

  CategoriaProblema({
    required this.idCategoria,
    required this.nombre,
    this.descripcion,
    this.iconoUrl,
  });

  factory CategoriaProblema.fromJson(Map<String, dynamic> json) {
    return CategoriaProblema(
      idCategoria: json['id_categoria'],
      nombre: json['nombre'],
      descripcion: json['descripcion'],
      iconoUrl: json['icono_url'],
    );
  }
}
```

### Prioridad
```dart
class Prioridad {
  final int idPrioridad;
  final String nivel;
  final int? tiempoRespuestaMinutos;

  Prioridad({
    required this.idPrioridad,
    required this.nivel,
    this.tiempoRespuestaMinutos,
  });

  factory Prioridad.fromJson(Map<String, dynamic> json) {
    return Prioridad(
      idPrioridad: json['id_prioridad'],
      nivel: json['nivel'],
      tiempoRespuestaMinutos: json['tiempo_respuesta_minutos'],
    );
  }
}
```

### IncidenteResponse
```dart
class IncidenteResponse {
  final int idIncidente;
  final int idUsuario;
  final int idVehiculo;
  final int idCategoria;
  final int idPrioridad;
  final int idEstado;
  final String descripcion;
  final String? observaciones;
  final double latitud;
  final double longitud;
  final DateTime createdAt;
  final Map<String, dynamic>? estado;
  final Map<String, dynamic>? categoria;
  final Map<String, dynamic>? vehiculo;

  IncidenteResponse({
    required this.idIncidente,
    required this.idUsuario,
    required this.idVehiculo,
    required this.idCategoria,
    required this.idPrioridad,
    required this.idEstado,
    required this.descripcion,
    this.observaciones,
    required this.latitud,
    required this.longitud,
    required this.createdAt,
    this.estado,
    this.categoria,
    this.vehiculo,
  });

  factory IncidenteResponse.fromJson(Map<String, dynamic> json) {
    return IncidenteResponse(
      idIncidente: json['id_incidente'],
      idUsuario: json['id_usuario'],
      idVehiculo: json['id_vehiculo'],
      idCategoria: json['id_categoria'],
      idPrioridad: json['id_prioridad'],
      idEstado: json['id_estado'],
      descripcion: json['descripcion'],
      observaciones: json['observaciones'],
      latitud: (json['latitud'] as num).toDouble(),
      longitud: (json['longitud'] as num).toDouble(),
      createdAt: DateTime.parse(json['created_at']),
      estado: json['estado'],
      categoria: json['categoria'],
      vehiculo: json['vehiculo'],
    );
  }
}
```

### IncidenteCreate
```dart
class IncidenteCreate {
  final int idVehiculo;
  final int idCategoria;
  final int idPrioridad;
  final String descripcion;
  final double latitud;
  final double longitud;
  final String? observaciones;

  IncidenteCreate({
    required this.idVehiculo,
    required this.idCategoria,
    required this.idPrioridad,
    required this.descripcion,
    required this.latitud,
    required this.longitud,
    this.observaciones,
  });

  Map<String, dynamic> toJson() => {
    'id_vehiculo': idVehiculo,
    'id_categoria': idCategoria,
    'id_prioridad': idPrioridad,
    'descripcion': descripcion,
    'latitud': latitud,
    'longitud': longitud,
    'observaciones': observaciones,
  };
}
```

---

## 🛠️ Servicio (lib/services/incidente_service.dart)

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:async';

class IncidenteService {
  static const String baseUrl = "http://10.0.2.2:8000";
  
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  // Obtener categorías
  Future<Map<String, dynamic>> obtenerCategorias() async {
    try {
      print('[INCIDENTE] Obteniendo categorías...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final response = await http.get(
        Uri.parse('$baseUrl/incidencias/categorias'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      ).timeout(Duration(seconds: 15));
      
      print('[INCIDENTE] Status categorías: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final List<dynamic> categorias = jsonDecode(response.body);
        print('[INCIDENTE] Categorías cargadas: ${categorias.length}');
        return {'success': true, 'categorias': categorias};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      }
      
      return {'success': false, 'error': 'Error al obtener categorías'};
    } catch (e) {
      print('[INCIDENTE] Exception categorías: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // Obtener prioridades
  Future<Map<String, dynamic>> obtenerPrioridades() async {
    try {
      print('[INCIDENTE] Obteniendo prioridades...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final response = await http.get(
        Uri.parse('$baseUrl/incidencias/prioridades'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      ).timeout(Duration(seconds: 15));
      
      print('[INCIDENTE] Status prioridades: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final List<dynamic> prioridades = jsonDecode(response.body);
        print('[INCIDENTE] Prioridades cargadas: ${prioridades.length}');
        return {'success': true, 'prioridades': prioridades};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      }
      
      return {'success': false, 'error': 'Error al obtener prioridades'};
    } catch (e) {
      print('[INCIDENTE] Exception prioridades: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // Crear incidencia
  Future<Map<String, dynamic>> crearIncidencia({
    required int idVehiculo,
    required int idCategoria,
    required int idPrioridad,
    required String descripcion,
    required double latitud,
    required double longitud,
    String? observaciones,
  }) async {
    try {
      print('[INCIDENTE] Creando incidencia...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final body = {
        'id_vehiculo': idVehiculo,
        'id_categoria': idCategoria,
        'id_prioridad': idPrioridad,
        'descripcion': descripcion,
        'latitud': latitud,
        'longitud': longitud,
        'observaciones': observaciones,
      };
      
      print('[INCIDENTE] Body: $body');
      
      final response = await http.post(
        Uri.parse('$baseUrl/incidencias'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
        body: jsonEncode(body),
      ).timeout(Duration(seconds: 15));
      
      print('[INCIDENTE] Status create: ${response.statusCode}');
      print('[INCIDENTE] Response: ${response.body}');
      
      if (response.statusCode == 201) {
        final incidente = jsonDecode(response.body);
        print('[INCIDENTE] ✅ Incidencia creada: ${incidente['id_incidente']}');
        return {'success': true, 'incidente': incidente};
      } else if (response.statusCode == 400) {
        final error = jsonDecode(response.body);
        return {'success': false, 'error': error['detail'] ?? 'Datos inválidos'};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Vehículo no encontrado'};
      }
      
      return {'success': false, 'error': 'Error al crear incidencia'};
    } catch (e) {
      print('[INCIDENTE] Exception create: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // Listar mis incidencias
  Future<Map<String, dynamic>> listarMisIncidencias() async {
    try {
      print('[INCIDENTE] Listando mis incidencias...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final response = await http.get(
        Uri.parse('$baseUrl/incidencias/mis-incidencias'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      ).timeout(Duration(seconds: 15));
      
      print('[INCIDENTE] Status list: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final List<dynamic> incidencias = jsonDecode(response.body);
        print('[INCIDENTE] Incidencias cargadas: ${incidencias.length}');
        return {'success': true, 'incidencias': incidencias};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      }
      
      return {'success': false, 'error': 'Error al listar incidencias'};
    } catch (e) {
      print('[INCIDENTE] Exception list: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
  
  // Obtener detalle de incidencia
  Future<Map<String, dynamic>> obtenerIncidencia(int id) async {
    try {
      print('[INCIDENTE] Obteniendo incidencia $id...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final response = await http.get(
        Uri.parse('$baseUrl/incidencias/$id'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json'
        },
      ).timeout(Duration(seconds: 15));
      
      print('[INCIDENTE] Status detail: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final incidente = jsonDecode(response.body);
        print('[INCIDENTE] Incidencia cargada');
        return {'success': true, 'incidente': incidente};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Incidencia no encontrada'};
      }
      
      return {'success': false, 'error': 'Error al obtener incidencia'};
    } catch (e) {
      print('[INCIDENTE] Exception detail: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
}
```

---

## 📱 Pantalla de Reporte (ReportarIncidenteScreen)

```dart
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../services/incidente_service.dart';

class ReportarIncidenteScreen extends StatefulWidget {
  @override
  State<ReportarIncidenteScreen> createState() => _ReportarIncidenteScreenState();
}

class _ReportarIncidenteScreenState extends State<ReportarIncidenteScreen> {
  final incidenteService = IncidenteService();
  final _formKey = GlobalKey<FormState>();
  
  // Datos
  List<dynamic> categorias = [];
  List<dynamic> prioridades = [];
  List<dynamic> vehiculos = [];
  
  // Controladores
  late TextEditingController _descripcionController;
  late TextEditingController _observacionesController;
  
  // Selecciones
  int? vehiculoSeleccionado;
  int? categoriaSeleccionada;
  int? prioridadSeleccionada;
  double? latitud;
  double? longitud;
  
  bool cargandoDatos = true;
  bool creando = false;
  String? errorGeneral;
  String? ubicacionTexto;
  
  @override
  void initState() {
    super.initState();
    _descripcionController = TextEditingController();
    _observacionesController = TextEditingController();
    cargarDatos();
  }
  
  void cargarDatos() async {
    // Cargar categorías
    final catResult = await incidenteService.obtenerCategorias();
    
    // Cargar prioridades
    final priResult = await incidenteService.obtenerPrioridades();
    
    if (!mounted) return;
    
    if (catResult['success'] && priResult['success']) {
      setState(() {
        categorias = catResult['categorias'];
        prioridades = priResult['prioridades'];
      });
    } else {
      setState(() {
        errorGeneral = 'Error al cargar datos. Intenta nuevamente.';
      });
    }
    
    setState(() => cargandoDatos = false);
  }
  
  void obtenerUbicacion() async {
    try {
      setState(() => ubicacionTexto = '📍 Obteniendo ubicación...');
      
      final position = await Geolocator.getCurrentPosition(
        locationSettings: LocationSettings(accuracy: LocationAccuracy.high),
      );
      
      setState(() {
        latitud = position.latitude;
        longitud = position.longitude;
        ubicacionTexto = '✅ Ubicación: ${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)}';
      });
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Ubicación obtenida'),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 2),
        ),
      );
    } catch (e) {
      setState(() => ubicacionTexto = '❌ Error: ${e.toString()}');
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Error al obtener ubicación: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
  
  void reportarIncidencia() async {
    if (!_formKey.currentState!.validate()) return;
    
    if (vehiculoSeleccionado == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Selecciona un vehículo'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    if (categoriaSeleccionada == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Selecciona una categoría'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    if (prioridadSeleccionada == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Selecciona una prioridad'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    if (latitud == null || longitud == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Obtén la ubicación actual'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    
    setState(() {
      creando = true;
      errorGeneral = null;
    });
    
    final resultado = await incidenteService.crearIncidencia(
      idVehiculo: vehiculoSeleccionado!,
      idCategoria: categoriaSeleccionada!,
      idPrioridad: prioridadSeleccionada!,
      descripcion: _descripcionController.text.trim(),
      latitud: latitud!,
      longitud: longitud!,
      observaciones: _observacionesController.text.trim().isEmpty
          ? null
          : _observacionesController.text.trim(),
    );
    
    if (!mounted) return;
    
    if (resultado['success']) {
      final incidente = resultado['incidente'];
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Incidencia reportada: #${incidente['id_incidente']}'),
          backgroundColor: Colors.green,
          duration: Duration(seconds: 2),
        ),
      );
      
      Future.delayed(Duration(seconds: 2), () {
        Navigator.pop(context, resultado['incidente']);
      });
    } else {
      setState(() {
        errorGeneral = resultado['error'];
        
        if (resultado['code'] == 'AUTH_EXPIRED') {
          Future.delayed(Duration(seconds: 2), () {
            Navigator.of(context).pushReplacementNamed('/login');
          });
        }
      });
    }
    
    setState(() => creando = false);
  }
  
  @override
  void dispose() {
    _descripcionController.dispose();
    _observacionesController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    if (cargandoDatos) {
      return Scaffold(
        appBar: AppBar(title: Text('Reportar Incidencia')),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    
    return Scaffold(
      appBar: AppBar(
        title: Text('Reportar Incidencia'),
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
              
              // Seleccionar Vehículo
              Text('Vehículo Afectado', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              DropdownButtonFormField<int>(
                value: vehiculoSeleccionado,
                decoration: InputDecoration(
                  hintText: 'Selecciona un vehículo',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.directions_car),
                ),
                items: vehiculos.isEmpty
                    ? [
                        DropdownMenuItem(
                          value: 0,
                          child: Text('No tienes vehículos registrados'),
                        )
                      ]
                    : vehiculos.map<DropdownMenuItem<int>>((v) {
                        return DropdownMenuItem<int>(
                          value: v['id_vehiculo'],
                          child: Text('${v['marca']} ${v['modelo']} (${v['placa']})'),
                        );
                      }).toList(),
                onChanged: vehiculos.isEmpty ? null : (value) {
                  setState(() => vehiculoSeleccionado = value);
                },
              ),
              SizedBox(height: 16),
              
              // Categoría
              Text('Categoría del Problema', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              DropdownButtonFormField<int>(
                value: categoriaSeleccionada,
                decoration: InputDecoration(
                  hintText: 'Selecciona una categoría',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.category),
                ),
                items: categorias.map<DropdownMenuItem<int>>((c) {
                  return DropdownMenuItem<int>(
                    value: c['id_categoria'],
                    child: Text(c['nombre']),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() => categoriaSeleccionada = value);
                },
              ),
              SizedBox(height: 8),
              if (categoriaSeleccionada != null)
                Text(
                  categorias
                      .firstWhere((c) => c['id_categoria'] == categoriaSeleccionada)['descripcion'] ??
                      '',
                  style: TextStyle(fontSize: 12, color: Colors.grey, fontStyle: FontStyle.italic),
                ),
              SizedBox(height: 16),
              
              // Prioridad
              Text('Prioridad', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              DropdownButtonFormField<int>(
                value: prioridadSeleccionada,
                decoration: InputDecoration(
                  hintText: 'Selecciona la prioridad',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.warning),
                ),
                items: prioridades.map<DropdownMenuItem<int>>((p) {
                  return DropdownMenuItem<int>(
                    value: p['id_prioridad'],
                    child: Text(
                      '${p['nivel'].toUpperCase()} (${p['tiempo_respuesta_minutos'] ?? '?'} min)',
                    ),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() => prioridadSeleccionada = value);
                },
              ),
              SizedBox(height: 16),
              
              // Descripción
              Text('Descripción del Problema', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              TextFormField(
                controller: _descripcionController,
                maxLines: 4,
                decoration: InputDecoration(
                  hintText: 'Describe detalladamente lo que está sucediendo...',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.description),
                ),
                validator: (value) {
                  if (value?.isEmpty ?? true) return 'Ingresa una descripción';
                  if (value!.length < 10) return 'Mínimo 10 caracteres';
                  return null;
                },
              ),
              SizedBox(height: 16),
              
              // Observaciones
              Text('Observaciones (Opcional)', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              TextFormField(
                controller: _observacionesController,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: 'Información adicional que pueda ser útil...',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.notes),
                ),
              ),
              SizedBox(height: 16),
              
              // Ubicación
              Text('Ubicación GPS', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: latitud != null ? Colors.green.shade50 : Colors.grey.shade50,
                  border: Border.all(
                    color: latitud != null ? Colors.green : Colors.grey,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (ubicacionTexto != null)
                      Text(ubicacionTexto!, style: TextStyle(fontSize: 12)),
                    SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: creando ? null : obtenerUbicacion,
                        icon: Icon(Icons.location_on),
                        label: Text('Obtener Ubicación Actual'),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: 24),
              
              // Botón Reportar
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton.icon(
                  onPressed: creando ? null : reportarIncidencia,
                  icon: Icon(Icons.report_problem),
                  label: creando
                      ? SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation(Colors.white),
                          ),
                        )
                      : Text('Reportar Incidencia'),
                ),
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

## 🖼️ Pantalla de Historial (HistorialIncidenciasScreen)

```dart
import 'package:flutter/material.dart';
import '../services/incidente_service.dart';

class HistorialIncidenciasScreen extends StatefulWidget {
  @override
  State<HistorialIncidenciasScreen> createState() => _HistorialIncidenciasScreenState();
}

class _HistorialIncidenciasScreenState extends State<HistorialIncidenciasScreen> {
  final incidenteService = IncidenteService();
  
  List<dynamic> incidencias = [];
  bool cargando = true;
  String? error;
  
  @override
  void initState() {
    super.initState();
    cargarIncidencias();
  }
  
  void cargarIncidencias() async {
    final resultado = await incidenteService.listarMisIncidencias();
    
    if (!mounted) return;
    
    if (resultado['success']) {
      setState(() {
        incidencias = resultado['incidencias'];
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
  
  Color _getColorPrioridad(int idPrioridad) {
    switch (idPrioridad) {
      case 1:
        return Colors.blue; // baja
      case 2:
        return Colors.yellow; // media
      case 3:
        return Colors.orange; // alta
      case 4:
        return Colors.red; // critica
      default:
        return Colors.grey;
    }
  }
  
  String _getNivelPrioridad(int idPrioridad) {
    const map = {1: 'BAJA', 2: 'MEDIA', 3: 'ALTA', 4: 'CRÍTICA'};
    return map[idPrioridad] ?? 'DESCONOCIDA';
  }
  
  String _getEstado(int idEstado) {
    const map = {
      1: '⏳ Pendiente',
      2: '⚙️ En Proceso',
      3: '✅ Atendido',
      4: '❌ Cancelado',
    };
    return map[idEstado] ?? 'Desconocido';
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Mis Incidencias'),
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
                        onPressed: cargarIncidencias,
                        child: Text('Reintentar'),
                      ),
                    ],
                  ),
                )
              : incidencias.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.inbox, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text('No tienes incidencias reportadas'),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: EdgeInsets.all(8),
                      itemCount: incidencias.length,
                      itemBuilder: (context, index) {
                        final inc = incidencias[index];
                        return Card(
                          margin: EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: _getColorPrioridad(inc['id_prioridad']),
                              child: Icon(Icons.report_problem, color: Colors.white),
                            ),
                            title: Text(
                              '#${inc['id_incidente']} - ${inc['vehiculo']?['marca'] ?? 'Vehículo'} ${inc['vehiculo']?['placa'] ?? ''}',
                              style: TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(height: 4),
                                Text(
                                  inc['categoria']?['nombre'] ?? 'Categoría desconocida',
                                  style: TextStyle(fontSize: 12),
                                ),
                                Text(
                                  '${_getNivelPrioridad(inc['id_prioridad'])} • ${_getEstado(inc['id_estado'])}',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: Colors.grey,
                                  ),
                                ),
                              ],
                            ),
                            trailing: Icon(Icons.chevron_right),
                            onTap: () {
                              // Navegar a detalles
                              Navigator.pushNamed(
                                context,
                                '/incidente-detalle',
                                arguments: inc['id_incidente'],
                              );
                            },
                          ),
                        );
                      },
                    ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          final resultado = await Navigator.pushNamed(
            context,
            '/reportar-incidente',
          );
          
          if (resultado != null) {
            cargarIncidencias();
          }
        },
        child: Icon(Icons.report_problem),
        tooltip: 'Nueva Incidencia',
      ),
    );
  }
}
```

---

## 🔄 Integración en Navegación

```dart
routes: {
  '/reportar-incidente': (context) => ReportarIncidenteScreen(),
  '/historial-incidencias': (context) => HistorialIncidenciasScreen(),
  '/incidente-detalle': (context) => DetalleIncidenteScreen(
    idIncidente: ModalRoute.of(context)!.settings.arguments as int,
  ),
},
```

---

## ✅ Dependencias Requeridas (pubspec.yaml)

```yaml
geolocator: ^9.0.0  # Para GPS
location_permissions: ^4.0.0  # Para permisos
```

---

## 🧪 Prueba Manual (Curl)

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email":"conductor@ejemplo.com","password":"cliente123!"}' \
  | jq -r '.access_token')

# 2. Obtener categorías
curl -X GET http://localhost:8000/incidencias/categorias \
  -H "Authorization: Bearer $TOKEN"

# 3. Obtener prioridades
curl -X GET http://localhost:8000/incidencias/prioridades \
  -H "Authorization: Bearer $TOKEN"

# 4. Crear incidencia
curl -X POST http://localhost:8000/incidencias \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_vehiculo": 1,
    "id_categoria": 1,
    "id_prioridad": 3,
    "descripcion": "El motor hace ruido extraño y humo blanco",
    "latitud": 4.7110,
    "longitud": -74.0721,
    "observaciones": "En la avenida principal"
  }'

# 5. Listar mis incidencias
curl -X GET http://localhost:8000/incidencias/mis-incidencias \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Validaciones

| Campo | Validación |
|-------|-----------|
| **Vehículo** | Requerido, debe existir |
| **Categoría** | Requerida |
| **Prioridad** | Requerida |
| **Descripción** | Mín 10 caracteres |
| **Latitud/Longitud** | Números decimales, entre -90 y 90 |

---

## 📋 Checklist

- ✅ Estados de incidencia insertados en BD
- ✅ Endpoints implementados en FastAPI
- ✅ Modelos Dart creados
- ✅ IncidenteService completoReportarIncidenteScreen implementadoHistorialIncidenciasScreen implementado
- ✅ Integración de GPS con geolocator
- ✅ Validaciones en cliente y servidor
- ✅ Manejo de errores y tokens expirados

---

**Próximo paso:** Integra estos archivos en tu app Flutter, agrega permisos de GPS (AndroidManifest.xml, Info.plist) y ¡prueba reportar una incidencia! 🚀

Después podemos pasar a **CU-07: Adjuntar Fotos/Audio** o **CU-08: Gestión de Talleres** 📸🎤
