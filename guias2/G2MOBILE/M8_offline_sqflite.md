# M8 — Modo offline (SQLite + outbox + sincronización)

> **Backend requerido:** ninguno especial (cualquier endpoint REST).
> **Esfuerzo:** 1.5 días.

## Objetivo (del enunciado)
> "Permitir visualizar y gestionar solicitudes existentes sin conexión. Encolar solicitudes nuevas realizadas sin internet para sincronizarlas al recuperar conexión."

Componentes:
1. **SQLite local (sqflite)** — cache de entidades + outbox.
2. **connectivity_plus** — detección de cambios de conexión.
3. **Repository pattern** — lee local primero, fallback a remoto.
4. **Outbox** — cola de mutaciones pendientes.
5. **Sync automático** — al recuperar conexión.

---

## Dependencias

```yaml
dependencies:
  sqflite: ^2.3.3+1
  path: ^1.9.0
  path_provider: ^2.1.4
  connectivity_plus: ^6.0.5
  uuid: ^4.4.2
```

```bash
flutter pub get
```

---

## 1. DB local

`flutter/lib/services/offline/local_db.dart`:

```dart
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

class LocalDB {
  static Database? _db;

  static Future<Database> get instance async {
    if (_db != null) return _db!;
    final dir = await getApplicationDocumentsDirectory();
    final dbPath = join(dir.path, 'yary.db');
    _db = await openDatabase(dbPath, version: 1, onCreate: _onCreate);
    return _db!;
  }

  static Future<void> _onCreate(Database db, int v) async {
    await db.execute('''
      CREATE TABLE incidentes (
        id_incidente INTEGER PRIMARY KEY,
        client_id TEXT,
        id_categoria INTEGER,
        descripcion_usuario TEXT,
        resumen_ia TEXT,
        latitud REAL NOT NULL,
        longitud REAL NOT NULL,
        estado_nombre TEXT,
        created_at TEXT NOT NULL,
        cached_at TEXT NOT NULL
      );
    ''');

    await db.execute('''
      CREATE TABLE vehiculos (
        id_vehiculo INTEGER PRIMARY KEY,
        placa TEXT NOT NULL,
        marca TEXT,
        modelo TEXT,
        anio INTEGER,
        color TEXT,
        cached_at TEXT NOT NULL
      );
    ''');

    await db.execute('''
      CREATE TABLE outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL UNIQUE,
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        body_json TEXT,
        files_paths TEXT,
        token TEXT,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        created_at TEXT NOT NULL
      );
    ''');

    await db.execute('CREATE INDEX ix_outbox_created ON outbox(created_at);');
    await db.execute('CREATE INDEX ix_incidentes_created ON incidentes(created_at);');
  }

  static Future<void> close() async {
    await _db?.close();
    _db = null;
  }
}
```

---

## 2. OutboxService

`flutter/lib/services/offline/outbox_service.dart`:

