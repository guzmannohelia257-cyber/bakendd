# Guía de Actualización — App Móvil del Cliente (Flutter)

Esta guía resume **todo lo nuevo o que cambió en el backend** que afecta la app del cliente, y cómo ajustar Flutter.

---

## 1. Resumen ejecutivo

**1 endpoint nuevo:**

| Método | Ruta | Caso de uso |
|---|---|---|
| POST | `/incidencias/{id_incidente}/evaluar` | Cliente califica el servicio cuando el incidente queda `atendido` (CU-10) |

**1 endpoint existente con cambios (backwards-compatible):**

| Ruta | Cambio |
|---|---|
| `GET /incidencias/mis-incidencias` | Acepta query params `estado`, `desde`, `hasta` (A.4 / CU-12) |

**Cambios de comportamiento (mismos endpoints, nueva lógica):**

- El ciclo de vida de la asignación ahora pasa por **5 estados** en lugar de 2. Hay que renderizar `en_camino` y `completada`.
- El incidente ahora **se cierra automáticamente** (pasa a `atendido`) cuando el taller marca el servicio como completado.
- Cuando un taller rechaza, el backend **reasigna automáticamente** a otro taller. El cliente ve el cambio silenciosamente en el siguiente refresh.
- `GET /incidencias/{id}` sigue igual, pero `asignaciones[]` ahora incluye todos los cambios de estado en vivo (polling recomendado).

**NO implementado aún (próxima iteración):**
- Ver en vivo la ubicación GPS del técnico que viene en camino. El endpoint `GET /incidencias/{id}/tecnico-ubicacion` **aún no existe**. Sección 9 explica cómo preparar la UI.

---

## 2. Modelos Dart actualizados

### 2.1 Estados de asignación

Usá un enum para evitar strings sueltos:

```dart
// lib/models/estado_asignacion.dart
enum EstadoAsignacion {
  pendiente,
  aceptada,
  rechazada,
  enCamino,
  completada;

  static EstadoAsignacion fromJson(String s) {
    switch (s) {
      case 'pendiente':   return EstadoAsignacion.pendiente;
      case 'aceptada':    return EstadoAsignacion.aceptada;
      case 'rechazada':   return EstadoAsignacion.rechazada;
      case 'en_camino':   return EstadoAsignacion.enCamino;
      case 'completada':  return EstadoAsignacion.completada;
      default: throw ArgumentError('Estado desconocido: $s');
    }
  }

  String get displayLabel => switch (this) {
    EstadoAsignacion.pendiente   => 'Esperando respuesta del taller',
    EstadoAsignacion.aceptada    => 'Taller aceptó — preparando',
    EstadoAsignacion.rechazada   => 'Rechazada — buscando otro taller',
    EstadoAsignacion.enCamino    => 'Técnico en camino',
    EstadoAsignacion.completada  => 'Servicio completado',
  };

  Color get color => switch (this) {
    EstadoAsignacion.pendiente   => Colors.amber,
    EstadoAsignacion.aceptada    => Colors.blue,
    EstadoAsignacion.rechazada   => Colors.grey,
    EstadoAsignacion.enCamino    => Colors.orange,
    EstadoAsignacion.completada  => Colors.green,
  };

  IconData get icon => switch (this) {
    EstadoAsignacion.pendiente   => Icons.hourglass_empty,
    EstadoAsignacion.aceptada    => Icons.check_circle_outline,
    EstadoAsignacion.rechazada   => Icons.cancel_outlined,
    EstadoAsignacion.enCamino    => Icons.directions_car,
    EstadoAsignacion.completada  => Icons.task_alt,
  };
}
```

### 2.2 Estados de incidente

```dart
// lib/models/estado_incidente.dart
enum EstadoIncidente {
  pendiente,
  enProceso,
  atendido,
  cancelado;

  static EstadoIncidente fromJson(String s) {
    switch (s) {
      case 'pendiente':   return EstadoIncidente.pendiente;
      case 'en_proceso':  return EstadoIncidente.enProceso;   // NUEVO en el flujo
      case 'atendido':    return EstadoIncidente.atendido;    // NUEVO en el flujo
      case 'cancelado':   return EstadoIncidente.cancelado;
      default: throw ArgumentError('Estado desconocido: $s');
    }
  }

  String get displayLabel => switch (this) {
    EstadoIncidente.pendiente   => 'Pendiente',
    EstadoIncidente.enProceso   => 'En proceso',
    EstadoIncidente.atendido    => 'Atendido',
    EstadoIncidente.cancelado   => 'Cancelado',
  };

  bool get esEvaluable => this == EstadoIncidente.atendido;
}
```

