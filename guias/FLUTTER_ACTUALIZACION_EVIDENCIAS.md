# 📸 ACTUALIZACIÓN FLUTTER — Agregar Evidencias (CU-06)

Esta guía actualiza la app Flutter existente para permitir que el cliente **suba fotos y audios** al incidente que acaba de reportar. Los archivos se almacenan en **Cloudinary** y la URL queda registrada en la tabla `evidencia` del backend.

---

## 🆕 Nuevos endpoints disponibles en el backend

| Método | Ruta | Descripción |
|---|---|---|
| `GET`  | `/incidencias/evidencias/tipos`          | Lista los tipos (imagen / audio / texto) |
| `POST` | `/incidencias/{id_incidente}/evidencias` | Sube archivo (multipart/form-data) |
| `GET`  | `/incidencias/{id_incidente}/evidencias` | Lista evidencias del incidente |

**Body del POST (multipart):**
- `id_tipo_evidencia` (int): `1`=imagen, `2`=audio, `3`=texto
- `archivo` (File): el archivo binario

**Response (201):**
```json
{
  "id_evidencia": 1,
  "id_incidente": 5,
  "id_tipo_evidencia": 1,
  "url_archivo": "https://res.cloudinary.com/diukc5hag/image/upload/.../foto.jpg",
  "transcripcion_audio": null,
  "descripcion_ia": null,
  "created_at": "2026-04-19T10:30:00"
}
```

---

## 📦 Paso 1 — Nuevas dependencias

### Archivo: `pubspec.yaml`

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  shared_preferences: ^2.2.0
  geolocator: ^9.0.2
  intl: ^0.19.0

  # ⬇️ NUEVAS dependencias para evidencias
  image_picker: ^1.0.7        # tomar foto con cámara o galería
  record: ^5.0.4              # grabar audio
  audioplayers: ^5.2.1        # reproducir audio grabado
  path_provider: ^2.1.2       # guardar archivos temporales
```

**Instalar:**
```bash
flutter pub get
```

---

## 🔐 Paso 2 — Permisos nuevos

### Android (`android/app/src/main/AndroidManifest.xml`)

Agregar dentro de `<manifest>`:
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
```

### iOS (`ios/Runner/Info.plist`)

Agregar dentro de `<dict>`:
```xml
<key>NSCameraUsageDescription</key>
<string>La app necesita la cámara para capturar evidencia del incidente</string>

<key>NSMicrophoneUsageDescription</key>
<string>La app necesita el micrófono para grabar descripciones de audio</string>

<key>NSPhotoLibraryUsageDescription</key>
<string>La app necesita acceso a la galería para adjuntar fotos del incidente</string>
```

---

## 🛠️ Paso 3 — Nuevo modelo `Evidencia`

### Archivo: `lib/models/evidencia.dart`

```dart
class Evidencia {
  final int idEvidencia;
  final int idIncidente;
  final int idTipoEvidencia;
  final String urlArchivo;
  final String? transcripcionAudio;
  final String? descripcionIa;
  final DateTime createdAt;

  Evidencia({
    required this.idEvidencia,
    required this.idIncidente,
    required this.idTipoEvidencia,
    required this.urlArchivo,
    this.transcripcionAudio,
    this.descripcionIa,
    required this.createdAt,
  });

  factory Evidencia.fromJson(Map<String, dynamic> json) {
    return Evidencia(
      idEvidencia: json['id_evidencia'] ?? 0,
      idIncidente: json['id_incidente'] ?? 0,
      idTipoEvidencia: json['id_tipo_evidencia'] ?? 1,
      urlArchivo: json['url_archivo'] ?? '',
      transcripcionAudio: json['transcripcion_audio'],
      descripcionIa: json['descripcion_ia'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  bool get esImagen => idTipoEvidencia == 1;
  bool get esAudio  => idTipoEvidencia == 2;
  bool get esTexto  => idTipoEvidencia == 3;

  String getTipoNombre() {
    switch (idTipoEvidencia) {
      case 1: return '📷 Imagen';
      case 2: return '🎤 Audio';
      case 3: return '📝 Texto';
      default: return 'Desconocido';
    }
  }
}
```

---

## 📡 Paso 4 — Agregar métodos al `IncidenteService`

### Archivo: `lib/services/incidente_service.dart`

