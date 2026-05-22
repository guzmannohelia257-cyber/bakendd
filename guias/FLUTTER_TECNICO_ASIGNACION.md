# Guía de Flutter — Técnico: Login y Gestión de Asignaciones

Esta guía cubre **todo lo que el técnico necesita ver en su app móvil** después de que el taller le asigna una incidencia.

⚠️ **Importante:** Esta guía es SOLO para técnicos (usuarios con rol=3). Los clientes tienen otra app. Los talleres usan web.

---

## 1. Resumen ejecutivo

**Flujo del técnico:**

1. **Login** → Credenciales de técnico (email + password)
2. **Ver asignación actual** → Si hay una pendiente/aceptada
3. **Aceptar o rechazar** → Si está en `pendiente`
4. **Iniciar viaje** → Cambiar a `en_camino` (técnico saliendo)
5. **Completar servicio** → Cambiar a `completada` (trabajo hecho)

**3 endpoints principales (SOLO TÉCNICO):**

| Método | Ruta | Caso de uso |
|---|---|---|
| POST | `/usuarios/login` | Login con email técnico + password |
| GET | `/tecnicos/asignacion-actual` | Ver asignación pendiente/aceptada |
| PUT | `/tecnicos/mis-asignaciones/{id}/iniciar-viaje` | Estado: aceptada → en_camino |
| PUT | `/tecnicos/mis-asignaciones/{id}/completar` | Estado: en_camino → completada |

---

## 2. Diferenciación: Cliente vs Técnico vs Taller

### 2.1 Tipos de usuario en el backend

```
id_rol = 1: Cliente (reporta emergencias)
id_rol = 2: Usuario del Taller (gerente web)
id_rol = 3: Técnico (app móvil — está en esta guía)
id_rol = 4: Admin
```

### 2.2 Cómo diferenciar en Flutter

**En login, el endpoint retorna el objeto usuario con `id_rol`:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tipo": "usuario",
  "usuario": {
    "id_usuario": 1,
    "id_rol": 3,
    "nombre": "Juan",
    "email": "juan@taller.com"
  }
}
```

**Lee `id_rol` desde la respuesta JSON (más eficiente que decodificar JWT):**

```dart
// Usando la respuesta de /usuarios/login
final idRol = responseData['usuario']['id_rol'];  // 1=cliente, 3=técnico

if (idRol == 3) {
  // Es técnico → muestra esta app
  Navigator.pushNamed(context, '/tecnico-dashboard');
} else if (idRol == 1) {
  // Es cliente → muestra app cliente
  Navigator.pushNamed(context, '/cliente-dashboard');
} else {
  // Error: no es técnico ni cliente
  showError('Usuario no válido para esta app');
}
```

---

## 3. Login del Técnico

### 3.1 Pantalla de login

```dart
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class LoginTecnicoScreen extends StatefulWidget {
  @override
  _LoginTecnicoScreenState createState() => _LoginTecnicoScreenState();
}

class _LoginTecnicoScreenState extends State<LoginTecnicoScreen> {
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  bool isLoading = false;

  void handleLogin() async {
    if (emailController.text.isEmpty || passwordController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Email y contraseña son obligatorios')),
      );
      return;
    }

    setState(() => isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('${API_BASE_URL}/usuarios/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': emailController.text,
          'password': passwordController.text,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'];
        final idRol = data['usuario']['id_rol'];

        // ⚠️ Verificar que es técnico (id_rol == 3)
        if (idRol != 3) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Esta app es solo para técnicos (rol=3)')),
          );
          setState(() => isLoading = false);
          return;
        }

        // Guardar token en SharedPreferences
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('token', token);
        await prefs.setInt('id_usuario', data['usuario']['id_usuario']);
        await prefs.setInt('id_rol', idRol);

