# Guía de Actualización Flutter — Módulo de IA (Clasificación Automática)

Versión: 1.0
Fecha: 2026-04-20
Backend asociado: Yary Backend v1.0 con servicio Gemini

---

## 1. ¿Qué añade esta actualización?

Un **nuevo endpoint en el backend** que, a partir de:
- La **descripción** que escribió el usuario al reportar el incidente
- Las **imágenes** subidas como evidencia (ya están en Cloudinary)
- (Opcional) Las **transcripciones de audio** si existen

...llama a **Google Gemini 3 Flash (multimodal)** y rellena automáticamente en la BD:

| Campo del incidente | Qué recibe |
|---|---|
| `id_categoria` | ID de la categoría detectada (choque, falla mecánica, etc.) |
| `id_prioridad` | ID del nivel de urgencia (baja / media / alta / crítica) |
| `resumen_ia` | Texto breve técnico del problema |
| `clasificacion_ia_confianza` | Valor 0.0 a 1.0 |
| `requiere_revision_manual` | `true` si la confianza es < 0.6 |

La app Flutter solo necesita **1 endpoint nuevo** y **mostrar los campos nuevos** en la pantalla de detalle.

---

## 2. Nuevo endpoint backend

### `POST /incidencias/{id_incidente}/analizar-ia`

**Autenticación:** Bearer token (JWT) — el incidente debe pertenecer al usuario autenticado.

**Parámetros:**
- `id_incidente` (path): ID del incidente a analizar

**Body:** vacío (no envía nada)

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Respuesta 200 OK** — devuelve el incidente **completo actualizado**:

```json
{
  "id_incidente": 12,
  "id_usuario": 3,
  "id_vehiculo": 5,
  "id_estado": 1,
  "id_categoria": 2,
  "id_prioridad": 3,
  "latitud": -12.046374,
  "longitud": -77.042793,
  "descripcion_usuario": "Mi auto tiene humo saliendo del motor",
  "resumen_ia": "Vehículo con posible sobrecalentamiento del motor, humo blanco visible en el cofre. Requiere asistencia inmediata para evitar daño mayor.",
  "clasificacion_ia_confianza": 0.87,
  "requiere_revision_manual": false,
  "created_at": "2026-04-20T15:30:00Z",
  "updated_at": "2026-04-20T15:32:10Z",
  "estado": { "id_estado": 1, "nombre": "pendiente" },
  "categoria": { "id_categoria": 2, "nombre": "Falla Mecánica" },
  "prioridad": { "id_prioridad": 3, "nivel": "alta", "orden": 3 }
}
```

**Errores posibles:**

| Código | Significado |
|---|---|
| 401 | Token inválido o expirado |
| 404 | El incidente no existe o no te pertenece |
| 502 | Error del servicio de IA (Gemini caído o cuota agotada) |

**Tiempo de respuesta:** 3–8 segundos (depende del número de imágenes).

---

## 3. Requisitos previos

Antes de llamar a `analizar-ia` el incidente **debe tener**:
1. ✅ Creado (ya existe con `id_incidente`)
2. ✅ Al menos **1 foto** subida como evidencia (si no, Gemini solo analiza texto y la confianza baja)
3. ✅ Descripción del usuario llenada

Si no hay evidencias, el backend igual funciona pero el resumen será menos preciso.

---

## 4. Cambios en Flutter

### 4.1 — Actualizar el modelo `Incidente`

**Archivo:** `lib/models/incidente.dart`

Añade los campos que hasta ahora no se estaban capturando:

