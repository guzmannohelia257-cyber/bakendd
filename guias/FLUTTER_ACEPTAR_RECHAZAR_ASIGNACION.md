# Guía Flutter — Aceptar / Rechazar Asignaciones (Taller ↔ Cliente)

> **Contexto:** El motor de asignación ya asigna automáticamente un taller al incidente.
> Ahora el **taller** debe poder **aceptar** o **rechazar** esa asignación,
> y el **cliente** debe poder **ver el estado** de su solicitud en tiempo real.

---

## 0. Resumen del flujo completo

```
CLIENTE                                      TALLER
-------                                      ------
1. Reporta incidente (POST /incidencias)
2. Sube evidencias (fotos/audios)
3. Presiona "Analizar con IA"
   → IA clasifica
   → Motor asigna al mejor taller        ←── Llega solicitud "pendiente"
4. Ve "⏳ Esperando al taller..."
                                             5. Abre lista de solicitudes
                                             6. Ve detalle (cliente, descripción, ubicación)
                                             7. Acepta → pone ETA  ó  Rechaza → pone motivo
8. Refresca pantalla
9. Ve "✅ Taller X aceptó (ETA: 20 min)"
   ó "❌ Rechazada: motivo. Elige otro"
10. Si rechazado → usa /cambiar-taller
    con otro candidato
```

---

## 1. Endpoints nuevos del backend

### 1.1 Lado TALLER (autenticado como taller con `POST /talleres/login`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/talleres/mi-taller/asignaciones` | Listar todas las asignaciones del taller |
| GET | `/talleres/mi-taller/asignaciones?estado=pendiente` | Filtrar por estado |
| GET | `/talleres/mi-taller/asignaciones/{id_asignacion}` | Detalle de una asignación |
| PUT | `/talleres/mi-taller/asignaciones/{id}/aceptar` | Aceptar |
| PUT | `/talleres/mi-taller/asignaciones/{id}/rechazar` | Rechazar |

**Estados válidos para filtrar:** `pendiente | aceptada | rechazada | en_camino | completada`

### 1.2 Lado CLIENTE (ya existían, solo cambia la respuesta)

| Método | Endpoint | Cambio |
|---|---|---|
| GET | `/incidencias/{id}` | Ahora incluye `asignaciones[]` |
| POST | `/incidencias/{id}/analizar-ia` | Ahora incluye `asignaciones[]` |
| PUT | `/incidencias/{id}/cambiar-taller` | Ya existe — usar cuando el taller rechace |

---

## 2. Contratos de los endpoints

### 2.1 Listar asignaciones del taller

**Request:**
```http
GET /talleres/mi-taller/asignaciones?estado=pendiente
Authorization: Bearer <token_taller>
```

**Response 200:**
```json
[
  {
    "id_asignacion": 12,
    "id_incidente": 8,
    "id_taller": 5,
    "id_tecnico": null,
    "id_estado_asignacion": 1,
    "eta_minutos": null,
    "nota_taller": null,
    "created_at": "2026-04-21T01:42:11.123Z",
    "updated_at": "2026-04-21T01:42:11.123Z",
    "estado": {
      "id_estado_asignacion": 1,
      "nombre": "pendiente"
    },
    "incidente": {
      "id_incidente": 8,
      "descripcion_usuario": "Se me pinchó la llanta en la autopista",
      "resumen_ia": "Llanta pinchada en autopista, cliente solo de noche",
      "latitud": -17.8454274,
      "longitud": -63.1561987,
      "created_at": "2026-04-21T01:41:55.000Z",
      "usuario": {
        "id_usuario": 3,
        "nombre": "Juan Pérez",
        "telefono": "+59170000001"
      },
      "vehiculo": {
        "id_vehiculo": 2,
        "placa": "3456ABC",
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2018,
        "color": "Blanco"
      },
      "categoria": { "id_categoria": 2, "nombre": "Falla de llanta" },
      "prioridad": { "id_prioridad": 3, "nivel": "alta", "orden": 3 }
    }
  }
]
```

### 2.2 Aceptar asignación