### 2.3 Asignación (vista del cliente)

Lo que vas a recibir dentro de `IncidenteDetalle.asignaciones[]`:

```dart
class Asignacion {
  final int idAsignacion;
  final int idIncidente;
  final int idTaller;
  final int? idTecnico;          // null hasta que el taller asigne un técnico
  final int idEstadoAsignacion;
  final int? etaMinutos;         // null si el taller no lo reportó
  final String? notaTaller;      // mensaje del taller al cliente
  final DateTime createdAt;
  final DateTime updatedAt;

  final EstadoAsignacion estado;
  final TallerMini taller;

  Asignacion.fromJson(Map<String, dynamic> j)
    : idAsignacion = j['id_asignacion'],
      idIncidente = j['id_incidente'],
      idTaller = j['id_taller'],
      idTecnico = j['id_tecnico'],
      idEstadoAsignacion = j['id_estado_asignacion'],
      etaMinutos = j['eta_minutos'],
      notaTaller = j['nota_taller'],
      createdAt = DateTime.parse(j['created_at']),
      updatedAt = DateTime.parse(j['updated_at']),
      estado = EstadoAsignacion.fromJson(j['estado']['nombre']),
      taller = TallerMini.fromJson(j['taller']);
}

class TallerMini {
  final int idTaller;
  final String nombre;
  final String? direccion;
  final String? telefono;

  TallerMini.fromJson(Map<String, dynamic> j)
    : idTaller = j['id_taller'],
      nombre = j['nombre'],
      direccion = j['direccion'],
      telefono = j['telefono'];
}
```

### 2.4 IncidenteDetalle

```dart
class IncidenteDetalle {
  final int idIncidente;
  final int idUsuario;
  final int idVehiculo;
  final String? descripcionUsuario;
  final double latitud;
  final double longitud;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Campos de IA
  final String? resumenIa;
  final double? clasificacionIaConfianza;
  final bool requiereRevisionManual;

  // Relaciones
  final VehiculoMini vehiculo;
  final EstadoIncidente estado;
  final CategoriaMini? categoria;
  final PrioridadMini? prioridad;
  final List<Candidato> candidatos;       // lista de opciones generadas por el motor
  final List<Asignacion> asignaciones;    // historial de asignaciones (la última refleja el estado actual)

  IncidenteDetalle.fromJson(Map<String, dynamic> j)
    : idIncidente = j['id_incidente'],
      idUsuario = j['id_usuario'],
      idVehiculo = j['id_vehiculo'],
      descripcionUsuario = j['descripcion_usuario'],
      latitud = (j['latitud'] as num).toDouble(),
      longitud = (j['longitud'] as num).toDouble(),
      createdAt = DateTime.parse(j['created_at']),
      updatedAt = DateTime.parse(j['updated_at']),
      resumenIa = j['resumen_ia'],
      clasificacionIaConfianza = (j['clasificacion_ia_confianza'] as num?)?.toDouble(),
      requiereRevisionManual = j['requiere_revision_manual'] ?? false,
      vehiculo = VehiculoMini.fromJson(j['vehiculo']),
      estado = EstadoIncidente.fromJson(j['estado']['nombre']),
      categoria = j['categoria'] != null ? CategoriaMini.fromJson(j['categoria']) : null,
      prioridad = j['prioridad'] != null ? PrioridadMini.fromJson(j['prioridad']) : null,
      candidatos = ((j['candidatos'] ?? []) as List).map((c) => Candidato.fromJson(c)).toList(),
      asignaciones = ((j['asignaciones'] ?? []) as List).map((a) => Asignacion.fromJson(a)).toList();

  /// La asignación que refleja el estado actual (la más reciente).
  Asignacion? get asignacionActual {
    if (asignaciones.isEmpty) return null;
    return asignaciones.reduce((a, b) => a.updatedAt.isAfter(b.updatedAt) ? a : b);
  }
}
```

