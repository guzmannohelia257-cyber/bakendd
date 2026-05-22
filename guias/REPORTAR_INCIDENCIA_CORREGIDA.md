# 🚨 Guía: Reportar Incidencia (CU-06) - VERSIÓN CORREGIDA

## 📌 Overview

El cliente (rol=1) reporta una emergencia vehicular enviando:
- Vehículo afectado
- Descripción del problema
- Ubicación GPS

**IMPORTANTE:** La categoría y prioridad NO las envía el cliente. La IA las asigna automáticamente después basándose en la descripción y ubicación.

---

## 🔗 Endpoints del Backend

### 1. Obtener Categorías (GET /incidencias/categorias)

Catálogos disponibles (informativo para la UI).

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
  }
]
```

### 2. Obtener Prioridades (GET /incidencias/prioridades)

Niveles de prioridad (informativo para la UI).

```bash
curl -X GET http://localhost:8000/incidencias/prioridades \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**
```json
[
  {"id_prioridad": 1, "nivel": "baja", "orden": 1},
  {"id_prioridad": 2, "nivel": "media", "orden": 2},
  {"id_prioridad": 3, "nivel": "alta", "orden": 3},
  {"id_prioridad": 4, "nivel": "critica", "orden": 4}
]
```

### 3. Crear Incidencia (POST /incidencias) ⭐ ENDPOINT PRINCIPAL

**Requiere:** JWT token + JSON body mínimo

```bash
curl -X POST http://localhost:8000/incidencias \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id_vehiculo": 1,
    "descripcion_usuario": "El motor hace ruido extraño y humo blanco",
    "latitud": 4.7110,
    "longitud": -74.0721
  }'
```

**Response (201 Created):**
```json
{
  "id_incidente": 1,
  "id_usuario": 1,
  "id_vehiculo": 1,
  "id_categoria": null,
  "id_prioridad": null,
  "id_estado": 1,
  "descripcion_usuario": "El motor hace ruido extraño y humo blanco",
  "latitud": 4.7110,
  "longitud": -74.0721,
  "created_at": "2026-04-19T03:15:22"
}
```

**Nota importante:** Los campos `id_categoria` e `id_prioridad` son `null` porque:
- Se asignan automáticamente por el sistema de IA
- El cliente NO debe enviarlos (aunque intente, serán ignorados)
- Después de algunos segundos, tendrán valores cuando la IA procese el incidente

### 4. Listar Mis Incidencias (GET /incidencias/mis-incidencias)

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
    "descripcion_usuario": "El motor hace ruido extraño",
    "latitud": 4.7110,
    "longitud": -74.0721,
    "created_at": "2026-04-19T03:15:22",
    "updated_at": "2026-04-19T03:16:45",
    "vehiculo": {
      "id_vehiculo": 1,
      "placa": "TEST001",
      "marca": "Toyota"
    },
    "estado": {
      "id_estado": 1,
      "nombre": "pendiente"
    },
    "categoria": {
      "id_categoria": 1,
      "nombre": "Falla Mecánica"
    },
    "prioridad": {
      "id_prioridad": 3,
      "nivel": "alta",
      "orden": 3
    }
  }
]
```

### 5. Obtener Detalle de Incidencia (GET /incidencias/{id})

```bash
curl -X GET http://localhost:8000/incidencias/1 \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):** (misma estructura que en listado)

---

## 🎯 Modelos de Datos

### IncidenteCreate (Lo que envía Flutter)

```dart
class IncidenteCreate {
  final int idVehiculo;
  final String descripcionUsuario;
  final double latitud;
  final double longitud;

  IncidenteCreate({
    required this.idVehiculo,
    required this.descripcionUsuario,
    required this.latitud,
    required this.longitud,
  });

  Map<String, dynamic> toJson() => {
    'id_vehiculo': idVehiculo,
    'descripcion_usuario': descripcionUsuario,
    'latitud': latitud,
    'longitud': longitud,
  };
}
```

### IncidenteResponse (Lo que retorna el servidor)