**Request:**
```http
PUT /talleres/mi-taller/asignaciones/12/aceptar
Authorization: Bearer <token_taller>
Content-Type: application/json

{
  "eta_minutos": 20,
  "nota": "Vamos en camino, llevamos llanta 17\""
}
```

**Response 200:** Mismo schema `AsignacionTallerResponse` con `estado.nombre = "aceptada"` y `eta_minutos = 20`.

**Response 400:** Si ya fue aceptada/rechazada antes:
```json
{ "detail": "La asignación ya está en estado 'aceptada', no se puede aceptar" }
```

### 2.3 Rechazar asignación

**Request:**
```http
PUT /talleres/mi-taller/asignaciones/12/rechazar
Authorization: Bearer <token_taller>
Content-Type: application/json

{
  "motivo": "Sin stock de llanta 17 pulgadas"
}
```

**Response 200:** Mismo schema con `estado.nombre = "rechazada"` y `nota_taller = motivo`.

### 2.4 Cliente ve la asignación (incluida en `GET /incidencias/{id}`)

**Response 200 (extracto):**
```json
{
  "id_incidente": 8,
  "descripcion_usuario": "...",
  "resumen_ia": "...",
  "candidatos": [ ... ],
  "asignaciones": [
    {
      "id_asignacion": 12,
      "id_taller": 5,
      "id_estado_asignacion": 2,
      "eta_minutos": 20,
      "nota_taller": "Vamos en camino, llevamos llanta 17\"",
      "created_at": "...",
      "updated_at": "...",
      "taller": {
        "id_taller": 5,
        "nombre": "Mecánica Central SC",
        "direccion": "Av. Cristo Redentor #123",
        "telefono": "+59170000001"
      },
      "estado": {
        "id_estado_asignacion": 2,
        "nombre": "aceptada"
      }
    }
  ]
}
```

> Puede haber más de una asignación en el historial (si el cliente cambió de taller).
> **Usa siempre `asignaciones[0]` o ordena por `created_at` descendente** — la más reciente es la activa.

---

## 3. Implementación en Flutter

### 3.1 Modelos Dart nuevos

Crear `lib/models/asignacion.dart`:

```dart
class EstadoAsignacion {
  final int idEstadoAsignacion;
  final String nombre; // pendiente | aceptada | rechazada | en_camino | completada

  EstadoAsignacion({required this.idEstadoAsignacion, required this.nombre});

  factory EstadoAsignacion.fromJson(Map<String, dynamic> json) {
    return EstadoAsignacion(
      idEstadoAsignacion: json['id_estado_asignacion'],
      nombre: json['nombre'],
    );
  }
}

class TallerAsignado {
  final int idTaller;
  final String nombre;
  final String? direccion;
  final String? telefono;

  TallerAsignado({
    required this.idTaller,
    required this.nombre,
    this.direccion,
    this.telefono,
  });

  factory TallerAsignado.fromJson(Map<String, dynamic> json) {
    return TallerAsignado(
      idTaller: json['id_taller'],
      nombre: json['nombre'],
      direccion: json['direccion'],
      telefono: json['telefono'],
    );
  }
}

class Asignacion {
  final int idAsignacion;
  final int idIncidente;
  final int idTaller;
  final int? idTecnico;
  final int idEstadoAsignacion;
  final int? etaMinutos;
  final String? notaTaller;
  final DateTime createdAt;
  final DateTime updatedAt;

  final TallerAsignado taller;
  final EstadoAsignacion estado;

  Asignacion({
    required this.idAsignacion,
    required this.idIncidente,
    required this.idTaller,
    this.idTecnico,
    required this.idEstadoAsignacion,
    this.etaMinutos,
    this.notaTaller,
    required this.createdAt,
    required this.updatedAt,
    required this.taller,
    required this.estado,
  });

  factory Asignacion.fromJson(Map<String, dynamic> json) {
    return Asignacion(
      idAsignacion: json['id_asignacion'],
      idIncidente: json['id_incidente'],
      idTaller: json['id_taller'],
      idTecnico: json['id_tecnico'],
      idEstadoAsignacion: json['id_estado_asignacion'],
      etaMinutos: json['eta_minutos'],
      notaTaller: json['nota_taller'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      taller: TallerAsignado.fromJson(json['taller']),
      estado: EstadoAsignacion.fromJson(json['estado']),
    );
  }
}
```