### 2.5 Evaluación (nueva)

```dart
class EvaluacionCreate {
  final int estrellas;      // 1..5
  final String? comentario; // max 500

  EvaluacionCreate({required this.estrellas, this.comentario});

  Map<String, dynamic> toJson() => {
    'estrellas': estrellas,
    if (comentario != null) 'comentario': comentario,
  };
}

class EvaluacionResponse {
  final int idEvaluacion;
  final int idIncidente;
  final int idTaller;
  final int? idTecnico;
  final int estrellas;
  final String? comentario;
  final DateTime createdAt;

  EvaluacionResponse.fromJson(Map<String, dynamic> j)
    : idEvaluacion = j['id_evaluacion'],
      idIncidente = j['id_incidente'],
      idTaller = j['id_taller'],
      idTecnico = j['id_tecnico'],
      estrellas = j['estrellas'],
      comentario = j['comentario'],
      createdAt = DateTime.parse(j['created_at']);
}
```

---

## 3. Service HTTP actualizado

```dart
// lib/services/incidencia_service.dart
class IncidenciaService {
  final Dio _dio;
  IncidenciaService(this._dio);

  // CU-12 / A.4 — historial con filtros
  Future<List<IncidenteDetalle>> listarMisIncidencias({
    EstadoIncidente? estado,
    DateTime? desde,
    DateTime? hasta,
  }) async {
    final params = <String, dynamic>{};
    if (estado != null) params['estado'] = _estadoBackendName(estado);
    if (desde != null)  params['desde']  = _fmt(desde);
    if (hasta != null)  params['hasta']  = _fmt(hasta);

    final r = await _dio.get('/incidencias/mis-incidencias', queryParameters: params);
    return (r.data as List).map((j) => IncidenteDetalle.fromJson(j)).toList();
  }

  Future<IncidenteDetalle> obtenerDetalle(int idIncidente) async {
    final r = await _dio.get('/incidencias/$idIncidente');
    return IncidenteDetalle.fromJson(r.data);
  }

  Future<IncidenteDetalle> analizarIA(int idIncidente) async {
    final r = await _dio.post('/incidencias/$idIncidente/analizar-ia');
    return IncidenteDetalle.fromJson(r.data);
  }

  Future<IncidenteDetalle> cambiarTaller(int idIncidente, int idCandidato) async {
    final r = await _dio.put(
      '/incidencias/$idIncidente/cambiar-taller',
      data: {'id_candidato': idCandidato},
    );
    return IncidenteDetalle.fromJson(r.data);
  }

  // NUEVO — A.3 / CU-10
  Future<EvaluacionResponse> evaluarServicio(int idIncidente, EvaluacionCreate ev) async {
    final r = await _dio.post(
      '/incidencias/$idIncidente/evaluar',
      data: ev.toJson(),
    );
    return EvaluacionResponse.fromJson(r.data);
  }

  String _estadoBackendName(EstadoIncidente e) => switch (e) {
    EstadoIncidente.pendiente => 'pendiente',
    EstadoIncidente.enProceso => 'en_proceso',
    EstadoIncidente.atendido  => 'atendido',
    EstadoIncidente.cancelado => 'cancelado',
  };

  String _fmt(DateTime d) =>
    '${d.year.toString().padLeft(4,'0')}-${d.month.toString().padLeft(2,'0')}-${d.day.toString().padLeft(2,'0')}';
}
```

---

## 4. UI — renderizar el ciclo de vida completo

El usuario necesita ver en qué parte del proceso está su emergencia. En la pantalla de detalle del incidente, mostrá la `asignacionActual` con un badge dinámico.

### Widget de estado

```dart
class EstadoAsignacionBadge extends StatelessWidget {
  final Asignacion asignacion;
  const EstadoAsignacionBadge(this.asignacion, {super.key});

  @override
  Widget build(BuildContext context) {
    final estado = asignacion.estado;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: estado.color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: estado.color),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(estado.icon, color: estado.color, size: 18),
          const SizedBox(width: 6),
          Text(estado.displayLabel, style: TextStyle(color: estado.color, fontWeight: FontWeight.w600)),
          if (asignacion.etaMinutos != null && estado == EstadoAsignacion.aceptada) ...[
            const SizedBox(width: 6),
            Text('(ETA ${asignacion.etaMinutos} min)', style: TextStyle(color: estado.color)),
          ],
        ],
      ),
    );
  }
}
```

