# 📱 IMPLEMENTACIÓN: Reportar Emergencia en Flutter (CU-06)

## 🎯 Objetivo

El usuario presiona un botón de emergencia en su app móvil. La app envía:
- ID de su vehículo
- Descripción del problema
- Coordenadas GPS

El backend responde confirmando que la emergencia fue reportada (categoría y prioridad se asignan automáticamente por IA después).

---

## 📋 Requisitos Previos

### 1. Dependencias en `pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.0
  geolocator: ^9.0.2
  permission_handler: ^11.4.3
  intl: ^0.19.0
```

**Instalar:**
```bash
flutter pub get
```

---

## 🔐 Permisos en Android

### Archivo: `android/app/src/main/AndroidManifest.xml`

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- Permisos para GPS -->
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.INTERNET" />
    
    <application>
        <!-- ... resto de configuración ... -->
    </application>
</manifest>
```

### Archivo: `android/app/build.gradle`

```gradle
android {
    compileSdkVersion 34
    
    defaultConfig {
        targetSdkVersion 34
        minSdkVersion 21  // Geolocator necesita mínimo 21
    }
}
```

---

## 🔐 Permisos en iOS

### Archivo: `ios/Runner/Info.plist`

```xml
<dict>
    <!-- ... otras claves ... -->
    
    <!-- Permisos de ubicación -->
    <key>NSLocationWhenInUseUsageDescription</key>
    <string>La app necesita tu ubicación para reportar emergencias vehiculares</string>
    
    <key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
    <string>La app necesita tu ubicación para reportar emergencias vehiculares</string>
    
    <!-- ... resto de configuración ... -->
</dict>
```

---

## 🛠️ Modelos Dart

### Archivo: `lib/models/incidente.dart`

```dart
import 'package:intl/intl.dart';

/// Respuesta del servidor al crear incidencia
class IncidenteResponse {
  final int idIncidente;
  final int idUsuario;
  final int idVehiculo;
  final int? idCategoria;      // null = IA asignará después
  final int? idPrioridad;      // null = IA asignará después
  final int idEstado;          // 1=pendiente, 2=en_proceso, 3=atendido, 4=cancelado
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
      idIncidente: json['id_incidente'] ?? 0,
      idUsuario: json['id_usuario'] ?? 0,
      idVehiculo: json['id_vehiculo'] ?? 0,
      idCategoria: json['id_categoria'],
      idPrioridad: json['id_prioridad'],
      idEstado: json['id_estado'] ?? 1,
      descripcionUsuario: json['descripcion_usuario'],
      latitud: (json['latitud'] as num).toDouble(),
      longitud: (json['longitud'] as num).toDouble(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  /// Retorna estado legible
  String getEstadoNombre() {
    const estados = {
      1: '⏳ Pendiente',
      2: '⚙️ En Proceso',
      3: '✅ Atendido',
      4: '❌ Cancelado',
    };
    return estados[idEstado] ?? 'Desconocido';
  }

  /// Retorna ubicación formateada
  String getUbicacion() => '${latitud.toStringAsFixed(4)}, ${longitud.toStringAsFixed(4)}';

  /// Retorna hora de creación formateada
  String getFechaFormato() {
    return DateFormat('dd/MM/yyyy HH:mm').format(createdAt);
  }
}

/// Incidencia con datos completos (desde listado)
class IncidenteDetalle {
  final int idIncidente;
  final int idUsuario;
  final int idVehiculo;
  final int idEstado;
  final String? descripcionUsuario;
  final double latitud;
  final double longitud;
  final DateTime createdAt;
  final DateTime updatedAt;
  final Map<String, dynamic>? vehiculo;
  final Map<String, dynamic>? estado;
  final Map<String, dynamic>? categoria;
  final Map<String, dynamic>? prioridad;

  IncidenteDetalle({
    required this.idIncidente,
    required this.idUsuario,
    required this.idVehiculo,
    required this.idEstado,
    this.descripcionUsuario,
    required this.latitud,
    required this.longitud,
    required this.createdAt,
    required this.updatedAt,
    this.vehiculo,
    this.estado,
    this.categoria,
    this.prioridad,
  });

  factory IncidenteDetalle.fromJson(Map<String, dynamic> json) {
    return IncidenteDetalle(
      idIncidente: json['id_incidente'] ?? 0,
      idUsuario: json['id_usuario'] ?? 0,
      idVehiculo: json['id_vehiculo'] ?? 0,
      idEstado: json['estado']?['id_estado'] ?? 1,
      descripcionUsuario: json['descripcion_usuario'],
      latitud: (json['latitud'] as num).toDouble(),
      longitud: (json['longitud'] as num).toDouble(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      vehiculo: json['vehiculo'],
      estado: json['estado'],
      categoria: json['categoria'],
      prioridad: json['prioridad'],
    );
  }

  String getEstadoNombre() {
    const estados = {
      1: '⏳ Pendiente',
      2: '⚙️ En Proceso',
      3: '✅ Atendido',
      4: '❌ Cancelado',
    };
    return estados[idEstado] ?? 'Desconocido';
  }

  String getPlaca() => vehiculo?['placa'] ?? 'N/A';
  String getMarca() => vehiculo?['marca'] ?? 'N/A';
  String getCategoriaNombre() => categoria?['nombre'] ?? '🤖 Por asignar';
  String getNivelPrioridad() {
    final nivel = prioridad?['nivel']?.toString().toUpperCase() ?? 'N/A';
    if (nivel == 'CRITICA') return '🔴 CRÍTICA';
    if (nivel == 'ALTA') return '🟠 ALTA';
    if (nivel == 'MEDIA') return '🟡 MEDIA';
    if (nivel == 'BAJA') return '🟢 BAJA';
    return '🤖 $nivel';
  }
}
```

