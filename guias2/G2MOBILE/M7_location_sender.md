# M7 — LocationSender (técnico envía GPS)

> **Backend requerido:** [G2C2/F3](../G2C2/F3_tracking_gps.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
Servicio que corre en la app del técnico: cuando inicia un viaje, comienza a enviar su posición GPS al backend cada 12 segundos. El backend la persiste y la transmite al cliente via WS.

Endpoint consumido:
- `POST /tecnicos/me/ubicacion` — ping de ubicación

---

## Dependencias

`flutter/pubspec.yaml`:
```yaml
dependencies:
  geolocator: ^12.0.0
```

```bash
flutter pub get
```

## Permisos

### Android — `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
```

### iOS — `ios/Runner/Info.plist`:
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Yary necesita tu ubicación para que el cliente vea tu llegada en vivo</string>
```

---

## Servicio

`flutter/lib/services/location_sender.dart`:

```dart
import 'dart:async';
import 'dart:convert';
import 'package:geolocator/geolocator.dart';
import 'api_client.dart';

enum LocationSenderStatus {
  idle,
  pidiendoPermisos,
  permisosDenegados,
  enviando,
  error,
}

class LocationSenderResult {
  final bool ok;
  final int? etaMinutos;
  final double? distanciaKm;
  final bool llegadoAuto;
  LocationSenderResult({
    required this.ok,
    this.etaMinutos,
    this.distanciaKm,
    this.llegadoAuto = false,
  });
}

class LocationSender {
  final ApiClient _api = ApiClient();
  Timer? _timer;
  StreamSubscription<Position>? _positionStream;
  int? _idAsignacionActiva;

  final _statusCtrl = StreamController<LocationSenderStatus>.broadcast();
  Stream<LocationSenderStatus> get status => _statusCtrl.stream;
  final _resultCtrl = StreamController<LocationSenderResult>.broadcast();
  Stream<LocationSenderResult> get results => _resultCtrl.stream;

  /// Iniciar envío de GPS para una asignación activa
  Future<bool> start({
    required int idAsignacion,
    Duration interval = const Duration(seconds: 12),
  }) async {
    _statusCtrl.add(LocationSenderStatus.pidiendoPermisos);

    final perm = await _requestPermission();
    if (!perm) {
      _statusCtrl.add(LocationSenderStatus.permisosDenegados);
      return false;
    }

    _idAsignacionActiva = idAsignacion;
    _statusCtrl.add(LocationSenderStatus.enviando);

    // Enviar uno inmediato
    await _sendOnce();

    // Y luego cada `interval`
    _timer = Timer.periodic(interval, (_) => _sendOnce());

    return true;
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
    _positionStream?.cancel();
    _positionStream = null;
    _idAsignacionActiva = null;
    _statusCtrl.add(LocationSenderStatus.idle);
  }

  Future<bool> _requestPermission() async {
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    if (perm == LocationPermission.deniedForever ||
        perm == LocationPermission.denied) {
      return false;
    }
    return true;
  }

  Future<void> _sendOnce() async {
    if (_idAsignacionActiva == null) return;
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 8),
      );

      final r = await _api.post('/tecnicos/me/ubicacion', body: {
        'latitud': pos.latitude,
        'longitud': pos.longitude,
        'accuracy_m': pos.accuracy,
        'velocidad_kmh': (pos.speed * 3.6),  // m/s -> km/h
        'id_asignacion': _idAsignacionActiva,
      });

      if (r.statusCode == 200) {
        final j = jsonDecode(r.body);
        final eta = j['eta'] as Map<String, dynamic>?;
        final result = LocationSenderResult(
          ok: true,
          etaMinutos: eta?['eta_minutos'] as int?,
          distanciaKm: (eta?['distancia_km'] as num?)?.toDouble(),
          llegadoAuto: j['llegado_auto'] ?? false,
        );
        _resultCtrl.add(result);

        // Si el backend marca geofence automático, parar
        if (result.llegadoAuto) {
          stop();
        }
      } else {
        _statusCtrl.add(LocationSenderStatus.error);
      }
    } catch (_) {
      // Reintentar en el siguiente tick (no hacer add de error para no saturar UI)
    }
  }

  void dispose() {
    stop();
    _statusCtrl.close();
    _resultCtrl.close();
  }
}
```

---

## Integración con la pantalla del técnico

En la pantalla de detalle de asignación del técnico (`tecnico_asignacion_detalle.dart`):

```dart
import 'package:flutter/material.dart';
import '../services/location_sender.dart';

class TecnicoAsignacionDetalle extends StatefulWidget {
  final int idAsignacion;
  const TecnicoAsignacionDetalle({super.key, required this.idAsignacion});

  @override
  State<TecnicoAsignacionDetalle> createState() => _TecnicoAsignacionDetalleState();
}

class _TecnicoAsignacionDetalleState extends State<TecnicoAsignacionDetalle> {
  final _sender = LocationSender();
  bool _enviando = false;
  int? _etaMin;
  double? _distancia;

  @override
  void initState() {
    super.initState();
    _sender.results.listen((r) {
      setState(() {
        _etaMin = r.etaMinutos;
        _distancia = r.distanciaKm;
      });
      if (r.llegadoAuto) {
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Has llegado'),
            content: const Text('Tu estado pasó a "llegado". Procede con el servicio.'),
            actions: [
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    });
  }

  Future<void> _iniciarViaje() async {
    final ok = await _sender.start(idAsignacion: widget.idAsignacion);
    if (ok) {
      setState(() => _enviando = true);
      // TODO: tambien cambiar estado a "en_camino" via PUT
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Permiso de GPS denegado. Activalo en ajustes.'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _detenerViaje() {
    _sender.stop();
    setState(() => _enviando = false);
  }

  @override
  void dispose() {
    _sender.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Asignación')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // ... info del incidente, cliente, etc.

            if (!_enviando)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: const Icon(Icons.directions_car),
                  label: const Text('Iniciar viaje'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: _iniciarViaje,
                ),
              )
            else ...[
              Container(
                padding: const EdgeInsets.all(12),
                color: Colors.green.shade50,
                child: Row(children: [
                  const Icon(Icons.gps_fixed, color: Colors.green),
                  const SizedBox(width: 8),
                  const Expanded(child: Text('Enviando ubicación cada 12s')),
                  if (_etaMin != null) Text('ETA: $_etaMin min'),
                ]),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.stop),
                  label: const Text('Pausar envío'),
                  onPressed: _detenerViaje,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

---

## Validación manual
1. Login como técnico, ir a detalle de asignación activa.
2. Tocar "Iniciar viaje" → debe pedir permisos GPS (primera vez).
3. Aceptar → banner verde "Enviando ubicación cada 12s".
4. Cada 12s aparece ETA actualizada en el banner.
5. Cliente del incidente debe ver el marker moviéndose en su tracking (M6).
6. Si caminas / muevas el emulador GPS hasta el incidente → diálogo "Has llegado" automático.

## Checklist de cierre M7
- [ ] Permisos GPS pedidos correctamente.
- [ ] Snackbar si el usuario los deniega.
- [ ] Timer de 12s funcional (configurable).
- [ ] Envía lat, lng, accuracy, velocidad, id_asignacion.
- [ ] Procesa response: ETA + flag llegado_auto.
- [ ] Diálogo "Has llegado" si geofence activa.
- [ ] Detiene timer al disponer / al llegar.
- [ ] Banner UI visible con estado.

## Notas
- **Background GPS**: este servicio solo funciona en foreground. Si el técnico bloquea pantalla, deja de enviar. Background tracking real requiere `flutter_background_service` o `workmanager` — fuera de scope.
- **Batería**: 12s con `LocationAccuracy.high` consume notable batería. Si la jornada es larga, considerar bajar a 20-30s.
- **Permisos restringidos en emulador iOS**: emular ubicación con Xcode → Debug → Simulate Location.
