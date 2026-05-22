# 🔧 ERRORES ENCONTRADOS Y CORREGIDOS

## 📋 Problemas Detectados

### ❌ Error #1: Importaciones Faltantes en `incidente_service.dart`

**Problema:**
```dart
// ❌ FALTABAN ESTAS IMPORTACIONES
import 'dart:async';  // ← Para TimeoutException
import 'package:geolocator/geolocator.dart';  // ← Para GPS
```

**Error que generaba:**
```
Error: The getter 'Geolocator' isn't defined
Error: The type 'TimeoutException' isn't defined
Error: The type 'LocationPermission' isn't defined
```

**Solución:**
```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';  // ✅ AGREGADO
import 'package:shared_preferences/shared_preferences.dart';
import 'package:geolocator/geolocator.dart';  // ✅ AGREGADO
import '../models/incidente.dart';
```

---

### ❌ Error #2: Parámetro Incorrecto en GPS

**Problema:**
```dart
// ❌ INCORRECTO - LocationSettings no existe en geolocator ^9.0.2
final posicion = await Geolocator.getCurrentPosition(
  locationSettings: const LocationSettings(
    accuracy: LocationAccuracy.high,
    distanceFilter: 0,
  ),
);
```

**Error que generaba:**
```
Error: The constructor 'LocationSettings' isn't defined
```

**Solución:**
```dart
// ✅ CORRECTO - Usar desiredAccuracy
final posicion = await Geolocator.getCurrentPosition(
  desiredAccuracy: LocationAccuracy.high,
);
```

---

### ❌ Error #3: Tipo de Dato Incorrecto en Widget

**Problema:**
```dart
// ❌ INCORRECTO - Widget espera List<Map<String, dynamic>>
class ReportarEmergenciaScreen extends StatefulWidget {
  final List<dynamic> vehiculos;  // ← Muy genérico
```

**Solución:**
```dart
// ✅ CORRECTO - Especificar el tipo correcto
class ReportarEmergenciaScreen extends StatefulWidget {
  final List<Map<String, dynamic>> vehiculos;  // ← Más específico
```

---

### ❌ Error #4: Timeout Sin Manejo Correcto

**Problema:**
```dart
// ❌ Esto no lanza TimeoutException automáticamente
final response = await http
    .post(...)
    .timeout(Duration(seconds: 20));
```

**Solución:**
```dart
// ✅ CORRECTO - Usar onTimeout para lanzar excepción
final response = await http
    .post(...)
    .timeout(
      const Duration(seconds: 20),
      onTimeout: () {
        throw TimeoutException('Conexión expirada');
      },
    );
```

---

## ✅ CAMBIOS REALIZADOS

| Archivo | Cambio | Estado |
|---------|--------|--------|
| `incidente_service.dart` | Agregar `import 'dart:async'` | ✅ |
| `incidente_service.dart` | Agregar `import 'package:geolocator/geolocator.dart'` | ✅ |
| `incidente_service.dart` | Cambiar `LocationSettings` → `desiredAccuracy` | ✅ |
| `incidente_service.dart` | Mejorar manejo de `TimeoutException` | ✅ |
| `incidente_service.dart` | Agregar más logging para debug | ✅ |
| `reportar_emergencia_screen.dart` | Cambiar `List<dynamic>` → `List<Map<String, dynamic>>` | ✅ |
| `reportar_emergencia_screen.dart` | Agregar `const` en Widgets | ✅ |

---

## 🧪 CÓMO PROBAR

### 1. Reemplazar el Servicio

**Copiar:** [FLUTTER_REPORTAR_EMERGENCIA_CORREGIDO.dart](FLUTTER_REPORTAR_EMERGENCIA_CORREGIDO.dart)

O reemplaza manualmente en tu proyecto:

```bash
# En tu proyecto Flutter
lib/
├── models/
│   └── incidente.dart        # ✅ Modelos corregidos
├── services/
│   └── incidente_service.dart # ✅ Servicio corregido
└── screens/
    └── reportar_emergencia_screen.dart # ✅ Pantalla corregida
```

### 2. Verificar Dependencias

```yaml
# pubspec.yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.0
  geolocator: ^9.0.2  # ← IMPORTANTE
  intl: ^0.19.0
```

**Instalar:**
```bash
flutter pub get
```

### 3. Permisos Android

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.INTERNET" />
```

### 4. Probar Funcionalidad

```bash
# Terminal 1: Verificar backend corriendo
netstat -ano | findstr ":8000"
# Debe mostrar: TCP 127.0.0.1:8000 LISTENING

# Terminal 2: Correr Flutter
flutter run

# En la app:
# 1. Navega a "Reportar Emergencia"
# 2. Selecciona un vehículo
# 3. Ingresa descripción (ej: "Test")
# 4. Presiona "Obtener Ubicación"
# 5. Presiona "REPORTAR AHORA"
# 6. Debe aparecer confirmación con ID
```

---

## 📊 Endpoint Backend

**POST /incidencias/**

```bash
curl -X POST http://10.0.2.2:8000/incidencias/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "id_vehiculo": 1,
    "descripcion_usuario": "Motor hace ruido",
    "latitud": 4.7110,
    "longitud": -74.0721
  }'
```

**Respuesta esperada (201):**
```json
{
  "id_incidente": 1,
  "id_usuario": 1,
  "id_vehiculo": 1,
  "id_categoria": null,
  "id_prioridad": null,
  "id_estado": 1,
  "descripcion_usuario": "Motor hace ruido",
  "latitud": 4.7110,
  "longitud": -74.0721,
  "created_at": "2026-04-19T10:30:00"
}
```

---

## 🐛 Debug

### Ver Logs de Flutter

```bash
# Todos los logs
flutter logs

# Solo los de INCIDENTE
flutter logs | grep "INCIDENTE"

# Solo los de GPS
flutter logs | grep "GPS"
```

### Logs Esperados Cuando Funciona

```
[INCIDENTE] 🚨 Reportando emergencia...
[INCIDENTE] Vehículo: 1
[INCIDENTE] Descripción: Motor hace ruido
[INCIDENTE] GPS: 4.7110, -74.0721
[INCIDENTE] Body: {id_vehiculo: 1, descripcion_usuario: Motor hace ruido, latitud: 4.7110, longitud: -74.0721}
[INCIDENTE] URL: http://10.0.2.2:8000/incidencias/
[INCIDENTE] Status: 201
[INCIDENTE] Response: {"id_incidente": 1, ...}
[INCIDENTE] ✅ Emergencia reportada: #1
```

---

## 🚨 Errores Comunes y Soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `No autenticado` | Token no guardado | Haz login primero |
| `Vehículo no encontrado` | ID_vehículo incorrecto | Usa un vehículo existente |
| `Timeout` | Servidor no responde | Verifica que backend esté corriendo en :8000 |
| `Permiso denegado (GPS)` | Permiso no otorgado | Acepta permisos cuando Flutter lo pida |
| `Status: 400` | Datos inválidos | Revisa los logs del servidor |
| `Status: 401` | Sesión expirada | Haz login nuevamente |

---

## ✨ Lo que ahora funciona

✅ Reportar emergencia sin errores  
✅ GPS se obtiene correctamente  
✅ Manejo de timeouts  
✅ Mensajes de error claros  
✅ Logging para debug  
✅ Tipos correctos en Dart  

---

**¡Listo para usar! 🚀**