**Agregar estos imports al inicio:**
```dart
import 'dart:io';
import '../models/evidencia.dart';
```

**Agregar estos métodos dentro de la clase `IncidenteService`:**

```dart
/// 📷 SUBIR EVIDENCIA (imagen / audio)
///
/// [idIncidente]      ID del incidente al que pertenece
/// [idTipoEvidencia]  1=imagen, 2=audio, 3=texto
/// [archivo]          archivo local (File)
Future<Map<String, dynamic>> subirEvidencia({
  required int idIncidente,
  required int idTipoEvidencia,
  required File archivo,
}) async {
  try {
    print('[EVIDENCIA] 📤 Subiendo archivo...');
    print('[EVIDENCIA] Incidente: $idIncidente, Tipo: $idTipoEvidencia');
    print('[EVIDENCIA] Ruta: ${archivo.path}');

    final token = await _getToken();
    if (token == null) {
      return {'success': false, 'error': 'No autenticado'};
    }

    final uri = Uri.parse('$baseUrl/incidencias/$idIncidente/evidencias');
    final request = http.MultipartRequest('POST', uri);

    request.headers['Authorization'] = 'Bearer $token';
    request.fields['id_tipo_evidencia'] = idTipoEvidencia.toString();
    request.files.add(await http.MultipartFile.fromPath('archivo', archivo.path));

    final streamed = await request.send().timeout(Duration(seconds: 60));
    final response = await http.Response.fromStream(streamed);

    print('[EVIDENCIA] Status: ${response.statusCode}');
    print('[EVIDENCIA] Body: ${response.body}');

    if (response.statusCode == 201) {
      final evidencia = Evidencia.fromJson(jsonDecode(response.body));
      print('[EVIDENCIA] ✅ Subida: #${evidencia.idEvidencia}');
      print('[EVIDENCIA] URL: ${evidencia.urlArchivo}');
      return {'success': true, 'evidencia': evidencia};
    } else if (response.statusCode == 401) {
      return {'success': false, 'error': 'Sesión expirada', 'code': 'AUTH_EXPIRED'};
    } else if (response.statusCode == 404) {
      return {'success': false, 'error': 'Incidente no encontrado'};
    }

    return {'success': false, 'error': 'Error ${response.statusCode}'};
  } on TimeoutException catch (_) {
    return {'success': false, 'error': 'Tiempo de conexión agotado (60s)'};
  } catch (e) {
    print('[EVIDENCIA] ❌ Exception: $e');
    return {'success': false, 'error': 'Error: $e'};
  }
}

/// 📋 LISTAR EVIDENCIAS DE UN INCIDENTE
Future<Map<String, dynamic>> listarEvidencias(int idIncidente) async {
  try {
    final token = await _getToken();
    if (token == null) {
      return {'success': false, 'error': 'No autenticado'};
    }

    final response = await http
        .get(
          Uri.parse('$baseUrl/incidencias/$idIncidente/evidencias'),
          headers: {'Authorization': 'Bearer $token'},
        )
        .timeout(Duration(seconds: 15));

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      final evidencias = data.map((j) => Evidencia.fromJson(j)).toList();
      return {'success': true, 'evidencias': evidencias};
    } else if (response.statusCode == 401) {
      return {'success': false, 'error': 'Sesión expirada', 'code': 'AUTH_EXPIRED'};
    }

    return {'success': false, 'error': 'Error al cargar evidencias'};
  } catch (e) {
    return {'success': false, 'error': 'Error: $e'};
  }
}
```

---

## 📱 Paso 5 — Pantalla para subir evidencias

### Archivo: `lib/screens/subir_evidencia_screen.dart`

```dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import '../services/incidente_service.dart';
import '../models/evidencia.dart';

class SubirEvidenciaScreen extends StatefulWidget {
  final int idIncidente;

  const SubirEvidenciaScreen({required this.idIncidente});

  @override
  State<SubirEvidenciaScreen> createState() => _SubirEvidenciaScreenState();
}

class _SubirEvidenciaScreenState extends State<SubirEvidenciaScreen> {
  final incidenteService = IncidenteService();
  final ImagePicker _picker = ImagePicker();
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();

  List<Evidencia> evidencias = [];
  bool cargando = true;
  bool subiendo = false;
  bool grabando = false;
  String? audioPath;

  @override
  void initState() {
    super.initState();
    _cargarEvidencias();
  }

  @override
  void dispose() {
    _recorder.dispose();
    _player.dispose();
    super.dispose();
  }

  Future<void> _cargarEvidencias() async {
    final resultado = await incidenteService.listarEvidencias(widget.idIncidente);
    if (!mounted) return;
    if (resultado['success']) {
      setState(() {
        evidencias = resultado['evidencias'];
        cargando = false;
      });
    } else {
      setState(() => cargando = false);
    }
  }

  /// 📷 Tomar foto con cámara
  Future<void> _tomarFoto() async {
    final XFile? foto = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 80,
      maxWidth: 1920,
    );
    if (foto == null) return;
    await _subir(File(foto.path), 1); // 1 = imagen
  }

  /// 🖼️ Elegir foto de la galería
  Future<void> _elegirGaleria() async {
    final XFile? foto = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 80,
    );
    if (foto == null) return;
    await _subir(File(foto.path), 1);
  }

  /// 🎤 Iniciar/Detener grabación de audio
  Future<void> _toggleGrabacion() async {
    if (grabando) {
      final path = await _recorder.stop();
      setState(() {
        grabando = false;
        audioPath = path;
      });
      if (path != null) {
        await _subir(File(path), 2); // 2 = audio
      }
    } else {
      if (await _recorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final path = '${dir.path}/evidencia_${DateTime.now().millisecondsSinceEpoch}.m4a';
        await _recorder.start(const RecordConfig(), path: path);
        setState(() => grabando = true);
      } else {
        _mostrarError('Permiso de micrófono denegado');
      }
    }
  }

  Future<void> _subir(File archivo, int tipo) async {
    setState(() => subiendo = true);

    final resultado = await incidenteService.subirEvidencia(
      idIncidente: widget.idIncidente,
      idTipoEvidencia: tipo,
      archivo: archivo,
    );

    if (!mounted) return;
    setState(() => subiendo = false);

    if (resultado['success']) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('✅ Evidencia subida'), backgroundColor: Colors.green),
      );
      _cargarEvidencias();
    } else {
      _mostrarError(resultado['error'] ?? 'Error al subir');
    }
  }

  void _mostrarError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('❌ $msg'), backgroundColor: Colors.red),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('📎 Evidencias #${widget.idIncidente}'),
        backgroundColor: Colors.red,
      ),
      body: Column(
        children: [
          // Botones de acción
          Padding(
            padding: EdgeInsets.all(12),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ElevatedButton.icon(
                  onPressed: subiendo ? null : _tomarFoto,
                  icon: Icon(Icons.camera_alt),
                  label: Text('Cámara'),
                ),
                ElevatedButton.icon(
                  onPressed: subiendo ? null : _elegirGaleria,
                  icon: Icon(Icons.photo_library),
                  label: Text('Galería'),
                ),
                ElevatedButton.icon(
                  onPressed: subiendo ? null : _toggleGrabacion,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: grabando ? Colors.red : null,
                  ),
                  icon: Icon(grabando ? Icons.stop : Icons.mic),
                  label: Text(grabando ? 'Detener' : 'Grabar audio'),
                ),
              ],
            ),
          ),

          if (subiendo)
            Padding(
              padding: EdgeInsets.all(12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  SizedBox(
                    width: 20, height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 12),
                  Text('Subiendo a Cloudinary...'),
                ],
              ),
            ),

          Divider(),

          // Lista de evidencias
          Expanded(
            child: cargando
                ? Center(child: CircularProgressIndicator())
                : evidencias.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.folder_open, size: 64, color: Colors.grey),
                            SizedBox(height: 12),
                            Text('No hay evidencias aún'),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: EdgeInsets.all(8),
                        itemCount: evidencias.length,
                        itemBuilder: (ctx, i) {
                          final e = evidencias[i];
                          return Card(
                            child: ListTile(
                              leading: e.esImagen
                                  ? ClipRRect(
                                      borderRadius: BorderRadius.circular(4),
                                      child: Image.network(
                                        e.urlArchivo,
                                        width: 56,
                                        height: 56,
                                        fit: BoxFit.cover,
                                        errorBuilder: (_, __, ___) =>
                                            Icon(Icons.broken_image),
                                      ),
                                    )
                                  : Icon(
                                      e.esAudio ? Icons.audiotrack : Icons.description,
                                      size: 40,
                                      color: Colors.red,
                                    ),
                              title: Text(e.getTipoNombre()),
                              subtitle: Text(
                                e.descripcionIa ?? 'Pendiente de análisis IA',
                                style: TextStyle(fontSize: 12),
                              ),
                              trailing: e.esAudio
                                  ? IconButton(
                                      icon: Icon(Icons.play_arrow),
                                      onPressed: () => _player.play(UrlSource(e.urlArchivo)),
                                    )
                                  : null,
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
```

