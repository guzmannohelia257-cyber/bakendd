# M2 — Pantalla "Comparar cotizaciones" (cliente)

> **Backend requerido:** [G2C1/F2](../G2C1/F2_cotizacion.md) implementado.
> **Esfuerzo:** 1 día.

## Objetivo
Cliente solicita cotizaciones a top-3 talleres compatibles, espera respuestas, compara lado a lado, acepta una.

Endpoints consumidos:
- `POST /incidentes/{id}/cotizaciones/solicitar`
- `GET /incidentes/{id}/cotizaciones` (polling cada 8-10s hasta tener N respuestas)
- `POST /cotizaciones/{id}/aceptar`

> En el Ciclo 2 (M4 + WS) esto se reemplaza por evento push para no hacer polling. Por ahora polling es suficiente.

---

## Modelo

`flutter/lib/models/cotizacion.dart`:

```dart
class Cotizacion {
  final int idCotizacion;
  final int idIncidente;
  final int idTaller;
  final double? montoServicio;
  final double? montoRepuestos;
  final int? garantiaDias;
  final String? nota;
  final DateTime? validezHasta;
  final DateTime createdAt;
  final String estadoNombre;
  final String? tallerNombre;
  final String? tallerTelefono;

  Cotizacion({
    required this.idCotizacion,
    required this.idIncidente,
    required this.idTaller,
    this.montoServicio,
    this.montoRepuestos,
    this.garantiaDias,
    this.nota,
    this.validezHasta,
    required this.createdAt,
    required this.estadoNombre,
    this.tallerNombre,
    this.tallerTelefono,
  });

  double? get montoTotal {
    if (montoServicio == null) return null;
    return montoServicio! + (montoRepuestos ?? 0);
  }

  factory Cotizacion.fromJson(Map<String, dynamic> j) => Cotizacion(
    idCotizacion: j['id_cotizacion'],
    idIncidente: j['id_incidente'],
    idTaller: j['id_taller'],
    montoServicio: (j['monto_servicio'] as num?)?.toDouble(),
    montoRepuestos: (j['monto_repuestos'] as num?)?.toDouble(),
    garantiaDias: j['garantia_dias'],
    nota: j['nota'],
    validezHasta: j['validez_hasta'] != null ? DateTime.parse(j['validez_hasta']) : null,
    createdAt: DateTime.parse(j['created_at']),
    estadoNombre: j['estado']?['nombre'] ?? 'desconocido',
    tallerNombre: j['taller']?['nombre'],
    tallerTelefono: j['taller']?['telefono'],
  );
}
```

---

## Servicio

`flutter/lib/services/cotizacion_service.dart`:

```dart
import 'dart:convert';
import '../models/cotizacion.dart';
import 'api_client.dart';

class CotizacionService {
  final _client = ApiClient();

  Future<Map<String, dynamic>> solicitar({
    required int idIncidente,
    double radioKm = 20,
    int maxTalleres = 3,
    int validezHoras = 2,
  }) async {
    final r = await _client.post(
      '/incidentes/$idIncidente/cotizaciones/solicitar',
      body: {
        'radio_km': radioKm,
        'max_talleres': maxTalleres,
        'validez_horas': validezHoras,
      },
    );
    if (r.statusCode != 201) {
      throw jsonDecode(r.body)['detail'] ?? 'Error solicitando';
    }
    return jsonDecode(r.body);
  }

  Future<List<Cotizacion>> listar(int idIncidente) async {
    final r = await _client.get('/incidentes/$idIncidente/cotizaciones');
    if (r.statusCode != 200) throw 'Error listando';
    return (jsonDecode(r.body) as List).map((j) => Cotizacion.fromJson(j)).toList();
  }

  Future<int> aceptar(int idCotizacion) async {
    final r = await _client.post('/cotizaciones/$idCotizacion/aceptar');
    if (r.statusCode != 200) throw jsonDecode(r.body)['detail'] ?? 'Error';
    return jsonDecode(r.body)['id_asignacion'];
  }
}
```

---

## Pantalla

`flutter/lib/screens/cotizaciones_screen.dart`:

```dart
import 'dart:async';
import 'package:flutter/material.dart';
import '../models/cotizacion.dart';
import '../services/cotizacion_service.dart';

class CotizacionesScreen extends StatefulWidget {
  final int idIncidente;
  const CotizacionesScreen({super.key, required this.idIncidente});

  @override
  State<CotizacionesScreen> createState() => _CotizacionesScreenState();
}

class _CotizacionesScreenState extends State<CotizacionesScreen> {
  final _svc = CotizacionService();
  Timer? _pollTimer;
  bool _solicitando = true;
  bool _aceptando = false;
  String? _error;
  List<Cotizacion> _cotizaciones = [];
  int _invitadas = 0;

  @override
  void initState() {
    super.initState();
    _solicitarYpoll();
  }

  Future<void> _solicitarYpoll() async {
    try {
      final resp = await _svc.solicitar(idIncidente: widget.idIncidente);
      _invitadas = resp['invitadas'];
      setState(() => _solicitando = false);
      _startPolling();
    } catch (e) {
      setState(() {
        _solicitando = false;
        _error = e.toString();
      });
    }
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 8), (_) async {
      try {
        final lista = await _svc.listar(widget.idIncidente);
        setState(() => _cotizaciones = lista);
        // si todas respondieron o estoy en estado aceptada, parar
        final enviadas = lista.where((c) => c.estadoNombre == 'enviada').length;
        if (enviadas >= _invitadas) {
          _pollTimer?.cancel();
        }
      } catch (_) {}
    });
    // fetch inicial
    _svc.listar(widget.idIncidente).then((l) => setState(() => _cotizaciones = l));
  }

  Future<void> _aceptar(Cotizacion c) async {
    setState(() => _aceptando = true);
    try {
      final idAsig = await _svc.aceptar(c.idCotizacion);
      if (mounted) {
        Navigator.pushReplacementNamed(
          context, '/tracking',
          arguments: {'id_asignacion': idAsig, 'id_incidente': widget.idIncidente},
        );
      }
    } catch (e) {
      setState(() {
        _aceptando = false;
        _error = e.toString();
      });
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Comparar cotizaciones')),
      body: _build(),
    );
  }

  Widget _build() {
    if (_solicitando) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Solicitando cotizaciones a talleres...'),
          ],
        ),
      );
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(_error!, style: const TextStyle(color: Colors.red)),
        ),
      );
    }

    final enviadas = _cotizaciones.where((c) => c.estadoNombre == 'enviada').toList();
    final pendientes = _cotizaciones.where((c) => c.estadoNombre == 'pendiente').length;

    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          color: Colors.blue.shade50,
          child: Row(children: [
            Expanded(child: Text('$_invitadas talleres invitados — ${enviadas.length} respondieron, $pendientes pendientes')),
            if (pendientes > 0)
              const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
          ]),
        ),
        if (enviadas.isEmpty)
          const Expanded(
            child: Center(child: Text('Esperando respuestas...')),
          )
        else
          Expanded(
            child: ListView.builder(
              itemCount: enviadas.length,
              itemBuilder: (_, i) {
                final c = enviadas[i];
                return Card(
                  margin: const EdgeInsets.all(8),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(c.tallerNombre ?? 'Taller #${c.idTaller}',
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        _row('Servicio', '\$${c.montoServicio?.toStringAsFixed(2)}'),
                        _row('Repuestos', '\$${c.montoRepuestos?.toStringAsFixed(2)}'),
                        _row('Total', '\$${c.montoTotal?.toStringAsFixed(2)}', bold: true),
                        if (c.garantiaDias != null) _row('Garantía', '${c.garantiaDias} días'),
                        if (c.nota != null) Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(c.nota!, style: const TextStyle(fontStyle: FontStyle.italic, color: Colors.grey)),
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _aceptando ? null : () => _confirmarAceptar(c),
                            child: const Text('Aceptar este'),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
      ],
    );
  }

  Widget _row(String label, String value, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: TextStyle(fontWeight: bold ? FontWeight.bold : FontWeight.normal),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmarAceptar(Cotizacion c) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Aceptar cotización'),
        content: Text(
          '¿Confirmas aceptar la cotización de ${c.tallerNombre} por \$${c.montoTotal?.toStringAsFixed(2)}?\n\n'
          'Las otras cotizaciones quedarán rechazadas.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Aceptar')),
        ],
      ),
    );
    if (ok == true) _aceptar(c);
  }
}
```

---

## Registrar ruta

`main.dart`:
```dart
'/cotizaciones': (ctx) {
  final args = ModalRoute.of(ctx)!.settings.arguments as Map;
  return CotizacionesScreen(idIncidente: args['id_incidente']);
},
```

---

## Validación manual
1. Crear incidente de chapería (categoría con `requiere_cotizacion=true`).
2. Navegar a `CotizacionesScreen`.
3. Ver "Solicitando..." → "3 talleres invitados, 0 respondieron".
4. Desde otra ventana, simular 2 respuestas con `POST /cotizaciones/{id}/responder`.
5. En ~10s la pantalla muestra las 2 tarjetas con precios.
6. Aceptar la más barata.
7. Confirmar modal → navega a tracking.

## Checklist de cierre M2
- [ ] Modelo Cotizacion con `montoTotal` derivado.
- [ ] Polling cada 8s mientras hay pendientes.
- [ ] Cancelar polling al destruir la pantalla.
- [ ] Tarjetas con: total, garantía, nota.
- [ ] Modal de confirmación antes de aceptar.
- [ ] Navegación a `/tracking` con `id_asignacion` recibido.
- [ ] Manejo de error visible.