### Pantalla de detalle

```dart
class IncidenteDetalleScreen extends StatefulWidget {
  final int idIncidente;
  const IncidenteDetalleScreen({required this.idIncidente, super.key});
  @override State<IncidenteDetalleScreen> createState() => _IncidenteDetalleState();
}

class _IncidenteDetalleState extends State<IncidenteDetalleScreen> {
  IncidenteDetalle? _incidente;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _cargar();
    // Polling cada 10s — refresca el estado hasta que llegue a atendido/cancelado
    _pollTimer = Timer.periodic(const Duration(seconds: 10), (_) => _cargar());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _cargar() async {
    final i = await context.read<IncidenciaService>().obtenerDetalle(widget.idIncidente);
    if (mounted) setState(() => _incidente = i);

    // Detener polling si ya no hay cambios de estado esperables
    if (i.estado == EstadoIncidente.atendido || i.estado == EstadoIncidente.cancelado) {
      _pollTimer?.cancel();
    }
  }

  @override
  Widget build(BuildContext context) {
    final i = _incidente;
    if (i == null) return const Center(child: CircularProgressIndicator());

    final asignacion = i.asignacionActual;

    return Scaffold(
      appBar: AppBar(title: Text('Emergencia #${i.idIncidente}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (asignacion != null) EstadoAsignacionBadge(asignacion),
          const SizedBox(height: 16),
          if (i.resumenIa != null) Card(
            child: Padding(padding: const EdgeInsets.all(12),
              child: Text('Diagnóstico IA: ${i.resumenIa}')),
          ),
          if (asignacion != null) _buildTallerInfo(asignacion),
          if (asignacion?.notaTaller != null) _buildNotaTaller(asignacion!.notaTaller!),
          _buildEvidencias(i),

          // Botón de evaluación solo cuando el incidente está atendido
          if (i.estado.esEvaluable) _buildBotonEvaluar(i),
        ],
      ),
    );
  }

  Widget _buildTallerInfo(Asignacion a) => Card(
    child: ListTile(
      leading: const Icon(Icons.business),
      title: Text(a.taller.nombre),
      subtitle: Text(a.taller.direccion ?? 'Sin dirección'),
      trailing: a.taller.telefono != null
        ? IconButton(icon: const Icon(Icons.phone), onPressed: () {/* launch tel: */})
        : null,
    ),
  );

  Widget _buildNotaTaller(String nota) => Card(
    color: Colors.blue.shade50,
    child: Padding(padding: const EdgeInsets.all(12),
      child: Row(children: [
        const Icon(Icons.chat_bubble_outline, color: Colors.blue),
        const SizedBox(width: 8),
        Expanded(child: Text('Taller dice: $nota')),
      ]),
    ),
  );

  Widget _buildBotonEvaluar(IncidenteDetalle i) => Padding(
    padding: const EdgeInsets.only(top: 24),
    child: FilledButton.icon(
      icon: const Icon(Icons.star),
      label: const Text('Evaluar el servicio'),
      onPressed: () async {
        final result = await showDialog<EvaluacionCreate>(
          context: context,
          builder: (_) => EvaluarServicioDialog(),
        );
        if (result == null) return;
        try {
          await context.read<IncidenciaService>().evaluarServicio(i.idIncidente, result);
          if (mounted) ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('¡Gracias por tu evaluación!')),
          );
        } on DioException catch (e) {
          final detail = e.response?.data?['detail'] ?? 'Error al enviar';
          if (mounted) ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(detail.toString())),
          );
        }
      },
    ),
  );

  Widget _buildEvidencias(IncidenteDetalle i) => const SizedBox.shrink();
}
```

---

## 5. Pantalla: Evaluar servicio