```dart
class IncidenteResponse {
  final int idIncidente;
  final int idUsuario;
  final int idVehiculo;
  final int? idCategoria;      // null hasta que IA procese
  final int? idPrioridad;      // null hasta que IA procese
  final int idEstado;
  final String? descripcionUsuario;
  final double latitud;
  final double longitud;
  final DateTime createdAt;

  IncidenteResponse({
    required this.idIncidente,
    required this.idUsuario,
    required this.idVehiculo,
    this.idCategoria,
    this.idPrioridad,
    required this.idEstado,
    this.descripcionUsuario,
    required this.latitud,
    required this.longitud,
    required this.createdAt,
  });

  factory IncidenteResponse.fromJson(Map<String, dynamic> json) {
    return IncidenteResponse(
      idIncidente: json['id_incidente'],
      idUsuario: json['id_usuario'],
      idVehiculo: json['id_vehiculo'],
      idCategoria: json['id_categoria'],
      idPrioridad: json['id_prioridad'],
      idEstado: json['id_estado'],
      descripcionUsuario: json['descripcion_usuario'],
      latitud: (json['latitud'] as num).toDouble(),
      longitud: (json['longitud'] as num).toDouble(),
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
```

### Prioridad (Estructura correcta del catálogo)

```dart
class Prioridad {
  final int idPrioridad;
  final String nivel;      // "baja", "media", "alta", "critica"
  final int orden;         // 1, 2, 3, 4

  Prioridad({
    required this.idPrioridad,
    required this.nivel,
    required this.orden,
  });

  factory Prioridad.fromJson(Map<String, dynamic> json) {
    return Prioridad(
      idPrioridad: json['id_prioridad'],
      nivel: json['nivel'],
      orden: json['orden'],
    );
  }
}
```

---