---

## 📡 Servicio (API)

### Archivo: `lib/services/incidente_service.dart`

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:geolocator/geolocator.dart';
import '../models/incidente.dart';

class IncidenteService {
  static const String baseUrl = "http://10.0.2.2:8000";

  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  /// 🚨 CREAR EMERGENCIA (Principal)
  /// 
  /// Envía: vehículo + descripción + ubicación
  /// Recibe: ID de incidencia confirmado + estado pendiente
  Future<Map<String, dynamic>> crearIncidencia({
    required int idVehiculo,
    required String descripcionUsuario,
    required double latitud,
    required double longitud,
  }) async {
    try {
      print('[INCIDENTE] 🚨 Reportando emergencia...');
      print('[INCIDENTE] Vehículo: $idVehiculo');
      print('[INCIDENTE] Descripción: $descripcionUsuario');
      print('[INCIDENTE] GPS: $latitud, $longitud');

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

      final response = await http
          .post(
            Uri.parse('$baseUrl/incidencias/'),
            headers: {
              'Authorization': 'Bearer $token',
              'Content-Type': 'application/json'
            },
            body: jsonEncode(body),
          )
          .timeout(Duration(seconds: 20), onTimeout: () {
        throw TimeoutException('Conexión expirada');
      });

      print('[INCIDENTE] Status: ${response.statusCode}');
      print('[INCIDENTE] Response: ${response.body}');

      if (response.statusCode == 201) {
        final incidente = IncidenteResponse.fromJson(jsonDecode(response.body));
        print('[INCIDENTE] ✅ Emergencia reportada: #${incidente.idIncidente}');
        print('[INCIDENTE] Categoría (IA asignará): ${incidente.idCategoria}');
        print('[INCIDENTE] Prioridad (IA asignará): ${incidente.idPrioridad}');
        print('[INCIDENTE] Estado: ${incidente.getEstadoNombre()}');
        
        return {
          'success': true,
          'incidente': incidente,
          'message': '✅ Emergencia reportada. Técnicos en camino...'
        };
      } else if (response.statusCode == 400) {
        final error = jsonDecode(response.body);
        return {'success': false, 'error': error['detail'] ?? 'Datos inválidos'};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Sesión expirada', 'code': 'AUTH_EXPIRED'};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Vehículo no encontrado'};
      } else if (response.statusCode == 500) {
        return {'success': false, 'error': 'Error en el servidor'};
      }

      return {'success': false, 'error': 'Error ${response.statusCode}: ${response.body}'};
    } on TimeoutException catch (_) {
      print('[INCIDENTE] ❌ Timeout');
      return {'success': false, 'error': 'Tiempo de conexión agotado (20s)'};
    } catch (e) {
      print('[INCIDENTE] ❌ Exception: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }

  /// 📋 LISTAR MIS EMERGENCIAS
  /// 
  /// Retorna todas las incidencias del usuario (con categoría y prioridad ya asignadas)
  Future<Map<String, dynamic>> listarMisIncidencias() async {
    try {
      print('[INCIDENTE] 📋 Cargando historial...');

      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }

      final response = await http
          .get(
            Uri.parse('$baseUrl/incidencias/mis-incidencias'),
            headers: {'Authorization': 'Bearer $token'},
          )
          .timeout(Duration(seconds: 15), onTimeout: () {
        throw TimeoutException('Conexión expirada');
      });

      print('[INCIDENTE] Status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        final incidencias = data
            .map((json) => IncidenteDetalle.fromJson(json))
            .toList();

        print('[INCIDENTE] ✅ ${incidencias.length} incidencias cargadas');
        return {'success': true, 'incidencias': incidencias};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Sesión expirada', 'code': 'AUTH_EXPIRED'};
      }

      return {'success': false, 'error': 'Error al cargar incidencias'};
    } on TimeoutException catch (_) {
      print('[INCIDENTE] ❌ Timeout');
      return {'success': false, 'error': 'Tiempo de conexión agotado'};
    } catch (e) {
      print('[INCIDENTE] ❌ Exception: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }

  /// 📌 OBTENER DETALLE DE UNA INCIDENCIA
  Future<Map<String, dynamic>> obtenerIncidencia(int idIncidente) async {
    try {
      print('[INCIDENTE] 📌 Cargando detalle #$idIncidente...');

      final token = await _getToken();
      if (token == null) {
        return {'success': false, 'error': 'No autenticado'};
      }

      final response = await http
          .get(
            Uri.parse('$baseUrl/incidencias/$idIncidente'),
            headers: {'Authorization': 'Bearer $token'},
          )
          .timeout(Duration(seconds: 15), onTimeout: () {
        throw TimeoutException('Conexión expirada');
      });

      print('[INCIDENTE] Status: ${response.statusCode}');

      if (response.statusCode == 200) {
        final incidente = IncidenteDetalle.fromJson(jsonDecode(response.body));
        print('[INCIDENTE] ✅ Detalle cargado');
        return {'success': true, 'incidente': incidente};
      } else if (response.statusCode == 401) {
        return {'success': false, 'error': 'Sesión expirada', 'code': 'AUTH_EXPIRED'};
      } else if (response.statusCode == 404) {
        return {'success': false, 'error': 'Incidencia no encontrada'};
      }

      return {'success': false, 'error': 'Error al cargar incidencia'};
    } on TimeoutException catch (_) {
      print('[INCIDENTE] ❌ Timeout');
      return {'success': false, 'error': 'Tiempo de conexión agotado'};
    } catch (e) {
      print('[INCIDENTE] ❌ Exception: $e');
      return {'success': false, 'error': 'Error: $e'};
    }
  }

  /// 📍 OBTENER UBICACIÓN ACTUAL
  Future<Map<String, double>?> obtenerUbicacionActual() async {
    try {
      print('[GPS] 📍 Solicitando ubicación...');

      // Verificar permisos
      final permiso = await _verificarPermisoGPS();
      if (!permiso) {
        print('[GPS] ❌ Permiso denegado');
        return null;
      }

      final posicion = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      print('[GPS] ✅ ${posicion.latitude}, ${posicion.longitude}');
      return {
        'latitud': posicion.latitude,
        'longitud': posicion.longitude,
      };
    } catch (e) {
      print('[GPS] ❌ Exception: $e');
      return null;
    }
  }

  /// 🔐 Verificar permisos GPS
  Future<bool> _verificarPermisoGPS() async {
    try {
      // Verificar si está habilitado
      final habilitado = await Geolocator.isLocationServiceEnabled();
      if (!habilitado) {
        print('[GPS] ❌ Servicios de ubicación deshabilitados');
        return false;
      }

      // Verificar permiso
      var permiso = await Geolocator.checkPermission();
      if (permiso == LocationPermission.denied) {
        permiso = await Geolocator.requestPermission();
        if (permiso == LocationPermission.denied) {
          print('[GPS] ❌ Permiso denegado');
          return false;
        }
      }

      if (permiso == LocationPermission.deniedForever) {
        print('[GPS] ❌ Permiso permanentemente denegado');
        return false;
      }

      print('[GPS] ✅ Permiso otorgado');
      return true;
    } catch (e) {
      print('[GPS] ❌ Error: $e');
      return false;
    }
  }
}
```

---

## 📱 Pantalla Principal de Emergencia

### Archivo: `lib/screens/reportar_emergencia_screen.dart`

```dart
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import '../services/incidente_service.dart';
import '../models/incidente.dart';

class ReportarEmergenciaScreen extends StatefulWidget {
  final List<Map<String, dynamic>> vehiculos;

  const ReportarEmergenciaScreen({required this.vehiculos});

  @override
  State<ReportarEmergenciaScreen> createState() => _ReportarEmergenciaScreenState();
}

class _ReportarEmergenciaScreenState extends State<ReportarEmergenciaScreen> {
  final incidenteService = IncidenteService();
  final _formKey = GlobalKey<FormState>();

  // Controladores
  late TextEditingController _descripcionController;

  // Estado
  int? vehiculoSeleccionado;
  double? latitud;
  double? longitud;
  bool obteniendo = false;
  bool reportando = false;
  String? ubicacionTexto;
  String? errorGeneral;

  @override
  void initState() {
    super.initState();
    _descripcionController = TextEditingController();
  }

  @override
  void dispose() {
    _descripcionController.dispose();
    super.dispose();
  }

  /// Obtener GPS actual
  void _obtenerUbicacion() async {
    setState(() => obteniendo = true);

    final resultado = await incidenteService.obtenerUbicacionActual();

    if (mounted) {
      if (resultado != null) {
        setState(() {
          latitud = resultado['latitud'];
          longitud = resultado['longitud'];
          ubicacionTexto =
              '✅ ${resultado['latitud']?.toStringAsFixed(4)}, ${resultado['longitud']?.toStringAsFixed(4)}';
          errorGeneral = null;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ Ubicación obtenida'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      } else {
        setState(() {
          ubicacionTexto = '❌ No se pudo obtener ubicación';
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Verifica que GPS esté habilitado'),
            backgroundColor: Colors.red,
          ),
        );
      }

      setState(() => obteniendo = false);
    }
  }

  /// Reportar emergencia
  void _reportarEmergencia() async {
    if (!_formKey.currentState!.validate()) return;

    if (vehiculoSeleccionado == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('⚠️ Selecciona un vehículo'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    if (latitud == null || longitud == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('⚠️ Obtén tu ubicación'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() {
      reportando = true;
      errorGeneral = null;
    });

    final resultado = await incidenteService.crearIncidencia(
      idVehiculo: vehiculoSeleccionado!,
      descripcionUsuario: _descripcionController.text.trim(),
      latitud: latitud!,
      longitud: longitud!,
    );

    if (!mounted) return;

    if (resultado['success']) {
      final incidente = resultado['incidente'] as IncidenteResponse;

      // Mostrar confirmación
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          backgroundColor: Colors.green.shade50,
          title: Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green, size: 28),
              SizedBox(width: 12),
              Expanded(child: Text('¡Emergencia Reportada!'))
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('✅ Incidencia #${incidente.idIncidente}'),
              SizedBox(height: 8),
              Text('Técnicos en camino...'),
              SizedBox(height: 8),
              Text(
                'Estado: ${incidente.getEstadoNombre()}',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                'Ubicación:\n${incidente.getUbicacion()}',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                Navigator.pop(context, incidente);
              },
              child: Text('Cerrar'),
            ),
          ],
        ),
      );
    } else {
      if (resultado['code'] == 'AUTH_EXPIRED') {
        Navigator.of(context).pushReplacementNamed('/login');
      } else {
        setState(() => errorGeneral = resultado['error']);
      }
    }

    setState(() => reportando = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('🚨 Reportar Emergencia'),
        centerTitle: true,
        backgroundColor: Colors.red,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Mensaje de alerta
              Container(
                padding: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  border: Border.all(color: Colors.red),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning, color: Colors.red),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Este es un reporte de emergencia. Técnicos serán asignados automáticamente.',
                        style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: 16),

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

              // Seleccionar vehículo
              Text(
                '🚗 Mi Vehículo',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(height: 8),
              DropdownButtonFormField<int>(
                value: vehiculoSeleccionado,
                decoration: InputDecoration(
                  hintText: 'Selecciona el vehículo afectado',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.directions_car),
                ),
                items: widget.vehiculos.isEmpty
                    ? [
                        DropdownMenuItem(
                          enabled: false,
                          child: Text('No tienes vehículos registrados'),
                        )
                      ]
                    : widget.vehiculos
                        .map<DropdownMenuItem<int>>((v) {
                          return DropdownMenuItem<int>(
                            value: v['id_vehiculo'],
                            child: Text(
                              '${v['marca']} ${v['modelo']} (${v['placa']})',
                            ),
                          );
                        })
                        .toList(),
                onChanged: widget.vehiculos.isEmpty ? null : (v) {
                  setState(() => vehiculoSeleccionado = v);
                },
                validator: (v) {
                  if (v == null) return 'Selecciona un vehículo';
                  return null;
                },
              ),
              SizedBox(height: 20),

              // Descripción del problema
              Text(
                '❓ ¿Qué pasó?',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(height: 8),
              TextFormField(
                controller: _descripcionController,
                maxLines: 5,
                decoration: InputDecoration(
                  hintText: 'Describe el problema con tu vehículo\n'
                      'Ej: Motor hace ruido, no arranca, llanta pinchada, etc.',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.description),
                ),
                validator: (v) {
                  if (v?.isEmpty ?? true) return 'Ingresa una descripción';
                  if (v!.length < 10) return 'Mínimo 10 caracteres';
                  return null;
                },
              ),
              SizedBox(height: 20),

              // Ubicación GPS
              Text(
                '📍 Mi Ubicación GPS',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              SizedBox(height: 8),
              Container(
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
                      Padding(
                        padding: EdgeInsets.only(bottom: 12),
                        child: Text(
                          ubicacionTexto!,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: latitud != null ? Colors.green : Colors.red,
                          ),
                        ),
                      ),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: obteniendo || reportando ? null : _obtenerUbicacion,
                        icon: obteniendo
                            ? SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Icon(Icons.location_on),
                        label: Text(
                          obteniendo ? 'Obteniendo...' : 'Obtener Mi Ubicación',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: 24),

              // Botón Reportar (PRINCIPAL)
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton.icon(
                  onPressed: reportando ? null : _reportarEmergencia,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    disabledBackgroundColor: Colors.red.shade300,
                  ),
                  icon: reportando
                      ? SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation(Colors.white),
                          ),
                        )
                      : Icon(Icons.emergency, size: 28),
                  label: Text(
                    reportando ? '⏳ Reportando...' : '🚨 ¡AUXILIO! REPORTAR AHORA',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
              SizedBox(height: 12),

              // Botón cancelar
              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton.icon(
                  onPressed: reportando ? null : () => Navigator.pop(context),
                  icon: Icon(Icons.close),
                  label: Text('Cancelar'),
                ),
              ),
              SizedBox(height: 20),

              // Ayuda
              Container(
                padding: EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '💡 Consejos:',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text('• Describe el problema de forma clara'),
                    Text('• Asegúrate que tu GPS esté activado'),
                    Text('• Un técnico será asignado automáticamente'),
                    Text('• Puedes ver el estado en tu historial'),
                  ],
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

## 📋 Pantalla de Historial

### Archivo: `lib/screens/historial_emergencias_screen.dart`

```dart
import 'package:flutter/material.dart';
import '../services/incidente_service.dart';
import '../models/incidente.dart';

class HistorialEmergenciasScreen extends StatefulWidget {
  @override
  State<HistorialEmergenciasScreen> createState() => _HistorialEmergenciasScreenState();
}

class _HistorialEmergenciasScreenState extends State<HistorialEmergenciasScreen> {
  final incidenteService = IncidenteService();

  List<IncidenteDetalle> incidencias = [];
  bool cargando = true;
  String? error;

  @override
  void initState() {
    super.initState();
    _cargarIncidencias();
  }

  void _cargarIncidencias() async {
    final resultado = await incidenteService.listarMisIncidencias();

    if (!mounted) return;

    if (resultado['success']) {
      setState(() {
        incidencias = resultado['incidencias'] ?? [];
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

  /// Color según estado
  Color _getColorEstado(int idEstado) {
    switch (idEstado) {
      case 1:
        return Colors.orange; // Pendiente
      case 2:
        return Colors.blue; // En proceso
      case 3:
        return Colors.green; // Atendido
      case 4:
        return Colors.red; // Cancelado
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('📋 Mis Emergencias'),
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
                        onPressed: () {
                          setState(() {
                            cargando = true;
                            error = null;
                          });
                          _cargarIncidencias();
                        },
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
                          Icon(Icons.inbox_outlined, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text('No tienes emergencias reportadas'),
                          SizedBox(height: 24),
                          ElevatedButton.icon(
                            onPressed: () => Navigator.pushNamed(
                              context,
                              '/reportar-emergencia',
                            ),
                            icon: Icon(Icons.emergency),
                            label: Text('Reportar Emergencia'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                            ),
                          ),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: () async {
                        setState(() => cargando = true);
                        _cargarIncidencias();
                      },
                      child: ListView.builder(
                        padding: EdgeInsets.all(8),
                        itemCount: incidencias.length,
                        itemBuilder: (context, index) {
                          final inc = incidencias[index];
                          return Card(
                            margin: EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: _getColorEstado(inc.idEstado),
                                child: Icon(Icons.emergency, color: Colors.white),
                              ),
                              title: Text(
                                '#${inc.idIncidente} - ${inc.getMarca()} ${inc.getPlaca()}',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SizedBox(height: 4),
                                  Text(
                                    inc.getCategoriaNombre(),
                                    style: TextStyle(fontSize: 12),
                                  ),
                                  Text(
                                    '${inc.getEstadoNombre()} • ${inc.getNivelPrioridad()}',
                                    style: TextStyle(fontSize: 11, color: Colors.grey),
                                  ),
                                  Text(
                                    inc.getFechaFormato(),
                                    style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                                  ),
                                ],
                              ),
                              trailing: Icon(Icons.chevron_right),
                              onTap: () {
                                // Navegar a detalles si es necesario
                                showDetailDialog(context, inc);
                              },
                            ),
                          );
                        },
                      ),
                    ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final resultado = await Navigator.pushNamed(
            context,
            '/reportar-emergencia',
          );
          if (resultado != null) {
            _cargarIncidencias();
          }
        },
        label: Text('Nueva Emergencia'),
        icon: Icon(Icons.emergency),
        backgroundColor: Colors.red,
      ),
    );
  }

  void showDetailDialog(BuildContext context, IncidenteDetalle inc) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('#${inc.idIncidente} - Detalles'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _detailRow('Estado:', inc.getEstadoNombre()),
              _detailRow('Vehículo:', '${inc.getMarca()} ${inc.getPlaca()}'),
              _detailRow('Categoría:', inc.getCategoriaNombre()),
              _detailRow('Prioridad:', inc.getNivelPrioridad()),
              _detailRow('Ubicación:', inc.getUbicacion()),
              _detailRow('Fecha:', inc.getFechaFormato()),
              if (inc.descripcionUsuario != null) ...[
                SizedBox(height: 12),
                Text('Descripción:', style: TextStyle(fontWeight: FontWeight.bold)),
                SizedBox(height: 4),
                Text(inc.descripcionUsuario!),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontWeight: FontWeight.bold), softWrap: true),
          SizedBox(width: 12),
          Expanded(child: Text(value, softWrap: true)),
        ],
      ),
    );
  }
}
```

---

## 🗂️ Integración en App

### Archivo: `lib/main.dart` (Fragment)

```dart
MaterialApp(
  title: 'Emergencias Vehiculares',
  routes: {
    '/reportar-emergencia': (context) {
      // Obtener vehículos desde Provider, Riverpod, GetX, o BLoC
      final vehiculos = <Map<String, dynamic>>[
        // Ejemplo: {'id_vehiculo': 1, 'marca': 'Toyota', 'modelo': 'Corolla', 'placa': 'ABC-123'}
      ];
      return ReportarEmergenciaScreen(vehiculos: vehiculos);
    },
    '/historial-emergencias': (context) => HistorialEmergenciasScreen(),
  },
)
```

### Desde otra pantalla (recomendado):

```dart
// ✅ OPCIÓN 1: Pasar vehículos desde una pantalla
FloatingActionButton(
  onPressed: () {
    final vehiculos = [
      {'id_vehiculo': 1, 'marca': 'Toyota', 'modelo': 'Corolla', 'placa': 'ABC-123'},
      {'id_vehiculo': 2, 'marca': 'Honda', 'modelo': 'Civic', 'placa': 'XYZ-789'},
    ];
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ReportarEmergenciaScreen(vehiculos: vehiculos),
      ),
    );
  },
  child: Icon(Icons.emergency),
  backgroundColor: Colors.red,
)

// ✅ OPCIÓN 2: Usando rutas nombradas (requiere Provider/BLoC)
FloatingActionButton(
  onPressed: () => Navigator.pushNamed(context, '/reportar-emergencia'),
  child: Icon(Icons.emergency),
  backgroundColor: Colors.red,
)

// ✅ OPCIÓN 3: Ver historial
ListTile(
  title: Text('Mis Emergencias'),
  onTap: () => Navigator.pushNamed(context, '/historial-emergencias'),
)
```

---

## ✅ Checklist de Implementación

- [ ] Agregar dependencias a `pubspec.yaml`: `http`, `geolocator`, `shared_preferences`, `intl`
- [ ] Ejecutar `flutter pub get`
- [ ] Configurar permisos en `android/app/src/main/AndroidManifest.xml`
- [ ] Configurar permisos en `ios/Runner/Info.plist`
- [ ] Crear archivo `lib/models/incidente.dart` con clases IncidenteResponse y IncidenteDetalle
- [ ] Crear archivo `lib/services/incidente_service.dart` (✅ Verificar importaciones: `dart:async` y `geolocator`)
- [ ] Crear archivo `lib/screens/reportar_emergencia_screen.dart`
- [ ] Crear archivo `lib/screens/historial_emergencias_screen.dart`
- [ ] Importar pantallas en `lib/main.dart`
- [ ] Registrar rutas con navegación correcta
- [ ] ✅ Verificar que backend esté corriendo en `http://10.0.2.2:8000` (emulador) o `http://localhost:8000` (dispositivo)
- [ ] Probar en emulador/dispositivo real
- [ ] Verificar logs con `flutter logs | grep "INCIDENTE"`

---

## 🧪 Pruebas

### Test Completo (Paso a Paso)

```bash
# 1. Verificar backend corriendo
netstat -ano | findstr ":8000"
# Output: TCP 127.0.0.1:8000 LISTENING ✅

# 2. Correr la app
flutter run

# 3. Interacciones en la app:
#    - Ir a "Reportar Emergencia"
#    - Seleccionar vehículo (si existe)
#    - Ingresar descripción: "Motor hace ruido"
#    - Presionar "Obtener Ubicación"
#    - Esperar GPS (debe mostrar coordenadas)
#    - Presionar "REPORTAR AHORA"
#    - Debe aparecer diálogo: "¡Emergencia Reportada! Incidencia #X"

# 4. Ver logs
flutter logs

# Logs esperados:
# [INCIDENTE] 🚨 Reportando emergencia...
# [INCIDENTE] Vehículo: 1
# [INCIDENTE] Status: 201
# [INCIDENTE] ✅ Emergencia reportada: #1
```

### Test de Historial

```bash
# Después de reportar emergencia:
# 1. Navegar a "Mis Emergencias"
# 2. Debe aparecer el reporte creado
# 3. Presionar para ver detalles
# 4. Verificar que categoría y prioridad están asignadas (IA)
```

### Logs para Debug

```bash
flutter logs | grep "INCIDENTE"
flutter logs | grep "GPS"
flutter logs | grep "Exception"
```

---

## 🚨 Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `❌ No se pudo obtener ubicación` | GPS deshabilitado en emulador/dispositivo | Activa GPS: Settings > Location > ON |
| `❌ Sesión expirada` | Token JWT vencido | Haz login nuevamente |
| `❌ Vehículo no encontrado` | No tienes vehículos registrados | Crea un vehículo en CU-05 primero |
| `Timeout - 20s` | Servidor no responde | Verifica: `netstat -ano \| findstr ":8000"` |
| `Permiso denegado` | No aceptaste permisos | Abre Settings > Permissions > Location: Allow |
| `Geolocator' isn't defined` | Importación faltante | Verifica: `import 'package:geolocator/geolocator.dart'` |
| `LocationSettings' isn't defined` | Versión incorrecta de geolocator | Usa: `desiredAccuracy: LocationAccuracy.high` |
| `The getter 'Geolocator' isn't defined` | Falta importación de dart:async | Verifica: `import 'dart:async'` |
| `TypeError: null is not a Map` | Respuesta del servidor incorrecta | Revisa logs del backend en terminal |
| `Error: The type 'TimeoutException' isn't defined` | Falta importación de dart:async | ✅ Ya corregido en servicio |

---

## 📞 Soporte Técnico

### Verificar conectividad con backend

```bash
# Emulador Android
ping 10.0.2.2

# iOS Simulator o dispositivo real
ping localhost

# Verificar puerto
netstat -ano | findstr ":8000"
```

### Prueba directa en Postman

```
POST http://localhost:8000/incidencias/
Authorization: Bearer {token_aqui}
Content-Type: application/json

Body:
{
  "id_vehiculo": 1,
  "descripcion_usuario": "Test",
  "latitud": 4.7110,
  "longitud": -74.0721
}

Response esperado (201):
{
  "id_incidente": 1,
  "id_usuario": 1,
  "id_vehiculo": 1,
  "id_categoria": null,
  "id_prioridad": null,
  "id_estado": 1,
  "descripcion_usuario": "Test",
  "latitud": 4.7110,
  "longitud": -74.0721,
  "created_at": "2026-04-19T10:30:00"
}
```

### Revisar logs en tiempo real

```bash
# Terminal 1: Backend
python -m uvicorn app.main:app --reload

# Terminal 2: Flutter logs
flutter logs -f

# Terminal 3: Ejecutar app
flutter run
```

---

**¡Lista para producción! 🚀**

---

## ✨ CAMBIOS CORREGIDOS EN ESTA VERSIÓN

✅ **Importaciones:** Agregado `import 'dart:async'` y `import 'package:geolocator/geolocator.dart'`  
✅ **GPS:** Cambio de `LocationSettings` a `desiredAccuracy: LocationAccuracy.high`  
✅ **Timeouts:** Manejo correcto con `onTimeout` y `TimeoutException`  
✅ **Tipos de dato:** Cambio de `List<dynamic>` a `List<Map<String, dynamic>>`  
✅ **Error handling:** Mejor logging y mensajes de error descriptivos  
✅ **Documentación:** Checklist detallado y ejemplos de pruebas  

### Referencia Rápida de Correcciones

```dart
// ❌ ANTES
class ReportarEmergenciaScreen extends StatefulWidget {
  final List<dynamic> vehiculos;  // ← Genérico

// ✅ DESPUÉS  
class ReportarEmergenciaScreen extends StatefulWidget {
  final List<Map<String, dynamic>> vehiculos;  // ← Específico
```

```dart
// ❌ ANTES
import 'package:http/http.dart' as http;
import 'dart:convert';
// Faltaba import 'dart:async' y import 'package:geolocator/geolocator.dart'

// ✅ DESPUÉS
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';  // ← AGREGADO
import 'package:shared_preferences/shared_preferences.dart';
import 'package:geolocator/geolocator.dart';  // ← AGREGADO
```

```dart
// ❌ ANTES
final posicion = await Geolocator.getCurrentPosition(
  locationSettings: const LocationSettings(
    accuracy: LocationAccuracy.high,
    distanceFilter: 0,
  ),
);

// ✅ DESPUÉS
final posicion = await Geolocator.getCurrentPosition(
  desiredAccuracy: LocationAccuracy.high,
);
```

```dart
// ❌ ANTES
.timeout(Duration(seconds: 20));

// ✅ DESPUÉS
.timeout(
  Duration(seconds: 20),
  onTimeout: () {
    throw TimeoutException('Conexión expirada');
  },
);
```
