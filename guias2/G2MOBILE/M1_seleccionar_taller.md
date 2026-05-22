# M1 — Pantalla "Seleccionar taller" (cliente, filtro por categoría)

> **Backend requerido:** [G2C1/F1](../G2C1/F1_servicios_extendidos.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
Tras clasificar el incidente (IA o manual), el cliente ve los talleres compatibles ordenados por cercanía. Si la categoría `requiere_cotizacion=true`, el flujo pasa a [M2](./M2_cotizacion.md). Si no, asigna directo al taller elegido.

Endpoints consumidos:
- `GET /categorias` — para clasificación manual y mostrar info de categoría
- `GET /talleres/compatibles?id_categoria=X&latitud=Y&longitud=Z&radio_km=20`

---

## Modelo

`flutter/lib/models/taller.dart`:

```dart
class TallerCompatible {
  final int idTaller;
  final String nombre;
  final String? telefono;
  final double? latitud;
  final double? longitud;
  final double? distanciaKm;
  final double? tarifaBase;
  final double? ratingPromedio;
  final bool disponible;

  TallerCompatible({
    required this.idTaller,
    required this.nombre,
    this.telefono,
    this.latitud,
    this.longitud,
    this.distanciaKm,
    this.tarifaBase,
    this.ratingPromedio,
    this.disponible = true,
  });

  factory TallerCompatible.fromJson(Map<String, dynamic> j) => TallerCompatible(
    idTaller: j['id_taller'],
    nombre: j['nombre'],
    telefono: j['telefono'],
    latitud: (j['latitud'] as num?)?.toDouble(),
    longitud: (j['longitud'] as num?)?.toDouble(),
    distanciaKm: (j['distancia_km'] as num?)?.toDouble(),
    tarifaBase: (j['tarifa_base'] as num?)?.toDouble(),
    ratingPromedio: (j['rating_promedio'] as num?)?.toDouble(),
    disponible: j['disponible'] ?? true,
  );
}
```

`flutter/lib/models/categoria.dart`:

```dart
class Categoria {
  final int idCategoria;
  final String? codigo;
  final String nombre;
  final String? descripcion;
  final bool requiereCotizacion;

  Categoria({
    required this.idCategoria,
    this.codigo,
    required this.nombre,
    this.descripcion,
    required this.requiereCotizacion,
  });

  factory Categoria.fromJson(Map<String, dynamic> j) => Categoria(
    idCategoria: j['id_categoria'],
    codigo: j['codigo'],
    nombre: j['nombre'],
    descripcion: j['descripcion'],
    requiereCotizacion: j['requiere_cotizacion'] ?? false,
  );
}
```

---

## Servicio

`flutter/lib/services/taller_service.dart`:

```dart
import 'dart:convert';
import '../config/api_config.dart';
import '../models/categoria.dart';
import '../models/taller.dart';
import 'api_client.dart';

class TallerService {
  final _client = ApiClient();

  Future<List<Categoria>> listarCategorias() async {
    final r = await _client.get('/categorias');
    if (r.statusCode != 200) throw 'Error listando categorias';
    return (jsonDecode(r.body) as List).map((j) => Categoria.fromJson(j)).toList();
  }

  Future<List<TallerCompatible>> compatibles({
    required int idCategoria,
    required double latitud,
    required double longitud,
    double radioKm = 20,
  }) async {
    final r = await _client.get(
      '/talleres/compatibles?id_categoria=$idCategoria'
      '&latitud=$latitud&longitud=$longitud&radio_km=$radioKm',
    );
    if (r.statusCode != 200) throw 'Error buscando talleres';
    return (jsonDecode(r.body) as List)
        .map((j) => TallerCompatible.fromJson(j))
        .toList();
  }
}
```

---

## Pantalla

`flutter/lib/screens/seleccionar_taller_screen.dart`:

```dart
import 'package:flutter/material.dart';
import '../models/categoria.dart';
import '../models/taller.dart';
import '../services/taller_service.dart';

class SeleccionarTallerScreen extends StatefulWidget {
  final Categoria categoria;
  final double latitud;
  final double longitud;

  const SeleccionarTallerScreen({
    super.key,
    required this.categoria,
    required this.latitud,
    required this.longitud,
  });

  @override
  State<SeleccionarTallerScreen> createState() => _SeleccionarTallerScreenState();
}

class _SeleccionarTallerScreenState extends State<SeleccionarTallerScreen> {
  final _svc = TallerService();
  bool cargando = true;
  String? error;
  List<TallerCompatible> talleres = [];
  double radioKm = 20;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() {
      cargando = true;
      error = null;
    });
    try {
      final lista = await _svc.compatibles(
        idCategoria: widget.categoria.idCategoria,
        latitud: widget.latitud,
        longitud: widget.longitud,
        radioKm: radioKm,
      );
      setState(() {
        talleres = lista;
        cargando = false;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
        cargando = false;
      });
    }
  }

  void _onTallerTap(TallerCompatible t) {
    if (widget.categoria.requiereCotizacion) {
      // Ir a flujo de cotizaciones (M2)
      Navigator.pushNamed(context, '/cotizar', arguments: {
        'categoria': widget.categoria,
        'taller_preferido': t,
      });
    } else {
      // Asignación directa (taller acepta o no)
      Navigator.pushNamed(context, '/esperando-taller', arguments: {
        'taller': t,
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Talleres compatibles'),
            Text(
              widget.categoria.nombre,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.normal),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          if (widget.categoria.requiereCotizacion)
            Container(
              padding: const EdgeInsets.all(12),
              color: Colors.amber.shade50,
              child: Row(children: const [
                Icon(Icons.info_outline, color: Colors.amber),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Este servicio requiere cotización previa. Podrás comparar precios antes de decidir.',
                  ),
                ),
              ]),
            ),

          // Filtro de radio
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Text('Radio: ${radioKm.toInt()} km'),
              Expanded(
                child: Slider(
                  value: radioKm,
                  min: 5, max: 50, divisions: 9,
                  onChanged: (v) => setState(() => radioKm = v),
                  onChangeEnd: (_) => _cargar(),
                ),
              ),
            ]),
          ),

          // Lista
          Expanded(
            child: _buildContenido(),
          ),
        ],
      ),
    );
  }

  Widget _buildContenido() {
    if (cargando) return const Center(child: CircularProgressIndicator());
    if (error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: Colors.red, size: 48),
            const SizedBox(height: 8),
            Text(error!),
            const SizedBox(height: 8),
            ElevatedButton(onPressed: _cargar, child: const Text('Reintentar')),
          ],
        ),
      );
    }
    if (talleres.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'No hay talleres compatibles en este radio. '
            'Amplía la búsqueda o intenta otra categoría.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return ListView.separated(
      itemCount: talleres.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (_, i) {
        final t = talleres[i];
        return ListTile(
          leading: CircleAvatar(child: Text('${i + 1}')),
          title: Text(t.nombre, style: const TextStyle(fontWeight: FontWeight.bold)),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (t.distanciaKm != null) Text('${t.distanciaKm!.toStringAsFixed(1)} km'),
              if (t.tarifaBase != null) Text('Desde \$${t.tarifaBase!.toStringAsFixed(0)}'),
              if (t.ratingPromedio != null)
                Row(children: [
                  const Icon(Icons.star, size: 14, color: Colors.amber),
                  Text(' ${t.ratingPromedio!.toStringAsFixed(1)}'),
                ]),
            ],
          ),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => _onTallerTap(t),
        );
      },
    );
  }
}
```

---

## Integración con la pantalla de "Reportar emergencia" existente

Después de clasificar el incidente (IA o manual), el flujo actual debe:
1. Obtener `id_categoria` (de la IA o selección manual).
2. Obtener `latitud`/`longitud` del GPS.
3. Navegar a `SeleccionarTallerScreen` con esos parámetros.

Ejemplo en el flujo de reportar:

```dart
// despues del POST /incidencias y obtener id_categoria clasificada
final categoria = await tallerService.getCategoria(idCategoria);  // del catalogo
Navigator.push(context, MaterialPageRoute(
  builder: (_) => SeleccionarTallerScreen(
    categoria: categoria,
    latitud: posicion.latitude,
    longitud: posicion.longitude,
  ),
));
```

---

## Validación manual
1. Backend levantado, 3 talleres en distintas categorías y zonas.
2. Login como cliente, reportar incidente "se me pinchó la llanta".
3. Tras clasificar, ver lista solo con talleres que atienden "llantas".
4. Cambiar radio del slider → ver que cambia la lista.
5. Tocar un taller de categoría directa → debe ir a `EsperandoTallerScreen`.
6. (Si pruebas con chapería) → debe ir a `CotizacionesScreen` (M2).

## Checklist de cierre M1
- [ ] Modelo `TallerCompatible` con todos los campos del response.
- [ ] Servicio HTTP funcional.
- [ ] Pantalla con slider de radio.
- [ ] Banner amarillo si la categoría requiere cotización.
- [ ] Empty state cuando no hay talleres.
- [ ] Loading + error con botón reintentar.
- [ ] Navegación condicional (cotizar vs directo).