### 3.2 Actualizar modelo `Incidente`

En tu clase `Incidente` agrega:

```dart
class Incidente {
  // ... campos existentes ...
  final List<Asignacion> asignaciones;

  Incidente({
    // ... campos existentes ...
    this.asignaciones = const [],
  });

  factory Incidente.fromJson(Map<String, dynamic> json) {
    return Incidente(
      // ... campos existentes ...
      asignaciones: (json['asignaciones'] as List<dynamic>? ?? [])
          .map((e) => Asignacion.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  /// La asignación activa (la más reciente)
  Asignacion? get asignacionActiva =>
      asignaciones.isNotEmpty ? asignaciones.first : null;
}
```

### 3.3 Pantalla de detalle del CLIENTE — mostrar estado

```dart
Widget _buildEstadoAsignacion(Incidente incidente) {
  final asig = incidente.asignacionActiva;
  if (asig == null) {
    return _estadoCard(
      icon: Icons.search,
      color: Colors.blue,
      title: "Buscando taller disponible...",
      subtitle: "El motor de asignación está buscando el taller más cercano",
    );
  }

  switch (asig.estado.nombre) {
    case 'pendiente':
      return _estadoCard(
        icon: Icons.access_time,
        color: Colors.orange,
        title: "Esperando confirmación del taller",
        subtitle: "${asig.taller.nombre} fue notificado",
      );

    case 'aceptada':
      final eta = asig.etaMinutos != null
          ? " (ETA: ${asig.etaMinutos} min)"
          : "";
      return _estadoCard(
        icon: Icons.check_circle,
        color: Colors.green,
        title: "✅ ${asig.taller.nombre} aceptó$eta",
        subtitle: asig.notaTaller ?? "Vienen en camino",
        action: asig.taller.telefono != null
            ? TextButton.icon(
                icon: const Icon(Icons.phone),
                label: Text(asig.taller.telefono!),
                onPressed: () => launchUrl(
                    Uri(scheme: 'tel', path: asig.taller.telefono)),
              )
            : null,
      );

    case 'rechazada':
      return _estadoCard(
        icon: Icons.cancel,
        color: Colors.red,
        title: "❌ ${asig.taller.nombre} rechazó la solicitud",
        subtitle: asig.notaTaller ?? "Puedes elegir otro taller abajo",
      );

    case 'en_camino':
      return _estadoCard(
        icon: Icons.local_shipping,
        color: Colors.blue,
        title: "🚚 ${asig.taller.nombre} viene en camino",
        subtitle: asig.etaMinutos != null
            ? "Llega en ${asig.etaMinutos} min aprox."
            : "",
      );

    case 'completada':
      return _estadoCard(
        icon: Icons.verified,
        color: Colors.green,
        title: "✅ Servicio completado",
        subtitle: "Gracias por usar Yary",
      );

    default:
      return const SizedBox.shrink();
  }
}
```

### 3.4 Polling / refresh automático en pantalla del cliente

Para que el cliente vea cuando el taller acepta sin tener que refrescar manualmente:

```dart
Timer? _pollingTimer;

@override
void initState() {
  super.initState();
  _cargarIncidente();
  // Refrescar cada 10 segundos mientras esté pendiente
  _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) {
    if (mounted && _debePollear()) _cargarIncidente();
  });
}

bool _debePollear() {
  final estado = _incidente?.asignacionActiva?.estado.nombre;
  return estado == null || estado == 'pendiente' || estado == 'aceptada';
}

@override
void dispose() {
  _pollingTimer?.cancel();
  super.dispose();
}
```

> **Mejora futura:** reemplazar polling por WebSocket o push notifications (Firebase / OneSignal).

### 3.5 Pantalla del TALLER — lista de solicitudes