## 🛠️ Servicio (lib/services/incidente_service.dart)

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class IncidenteService {
  static const String baseUrl = "http://10.0.2.2:8000";
  
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }
  
  // Crear incidencia (LO PRINCIPAL)
  Future<Map<String, dynamic>> crearIncidencia({
    required int idVehiculo,
    required String descripcionUsuario,
    required double latitud,
    required double longitud,
  }) async {
    try {
      print('[INCIDENTE] Creando incidencia...');
      
      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }
      
      final body = {
        'id_vehiculo': idVehiculo,
        'descripcion_usuario': descripcionUsuario,
        'latitud': latitud,
        'longitud': longitud,
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
      
      print('[INCIDENTE] Status: ${response.statusCode}');
      
      if (response.statusCode == 201) {
        final incidente = jsonDecode(response.body);
        print('[INCIDENTE] ✅ Incidencia creada: ${incidente['id_incidente']}');
        print('[INCIDENTE] Categoría asignará IA: ${incidente['id_categoria']}');
        print('[INCIDENTE] Prioridad asignará IA: ${incidente['id_prioridad']}');
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
      print('[INCIDENTE] Exception: $e');
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
      
      print('[INCIDENTE] Status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final List<dynamic> incidencias = jsonDecode(response.body);
        print('[INCIDENTE] Incidencias cargadas: ${incidencias.length}');
        return {'success': true, 'incidencias': incidencias};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Token expirado', 'code': 'AUTH_EXPIRED'};
      }
      
      return {'success': false, 'error': 'Error al listar incidencias'};
    } catch (e) {
      print('[INCIDENTE] Exception: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }
}
```

---

## 📱 Pantalla de Reporte Simplificada

```dart
class ReportarIncidenteScreen extends StatefulWidget {
  @override
  State<ReportarIncidenteScreen> createState() => _ReportarIncidenteScreenState();
}

class _ReportarIncidenteScreenState extends State<ReportarIncidenteScreen> {
  final incidenteService = IncidenteService();
  final _formKey = GlobalKey<FormState>();
  
  late TextEditingController _descripcionController;
  int? vehiculoSeleccionado;
  double? latitud;
  double? longitud;
  
  bool creando = false;
  String? errorGeneral;
  String? ubicacionTexto;
  
  @override
  void initState() {
    super.initState();
    _descripcionController = TextEditingController();
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
        ubicacionTexto = '✅ ${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)}';
      });
    } catch (e) {
      setState(() => ubicacionTexto = '❌ Error: $e');
    }
  }
  
  void reportarIncidencia() async {
    if (!_formKey.currentState!.validate()) return;
    
    if (vehiculoSeleccionado == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Selecciona un vehículo'), backgroundColor: Colors.red),
      );
      return;
    }
    
    if (latitud == null || longitud == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Obtén la ubicación actual'), backgroundColor: Colors.red),
      );
      return;
    }
    
    setState(() => creando = true);
    
    final resultado = await incidenteService.crearIncidencia(
      idVehiculo: vehiculoSeleccionado!,
      descripcionUsuario: _descripcionController.text.trim(),
      latitud: latitud!,
      longitud: longitud!,
    );
    
    if (!mounted) return;
    
    if (resultado['success']) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Incidencia #${resultado['incidente']['id_incidente']} reportada'),
          backgroundColor: Colors.green,
        ),
      );
      Future.delayed(Duration(seconds: 2), () => Navigator.pop(context, resultado['incidente']));
    } else {
      setState(() => errorGeneral = resultado['error']);
    }
    
    setState(() => creando = false);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Reportar Emergencia'), centerTitle: true),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (errorGeneral != null) ...[
                Container(
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    border: Border.all(color: Colors.red),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(errorGeneral!, style: TextStyle(color: Colors.red)),
                ),
                SizedBox(height: 16),
              ],
              
              // Seleccionar Vehículo
              Text('Vehículo Afectado', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              DropdownButtonFormField<int>(
                value: vehiculoSeleccionado,
                decoration: InputDecoration(hintText: 'Selecciona tu vehículo', border: OutlineInputBorder()),
                items: [
                  DropdownMenuItem(value: 1, child: Text('Toyota TEST001')),
                ],
                onChanged: (v) => setState(() => vehiculoSeleccionado = v),
              ),
              SizedBox(height: 16),
              
              // Descripción
              Text('¿Qué pasó?', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              TextFormField(
                controller: _descripcionController,
                maxLines: 4,
                decoration: InputDecoration(
                  hintText: 'Describe lo que sucede...',
                  border: OutlineInputBorder(),
                ),
                validator: (v) {
                  if (v?.isEmpty ?? true) return 'Ingresa una descripción';
                  if (v!.length < 10) return 'Mínimo 10 caracteres';
                  return null;
                },
              ),
              SizedBox(height: 16),
              
              // Ubicación
              Text('Mi Ubicación GPS', style: TextStyle(fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              Container(
                padding: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  border: Border.all(color: Colors.grey),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (ubicacionTexto != null) Text(ubicacionTexto!, style: TextStyle(fontSize: 12)),
                    SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: creando ? null : obtenerUbicacion,
                        icon: Icon(Icons.location_on),
                        label: Text('Obtener Mi Ubicación'),
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
                  icon: Icon(Icons.emergency),
                  label: creando
                      ? SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, valueColor: AlwaysStoppedAnimation(Colors.white)),
                        )
                      : Text('¡AUXILIO! REPORTAR AHORA'),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
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

## 🧪 Prueba Manual (Curl)

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email":"conductor@ejemplo.com","password":"cliente123!"}' \
  | jq -r '.access_token')

# 2. Crear incidencia (SIN categoría ni prioridad)
curl -X POST http://localhost:8000/incidencias \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_vehiculo": 1,
    "descripcion_usuario": "El motor hace ruido extraño y humo blanco",
    "latitud": 4.7110,
    "longitud": -74.0721
  }'

# 3. Listar mis incidencias (categoría y prioridad ya asignadas por IA)
curl -X GET http://localhost:8000/incidencias/mis-incidencias \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📊 Cambios vs Guía Original

| Aspecto | Original | Corregido |
|--------|----------|-----------|
| **Campos al crear** | id_categoria, id_prioridad requeridos | NO requeridos (IA asigna) |
| **Campo descripción** | `descripcion` + `observaciones` | Solo `descripcion_usuario` |
| **Prioridad.orden** | `tiempo_respuesta_minutos` | `orden: int` (1-4) |
| **Implementación** | Validaba categoría y prioridad | Ya no valida (IA asigna) |

---

## ✅ Estado del Desarrollo

- ✅ Modelo Incidente (correcto)
- ✅ Schemas Pydantic (corregidos)
- ✅ Router con validaciones correctas
- ✅ Estados de incidente verificados en BD
- ✅ Endpoints funcionando
- ✅ Seguridad: Solo acceso a propios incidentes

**Listo para probar en Flutter! 🚀**
