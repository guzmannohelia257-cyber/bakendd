# M0 — Setup y adaptación al proyecto existente

> **Lee esto ANTES** de M1-M8. Las otras guías asumen un proyecto limpio,
> pero `flutter/` **ya existe** con código del 1er parcial. Aquí ajustamos diferencias.

---

## 1. Estado actual del proyecto `flutter/`

### Lo que YA existe (no tocar / reusar)

| Path | Qué es |
|---|---|
| `lib/main.dart` | Entry point + setup Firebase + routes |
| `lib/config/api_config.dart` | `baseUrl` apunta a `https://back-despliegue-cp05.onrender.com` |
| `lib/config/stripe_config.dart` | Stripe key |
| `lib/services/auth_service.dart` | Login cliente — **reusar** |
| `lib/services/tecnico_auth_service.dart` | Login técnico — **reusar** |
| `lib/services/incidente_service.dart` | Reportar incidente — **extender** para usar nuevos endpoints |
| `lib/services/mensajes_service.dart` | Chat |
| `lib/services/notification_service.dart` | FCM |
| `lib/services/pagos_service.dart` | Stripe |
| `lib/services/tecnico_asignaciones_service.dart` | Asignaciones del técnico |
| `lib/services/usuario_service.dart` | CRUD usuario |
| `lib/services/vehiculo_service.dart` | CRUD vehículo |
| `lib/screens/*` | 21 pantallas (login, conductor_home, tecnico_home, reportar_emergencia, etc.) |
| `lib/models/*` | Modelos (incidente, asignacion, evidencia, candidato_asignacion, etc.) |
| `lib/widgets/completar_servicio_dialog.dart` | Modal técnico completa servicio |
| `lib/utils/app_logger.dart` | Logger custom |

### Dependencias actuales (`pubspec.yaml`)

| Paquete | Versión | Para |
|---|---|---|
| `http` | 1.1.0 | API |
| `shared_preferences` | 2.2.2 | Storage simple |
| `flutter_secure_storage` | 9.2.2 | Storage seguro tokens |
| `geolocator` | 13.0.1 | GPS |
| `permission_handler` | 12.0.1 | Permisos |
| `flutter_map` | 7.0.2 | Mapas |
| `latlong2` | 0.9.1 | Coords |
| `firebase_core` + `firebase_messaging` | 3.6 / 15.1 | FCM |
| `flutter_local_notifications` | 18.0.1 | Notif locales |
| `flutter_stripe` | 10.2.0 | Pagos |
| `image_picker` + `record` + `audioplayers` + `path_provider` | varias | Evidencias |
| `intl` | 0.20.2 | Fechas |

### LO QUE FALTA INSTALAR (para C1+C2)

Agregar a `pubspec.yaml` dentro de `dependencies:`:

```yaml
  # WebSocket cliente (M4)
  web_socket_channel: ^3.0.0

  # Detección de conectividad (M8)
  connectivity_plus: ^6.0.5

  # SQLite local (M8)
  sqflite: ^2.3.3+1
  path: ^1.9.0

  # UUID para idempotencia outbox (M8)
  uuid: ^4.4.2
```

Después correr:
```bash
cd flutter
flutter pub get
```

---

## 2. Diferencias clave vs. guías M1-M8

### Diferencia #1 — Backend en Render, NO localhost

Las guías M1-M8 mencionan `http://10.0.2.2:8000` y `ws://10.0.2.2:8000` (emulador → host). **El proyecto real ya usa Render**:

```dart
// lib/config/api_config.dart actual
static const String _emulatorUrl = 'https://back-despliegue-cp05.onrender.com';
static const String _deviceUrl = 'https://back-despliegue-cp05.onrender.com';
static const String baseUrl = isEmulator ? _emulatorUrl : _deviceUrl;
```

**Cambio sugerido al `api_config.dart`** para agregar WS URL:

```dart
class ApiConfig {
  static const bool isEmulator = false;
  static const String baseUrl = 'https://back-despliegue-cp05.onrender.com';
  static const String wsUrl = 'wss://back-despliegue-cp05.onrender.com';
}
```