---

## 🔗 Paso 6 — Integrar en el flujo existente

### Opción A — Abrir pantalla de evidencias tras reportar

En `reportar_emergencia_screen.dart`, después de un reporte exitoso:

```dart
// Antes:
Navigator.pop(context, incidente);

// Cambiar a:
Navigator.pushReplacement(
  context,
  MaterialPageRoute(
    builder: (_) => SubirEvidenciaScreen(idIncidente: incidente.idIncidente),
  ),
);
```

### Opción B — Desde la lista de historial

En `historial_emergencias_screen.dart`, al tocar una incidencia:

```dart
onTap: () {
  Navigator.push(
    context,
    MaterialPageRoute(
      builder: (_) => SubirEvidenciaScreen(idIncidente: inc.idIncidente),
    ),
  );
},
```

### Opción C — Agregar ruta nombrada en `main.dart`

```dart
routes: {
  // ... rutas existentes ...
  '/evidencias': (context) {
    final id = ModalRoute.of(context)!.settings.arguments as int;
    return SubirEvidenciaScreen(idIncidente: id);
  },
}

// Uso:
Navigator.pushNamed(context, '/evidencias', arguments: incidente.idIncidente);
```

---

## ✅ Checklist de actualización

- [ ] Agregar `image_picker`, `record`, `audioplayers`, `path_provider` a `pubspec.yaml`
- [ ] `flutter pub get`
- [ ] Agregar permisos de cámara y micrófono (Android + iOS)
- [ ] Crear `lib/models/evidencia.dart`
- [ ] Agregar métodos `subirEvidencia()` y `listarEvidencias()` en `incidente_service.dart`
- [ ] Crear `lib/screens/subir_evidencia_screen.dart`
- [ ] Enganchar la pantalla tras reportar emergencia (o desde el historial)
- [ ] Probar en dispositivo real (el emulador puede no tener cámara)

---

## 🧪 Prueba paso a paso

1. Reportar una emergencia → obtener `id_incidente` (ej. 5)
2. Ir a la pantalla de evidencias del incidente 5
3. Tocar **Cámara** → tomar foto → aparece en la lista con URL de Cloudinary
4. Tocar **Grabar audio** → hablar 5 s → **Detener** → aparece en la lista
5. Tocar ▶ para reproducir el audio
6. Verificar en Cloudinary dashboard → `Assets` → se ven los archivos en la carpeta `emergencias/incidente_5/`

---

## 🚨 Errores comunes

| Error | Solución |
|---|---|
| `Permiso denegado (cámara)` | Aceptar permisos en la primera apertura o ir a Settings |
| `Status 404` al subir | El `id_incidente` no existe o no te pertenece |
| `Status 400` | El `id_tipo_evidencia` no está en la BD — córrer `INSERT INTO tipo_evidencia...` |
| `Timeout 60s` | Conexión lenta; aumenta el timeout o revisa tu red |
| `https://res.cloudinary.com` tarda en cargar | Normal la primera vez; luego usa CDN |

---

## 📞 Prueba del endpoint en Postman

```
POST http://10.0.2.2:8000/incidencias/5/evidencias
Authorization: Bearer {token}
Body (form-data):
  id_tipo_evidencia = 1
  archivo = [seleccionar archivo]
```

**Response esperado (201):**
```json
{
  "id_evidencia": 1,
  "id_incidente": 5,
  "id_tipo_evidencia": 1,
  "url_archivo": "https://res.cloudinary.com/diukc5hag/image/upload/v.../foto.jpg",
  "transcripcion_audio": null,
  "descripcion_ia": null,
  "created_at": "2026-04-19T10:30:00"
}
```

---

**Actualización lista.** Después de esto, el backend podrá correr el módulo de IA sobre esas URLs para clasificar el incidente automáticamente. 🤖
