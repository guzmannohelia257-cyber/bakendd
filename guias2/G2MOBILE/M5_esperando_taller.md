# M5 — Pantalla "Esperando taller" (cliente)

> **Backend requerido:** [G2C2/F2](../G2C2/F2_broadcast_emergencia.md) implementado.
> **Pre-requisito frontend:** [M4](./M4_websocket_client.md) (RealtimeService).
> **Esfuerzo:** 0.5 día.

## Objetivo
Después de reportar un incidente, el cliente entra a esta pantalla y espera a que un taller acepte. Cuando llega el evento `incidente.asignado` por WebSocket, navega a tracking en mapa (M6).

Eventos WS escuchados (canal `usuario:{id}` auto-suscrito al login):
- `incidente.asignado` — un taller aceptó

---

## Pantalla

`flutter/lib/screens/esperando_taller_screen.dart`:

```dart
import 'dart:async';
import 'package:flutter/material.dart';
import '../services/realtime_service.dart';

class EsperandoTallerScreen extends StatefulWidget {
  final int idIncidente;
  const EsperandoTallerScreen({super.key, required this.idIncidente});

  @override
  State<EsperandoTallerScreen> createState() => _EsperandoTallerScreenState();
}

class _EsperandoTallerScreenState extends State<EsperandoTallerScreen>
    with SingleTickerProviderStateMixin {
  final _rt = RealtimeService();
  StreamSubscription? _sub;
  late AnimationController _pulseCtrl;
  Timer? _timeoutTimer;

  int _segundosEspera = 0;
  Timer? _tickTimer;
  bool _navegando = false;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _rt.subscribe('incidente:${widget.idIncidente}');
    _sub = _rt.events.listen(_onEvent);

    _tickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _segundosEspera++);
    });

    // Timeout sugerido: 3 minutos sin respuesta -> ofrecer cancelar
    _timeoutTimer = Timer(const Duration(minutes: 3), _mostrarTimeout);
  }

  void _onEvent(WsEvent evt) {
    if (_navegando) return;

    if (evt.event == 'incidente.asignado' &&
        evt.data?['id_incidente'] == widget.idIncidente) {
      _navegando = true;
      final data = evt.data!;
      Navigator.pushReplacementNamed(
        context,
        '/tracking',
        arguments: {
          'id_incidente': widget.idIncidente,
          'id_asignacion': data['id_asignacion'],
          'taller': data['taller'],
        },
      );
    }
  }

  void _mostrarTimeout() {
    if (!mounted || _navegando) return;
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sin respuesta'),
        content: const Text(
          'Han pasado 3 minutos sin que ningún taller acepte tu solicitud. '
          '¿Quieres seguir esperando o cancelar?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Seguir esperando'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () {
              Navigator.pop(context);
              Navigator.popUntil(context, ModalRoute.withName('/home'));
              // TODO: endpoint para cancelar el incidente
            },
            child: const Text('Cancelar emergencia'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _rt.unsubscribe('incidente:${widget.idIncidente}');
    _sub?.cancel();
    _pulseCtrl.dispose();
    _tickTimer?.cancel();
    _timeoutTimer?.cancel();
    super.dispose();
  }

  String _formatTime(int s) {
    final m = s ~/ 60;
    final ss = s % 60;
    return '${m.toString().padLeft(2, '0')}:${ss.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blue.shade50,
      appBar: AppBar(
        title: const Text('Buscando taller'),
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
        automaticallyImplyLeading: false,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Animación de pulso
            AnimatedBuilder(
              animation: _pulseCtrl,
              builder: (_, __) {
                return Container(
                  width: 160 + (_pulseCtrl.value * 40),
                  height: 160 + (_pulseCtrl.value * 40),
                  decoration: BoxDecoration(
                    color: Colors.blue.withOpacity(0.2 - _pulseCtrl.value * 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Container(
                      width: 140,
                      height: 140,
                      decoration: const BoxDecoration(
                        color: Colors.blue,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.search, size: 70, color: Colors.white),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: 32),
            const Text(
              'Notificando talleres cercanos...',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                'Te avisaremos en cuanto un taller acepte tu solicitud.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.black54),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              _formatTime(_segundosEspera),
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: Colors.blue.shade700,
                fontFeatures: const [FontFeature.tabularFigures()],
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
'/esperando-taller': (ctx) {
  final args = ModalRoute.of(ctx)!.settings.arguments as Map;
  return EsperandoTallerScreen(idIncidente: args['id_incidente']);
},
```

---

## Flujo completo

```
Cliente reporta -> POST /incidencias -> obtiene id_incidente
       |
       v
Navigator.pushReplacement('/esperando-taller', { id_incidente })
       |
       v
EsperandoTallerScreen suscribe a "incidente:{id}"
       |
       v
Backend hace broadcast a talleres compatibles (G2C2/F2)
       |
       v
Algún taller hace POST /incidentes/{id}/aceptar (W5)
       |
       v
Backend publica "incidente.asignado" en canal "usuario:{cliente_id}" e "incidente:{id}"
       |
       v
EsperandoTallerScreen recibe el evento -> navega a /tracking (M6)
```

---

## Validación manual
1. Cliente reporta incidente de llantas.
2. Navega a EsperandoTallerScreen → ver pulso animado + contador.
3. En otra ventana / Postman, hacer `POST /incidentes/{id}/aceptar` como taller.
4. La pantalla del cliente debe navegar automáticamente a tracking.
5. Si no aceptas nada en 3 minutos → debe aparecer diálogo de timeout.

## Checklist de cierre M5
- [ ] Animación de pulso visible.
- [ ] Contador de segundos en formato MM:SS.
- [ ] Suscripción al canal del incidente.
- [ ] Navega a `/tracking` al recibir `incidente.asignado`.
- [ ] Timeout 3 minutos con opción de cancelar.
- [ ] Cleanup correcto (unsubscribe, dispose).
- [ ] No tiene back button (`automaticallyImplyLeading: false`).