```dart
class Incidente {
  final int idIncidente;
  final int idUsuario;
  final int idVehiculo;
  final int idEstado;
  final int? idCategoria;              // ← NUEVO (lo llena la IA)
  final int? idPrioridad;              // ← NUEVO (lo llena la IA)
  final double latitud;
  final double longitud;
  final String? descripcionUsuario;
  final String? resumenIa;              // ← NUEVO
  final double? clasificacionIaConfianza; // ← NUEVO
  final bool requiereRevisionManual;    // ← NUEVO
  final DateTime createdAt;
  final DateTime? updatedAt;

  // Objetos anidados (ya los recibes)
  final Map<String, dynamic>? estado;
  final Map<String, dynamic>? categoria;
  final Map<String, dynamic>? prioridad;

  Incidente({
    required this.idIncidente,
    required this.idUsuario,
    required this.idVehiculo,
    required this.idEstado,
    this.idCategoria,
    this.idPrioridad,
    required this.latitud,
    required this.longitud,
    this.descripcionUsuario,
    this.resumenIa,
    this.clasificacionIaConfianza,
    this.requiereRevisionManual = false,
    required this.createdAt,
    this.updatedAt,
    this.estado,
    this.categoria,
    this.prioridad,
  });

  factory Incidente.fromJson(Map<String, dynamic> json) {
    return Incidente(
      idIncidente: json['id_incidente'],
      idUsuario: json['id_usuario'],
      idVehiculo: json['id_vehiculo'],
      idEstado: json['estado']?['id_estado'] ?? json['id_estado'] ?? 1,
      idCategoria: json['id_categoria'],
      idPrioridad: json['id_prioridad'],
      latitud: (json['latitud'] as num).toDouble(),
      longitud: (json['longitud'] as num).toDouble(),
      descripcionUsuario: json['descripcion_usuario'],
      resumenIa: json['resumen_ia'],
      clasificacionIaConfianza:
          (json['clasificacion_ia_confianza'] as num?)?.toDouble(),
      requiereRevisionManual: json['requiere_revision_manual'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      estado: json['estado'] as Map<String, dynamic>?,
      categoria: json['categoria'] as Map<String, dynamic>?,
      prioridad: json['prioridad'] as Map<String, dynamic>?,
    );
  }
}
```

> **Nota:** Si tu modelo actual ya tiene algunos de estos campos, solo añade los marcados "NUEVO".

---

### 4.2 — Añadir método en `IncidenteService`

**Archivo:** `lib/services/incidente_service.dart`

Añade este método al servicio que ya tienes:

```dart
/// Llama al backend para analizar el incidente con IA (Gemini).
/// Retorna el incidente actualizado con categoría, prioridad y resumen llenos.
///
/// Requisitos previos: el incidente debe tener al menos 1 foto subida
/// como evidencia, de lo contrario la confianza será baja.
///
/// Tiempo de respuesta típico: 3–8 segundos.
Future<Incidente> analizarConIA(int idIncidente) async {
  final token = await AuthService.getToken();

  final response = await http.post(
    Uri.parse('$baseUrl/incidencias/$idIncidente/analizar-ia'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(utf8.decode(response.bodyBytes));
    return Incidente.fromJson(data);
  } else if (response.statusCode == 401) {
    throw Exception('Sesión expirada. Inicia sesión de nuevo.');
  } else if (response.statusCode == 404) {
    throw Exception('El incidente no existe o no te pertenece.');
  } else if (response.statusCode == 502) {
    throw Exception(
      'El servicio de IA está temporalmente no disponible. Intenta más tarde.',
    );
  } else {
    throw Exception('Error al analizar: ${response.body}');
  }
}
```

> **Importante:** no pongas `timeout` muy bajo — Gemini puede tardar hasta 10s. Si usas `http.post().timeout(...)`, ponle mínimo **30 segundos**.

---

### 4.3 — Integración en la UI (3 opciones, elige una)

#### Opción A (recomendada) — Botón "Analizar con IA" en la pantalla de detalle

En tu `DetalleIncidenteScreen` (o como se llame) añade este botón cuando el incidente **no** tenga aún categoría asignada:

```dart
if (incidente.idCategoria == null) ...[
  const SizedBox(height: 16),
  ElevatedButton.icon(
    icon: const Icon(Icons.auto_awesome),
    label: const Text('Analizar con IA'),
    style: ElevatedButton.styleFrom(
      backgroundColor: Colors.deepPurple,
      foregroundColor: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 14),
    ),
    onPressed: () => _analizarConIA(context),
  ),
]
```

Y el método:

```dart
Future<void> _analizarConIA(BuildContext context) async {
  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (_) => const AlertDialog(
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Analizando evidencias con IA...'),
          SizedBox(height: 8),
          Text(
            'Puede tardar unos segundos',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ],
      ),
    ),
  );

  try {
    final actualizado = await IncidenteService()
        .analizarConIA(widget.incidente.idIncidente);

    if (!context.mounted) return;
    Navigator.pop(context); // cerrar loading

    setState(() {
      widget.incidente = actualizado;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Análisis completado ✨'),
        backgroundColor: Colors.green,
      ),
    );
  } catch (e) {
    if (!context.mounted) return;
    Navigator.pop(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(e.toString().replaceAll('Exception: ', '')),
        backgroundColor: Colors.red,
      ),
    );
  }
}
```