Nueva pantalla `lib/screens/taller/solicitudes_screen.dart`:

```dart
class SolicitudesScreen extends StatefulWidget {
  const SolicitudesScreen({super.key});

  @override
  State<SolicitudesScreen> createState() => _SolicitudesScreenState();
}

class _SolicitudesScreenState extends State<SolicitudesScreen> {
  List<AsignacionTaller> _solicitudes = [];
  bool _cargando = true;
  String _filtroEstado = 'pendiente';

  @override
  void initState() {
    super.initState();
    _cargarSolicitudes();
  }

  Future<void> _cargarSolicitudes() async {
    setState(() => _cargando = true);
    final token = await AuthService.getTokenTaller();
    final resp = await http.get(
      Uri.parse('$baseUrl/talleres/mi-taller/asignaciones?estado=$_filtroEstado'),
      headers: {'Authorization': 'Bearer $token'},
    );
    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body) as List;
      setState(() {
        _solicitudes = data.map((e) => AsignacionTaller.fromJson(e)).toList();
        _cargando = false;
      });
    } else {
      setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Solicitudes"),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: Row(
            children: ['pendiente', 'aceptada', 'completada', 'rechazada']
                .map((e) => Expanded(
                      child: InkWell(
                        onTap: () {
                          setState(() => _filtroEstado = e);
                          _cargarSolicitudes();
                        },
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          color: _filtroEstado == e
                              ? Colors.blue.shade100
                              : null,
                          alignment: Alignment.center,
                          child: Text(e),
                        ),
                      ),
                    ))
                .toList(),
          ),
        ),
      ),
      body: _cargando
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _cargarSolicitudes,
              child: ListView.builder(
                itemCount: _solicitudes.length,
                itemBuilder: (_, i) => _buildSolicitudCard(_solicitudes[i]),
              ),
            ),
    );
  }

  Widget _buildSolicitudCard(AsignacionTaller asig) {
    return Card(
      margin: const EdgeInsets.all(8),
      child: ListTile(
        title: Text("${asig.incidente.usuario.nombre} • ${asig.incidente.vehiculo.placa}"),
        subtitle: Text(
          "${asig.incidente.prioridad?.nivel ?? ''} • "
          "${asig.incidente.categoria?.nombre ?? ''}\n"
          "${asig.incidente.resumenIa ?? asig.incidente.descripcionUsuario ?? ''}",
        ),
        trailing: Text(asig.estado.nombre),
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => SolicitudDetalleScreen(asignacion: asig),
          ),
        ).then((_) => _cargarSolicitudes()),
      ),
    );
  }
}
```

### 3.6 Pantalla de detalle + aceptar/rechazar (taller)