> ⚠️ **WSS, no WS** porque Render es HTTPS.

### Diferencia #2 — Usar `flutter_secure_storage`, NO `shared_preferences`, para tokens

Las guías M2, M3, M7 muestran:
```dart
final prefs = await SharedPreferences.getInstance();
final token = prefs.getString('token');
```

**El proyecto ya usa `flutter_secure_storage`** que es más seguro:

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final _storage = const FlutterSecureStorage();
final token = await _storage.read(key: 'token');
```

**Adaptar todos los snippets** de las guías para usar secure storage.

### Diferencia #3 — `auth_service.dart` existente devuelve token

**Cliente (rol=1)**: el `auth_service.dart` actual ya hace login normal. Después del login, conectar el RealtimeService.

**Técnico (rol=3) ⚠️ caso especial multi-tenant**:
Como un técnico puede pertenecer a **varios talleres** (`usuario_taller` es M:N), el login normal no sabe a cuál asignar las acciones. La solución es **selector de taller PRE-login**:
- Pantalla 1: lista de talleres disponibles
- Pantalla 2: login con email + password (y `id_taller` ya elegido)
- Backend valida vínculo y devuelve token con `id_tenant` del taller elegido

**Ver guía dedicada**: [M9_login_tecnico_multi_taller.md](./M9_login_tecnico_multi_taller.md).

Para el cliente, sigue siendo lo de siempre — después de su login:

```dart
// En auth_service.dart, tras login exitoso:
import 'realtime_service.dart';

Future<bool> login(String email, String password) async {
  // ... lo existente que guarda el token
  await _storage.write(key: 'token', value: token);

  // AGREGAR:
  RealtimeService().connect(token);
  return true;
}

Future<void> logout() async {
  // ... lo existente
  RealtimeService().disconnect();
}
```

### Diferencia #4 — Adaptar `reportar_emergencia_screen.dart` existente

La pantalla actual `reportar_emergencia_screen.dart` ya existe. Tras crear el incidente, **debe ramificar** según categoría:

```dart
// Pseudo-código del flujo nuevo
final incidente = await incidenteService.reportar(...);

// Cargar la categoría asignada
final categoria = await tallerService.getCategoria(incidente.idCategoria);

if (categoria.requiereCotizacion) {
  // Cotizar: ir a M2
  Navigator.pushReplacementNamed(context, '/cotizaciones', arguments: {
    'id_incidente': incidente.idIncidente,
  });
} else {
  // Servicio directo: ir a M5 (esperando taller)
  Navigator.pushReplacementNamed(context, '/esperando-taller', arguments: {
    'id_incidente': incidente.idIncidente,
  });
}
```

### Diferencia #5 — Pantalla `seleccionar_taller_screen.dart` ya existe (vieja)

La pantalla actual probablemente lista talleres SIN filtro por categoría. **Reemplazar** su lógica con M1:
- Usar nuevo endpoint `/talleres/compatibles?...`
- Slider de radio
- Banner si categoría requiere cotización

### Diferencia #6 — `tecnico_tracking_screen.dart` ya existe (solo técnico)

La pantalla actual es del lado **técnico** (ve el incidente). M6 propone una pantalla del lado **cliente** (ve al técnico moviéndose). **Crear nueva**: `cliente_tracking_screen.dart`.

### Diferencia #7 — Rutas

`main.dart` ya tiene un mapa de rutas. **Agregar las nuevas**:

```dart
// main.dart - en MaterialApp.routes:
routes: {
  // ... existentes
  '/cotizaciones': (ctx) {
    final args = ModalRoute.of(ctx)!.settings.arguments as Map;
    return CotizacionesScreen(idIncidente: args['id_incidente']);
  },
  '/esperando-taller': (ctx) {
    final args = ModalRoute.of(ctx)!.settings.arguments as Map;
    return EsperandoTallerScreen(idIncidente: args['id_incidente']);
  },
  '/cliente-tracking': (ctx) {
    final args = ModalRoute.of(ctx)!.settings.arguments as Map;
    return ClienteTrackingScreen(
      idIncidente: args['id_incidente'],
      idAsignacion: args['id_asignacion'],
      ubicacionIncidente: args['ubicacion_incidente'],
      taller: args['taller'],
    );
  },
},
```

---

## 3. Permisos GPS para técnico (M7)

Ya tienes `permission_handler` y `geolocator` instalados. Solo verificar que `AndroidManifest.xml` tenga:

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
```