#### Opción B — Disparo automático después de subir la última evidencia

En tu `SubirEvidenciaScreen`, al terminar de subir la primera foto (o después de un botón "Terminar"):

```dart
ElevatedButton.icon(
  icon: const Icon(Icons.check),
  label: const Text('Terminar y analizar'),
  onPressed: () async {
    // Disparar análisis IA en background
    IncidenteService()
        .analizarConIA(widget.idIncidente)
        .catchError((e) => debugPrint('IA falló: $e'));

    // Volver a home
    Navigator.pushReplacementNamed(context, '/home');
  },
)
```

> Esta opción es **no bloqueante** — si la IA falla, el usuario no se entera (puede volver al detalle después para ver el resultado).

#### Opción C — Ruta dedicada con nombre (si usas Navigator 2.0)

```dart
// en routes
'/incidente/analizar': (ctx) => AnalizarIAScreen(
  idIncidente: ModalRoute.of(ctx)!.settings.arguments as int,
),
```

---

### 4.4 — Mostrar los resultados en el detalle

En la pantalla de detalle del incidente, añade una sección que se vea **solo si ya hay análisis IA**:

```dart
if (incidente.resumenIa != null) ...[
  const Divider(height: 32),
  Row(
    children: [
      const Icon(Icons.auto_awesome, color: Colors.deepPurple, size: 20),
      const SizedBox(width: 8),
      const Text(
        'Análisis de IA',
        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
      ),
      const Spacer(),
      if (incidente.clasificacionIaConfianza != null)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: _colorConfianza(incidente.clasificacionIaConfianza!),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            '${(incidente.clasificacionIaConfianza! * 100).toStringAsFixed(0)}% confianza',
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
        ),
    ],
  ),
  const SizedBox(height: 12),
  Container(
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: Colors.deepPurple.shade50,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: Colors.deepPurple.shade200),
    ),
    child: Text(
      incidente.resumenIa!,
      style: const TextStyle(fontSize: 14, height: 1.5),
    ),
  ),
  if (incidente.categoria != null) ...[
    const SizedBox(height: 8),
    Row(
      children: [
        const Icon(Icons.category, size: 16, color: Colors.grey),
        const SizedBox(width: 6),
        Text('Categoría: ${incidente.categoria!['nombre']}'),
      ],
    ),
  ],
  if (incidente.prioridad != null) ...[
    const SizedBox(height: 4),
    Row(
      children: [
        const Icon(Icons.priority_high, size: 16, color: Colors.grey),
        const SizedBox(width: 6),
        Text('Prioridad: ${incidente.prioridad!['nivel']}'),
      ],
    ),
  ],
  if (incidente.requiereRevisionManual) ...[
    const SizedBox(height: 12),
    Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.orange.shade100,
        borderRadius: BorderRadius.circular(6),
      ),
      child: const Row(
        children: [
          Icon(Icons.warning_amber, color: Colors.orange),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Baja confianza — un operador revisará manualmente.',
              style: TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    ),
  ],
],
```

Y el helper de color:

```dart
Color _colorConfianza(double c) {
  if (c >= 0.8) return Colors.green;
  if (c >= 0.6) return Colors.orange;
  return Colors.red;
}
```

---

## 5. Checklist de implementación

- [ ] Modelo `Incidente` tiene los 5 campos nuevos (`idCategoria`, `idPrioridad`, `resumenIa`, `clasificacionIaConfianza`, `requiereRevisionManual`)
- [ ] `Incidente.fromJson` parsea correctamente los campos nuevos
- [ ] `IncidenteService.analizarConIA()` agregado
- [ ] Timeout del http.post es ≥ 30 segundos
- [ ] Pantalla de detalle muestra sección de IA solo cuando `resumenIa != null`
- [ ] Botón "Analizar con IA" aparece solo cuando `idCategoria == null`
- [ ] Loading dialog bloqueante durante la llamada
- [ ] Manejo de errores 401 / 404 / 502 con mensajes claros
- [ ] Probado con incidente **con** fotos → confianza alta
- [ ] Probado con incidente **sin** fotos → confianza baja (requiere revisión manual)