```dart
class EvaluarServicioDialog extends StatefulWidget {
  @override State<EvaluarServicioDialog> createState() => _EvaluarServicioState();
}

class _EvaluarServicioState extends State<EvaluarServicioDialog> {
  int _estrellas = 5;
  final _comentarioCtrl = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('¿Cómo fue tu experiencia?'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (i) {
              final n = i + 1;
              return IconButton(
                icon: Icon(Icons.star, color: n <= _estrellas ? Colors.amber : Colors.grey),
                onPressed: () => setState(() => _estrellas = n),
              );
            }),
          ),
          TextField(
            controller: _comentarioCtrl,
            decoration: const InputDecoration(
              hintText: 'Comentario (opcional)',
              border: OutlineInputBorder(),
            ),
            maxLength: 500,
            maxLines: 3,
          ),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
        FilledButton(
          onPressed: () => Navigator.pop(context, EvaluacionCreate(
            estrellas: _estrellas,
            comentario: _comentarioCtrl.text.trim().isEmpty ? null : _comentarioCtrl.text.trim(),
          )),
          child: const Text('Enviar'),
        ),
      ],
    );
  }
}
```

### Errores que el backend devuelve

| Código | Motivo | Mensaje del backend |
|---|---|---|
| 400 | El incidente no está en estado `atendido` | `Solo puedes evaluar incidentes en estado 'atendido'. Estado actual: '{X}'.` |
| 400 | No hay asignación completada | `No hay asignación completada para este incidente` |
| 409 | Ya evaluaste antes | `Ya evaluaste este servicio` |
| 404 | No es tuyo | `Incidencia no encontrada o no te pertenece` |

Muestra `error.response.data['detail']` directamente — el backend devuelve textos en español listos.

---

## 6. Pantalla: Historial con filtros

```dart
class HistorialScreen extends StatefulWidget {
  @override State<HistorialScreen> createState() => _HistorialState();
}

class _HistorialState extends State<HistorialScreen> {
  EstadoIncidente? _filtroEstado;
  DateTime? _desde;
  DateTime? _hasta;
  List<IncidenteDetalle> _lista = [];

  @override void initState() { super.initState(); _cargar(); }

  Future<void> _cargar() async {
    final data = await context.read<IncidenciaService>().listarMisIncidencias(
      estado: _filtroEstado,
      desde: _desde,
      hasta: _hasta,
    );
    setState(() => _lista = data);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis emergencias')),
      body: Column(children: [
        _buildFiltros(),
        Expanded(
          child: ListView.builder(
            itemCount: _lista.length,
            itemBuilder: (_, i) {
              final inc = _lista[i];
              return ListTile(
                leading: Icon(inc.estado.esEvaluable ? Icons.star_border : Icons.history),
                title: Text(inc.resumenIa ?? inc.descripcionUsuario ?? 'Sin descripción'),
                subtitle: Text('${inc.estado.displayLabel} · ${inc.createdAt.toLocal()}'),
                onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => IncidenteDetalleScreen(idIncidente: inc.idIncidente),
                )),
              );
            },
          ),
        ),
      ]),
    );
  }

  Widget _buildFiltros() => Padding(
    padding: const EdgeInsets.all(12),
    child: Wrap(spacing: 8, children: [
      DropdownButton<EstadoIncidente?>(
        value: _filtroEstado,
        hint: const Text('Estado'),
        items: [
          const DropdownMenuItem(value: null, child: Text('Todos')),
          ...EstadoIncidente.values.map((e) =>
            DropdownMenuItem(value: e, child: Text(e.displayLabel))),
        ],
        onChanged: (v) { setState(() => _filtroEstado = v); _cargar(); },
      ),
      OutlinedButton.icon(
        icon: const Icon(Icons.date_range),
        label: Text(_desde == null ? 'Desde' : _fmt(_desde!)),
        onPressed: () async {
          final picked = await showDatePicker(
            context: context,
            initialDate: _desde ?? DateTime.now(),
            firstDate: DateTime(2024),
            lastDate: DateTime.now(),
          );
          if (picked != null) { setState(() => _desde = picked); _cargar(); }
        },
      ),
      OutlinedButton.icon(
        icon: const Icon(Icons.date_range),
        label: Text(_hasta == null ? 'Hasta' : _fmt(_hasta!)),
        onPressed: () async {
          final picked = await showDatePicker(
            context: context,
            initialDate: _hasta ?? DateTime.now(),
            firstDate: _desde ?? DateTime(2024),
            lastDate: DateTime.now(),
          );
          if (picked != null) { setState(() => _hasta = picked); _cargar(); }
        },
      ),
    ]),
  );

  String _fmt(DateTime d) =>
    '${d.day.toString().padLeft(2,'0')}/${d.month.toString().padLeft(2,'0')}/${d.year}';
}
```

