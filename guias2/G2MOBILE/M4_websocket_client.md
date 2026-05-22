# M4 — RealtimeService (cliente WebSocket Flutter)

> **Backend requerido:** [G2C2/F1](../G2C2/F1_redis_websocket_infra.md) implementado.
> **Bloquea:** M5 (esperando taller), M6 (tracking).
> **Esfuerzo:** 0.5 día.

## Objetivo
Servicio singleton que mantiene una conexión WS persistente, reconecta automáticamente, expone eventos como `Stream`.

---

## Dependencias

`flutter/pubspec.yaml`:
```yaml
dependencies:
  web_socket_channel: ^3.0.0
```

```bash
flutter pub get
```

---

## Código

`flutter/lib/services/realtime_service.dart`:

```dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

import '../config/api_config.dart';

enum WsState { disconnected, connecting, connected, reconnecting }

class WsEvent {
  final String event;
  final Map<String, dynamic>? data;
  final String? channel;
  final String? detail;
  WsEvent({required this.event, this.data, this.channel, this.detail});

  factory WsEvent.fromJson(Map<String, dynamic> j) => WsEvent(
    event: j['event'] as String? ?? 'unknown',
    data: j['data'] as Map<String, dynamic>?,
    channel: j['channel'] as String?,
    detail: j['detail'] as String?,
  );
}

class RealtimeService {
  static final RealtimeService _instance = RealtimeService._();
  factory RealtimeService() => _instance;
  RealtimeService._();

  WebSocketChannel? _channel;
  String? _token;
  int _attempts = 0;
  Timer? _reconnectTimer;
  bool _disposed = false;

  final Set<String> _subscribed = {};

  final _eventsCtrl = StreamController<WsEvent>.broadcast();
  Stream<WsEvent> get events => _eventsCtrl.stream;

  final _stateCtrl = StreamController<WsState>.broadcast();
  Stream<WsState> get state => _stateCtrl.stream;
  WsState _state = WsState.disconnected;
  WsState get currentState => _state;

  void connect(String token) {
    _token = token;
    _disposed = false;
    _connect();
  }

  void disconnect() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close(ws_status.goingAway);
    _channel = null;
    _subscribed.clear();
    _updateState(WsState.disconnected);
  }

  void subscribe(String channel) {
    _subscribed.add(channel);
    _send({'action': 'subscribe', 'channel': channel});
  }

  void unsubscribe(String channel) {
    _subscribed.remove(channel);
    _send({'action': 'unsubscribe', 'channel': channel});
  }

  void ping() {
    _send({'action': 'ping'});
  }

  // ---- privados ----

  void _connect() {
    if (_token == null || _disposed) return;

    _updateState(_attempts == 0 ? WsState.connecting : WsState.reconnecting);

    final url = Uri.parse(
      '${ApiConfig.wsBase}/ws?token=${Uri.encodeComponent(_token!)}',
    );

    try {
      _channel = WebSocketChannel.connect(url);
    } catch (e) {
      _scheduleReconnect();
      return;
    }

    _channel!.stream.listen(
      _onMessage,
      onError: (_) => _onClosed(null),
      onDone: () => _onClosed(_channel?.closeCode),
      cancelOnError: false,
    );

    // Re-suscribir tras (re)conectar — esperar un tick para handshake
    Future.delayed(const Duration(milliseconds: 200), () {
      if (_state == WsState.connected || _channel != null) {
        for (final ch in _subscribed) {
          _send({'action': 'subscribe', 'channel': ch});
        }
      }
    });
  }

  void _onMessage(dynamic raw) {
    try {
      final msg = jsonDecode(raw as String) as Map<String, dynamic>;
      final evt = WsEvent.fromJson(msg);
      if (evt.event == 'connected') {
        _attempts = 0;
        _updateState(WsState.connected);
      }
      _eventsCtrl.add(evt);
    } catch (_) {}
  }

  void _onClosed(int? code) {
    _channel = null;
    _updateState(WsState.disconnected);
    if (_disposed) return;
    if (code == 1008) {
      // Auth fallo: no reintentar
      return;
    }
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    final delay = Duration(seconds: (1 << _attempts).clamp(1, 30));
    _attempts++;
    _updateState(WsState.reconnecting);
    _reconnectTimer = Timer(delay, _connect);
  }

  void _send(Object payload) {
    if (_channel != null) {
      _channel!.sink.add(jsonEncode(payload));
    }
  }

  void _updateState(WsState s) {
    _state = s;
    if (!_stateCtrl.isClosed) _stateCtrl.add(s);
  }

  void dispose() {
    disconnect();
    _eventsCtrl.close();
    _stateCtrl.close();
  }
}
```

---

## Cómo se conecta

### Tras login exitoso

```dart
// auth_service.dart
import '../services/realtime_service.dart';

Future<void> afterLogin(String token) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('token', token);
  RealtimeService().connect(token);
}

Future<void> logout() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove('token');
  RealtimeService().disconnect();
}
```

### Al arrancar la app (si ya hay token guardado)

`main.dart`:
```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final token = prefs.getString('token');
  if (token != null) {
    RealtimeService().connect(token);
  }
  runApp(const MyApp());
}
```

---

## Uso en una pantalla

```dart
class MiPantalla extends StatefulWidget {...}

class _MiPantallaState extends State<MiPantalla> {
  final _rt = RealtimeService();
  StreamSubscription? _sub;

  @override
  void initState() {
    super.initState();
    _rt.subscribe('incidente:42');
    _sub = _rt.events.listen((evt) {
      if (evt.event == 'incidente.asignado' && evt.channel == 'incidente:42') {
        setState(() => /* actualizar UI */);
      }
    });
  }

  @override
  void dispose() {
    _rt.unsubscribe('incidente:42');
    _sub?.cancel();
    super.dispose();
  }
}
```

---

## Connection badge (opcional)

`flutter/lib/widgets/connection_badge.dart`:

```dart
import 'package:flutter/material.dart';
import '../services/realtime_service.dart';

class ConnectionBadge extends StatelessWidget {
  const ConnectionBadge({super.key});

  @override
  Widget build(BuildContext context) {
    final rt = RealtimeService();
    return StreamBuilder<WsState>(
      stream: rt.state,
      initialData: rt.currentState,
      builder: (_, snap) {
        final s = snap.data ?? WsState.disconnected;
        final (color, label) = switch (s) {
          WsState.connected => (Colors.green, 'En vivo'),
          WsState.connecting => (Colors.orange, 'Conectando…'),
          WsState.reconnecting => (Colors.orange, 'Reconectando…'),
          WsState.disconnected => (Colors.grey, 'Sin conexión'),
        };
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 11)),
        );
      },
    );
  }
}
```

Insertar en AppBar:
```dart
AppBar(
  title: const Text('Yary'),
  actions: const [ConnectionBadge(), SizedBox(width: 8)],
)
```

---

## Validación manual
1. Backend WS levantado.
2. Login → DevTools del emulador → ver conexión WS.
3. Apagar backend → badge cambia a "Reconectando".
4. Encender → vuelve a "En vivo".
5. `pubsub_broker.publish("usuario:N", {...})` desde backend → el evento llega al `events`.

## Checklist de cierre M4
- [ ] Singleton (un solo `RealtimeService` por app).
- [ ] Conecta tras login y al iniciar app si hay token.
- [ ] Reconexión exponencial 1s → 30s max.
- [ ] No reintenta si closeCode = 1008.
- [ ] Re-suscribe automáticamente a canales tras reconectar.
- [ ] `events` y `state` como Streams broadcast.
- [ ] ConnectionBadge visible en AppBar.
