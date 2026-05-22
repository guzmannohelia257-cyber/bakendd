# G2MOBILE — Guías de implementación frontend Flutter

> Guías para la **app móvil Flutter** (cliente final + técnico).
> Carpeta separada para que el equipo de mobile trabaje sin distracciones de backend.

## Pre-requisito
Cada `Mx.md` apunta al `Fx` de backend que debe estar antes.

> **⚠️ LEER PRIMERO**: [M0_setup_y_estado.md](./M0_setup_y_estado.md) — explica diferencias entre las guías M1-M8 y el estado real del proyecto `flutter/` (21 pantallas existentes, backend en Render, `flutter_secure_storage` para tokens, NO `shared_preferences`). **Hay que ajustar las guías a la realidad.**

| Mobile | Backend que la habilita | Producto |
|---|---|---|
| M0 | — | **Setup + adaptación al código existente (OBLIGATORIO LEER)** |
| **M9** | nuevos endpoints backend | **Login técnico con selector de taller pre-login (resuelve multi-tenant en mobile)** |
| M1 | [G2C1/F1](../G2C1/F1_servicios_extendidos.md) | Pantalla cliente "Seleccionar taller" con filtro por categoría |
| M2 | [G2C1/F2](../G2C1/F2_cotizacion.md) | Pantalla cliente "Comparar cotizaciones" |
| M3 | [G2C1/F3](../G2C1/F3_cancelacion.md) | Botón "Cancelar servicio" + UI compensación |
| M4 | [G2C2/F1](../G2C2/F1_redis_websocket_infra.md) | `RealtimeService` (cliente WS Flutter) |
| M5 | [G2C2/F2](../G2C2/F2_broadcast_emergencia.md) | Pantalla "Esperando taller" (cliente) |
| M6 | [G2C2/F3](../G2C2/F3_tracking_gps.md) | Pantalla "Tracking en mapa" (cliente ve técnico) |
| M7 | [G2C2/F3](../G2C2/F3_tracking_gps.md) | `LocationSender` (técnico envía GPS) |
| M8 | [G2C2/F6](../G2C2/F6_offline_flutter.md) | SQLite + outbox + sincronización |

## Orden de ejecución

```
M4 (Realtime) ─┬─► M5 (esperando)
               └─► M6 (tracking mapa)

M1, M2, M3, M7, M8 son independientes entre si.
```

Para la **1ra presentación (29 may)**: M1, M2, M3 listos.
Para la **2da presentación (7 jun)**: M4, M5, M6, M7, M8 listos.

---

## Stack / convenciones

| Capa | Tecnología | Cuándo |
|---|---|---|
| Framework | Flutter 3.x | base |
| HTTP | `http` package | base |
| State | `provider` o `riverpod` | recomendado |
| WS | `web_socket_channel` | M4 |
| Mapa | `flutter_map` + OpenStreetMap | M6 |
| GPS | `geolocator` | M7 |
| Offline | `sqflite` + `connectivity_plus` | M8 |

### Estructura recomendada

```
flutter/lib/
├── main.dart
├── config/
│   └── api_config.dart           (apiBase, wsBase)
├── models/
│   ├── incidente.dart
│   ├── cotizacion.dart
│   └── taller.dart
├── services/
│   ├── auth_service.dart
│   ├── api_client.dart           (wrapper http con auth)
│   ├── realtime_service.dart     ← M4
│   ├── incidente_service.dart
│   ├── cotizacion_service.dart   ← M2
│   ├── cancelacion_service.dart  ← M3
│   ├── location_sender.dart      ← M7
│   └── offline/                  ← M8
│       ├── local_db.dart
│       ├── outbox_service.dart
│       └── repository.dart
├── screens/
│   ├── login_screen.dart
│   ├── seleccionar_taller_screen.dart  ← M1
│   ├── cotizaciones_screen.dart        ← M2
│   ├── esperando_taller_screen.dart    ← M5
│   ├── tracking_screen.dart            ← M6
│   └── detalle_asignacion_screen.dart  (incluye M3)
└── widgets/
    ├── offline_banner.dart       ← M8
    └── connection_badge.dart     ← M4
```

### Configuración API

`flutter/lib/config/api_config.dart`:

```dart
class ApiConfig {
  // En emulador Android, 10.0.2.2 -> localhost del host
  // En iOS simulator y físico, usar IP de la maquina (192.168.x.x)
  static const apiBase = 'http://10.0.2.2:8000';
  static const wsBase = 'ws://10.0.2.2:8000';
}
```

> Para release / device físico, leer de `--dart-define=API_BASE=https://yary.app`.

### Autenticación
Token JWT en `shared_preferences`, agregado al header `Authorization: Bearer <token>` por un wrapper de `http.Client`:

```dart
// services/api_client.dart
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  Future<Map<String, String>> _headers({bool json = true}) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token');
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<http.Response> get(String path) async {
    return http.get(Uri.parse('${ApiConfig.apiBase}$path'), headers: await _headers(json: false));
  }
  Future<http.Response> post(String path, {Object? body}) async {
    return http.post(Uri.parse('${ApiConfig.apiBase}$path'), headers: await _headers(), body: body == null ? null : jsonEncode(body));
  }
  // ... put, patch, delete
}
```

---

## Permisos por plataforma

### Android (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
```

### iOS (`ios/Runner/Info.plist`):
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Yary necesita tu ubicación para asignar el taller más cercano</string>
```

---

## Checklist genérico al cerrar cada Mx
- [ ] Pantalla / servicio compila.
- [ ] Llamadas HTTP funcionan contra backend levantado.
- [ ] Manejo de loading + error visibles al usuario.
- [ ] Probado en emulador Android.
- [ ] Screenshot agregado al manual ([G2D/D3](../G2D/D3_manual_usuario.md)).