---

## 7. Comportamientos nuevos del backend que afectan la UI

### 7.1 Reasignación automática al rechazo (B.1)

Escenario: tu emergencia estaba con el Taller A, y A rechaza.

- Ya no tenés que hacer nada (el cliente no ve botón "elegir otro taller" automáticamente).
- El backend **inmediatamente** crea una nueva `Asignacion` con el siguiente mejor candidato (Taller B).
- En el siguiente polling (cada 10s que hicimos arriba), `IncidenteDetalle.asignaciones[]` va a incluir las dos asignaciones: la vieja rechazada y la nueva pendiente. Por eso usamos `asignacionActual` (la más reciente por `updatedAt`).
- **Mostrá un toast cuando detectes el cambio de taller** para que el usuario entienda:

```dart
void _detectarCambioTaller(IncidenteDetalle nuevo, IncidenteDetalle? viejo) {
  if (viejo == null) return;
  final tallerViejo = viejo.asignacionActual?.idTaller;
  final tallerNuevo = nuevo.asignacionActual?.idTaller;
  if (tallerViejo != null && tallerNuevo != null && tallerViejo != tallerNuevo) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text('Te reasignamos al ${nuevo.asignacionActual!.taller.nombre}'),
      duration: const Duration(seconds: 4),
    ));
  }
}
```

### 7.2 Fallback manual: cambiar de taller

Si quieres permitir que el usuario elija manualmente otro candidato (p. ej., prefiere uno más caro pero más cercano), ya existe `PUT /incidencias/{id}/cambiar-taller`:

```dart
await service.cambiarTaller(incidente.idIncidente, candidato.idCandidato);
```

El backend actualiza la asignación activa apuntando al nuevo taller.

### 7.3 Incidente se cierra automáticamente

Cuando el taller marca `completar`:
- `asignacion.estado` → `completada`.
- `incidente.estado` → `atendido`.

Ambos en el mismo response. Tu polling lo detecta y **mostrás el botón "Evaluar"** (ya codificado arriba).

### 7.4 Flag `requiere_revision_manual`

Cuando la IA clasifica con baja confianza (< 0.6), el flag queda en `true`. Opcionalmente podés mostrar un warning sutil al usuario:

```dart
if (incidente.requiereRevisionManual) Container(
  padding: const EdgeInsets.all(8),
  color: Colors.yellow.shade100,
  child: const Row(children: [
    Icon(Icons.info_outline),
    SizedBox(width: 8),
    Expanded(child: Text('Tu reporte tiene información incompleta, puede ser impreciso.')),
  ]),
),
```

No es obligatorio renderizarlo; el motor corre igual con la mejor aproximación.

---

## 8. Catálogos que podés pedir al backend (opcional)

```
GET /incidencias/categorias      → lista categorías (bateria, llanta, etc.)
GET /incidencias/prioridades     → lista prioridades (baja, media, alta, critica)
GET /incidencias/estados         → lista estados de incidente
```

Si ya los tenías cacheados, siguen iguales — no hubo cambios.

---

## 9. Pendiente: ubicación del técnico (NO implementado aún)

Cuando el taller marca `iniciar-viaje`, `asignacion.estado` pasa a `en_camino`. El técnico está efectivamente viajando hacia el cliente. **Hoy** la app del cliente **no puede** mostrar dónde está el técnico en tiempo real porque el endpoint `GET /incidencias/{id}/tecnico-ubicacion` aún no existe.

### UI tentativa para cuando se implemente

Sección recomendada en tu pantalla de detalle (ponela después del badge):

```dart
if (asignacion?.estado == EstadoAsignacion.enCamino) Card(
  child: Padding(
    padding: const EdgeInsets.all(12),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Tu técnico está en camino', style: TextStyle(fontWeight: FontWeight.bold)),
      if (asignacion!.etaMinutos != null)
        Text('ETA: ${asignacion.etaMinutos} min'),
      const SizedBox(height: 8),
      // Placeholder mientras no hay endpoint:
      Container(
        height: 180,
        color: Colors.grey.shade200,
        child: const Center(child: Text('Mapa del técnico (próximamente)')),
      ),
    ]),
  ),
),
```