Y en `ios/Runner/Info.plist`:
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Yary necesita ubicación para asignar talleres cercanos</string>
```

---

## 4. Limpieza menor

- `flutter/google-services.json` — **rotar credenciales** Firebase (estuvo en git en algún momento). Está bien tenerlo local pero rotar lo que se filtró.
- Muchos `.md` viejos en raíz (`DIAGNOSTICO_401.md`, `MEJORAS_DEFENSIVAS_AUTH.md`, etc.) — mover a `flutter/docs/` o eliminar.

---

## 5. Smoke test antes de implementar M1

```bash
cd flutter
flutter pub get
flutter analyze         # debe pasar sin errors
flutter run             # en emulador o dispositivo
```

Verificar:
- [ ] Login funciona contra Render.
- [ ] Pantalla home carga.
- [ ] No hay errors en consola.
- [ ] Permisos GPS solicitan correctamente.

Si todo OK, arrancar **M1**.

---

## 6. Pantallas a CREAR / REEMPLAZAR

| Estado | Acción |
|---|---|
| `seleccionar_taller_screen.dart` | **Reemplazar lógica** con M1 (filtro por categoría) |
| `cotizaciones_screen.dart` | **Crear nuevo** (M2) |
| `esperando_taller_screen.dart` | **Crear nuevo** (M5) — distinto del actual flujo |
| `cliente_tracking_screen.dart` | **Crear nuevo** (M6) — distinto al `tecnico_tracking_screen` actual |
| `tecnico_asignacion_detalle_screen.dart` | **Modificar** para agregar botón "Iniciar viaje" + `LocationSender` (M7) |
| `widgets/cancelar_button.dart` | **Crear nuevo** (M3) — reutilizable en varias pantallas |
| `widgets/offline_banner.dart` | **Crear nuevo** (M8) |
| `widgets/connection_badge.dart` | **Crear nuevo** (M4) |

## Servicios a CREAR

| Servicio | Para |
|---|---|
| `services/realtime_service.dart` | M4 — WS cliente |
| `services/cotizacion_service.dart` | M2 |
| `services/cancelacion_service.dart` | M3 |
| `services/location_sender.dart` | M7 |
| `services/taller_service.dart` | M1 — `/talleres/compatibles` (puede agregar a `incidente_service` si prefieres) |
| `services/offline/local_db.dart` | M8 |
| `services/offline/outbox_service.dart` | M8 |
| `services/offline/incidente_repository.dart` | M8 |

## Modelos a CREAR

| Modelo | Para |
|---|---|
| `models/categoria.dart` | M1 |
| `models/taller_compatible.dart` | M1 |
| `models/cotizacion.dart` | M2 |
| `models/cancelacion_response.dart` | M3 |

---

## Checklist M0
- [ ] `flutter pub get` instala las 5 dependencias nuevas.
- [ ] `flutter analyze` sin errors.
- [ ] App arranca contra Render OK.
- [ ] `api_config.dart` actualizado con `wsUrl`.
- [ ] Permisos AndroidManifest + Info.plist verificados.
- [ ] Plan de qué pantallas crear vs. modificar entendido.
- [ ] Decidido: reusar `flutter_secure_storage` (NO `shared_preferences` como dicen las guías).

## Notas de orden
- **M4 (RealtimeService) primero**, antes que M5/M6 (esperando + tracking).
- **M1, M2, M3, M7, M8** son independientes.
- **M3 produce un Widget**, no una pantalla — se incluye dentro de otras (tracking, detalle asignación).