        // Navegar al dashboard
        Navigator.pushReplacementNamed(context, '/tecnico-dashboard');
      } else if (response.statusCode == 401) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Email o contraseña incorrectos')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${response.body}')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error de conexión: $e')),
      );
    } finally {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Login — Técnico')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: emailController,
              decoration: InputDecoration(
                labelText: 'Email',
                hintText: 'tecnico@taller.com',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.emailAddress,
            ),
            SizedBox(height: 16),
            TextField(
              controller: passwordController,
              decoration: InputDecoration(
                labelText: 'Contraseña',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: isLoading ? null : handleLogin,
              child: isLoading
                  ? CircularProgressIndicator()
                  : Text('Iniciar Sesión'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }
}
```

---

## 4. Ver Asignación Actual

### 4.1 Endpoint y modelo

```dart
// Modelos
class AsignacionResponse {
  final int idAsignacion;
  final int idIncidente;
  final int idTaller;
  final int? idUsuario;
  final String estadoAsignacion;  // pendiente, aceptada, en_camino, completada
  final int? etaMinutos;
  final String? notaTaller;
  final DateTime createdAt;
  final IncidenteResponse incidente;

  AsignacionResponse({
    required this.idAsignacion,
    required this.idIncidente,
    required this.idTaller,
    this.idUsuario,
    required this.estadoAsignacion,
    this.etaMinutos,
    this.notaTaller,
    required this.createdAt,
    required this.incidente,
  });

  factory AsignacionResponse.fromJson(Map<String, dynamic> json) {
    return AsignacionResponse(
      idAsignacion: json['id_asignacion'],
      idIncidente: json['id_incidente'],
      idTaller: json['id_taller'],
      idUsuario: json['id_usuario'],
      estadoAsignacion: json['estado']['nombre'],
      etaMinutos: json['eta_minutos'],
      notaTaller: json['nota_taller'],
      createdAt: DateTime.parse(json['created_at']),
      incidente: IncidenteResponse.fromJson(json['incidente']),
    );
  }
}

class IncidenteResponse {
  final int idIncidente;
  final String descripcionUsuario;
  final String? resumenIa;
  final double latitud;
  final double longitud;
  final String categoria;
  final String prioridad;

  IncidenteResponse({
    required this.idIncidente,
    required this.descripcionUsuario,
    this.resumenIa,
    required this.latitud,
    required this.longitud,
    required this.categoria,
    required this.prioridad,
  });

  factory IncidenteResponse.fromJson(Map<String, dynamic> json) {
    return IncidenteResponse(
      idIncidente: json['id_incidente'],
      descripcionUsuario: json['descripcion_usuario'],
      resumenIa: json['resumen_ia'],
      latitud: json['latitud']?.toDouble() ?? 0.0,
      longitud: json['longitud']?.toDouble() ?? 0.0,
      categoria: json['categoria']?['nombre'] ?? 'Desconocida',
      prioridad: json['prioridad']?['nivel'] ?? 'normal',
    );
  }
}
```

### 4.2 Service para obtener asignación actual

```dart
class TecnicoService {
  final String apiUrl = 'http://your-api.com/api';  // Cambiar según env
  final String? token;

  TecnicoService({this.token});

  Future<AsignacionResponse> getAsignacionActual() async {
    if (token == null) throw Exception('Token no encontrado');

    final response = await http.get(
      Uri.parse('$apiUrl/tecnicos/asignacion-actual'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      return AsignacionResponse.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 404) {
      throw Exception('No hay asignación actual');
    } else {
      throw Exception('Error: ${response.body}');
    }
  }

  Future<IncidenteResponse> getIncidenteDetalle(int idIncidente) async {
    if (token == null) throw Exception('Token no encontrado');

    final response = await http.get(
      Uri.parse('$apiUrl/incidencias/$idIncidente'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      return IncidenteResponse.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Error al cargar incidente: ${response.body}');
    }
  }

  Future<AsignacionResponse> iniciarViaje(int idAsignacion) async {
    if (token == null) throw Exception('Token no encontrado');

    final response = await http.put(
      Uri.parse('$apiUrl/tecnicos/mis-asignaciones/$idAsignacion/iniciar-viaje'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({}),  // Opcional: geolocalización
    );

    if (response.statusCode == 200) {
      return AsignacionResponse.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Error: ${response.body}');
    }
  }

  Future<AsignacionResponse> completar(int idAsignacion) async {
    if (token == null) throw Exception('Token no encontrado');

    final response = await http.put(
      Uri.parse('$apiUrl/tecnicos/mis-asignaciones/$idAsignacion/completar'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({}),  // Opcional: costo_estimado, resumen_trabajo
    );

    if (response.statusCode == 200) {
      return AsignacionResponse.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Error: ${response.body}');
    }
  }
}
```

---

## 5. Dashboard del Técnico

### 5.1 Pantalla principal

```dart
class TecnicoDashboardScreen extends StatefulWidget {
  @override
  _TecnicoDashboardScreenState createState() => _TecnicoDashboardScreenState();
}

class _TecnicoDashboardScreenState extends State<TecnicoDashboardScreen> {
  AsignacionResponse? asignacion;
  IncidenteResponse? incidente;
  bool isLoading = true;
  String? errorMessage;
  late TecnicoService tecnicoService;

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  void _initializeAndLoad() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token');
    
    if (token == null) {
      Navigator.pushReplacementNamed(context, '/login');
      return;
    }

    tecnicoService = TecnicoService(token: token);
    _loadAsignacion();
  }

  void _loadAsignacion() async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
      final asig = await tecnicoService.getAsignacionActual();
      final inc = await tecnicoService.getIncidenteDetalle(asig.idIncidente);
      
      setState(() {
        asignacion = asig;
        incidente = inc;
        isLoading = false;
      });
    } catch (e) {
      setState(() {
        errorMessage = e.toString();
        isLoading = false;
      });
    }
  }

  void _handleIniciarViaje() async {
    if (asignacion == null) return;

    try {
      final updated = await tecnicoService.iniciarViaje(asignacion!.idAsignacion);
      setState(() => asignacion = updated);
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ Viaje iniciado. Dirígete al cliente.')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Error: $e')),
      );
    }
  }

  void _handleCompletar() async {
    if (asignacion == null) return;

    // Dialog con formulario opcional (costo, resumen)
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Completar Servicio'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('¿El servicio está terminado?'),
            SizedBox(height: 16),
            Text('Cliente: ${incidente?.descripcionUsuario ?? "N/A"}'),
            Text('Descripción: ${asignacion?.incidente.descripcionUsuario ?? "N/A"}'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              try {
                final updated = await tecnicoService.completar(asignacion!.idAsignacion);
                setState(() => asignacion = updated);
                
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('✅ Servicio completado. Cliente puede evaluar.')),
                );
              } catch (e) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('❌ Error: $e')),
                );
              }
            },
            child: Text('Confirmar'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Scaffold(
        appBar: AppBar(title: Text('Mi Asignación')),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (errorMessage != null) {
      return Scaffold(
        appBar: AppBar(title: Text('Mi Asignación')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('❌ $errorMessage', textAlign: TextAlign.center),
              SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadAsignacion,
                child: Text('Reintentar'),
              ),
            ],
          ),
        ),
      );
    }

    if (asignacion == null) {
      return Scaffold(
        appBar: AppBar(title: Text('Mi Asignación')),
        body: Center(
          child: Text('📭 No hay asignación pendiente en este momento.'),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('Mi Asignación Actual'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadAsignacion,
          ),
          IconButton(
            icon: Icon(Icons.logout),
            onPressed: () async {
              final prefs = await SharedPreferences.getInstance();
              await prefs.remove('token');
              Navigator.pushReplacementNamed(context, '/login');
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: (_) async => _loadAsignacion(),
        child: SingleChildScrollView(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Estado actual
              Card(
                color: _getColorForEstado(asignacion!.estadoAsignacion),
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Estado',
                            style: TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                          Text(
                            asignacion!.estadoAsignacion.toUpperCase(),
                            style: TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                      Icon(
                        _getIconForEstado(asignacion!.estadoAsignacion),
                        size: 40,
                        color: Colors.white,
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(height: 16),

              // ETA
              if (asignacion!.etaMinutos != null)
                Card(
                  child: Padding(
                    padding: EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Icon(Icons.timer, color: Colors.orange),
                        SizedBox(width: 12),
                        Text(
                          'ETA: ${asignacion!.etaMinutos} minutos',
                          style: TextStyle(fontSize: 16),
                        ),
                      ],
                    ),
                  ),
                ),
              SizedBox(height: 16),

              // Detalle del incidente
              if (incidente != null) ...[
              if (asignacion != null) ...[
                Text('📋 Detalle del Incidente', style: Theme.of(context).textTheme.titleLarge),
                SizedBox(height: 8),
                Card(
                  child: Padding(
                    padding: EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Categoría: ${incidente!.categoria}', style: TextStyle(fontSize: 14)),
                        Text('Categoría: ${asignacion!.incidente.categoria}', style: TextStyle(fontSize: 14)),
                        SizedBox(height: 4),
                        Text('Prioridad: ${incidente!.prioridad}', style: TextStyle(fontSize: 14)),
                        Text('Prioridad: ${asignacion!.incidente.prioridad}', style: TextStyle(fontSize: 14)),
                        SizedBox(height: 4),
                        Text('Descripción:', style: TextStyle(fontWeight: FontWeight.bold)),
                        Text(incidente!.descripcionUsuario, style: TextStyle(fontSize: 13)),
                        if (incidente!.resumenIa != null) ...[
                        Text(asignacion!.incidente.descripcionUsuario, style: TextStyle(fontSize: 13)),
                        if (asignacion!.incidente.resumenIa != null) ...[
                          SizedBox(height: 8),
                          Text('Análisis IA:', style: TextStyle(fontWeight: FontWeight.bold)),
                          Text(incidente!.resumenIa!, style: TextStyle(fontSize: 13, color: Colors.blueGrey)),
                          Text(asignacion!.incidente.resumenIa!, style: TextStyle(fontSize: 13, color: Colors.blueGrey)),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
              SizedBox(height: 24),

              // Botones de acción
              _buildActionButtons(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionButtons() {
    switch (asignacion!.estadoAsignacion) {
      case 'pendiente':
        // El taller aún no aceptó, solo lectura
        return Card(
          color: Colors.grey[200],
          child: Padding(
            padding: EdgeInsets.all(12),
            child: Text(
              '⏳ Esperando que el taller acepte la asignación...',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey[700]),
            ),
          ),
        );

      case 'aceptada':
        return Column(
          children: [
            Text(
              '✅ El taller aceptó tu asignación',
              style: TextStyle(fontSize: 14, color: Colors.green),
            ),
            SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _handleIniciarViaje,
                icon: Icon(Icons.directions_car),
                label: Text('Iniciar Viaje'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  padding: EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        );

      case 'en_camino':
        return Column(
          children: [
            Text(
              '🚗 En camino hacia el cliente',
              style: TextStyle(fontSize: 14, color: Colors.blue),
            ),
            SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _handleCompletar,
                icon: Icon(Icons.check_circle),
                label: Text('Completar Servicio'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.green,
                  padding: EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        );

      case 'completada':
        return Card(
          color: Colors.green[50],
          child: Padding(
            padding: EdgeInsets.all(12),
            child: Column(
              children: [
                Text(
                  '🎉 ¡Servicio completado!',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.green,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'El cliente puede evaluar tu trabajo.',
                  style: TextStyle(color: Colors.grey[700]),
                ),
              ],
            ),
          ),
        );

      default:
        return Text('Estado desconocido: ${asignacion!.estadoAsignacion}');
    }
  }

  Color _getColorForEstado(String estado) {
    switch (estado) {
      case 'pendiente':
        return Colors.grey;
      case 'aceptada':
        return Colors.green;
      case 'en_camino':
        return Colors.blue;
      case 'completada':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  IconData _getIconForEstado(String estado) {
    switch (estado) {
      case 'pendiente':
        return Icons.schedule;
      case 'aceptada':
        return Icons.check_circle;
      case 'en_camino':
        return Icons.directions_car;
      case 'completada':
        return Icons.done_all;
      default:
        return Icons.help;
    }
  }
}
```

---

## 6. Flujo de estados para técnico

```
┌─────────────────────────────────────────────────────────┐
│                 ASIGNACIÓN DEL TÉCNICO                  │
└─────────────────────────────────────────────────────────┘

1. PENDIENTE (apenas creada por el taller)
   ├─ Técnico ve: "El taller procesó tu solicitud"
   └─ Botones: NINGUNO (solo lectura, espera que taller acepte)

2. ACEPTADA (taller hizo PUT /aceptar con id_usuario)
   ├─ Técnico ve: "✅ El taller aceptó tu asignación"
   ├─ Botones: [Iniciar Viaje]
   └─ Acción: PUT /iniciar-viaje → en_camino

3. EN_CAMINO (técnico hizo PUT /iniciar-viaje)
   ├─ Técnico ve: "🚗 En camino hacia el cliente"
   ├─ Botones: [Completar Servicio]
   └─ Acción: PUT /completar → completada

4. COMPLETADA (técnico hizo PUT /completar)
   ├─ Técnico ve: "🎉 ¡Servicio completado!"
   └─ Botones: NINGUNO (solo lectura)
```

---

## 7. Manejo de errores

```dart
class ErrorHandler {
  static String handleError(dynamic error) {
    if (error.toString().contains('404')) {
      return 'No hay asignación actual. Espera a que un taller te asigne.';
    } else if (error.toString().contains('401')) {
      return 'Sesión expirada. Vuelve a iniciar sesión.';
    } else if (error.toString().contains('409')) {
      return 'Ya tienes otra asignación activa. Complétala primero.';
    } else if (error.toString().contains('Connection refused')) {
      return 'Error de conexión. Verifica tu internet.';
    } else {
      return 'Error: $error';
    }
  }
}
```

---

## 8. SharedPreferences — Guardar token

```dart
import 'package:shared_preferences/shared_preferences.dart';

class TokenManager {
  static Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
  }

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token');
  }

  static Future<void> deleteToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
  }

  static Future<bool> hasToken() async {
    final token = await getToken();
    return token != null;
  }
}
```

---

## 9. Configuración de rutas en main.dart

```dart
void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'App Técnico',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: SplashScreen(),  // ← Verifica token
      routes: {
        '/login': (context) => LoginTecnicoScreen(),
        '/tecnico-dashboard': (context) => TecnicoDashboardScreen(),
      },
    );
  }
}

class SplashScreen extends StatefulWidget {
  @override
  _SplashScreenState createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkToken();
  }

  void _checkToken() async {
    await Future.delayed(Duration(seconds: 1));
    
    final hasToken = await TokenManager.hasToken();

    if (hasToken) {
      // Si guardaste el id_rol en SharedPreferences durante el login
      final prefs = await SharedPreferences.getInstance();
      final idRol = prefs.getInt('id_rol');

      if (idRol == 3) {
        Navigator.pushReplacementNamed(context, '/tecnico-dashboard');
      } else {
        Navigator.pushReplacementNamed(context, '/login');
      }
    } else {
      Navigator.pushReplacementNamed(context, '/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.car_repair, size: 60, color: Colors.blue),
            SizedBox(height: 16),
            Text('App Técnico', style: TextStyle(fontSize: 24)),
            SizedBox(height: 24),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
```

---

## 10. Dependencies en pubspec.yaml

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0                    # HTTP requests
  shared_preferences: ^2.1.0      # Guardar token localmente
  intl: ^0.18.0                   # Formateo de fechas
  google_maps_flutter: ^2.2.0     # Mapas (opcional)
  geolocator: ^9.0.0              # Geolocalización (opcional)

dev_dependencies:
  flutter_test:
    sdk: flutter
```

---

## 11. Flujo completo: Cliente → Taller → Técnico

```
CLIENTE (App móvil)
  ↓
  1. Reporta emergencia (POST /incidencias)
  ↓
TALLER (Web)
  ↓
  2. Elige técnico + acepta (PUT /aceptar con id_usuario)
  ↓
TÉCNICO (App móvil) ← ESTA GUÍA
  ↓
  3. Ve asignación (GET /asignacion-actual)
  4. Inicia viaje (PUT /iniciar-viaje)
  5. Completa servicio (PUT /completar)
  ↓
CLIENTE (App móvil)
  ↓
  6. Evalúa técnico y taller
```

---

## 12. Checklist de implementación

- [ ] Package `http` instalado
- [ ] Package `shared_preferences` instalado
- [ ] Pantalla de login creada con validación
- [ ] TokenManager implementado para guardar/recuperar token
- [ ] SplashScreen con verificación de token
- [ ] Modelos (AsignacionResponse, IncidenteResponse) creados
- [ ] TecnicoService con 4 métodos (getAsignacion, getIncidente, iniciarViaje, completar)
- [ ] TecnicoDashboardScreen mostrado según estado
- [ ] Botones de acción (Iniciar Viaje, Completar) funcionando
- [ ] Manejo de errores y mensajes en español
- [ ] Logout implementado
- [ ] Refresh manual (pull-to-refresh) implementado
- [ ] Test: Login con técnico válido (id_rol=3) → acceso
- [ ] Test: Login con cliente (id_rol=1) → rechazo
- [ ] Test: Ver asignación aceptada → botón "Iniciar Viaje"
- [ ] Test: Clic "Iniciar Viaje" → estado en_camino
- [ ] Test: Clic "Completar Servicio" → estado completada

---

## 13. Variables de entorno y configuración

Crea un archivo `constants.dart`:

```dart
// lib/constants/config.dart

const String API_BASE_URL = 'http://192.168.1.10:8000/api';  // Cambiar según ambiente

// O para producción:
// const String API_BASE_URL = 'https://api.tudominio.com/api';

// Tokens duran 30 minutos (igual al backend)
const int TOKEN_EXPIRATION_MINUTES = 30;
```

---

## 14. Preguntas frecuentes

**¿Qué pasa si el técnico inicia sesión pero no es rol=3?**
Se rechaza el login con mensaje: "Esta app es solo para técnicos".

**¿Qué pasa si no hay asignación actual?**
Se muestra mensaje: "📭 No hay asignación pendiente en este momento." (está esperando que un taller la cree).

**¿Puedo ver el historial de asignaciones completadas?**
No está en esta guía básica. Es una pantalla adicional que puedes agregar con `GET /tecnicos/mis-asignaciones?estado=completada`.

**¿El token expira?**
Sí, en 30 minutos (como el backend). Si expira, se redirige a login automáticamente.

**¿Cómo sé si estoy conectado?**
En el AppBar hay un icono de logout. Si ves eso, estás autenticado.