---

## 6. Procedimiento de prueba end-to-end

1. **Login** con un usuario de prueba
2. **Crear vehículo** (si no tienes uno)
3. **Reportar incidente**:
   - Descripción: `"Mi auto tiene humo blanco saliendo del motor"`
   - Lat/Lng: cualquiera
4. **Subir 1–2 fotos** como evidencia (usa fotos reales de motor, accidente, etc.)
5. **Ir al detalle del incidente** → debería mostrar botón "Analizar con IA"
6. **Presionar el botón** → esperar 3–8 segundos
7. **Verificar que aparezca**:
   - Categoría detectada (ej: "Falla Mecánica")
   - Prioridad (ej: "Alta")
   - Resumen técnico en español
   - Badge de % de confianza
8. **Hacer pull-to-refresh** o reingresar a la pantalla → los datos persisten (ya están en BD)

### Casos de prueba

| Escenario | Qué esperar |
|---|---|
| Foto de motor humeando + descripción | Categoría mecánica, prioridad alta, confianza > 80% |
| Foto de parachoques chocado | Categoría accidente, prioridad alta/crítica |
| Foto borrosa o no relacionada | Confianza < 60%, `requiereRevisionManual = true` |
| Sin fotos, solo descripción | Funciona pero confianza más baja |
| Llamar 2 veces seguidas | Funciona — sobrescribe resultado anterior |

---

## 7. Errores comunes y soluciones

| Error Flutter | Causa probable | Solución |
|---|---|---|
| `SocketException` / timeout | Backend tarda >30s | Aumenta timeout a 60s |
| 401 Unauthorized | Token expirado | Forzar re-login |
| 404 Not Found | URL mal construida | Verifica que el `id_incidente` sea válido |
| 502 Bad Gateway | Gemini agotó cuota diaria | Espera 24h o pide al equipo backend cambiar de modelo |
| Response 200 pero `idCategoria == null` | Error en `fromJson` | Revisa el parseo del JSON |
| Descripción IA en otro idioma | — | El backend fuerza español, no debería pasar |

---

## 8. Ejemplo de prueba con Postman

```
POST http://localhost:8000/incidencias/12/analizar-ia
Authorization: Bearer eyJhbGc...
Content-Type: application/json

(body vacío)
```

Respuesta esperada (200 OK):

```json
{
  "id_incidente": 12,
  "id_categoria": 2,
  "id_prioridad": 3,
  "resumen_ia": "Vehículo con humo blanco del motor, posible sobrecalentamiento...",
  "clasificacion_ia_confianza": 0.87,
  "requiere_revision_manual": false,
  "categoria": { "id_categoria": 2, "nombre": "Falla Mecánica" },
  "prioridad": { "id_prioridad": 3, "nivel": "alta", "orden": 3 },
  ...
}
```

---

## 9. Notas sobre el modelo de IA

- **Proveedor:** Google Gemini (API gratuita, free tier)
- **Modelo:** `gemini-3-flash-preview` (multimodal, familia Gemini 3)
- **Límites free tier:** 10 requests/min, 250 requests/día, 250k tokens/día
- **Idioma de respuesta:** Español (forzado en el prompt del sistema)
- **Privacidad:** las imágenes se envían desde Cloudinary (URL pública) al backend, que las reenvía a Gemini. No se almacenan en Google según su política de la API gratuita con "opt-out" activo.

Si en el futuro se migra a **AWS Bedrock** (Nova Pro o Claude) el endpoint Flutter **no cambia** — solo cambia el servicio interno del backend.

---

## 10. Resumen ultrarrápido

| Archivo Flutter | Qué hacer |
|---|---|
| `lib/models/incidente.dart` | Añadir 5 campos nuevos + actualizar `fromJson` |
| `lib/services/incidente_service.dart` | Añadir método `analizarConIA(int)` |
| `lib/screens/detalle_incidente_screen.dart` | Botón "Analizar con IA" + sección de resultados |

Total: **~70 líneas de Dart** distribuidas en 3 archivos. Sin dependencias nuevas.
