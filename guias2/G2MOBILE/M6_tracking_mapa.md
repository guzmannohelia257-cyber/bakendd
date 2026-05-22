# M6 — Pantalla "Tracking en mapa" (cliente ve técnico en vivo)

> **Backend requerido:** [G2C2/F3](../G2C2/F3_tracking_gps.md) implementado.
> **Pre-requisito frontend:** [M4](./M4_websocket_client.md) (RealtimeService).
> **Esfuerzo:** 1 día.

## Objetivo
Cliente ve la posición del técnico moviéndose en un mapa, con ETA que se actualiza cada 12s. Cuando el técnico entra al radio de 100m (geofencing del backend), recibe alerta visual.

Eventos WS escuchados (canal `incidente:{id}`):
- `tecnico.posicion` — nueva ubicación + ETA
- `asignacion.llegado` — técnico llegó (geofencing)

---

## Dependencias

`flutter/pubspec.yaml`:
```yaml
dependencies:
  flutter_map: ^7.0.0
  latlong2: ^0.9.0
```

```bash
flutter pub get
```

---

## Pantalla

`flutter/lib/screens/tracking_screen.dart`:

```dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/realtime_service.dart';
import '../widgets/cancelar_button.dart';

class TrackingScreen extends StatefulWidget {
  final int idIncidente;
  final int idAsignacion;
  final LatLng ubicacionIncidente;
  final Map<String, dynamic>? taller;  // {id_taller, nombre, telefono}

  const TrackingScreen({
    super.key,
    required this.idIncidente,
    required this.idAsignacion,
    required this.ubicacionIncidente,
    this.taller,
  });

  @override
  State<TrackingScreen> createState() => _TrackingScreenState();
}

class _TrackingScreenState extends State<TrackingScreen> {
  final _rt = RealtimeService();
  StreamSubscription? _sub;
  final _mapCtrl = MapController();

  LatLng? _posTecnico;
  int? _etaMinutos;
  double? _distanciaKm;
  bool _llego = false;

  @override
  void initState() {
    super.initState();
    _rt.subscribe('incidente:${widget.idIncidente}');
    _sub = _rt.events.listen(_onEvent);
  }

  void _onEvent(WsEvent evt) {
    if (!mounted) return;
    final data = evt.data;
    if (data == null) return;

    if (evt.event == 'tecnico.posicion' &&
        data['id_asignacion'] == widget.idAsignacion) {
      final lat = (data['latitud'] as num?)?.toDouble();
      final lng = (data['longitud'] as num?)?.toDouble();
      final eta = data['eta'] as Map<String, dynamic>?;
      if (lat != null && lng != null) {
        setState(() {
          _posTecnico = LatLng(lat, lng);
          if (eta != null) {
            _etaMinutos = eta['eta_minutos'] as int?;
            _distanciaKm = (eta['distancia_km'] as num?)?.toDouble();
          }
        });
        _centrarMapa();
      }
    } else if (evt.event == 'asignacion.llegado' &&
        data['id_asignacion'] == widget.idAsignacion) {
      setState(() => _llego = true);
      _mostrarDialogoLlegada();
    }
  }

  void _centrarMapa() {
    if (_posTecnico == null) return;
    // Centrar entre el tecnico y el incidente
    final centroLat = (_posTecnico!.latitude + widget.ubicacionIncidente.latitude) / 2;
    final centroLng = (_posTecnico!.longitude + widget.ubicacionIncidente.longitude) / 2;
    _mapCtrl.move(LatLng(centroLat, centroLng), 14);
  }

  Future<void> _mostrarDialogoLlegada() async {
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Row(children: [
          Icon(Icons.check_circle, color: Colors.green),
          SizedBox(width: 8),
          Text('El técnico llegó'),
        ]),
        content: const Text('El técnico está a menos de 100m de tu ubicación.'),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _rt.unsubscribe('incidente:${widget.idIncidente}');
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tallerNombre = widget.taller?['nombre'] ?? 'Taller asignado';
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(tallerNombre, style: const TextStyle(fontSize: 16)),
            Text(
              _llego ? 'Llegó' : (_etaMinutos != null ? 'ETA: $_etaMinutos min' : 'En camino...'),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.normal),
            ),
          ],
        ),
      ),
      body: Stack(
        children: [
          _buildMapa(),
          if (_distanciaKm != null) _buildInfoBar(),
          if (_llego) _buildLlegoBanner(),
        ],
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(8),
        child: CancelarButton(
          idAsignacion: widget.idAsignacion,
          onCancelado: () => Navigator.popUntil(context, ModalRoute.withName('/home')),
        ),
      ),
    );
  }

  Widget _buildMapa() {
    return FlutterMap(
      mapController: _mapCtrl,
      options: MapOptions(
        initialCenter: widget.ubicacionIncidente,
        initialZoom: 14,
        interactionOptions: const InteractionOptions(
          flags: InteractiveFlag.all,
        ),
      ),
      children: [
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.yary.app',
          maxZoom: 19,
        ),
        // Línea entre técnico e incidente
        if (_posTecnico != null)
          PolylineLayer(
            polylines: [
              Polyline(
                points: [_posTecnico!, widget.ubicacionIncidente],
                strokeWidth: 3,
                color: Colors.blue.withOpacity(0.5),
                pattern: const StrokePattern.dashed(segments: [10, 5]),
              ),
            ],
          ),
        MarkerLayer(
          markers: [
            // Incidente (rojo)
            Marker(
              point: widget.ubicacionIncidente,
              width: 50,
              height: 50,
              child: const Icon(Icons.location_on, color: Colors.red, size: 50),
            ),
            // Técnico (azul, solo si tiene posición)
            if (_posTecnico != null)
              Marker(
                point: _posTecnico!,
                width: 50,
                height: 50,
                child: Container(
                  decoration: const BoxDecoration(
                    color: Colors.blue,
                    shape: BoxShape.circle,
                    boxShadow: [BoxShadow(blurRadius: 6, color: Colors.black26)],
                  ),
                  child: const Icon(Icons.directions_car, color: Colors.white, size: 28),
                ),
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildInfoBar() {
    return Positioned(
      top: 16,
      left: 16,
      right: 16,
      child: Card(
        elevation: 4,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Column(children: [
                const Icon(Icons.straighten),
                Text('${_distanciaKm!.toStringAsFixed(1)} km'),
              ]),
              Column(children: [
                const Icon(Icons.access_time),
                Text(_etaMinutos != null ? '$_etaMinutos min' : '-'),
              ]),
              if (widget.taller?['telefono'] != null)
                IconButton(
                  icon: const Icon(Icons.phone, color: Colors.green),
                  tooltip: 'Llamar al taller',
                  onPressed: () {
                    // Usar url_launcher si querés abrir el dialer
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLlegoBanner() {
    return Positioned(
      bottom: 80,
      left: 16,
      right: 16,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.green,
          borderRadius: BorderRadius.circular(8),
          boxShadow: const [BoxShadow(blurRadius: 8, color: Colors.black26)],
        ),
        child: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.white, size: 32),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'El técnico llegó al sitio',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## Ruta

```dart
'/tracking': (ctx) {
  final args = ModalRoute.of(ctx)!.settings.arguments as Map;
  return TrackingScreen(
    idIncidente: args['id_incidente'],
    idAsignacion: args['id_asignacion'],
    ubicacionIncidente: args['ubicacion_incidente'] ?? const LatLng(-16.5, -68.15),
    taller: args['taller'],
  );
},
```

> Pasar la `ubicacionIncidente` desde la pantalla anterior (la guardamos al crear el incidente).

---

## Validación manual
1. Cliente con asignación activa entra a tracking.
2. Técnico (en otro dispositivo o curl) hace `POST /tecnicos/me/ubicacion` con nuevo lat/lng cada 12s.
3. En la pantalla del cliente:
   - Aparece marker azul moviéndose.
   - InfoBar muestra distancia y ETA actualizándose.
   - Polyline dashed entre técnico e incidente.
4. Cuando técnico envía lat/lng dentro del radio 100m → backend cambia estado a "llegado" y publica `asignacion.llegado` → la pantalla muestra banner verde + dialog.

## Checklist de cierre M6
- [ ] Mapa OSM cargando.
- [ ] Marker rojo en incidente, azul en técnico.
- [ ] Polyline dashed entre ambos.
- [ ] InfoBar con distancia + ETA.
- [ ] Auto-centrar el mapa entre ambos.
- [ ] Banner verde + dialog cuando llega.
- [ ] Botón "Cancelar servicio" (de M3) en bottomNavigationBar.
- [ ] Cleanup correcto.

## Notas
- **OSM sin API key**: gratis. Para producción heavy, considerar Mapbox o MapTiler.
- **Permisos**: la pantalla SOLO consume ubicación del técnico via WS — no necesita permiso GPS del cliente (la posición del incidente ya viene del paso anterior).
- **Reload de mapa**: si el cliente cierra la pantalla y vuelve a entrar, perderá el historial de posiciones. Para mostrar trayectoria completa habría que cargar `GET /asignaciones/{id}/ubicaciones` (no implementado en C2).