```dart
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';

import '../../config/api_config.dart';
import 'local_db.dart';

class OutboxService {
  static final OutboxService _instance = OutboxService._();
  factory OutboxService() => _instance;
  OutboxService._();

  final _connectivity = Connectivity();
  bool _syncing = false;
  StreamSubscription? _connSub;

  final pendingCount = ValueNotifier<int>(0);

  Future<void> start() async {
    await _refreshCount();
    _connSub = _connectivity.onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online) drain();
    });
    drain();  // intento inicial
  }

  void stop() => _connSub?.cancel();

  /// Encola una mutacion. Si hay red, intenta drenar inmediatamente.
  Future<String> enqueue({
    required String method,
    required String path,
    Map<String, dynamic>? body,
    List<String>? files,
    required String token,
  }) async {
    final db = await LocalDB.instance;
    final clientId = const Uuid().v4();
    await db.insert('outbox', {
      'client_id': clientId,
      'method': method,
      'path': path,
      'body_json': body == null ? null : jsonEncode(body),
      'files_paths': files == null ? null : files.join('|'),
      'token': token,
      'attempts': 0,
      'created_at': DateTime.now().toIso8601String(),
    });
    await _refreshCount();
    unawaited(drain());
    return clientId;
  }

  Future<void> drain({int maxAttempts = 5}) async {
    if (_syncing) return;
    final conn = await _connectivity.checkConnectivity();
    if (conn.every((r) => r == ConnectivityResult.none)) return;

    _syncing = true;
    try {
      final db = await LocalDB.instance;
      final items = await db.query('outbox', orderBy: 'created_at ASC');
      for (final item in items) {
        final ok = await _send(item);
        if (ok) {
          await db.delete('outbox', where: 'id = ?', whereArgs: [item['id']]);
        } else {
          final attempts = (item['attempts'] as int) + 1;
          await db.update('outbox',
              {'attempts': attempts, 'last_error': 'http error'},
              where: 'id = ?', whereArgs: [item['id']]);
          if (attempts >= maxAttempts) {
            await db.delete('outbox', where: 'id = ?', whereArgs: [item['id']]);
          }
        }
      }
    } finally {
      _syncing = false;
      await _refreshCount();
    }
  }

  Future<bool> _send(Map<String, Object?> item) async {
    final method = item['method'] as String;
    final path = item['path'] as String;
    final token = item['token'] as String?;
    final body = item['body_json'] == null
        ? null
        : jsonDecode(item['body_json'] as String) as Map<String, dynamic>;
    final filesPaths = (item['files_paths'] as String?)?.split('|') ?? [];

    final uri = Uri.parse('${ApiConfig.apiBase}$path');
    final headers = <String, String>{
      if (token != null) 'Authorization': 'Bearer $token',
      'X-Client-Id': item['client_id'] as String,
    };

    try {
      http.Response resp;
      if (filesPaths.isNotEmpty) {
        final req = http.MultipartRequest(method, uri)..headers.addAll(headers);
        body?.forEach((k, v) => req.fields[k.toString()] = v.toString());
        for (final p in filesPaths) {
          final file = File(p);
          if (await file.exists()) {
            req.files.add(await http.MultipartFile.fromPath('archivo', p));
          }
        }
        resp = await http.Response.fromStream(await req.send());
      } else {
        headers['Content-Type'] = 'application/json';
        switch (method) {
          case 'POST':
            resp = await http.post(uri, headers: headers, body: body == null ? null : jsonEncode(body));
            break;
          case 'PUT':
            resp = await http.put(uri, headers: headers, body: body == null ? null : jsonEncode(body));
            break;
          case 'PATCH':
            resp = await http.patch(uri, headers: headers, body: body == null ? null : jsonEncode(body));
            break;
          case 'DELETE':
            resp = await http.delete(uri, headers: headers);
            break;
          default:
            return true;  // metodo no soportado: descartar
        }
      }

      // 2xx = ok, 4xx = descartar (no reintentar), 5xx = reintentar
      if (resp.statusCode >= 200 && resp.statusCode < 300) return true;
      if (resp.statusCode >= 400 && resp.statusCode < 500) return true;
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<void> _refreshCount() async {
    final db = await LocalDB.instance;
    final res = await db.rawQuery('SELECT COUNT(*) AS c FROM outbox');
    pendingCount.value = (res.first['c'] as int);
  }
}
```

---

## 3. Repository con fallback

`flutter/lib/services/offline/incidente_repository.dart`:

```dart
import 'dart:convert';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

import '../../config/api_config.dart';
import 'local_db.dart';
import 'outbox_service.dart';

class IncidenteRepository {
  static final IncidenteRepository _instance = IncidenteRepository._();
  factory IncidenteRepository() => _instance;
  IncidenteRepository._();

  Future<bool> get _online async {
    final r = await Connectivity().checkConnectivity();
    return r.any((c) => c != ConnectivityResult.none);
  }

  Future<String?> _token() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token');
  }

  /// Lista incidentes. Online -> refresca cache. Offline -> lee local.
  Future<List<Map<String, dynamic>>> listar() async {
    if (await _online) {
      try {
        final token = await _token();
        final resp = await http.get(
          Uri.parse('${ApiConfig.apiBase}/incidencias/mis-incidencias'),
          headers: {if (token != null) 'Authorization': 'Bearer $token'},
        ).timeout(const Duration(seconds: 5));
        if (resp.statusCode == 200) {
          final items = (jsonDecode(resp.body) as List).cast<Map<String, dynamic>>();
          await _cacheList(items);
          return items;
        }
      } catch (_) {/* fallback */}
    }
    return _readCached();
  }

  /// Reportar incidente. Online -> directo. Offline -> outbox + entrada local optimista.
  Future<Map<String, dynamic>> reportar({
    required Map<String, dynamic> body,
    List<String> fotos = const [],
  }) async {
    final token = await _token();

    if (await _online) {
      try {
        final resp = await http.post(
          Uri.parse('${ApiConfig.apiBase}/incidencias'),
          headers: {
            if (token != null) 'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        );
        if (resp.statusCode == 201 || resp.statusCode == 200) {
          final created = jsonDecode(resp.body) as Map<String, dynamic>;
          await _upsertOne(created);
          return created;
        }
      } catch (_) {/* fallback */}
    }

    // Encolar para sincronizar despues
    final clientId = await OutboxService().enqueue(
      method: 'POST',
      path: '/incidencias',
      body: body,
      files: fotos,
      token: token ?? '',
    );

    // Entrada optimista en local con id negativo (para distinguirlo)
    final localId = -DateTime.now().millisecondsSinceEpoch;
    final pending = <String, dynamic>{
      ...body,
      'id_incidente': localId,
      'client_id': clientId,
      'estado_nombre': 'pendiente_local',
      'created_at': DateTime.now().toIso8601String(),
    };
    await _upsertOne(pending);
    return pending;
  }

  Future<void> _cacheList(List<Map<String, dynamic>> items) async {
    final db = await LocalDB.instance;
    await db.transaction((tx) async {
      // No tocar entradas locales (id_incidente negativos)
      await tx.delete('incidentes', where: 'id_incidente > 0');
      for (final i in items) {
        await tx.insert('incidentes', _row(i),
            conflictAlgorithm: ConflictAlgorithm.replace);
      }
    });
  }

  Future<void> _upsertOne(Map<String, dynamic> i) async {
    final db = await LocalDB.instance;
    await db.insert('incidentes', _row(i),
        conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<Map<String, dynamic>>> _readCached() async {
    final db = await LocalDB.instance;
    return await db.query('incidentes', orderBy: 'created_at DESC');
  }

  Map<String, Object?> _row(Map<String, dynamic> i) => {
    'id_incidente': i['id_incidente'],
    'client_id': i['client_id'],
    'id_categoria': i['id_categoria'],
    'descripcion_usuario': i['descripcion_usuario'],
    'resumen_ia': i['resumen_ia'],
    'latitud': (i['latitud'] as num).toDouble(),
    'longitud': (i['longitud'] as num).toDouble(),
    'estado_nombre': i['estado_nombre'] ?? (i['estado']?['nombre']),
    'created_at': i['created_at'],
    'cached_at': DateTime.now().toIso8601String(),
  };
}
```