```dart
class SolicitudDetalleScreen extends StatefulWidget {
  final AsignacionTaller asignacion;
  const SolicitudDetalleScreen({super.key, required this.asignacion});

  @override
  State<SolicitudDetalleScreen> createState() => _SolicitudDetalleScreenState();
}

class _SolicitudDetalleScreenState extends State<SolicitudDetalleScreen> {
  bool _procesando = false;

  Future<void> _aceptar() async {
    final etaController = TextEditingController(text: '20');
    final notaController = TextEditingController();

    final confirmar = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Aceptar solicitud"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: etaController,
              decoration: const InputDecoration(labelText: "ETA (minutos)"),
              keyboardType: TextInputType.number,
            ),
            TextField(
              controller: notaController,
              decoration: const InputDecoration(labelText: "Nota al cliente (opcional)"),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancelar")),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Aceptar")),
        ],
      ),
    );

    if (confirmar != true) return;

    setState(() => _procesando = true);
    final token = await AuthService.getTokenTaller();
    final resp = await http.put(
      Uri.parse('$baseUrl/talleres/mi-taller/asignaciones/${widget.asignacion.idAsignacion}/aceptar'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'eta_minutos': int.tryParse(etaController.text),
        if (notaController.text.isNotEmpty) 'nota': notaController.text,
      }),
    );
    setState(() => _procesando = false);

    if (resp.statusCode == 200) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Solicitud aceptada"), backgroundColor: Colors.green),
        );
        Navigator.pop(context);
      }
    } else {
      final err = jsonDecode(resp.body)['detail'] ?? 'Error';
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(err), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _rechazar() async {
    final motivoController = TextEditingController();

    final confirmar = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Rechazar solicitud"),
        content: TextField(
          controller: motivoController,
          decoration: const InputDecoration(
            labelText: "Motivo (obligatorio)",
            hintText: "Ej: Sin stock de la pieza requerida",
          ),
          maxLines: 3,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Cancelar")),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () {
              if (motivoController.text.trim().length < 3) return;
              Navigator.pop(ctx, true);
            },
            child: const Text("Rechazar"),
          ),
        ],
      ),
    );

    if (confirmar != true) return;

    setState(() => _procesando = true);
    final token = await AuthService.getTokenTaller();
    final resp = await http.put(
      Uri.parse('$baseUrl/talleres/mi-taller/asignaciones/${widget.asignacion.idAsignacion}/rechazar'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'motivo': motivoController.text.trim()}),
    );
    setState(() => _procesando = false);

    if (resp.statusCode == 200) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Solicitud rechazada"), backgroundColor: Colors.orange),
        );
        Navigator.pop(context);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asig = widget.asignacion;
    final inc = asig.incidente;
    final esPendiente = asig.estado.nombre == 'pendiente';

    return Scaffold(
      appBar: AppBar(title: Text("Solicitud #${asig.idAsignacion}")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _section("Cliente", [
            _row("Nombre", inc.usuario.nombre),
            _row("Teléfono", inc.usuario.telefono ?? "-"),
          ]),
          _section("Vehículo", [
            _row("Placa", inc.vehiculo.placa),
            _row("Modelo", "${inc.vehiculo.marca ?? ''} ${inc.vehiculo.modelo ?? ''}".trim()),
            _row("Año", inc.vehiculo.anio?.toString() ?? "-"),
            _row("Color", inc.vehiculo.color ?? "-"),
          ]),
          _section("Problema", [
            _row("Categoría", inc.categoria?.nombre ?? "-"),
            _row("Prioridad", inc.prioridad?.nivel ?? "-"),
            _row("Descripción del cliente", inc.descripcionUsuario ?? "-"),
            _row("Resumen IA", inc.resumenIa ?? "-"),
          ]),
          _section("Ubicación", [
            _row("Lat/Lng", "${inc.latitud}, ${inc.longitud}"),
            TextButton.icon(
              icon: const Icon(Icons.map),
              label: const Text("Abrir en Google Maps"),
              onPressed: () => launchUrl(Uri.parse(
                'https://www.google.com/maps?q=${inc.latitud},${inc.longitud}',
              )),
            ),
          ]),
          const SizedBox(height: 24),
          if (esPendiente) ...[
            FilledButton.icon(
              onPressed: _procesando ? null : _aceptar,
              style: FilledButton.styleFrom(
                backgroundColor: Colors.green,
                minimumSize: const Size.fromHeight(56),
              ),
              icon: const Icon(Icons.check),
              label: const Text("ACEPTAR"),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _procesando ? null : _rechazar,
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red,
                minimumSize: const Size.fromHeight(56),
              ),
              icon: const Icon(Icons.close),
              label: const Text("RECHAZAR"),
            ),
          ] else
            Text(
              "Estado: ${asig.estado.nombre}",
              style: Theme.of(context).textTheme.titleMedium,
            ),
        ],
      ),
    );
  }

  Widget _section(String titulo, List<Widget> hijos) => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(titulo, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              const Divider(),
              ...hijos,
            ],
          ),
        ),
      );

  Widget _row(String label, String valor) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(width: 120, child: Text(label, style: const TextStyle(color: Colors.grey))),
            Expanded(child: Text(valor)),
          ],
        ),
      );
}
```

### 3.7 Modelos Dart para lado taller

Crear `lib/models/asignacion_taller.dart`:

```dart
class ClienteMini {
  final int idUsuario;
  final String nombre;
  final String? telefono;
  ClienteMini({required this.idUsuario, required this.nombre, this.telefono});
  factory ClienteMini.fromJson(Map<String, dynamic> j) => ClienteMini(
        idUsuario: j['id_usuario'],
        nombre: j['nombre'],
        telefono: j['telefono'],
      );
}

class VehiculoMiniT {
  final int idVehiculo;
  final String placa;
  final String? marca, modelo, color;
  final int? anio;
  VehiculoMiniT({
    required this.idVehiculo, required this.placa,
    this.marca, this.modelo, this.anio, this.color,
  });
  factory VehiculoMiniT.fromJson(Map<String, dynamic> j) => VehiculoMiniT(
        idVehiculo: j['id_vehiculo'],
        placa: j['placa'],
        marca: j['marca'], modelo: j['modelo'],
        anio: j['anio'], color: j['color'],
      );
}

class CategoriaMiniT {
  final int idCategoria;
  final String nombre;
  CategoriaMiniT({required this.idCategoria, required this.nombre});
  factory CategoriaMiniT.fromJson(Map<String, dynamic> j) =>
      CategoriaMiniT(idCategoria: j['id_categoria'], nombre: j['nombre']);
}

class PrioridadMiniT {
  final int idPrioridad;
  final String nivel;
  final int orden;
  PrioridadMiniT({required this.idPrioridad, required this.nivel, required this.orden});
  factory PrioridadMiniT.fromJson(Map<String, dynamic> j) => PrioridadMiniT(
        idPrioridad: j['id_prioridad'],
        nivel: j['nivel'],
        orden: j['orden'],
      );
}

class IncidenteParaTaller {
  final int idIncidente;
  final String? descripcionUsuario;
  final String? resumenIa;
  final double latitud;
  final double longitud;
  final DateTime createdAt;
  final ClienteMini usuario;
  final VehiculoMiniT vehiculo;
  final CategoriaMiniT? categoria;
  final PrioridadMiniT? prioridad;

  IncidenteParaTaller({
    required this.idIncidente,
    this.descripcionUsuario, this.resumenIa,
    required this.latitud, required this.longitud,
    required this.createdAt,
    required this.usuario, required this.vehiculo,
    this.categoria, this.prioridad,
  });

  factory IncidenteParaTaller.fromJson(Map<String, dynamic> j) => IncidenteParaTaller(
        idIncidente: j['id_incidente'],
        descripcionUsuario: j['descripcion_usuario'],
        resumenIa: j['resumen_ia'],
        latitud: (j['latitud'] as num).toDouble(),
        longitud: (j['longitud'] as num).toDouble(),
        createdAt: DateTime.parse(j['created_at']),
        usuario: ClienteMini.fromJson(j['usuario']),
        vehiculo: VehiculoMiniT.fromJson(j['vehiculo']),
        categoria: j['categoria'] == null ? null : CategoriaMiniT.fromJson(j['categoria']),
        prioridad: j['prioridad'] == null ? null : PrioridadMiniT.fromJson(j['prioridad']),
      );
}

class EstadoMiniT {
  final int idEstadoAsignacion;
  final String nombre;
  EstadoMiniT({required this.idEstadoAsignacion, required this.nombre});
  factory EstadoMiniT.fromJson(Map<String, dynamic> j) =>
      EstadoMiniT(idEstadoAsignacion: j['id_estado_asignacion'], nombre: j['nombre']);
}

class AsignacionTaller {
  final int idAsignacion;
  final int idIncidente;
  final int idTaller;
  final int? idTecnico;
  final int idEstadoAsignacion;
  final int? etaMinutos;
  final String? notaTaller;
  final DateTime createdAt;
  final DateTime updatedAt;
  final EstadoMiniT estado;
  final IncidenteParaTaller incidente;

  AsignacionTaller({
    required this.idAsignacion, required this.idIncidente,
    required this.idTaller, this.idTecnico,
    required this.idEstadoAsignacion, this.etaMinutos, this.notaTaller,
    required this.createdAt, required this.updatedAt,
    required this.estado, required this.incidente,
  });

  factory AsignacionTaller.fromJson(Map<String, dynamic> j) => AsignacionTaller(
        idAsignacion: j['id_asignacion'],
        idIncidente: j['id_incidente'],
        idTaller: j['id_taller'],
        idTecnico: j['id_tecnico'],
        idEstadoAsignacion: j['id_estado_asignacion'],
        etaMinutos: j['eta_minutos'],
        notaTaller: j['nota_taller'],
        createdAt: DateTime.parse(j['created_at']),
        updatedAt: DateTime.parse(j['updated_at']),
        estado: EstadoMiniT.fromJson(j['estado']),
        incidente: IncidenteParaTaller.fromJson(j['incidente']),
      );
}
```