Cuando se implemente el endpoint:
- Vas a hacer polling cada 15s a `GET /incidencias/{id}/tecnico-ubicacion`.
- Pintar un pin con la lat/lng del técnico + un pin con la lat/lng del incidente.
- Detener polling cuando el estado pase a `completada`.

Te avisamos cuando esté listo — la UI hoy solo debe dejar el hueco preparado.

---

## 10. Checklist de implementación

### Código

- [ ] Crear enums `EstadoAsignacion` y `EstadoIncidente` con 5/4 valores respectivamente
- [ ] Actualizar modelo `Asignacion` con `idTecnico`, `etaMinutos`, `notaTaller`
- [ ] Actualizar modelo `IncidenteDetalle` con `asignaciones[]` y getter `asignacionActual`
- [ ] Agregar `EvaluacionCreate` y `EvaluacionResponse`
- [ ] Agregar `evaluarServicio()` al `IncidenciaService`
- [ ] Agregar query params `estado`, `desde`, `hasta` a `listarMisIncidencias()`

### UI

- [ ] Widget `EstadoAsignacionBadge` con 5 estados (color + icono + label)
- [ ] Polling de 10s en pantalla de detalle (detener en `atendido`/`cancelado`)
- [ ] Mostrar `notaTaller` cuando existe
- [ ] Mostrar `etaMinutos` cuando estado es `aceptada` o `enCamino`
- [ ] Botón "Evaluar el servicio" visible solo si `estado == atendido` y no evaluado antes
- [ ] Dialog de evaluación con 5 estrellas + comentario opcional
- [ ] Pantalla de historial con filtros `estado` + `desde`/`hasta`
- [ ] Placeholder "Mapa del técnico (próximamente)" cuando estado `enCamino`
- [ ] Toast cuando se detecta reasignación automática

### Testing manual

- [ ] Reportar una emergencia → ver estado `pendiente`
- [ ] Esperar a que el taller (desde su dashboard) acepte → ver cambio a `aceptada` con ETA
- [ ] Taller inicia viaje → ver `en_camino`
- [ ] Taller completa → ver `completada` + incidente pasa a `atendido`
- [ ] Botón "Evaluar" aparece → enviar 5 estrellas → ver confirmación
- [ ] Intentar evaluar dos veces → mensaje "Ya evaluaste este servicio"
- [ ] Taller rechaza → en siguiente polling el taller cambia → ver toast de reasignación
- [ ] Usar filtros de historial (estado, fechas) y ver que trae correctos

---

## 11. Credenciales de prueba

| Dato | Valor |
|---|---|
| Email | `conductor@ejemplo.com` |
| Password | `cliente123!` |
| Endpoint login | `POST /usuarios/login` |

---

## 12. Preguntas frecuentes

**¿Necesito polling o tengo push notifications?**
Hoy solo polling. Push notifications (FCM) están planeadas en bloque C.1 del roadmap pero no implementadas.

**¿Qué hago si el motor no encontró talleres?**
`GET /incidencias/{id}` va a devolver `asignaciones: []` y `candidatos: []`. La UI debería mostrar un mensaje claro y ofrecer reintentar `POST /incidencias/{id}/analizar-ia`.

**¿La reasignación automática cuántas veces se repite?**
Hasta agotar los candidatos que el motor guardó (hasta 10). Si rechazan todos, el incidente queda en `pendiente` sin asignación. Punto muerto que hoy no resuelve automáticamente la app — eventualmente habrá que agregar "reintentar análisis IA" en la UI.

**¿Puedo cancelar mi emergencia?**
Aún no hay endpoint `PUT /incidencias/{id}/cancelar`. Está en las preguntas pendientes del roadmap.

**¿Cómo se ve el flag `requiere_revision_manual` en la API real?**
Es un `bool` en el nivel raíz de `IncidenteDetalle`, con `true` si la confianza de la IA fue < 0.6.

**¿Qué hago si el `updatedAt` de dos asignaciones es idéntico al milisegundo?**
Edge case improbable. Si pasa, `asignacionActual` puede elegir cualquiera. Si querés estabilidad, ordenar por `idAsignacion DESC` también. En la práctica el backend siempre actualiza en commits distintos, así que no debería suceder.