---

## 4. Banner UI

`flutter/lib/widgets/offline_banner.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import '../services/offline/outbox_service.dart';

class OfflineBanner extends StatefulWidget {
  const OfflineBanner({super.key});

  @override
  State<OfflineBanner> createState() => _OfflineBannerState();
}

class _OfflineBannerState extends State<OfflineBanner> {
  bool _online = true;
  int _pending = 0;
  StreamSubscription? _connSub;

  @override
  void initState() {
    super.initState();
    Connectivity().checkConnectivity().then(_apply);
    _connSub = Connectivity().onConnectivityChanged.listen(_apply);
    OutboxService().pendingCount.addListener(_onCount);
    _pending = OutboxService().pendingCount.value;
  }

  void _apply(List<ConnectivityResult> r) {
    setState(() => _online = r.any((c) => c != ConnectivityResult.none));
  }

  void _onCount() => setState(() => _pending = OutboxService().pendingCount.value);

  @override
  void dispose() {
    _connSub?.cancel();
    OutboxService().pendingCount.removeListener(_onCount);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_online && _pending == 0) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(8),
      color: _online ? Colors.orange : Colors.red,
      child: Text(
        _online
            ? '🔄 Sincronizando $_pending acción(es)...'
            : '⚠️ Sin conexión — $_pending pendiente(s)',
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
        textAlign: TextAlign.center,
      ),
    );
  }
}
```

---

## 5. Cableado en `main.dart`

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Inicializar outbox al arrancar la app
  await OutboxService().start();
  runApp(const MyApp());
}
```

Insertar el banner en el layout principal:

```dart
@override
Widget build(BuildContext context) {
  return MaterialApp(
    home: Scaffold(
      body: Column(
        children: [
          const OfflineBanner(),
          Expanded(child: /* router */),
        ],
      ),
    ),
  );
}
```

---

## Plan de pruebas manual

Crear archivo `flutter/OFFLINE_TEST_PLAN.md` y documentar:

1. Compilar APK debug: `flutter build apk --debug`
2. Instalar en emulador Android.
3. Login.
4. Ir a "Mis incidentes" → ver lista cacheada.
5. **Modo avión ON**.
6. Reportar incidente nuevo: pantalla muestra badge "pendiente_local".
7. DB local (con DB Inspector): tabla `outbox` tiene 1 fila.
8. **Modo avión OFF**.
9. En <10s la outbox se vacía, banner desaparece.
10. Refresh lista → el incidente aparece con id_incidente real.
11. Verificar con `curl GET /incidencias/mis-incidencias` que llegó al backend.

---

## Checklist de cierre M8
- [ ] Dependencias instaladas.
- [ ] LocalDB crea tablas en primer arranque.
- [ ] OutboxService inicializado en `main`.
- [ ] Encolado funciona offline (POST devuelve client_id).
- [ ] Sincroniza al recuperar conexión.
- [ ] 4xx descarta, 5xx reintenta hasta maxAttempts.
- [ ] Header `X-Client-Id` enviado en cada request encolado.
- [ ] OfflineBanner visible.
- [ ] Plan de pruebas documentado.

## Notas
- **Idempotencia server-side**: el backend honra `X-Client-Id` para deduplicar (ver [G2C2/F6](../G2C2/F6_offline_flutter.md#idempotencia-server-side)). Si no está implementado, un POST reenviado podría crear duplicados.
- **Background sync real**: requiere `flutter_background_service` o `workmanager` (fuera de scope).
- **Fotos**: si la app se desinstala antes de sincronizar, se pierden. Documentado como limitación.
- **DB Inspector** (Android Studio): permite ver el contenido de SQLite local mientras la app corre.