---

## 4. Errores comunes y cómo manejarlos

| Código | Causa | Cómo responder en UI |
|---|---|---|
| 400 | Intentar aceptar/rechazar algo que ya no está pendiente | Mostrar mensaje "La solicitud ya fue procesada" + refrescar lista |
| 401 | Token del taller expirado | Redirigir a login |
| 404 | La asignación no pertenece a este taller | Mostrar "No encontrada" + volver a lista |
| 422 | Falta `motivo` al rechazar o `eta_minutos` inválido | Validar antes de enviar |

---

## 5. Checklist de implementación

### Lado cliente
- [ ] Modelo `Asignacion` + `EstadoAsignacion` + `TallerAsignado` creados
- [ ] `Incidente.fromJson` parsea `asignaciones[]`
- [ ] Getter `asignacionActiva` agregado
- [ ] Widget `_buildEstadoAsignacion` mostrado en pantalla de detalle del incidente
- [ ] Polling cada 10s mientras esté pendiente/aceptada
- [ ] Si estado == `rechazada` → mostrar sección de candidatos para elegir otro taller (ya existe `/cambiar-taller`)

### Lado taller (app separada o pantalla separada del mismo app)
- [ ] Login del taller (`POST /talleres/login`) — token se guarda separado del token del cliente
- [ ] Modelo `AsignacionTaller` y sub-modelos creados
- [ ] Pantalla `SolicitudesScreen` con tabs por estado
- [ ] Pantalla `SolicitudDetalleScreen` con info completa del incidente
- [ ] Botón ACEPTAR con diálogo de ETA + nota
- [ ] Botón RECHAZAR con diálogo de motivo (obligatorio ≥3 chars)
- [ ] Manejar error 400 cuando ya fue procesada
- [ ] `RefreshIndicator` para pull-to-refresh

---

## 6. Test end-to-end

1. **Prerrequisitos:** correr `seed_motor_asignacion.py` para tener talleres cerca.
2. Desde app cliente: crear incidente + subir 1 foto + analizar con IA.
3. Desde app taller: login con `autonorte@talleres.test` / `password123`.
4. Ver sección "Solicitudes" → aparece el incidente recién creado en pestaña "pendiente".
5. Abrir detalle → ver info del cliente, vehículo, descripción.
6. Presionar ACEPTAR → poner ETA 15 min → confirmar.
7. Volver al app cliente → refrescar o esperar polling → ver "✅ Mecánica Central SC aceptó (ETA: 15 min)".
8. Repetir con otro incidente pero **RECHAZAR** con motivo.
9. Verificar en cliente que ve "❌ Rechazada" y puede elegir otro taller de `candidatos`.

---

## 7. Notas importantes

- El **token del taller** NO es intercambiable con el token del cliente. Son JWTs con `tipo` diferente (`"taller"` vs `"cliente"`). Guarda cada uno en su propio `SharedPreferences` key.
- Por ahora el backend **NO envía push notifications** al taller — es polling manual. Implementar push es una mejora futura.
- El cliente puede cambiar de taller **en cualquier momento** (no solo cuando le rechazan) vía `PUT /incidencias/{id}/cambiar-taller` con `id_candidato` de otro taller de la lista.
- Si el taller ya aceptó y luego quiere cancelar, **no hay endpoint todavía** — sería necesario agregar uno tipo `PUT /asignaciones/{id}/cancelar` si el caso lo requiere.
