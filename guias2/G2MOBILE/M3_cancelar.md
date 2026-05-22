# M3 — Botón "Cancelar servicio" + UI compensación

> **Backend requerido:** [G2C1/F3](../G2C1/F3_cancelacion.md) implementado.
> **Esfuerzo:** 0.5 día.

## Objetivo
En la pantalla de detalle de asignación activa (después de que un taller aceptó), mostrar botón rojo "Cancelar servicio". Al tocarlo, pedir motivo en modal, mostrar la compensación calculada al taller.

Endpoint consumido:
- `POST /asignaciones/{id}/cancelar`

---

## Servicio

`flutter/lib/services/cancelacion_service.dart`:

```dart
import 'dart:convert';
import 'api_client.dart';

class CancelacionResponse {
  final int idAsignacion;
  final int idTaller;
  final String? canceladaPor;
  final String? motivoCancelacion;
  final double compensacionMonto;
  final bool compensacionPagada;
  final String nuevoEstado;

  CancelacionResponse({
    required this.idAsignacion,
    required this.idTaller,
    this.canceladaPor,
    this.motivoCancelacion,
    required this.compensacionMonto,
    required this.compensacionPagada,
    required this.nuevoEstado,
  });

  factory CancelacionResponse.fromJson(Map<String, dynamic> j) => CancelacionResponse(
    idAsignacion: j['id_asignacion'],
    idTaller: j['id_taller'],
    canceladaPor: j['cancelada_por'],
    motivoCancelacion: j['motivo_cancelacion'],
    compensacionMonto: (j['compensacion_monto'] as num).toDouble(),
    compensacionPagada: j['compensacion_pagada'],
    nuevoEstado: j['nuevo_estado'],
  );
}

class CancelacionService {
  final _client = ApiClient();

  Future<CancelacionResponse> cancelar(int idAsignacion, String motivo) async {
    final r = await _client.post(
      '/asignaciones/$idAsignacion/cancelar',
      body: {'motivo': motivo},
    );
    if (r.statusCode == 409) {
      throw jsonDecode(r.body)['detail'] ?? 'No se puede cancelar';
    }
    if (r.statusCode != 200) {
      throw jsonDecode(r.body)['detail'] ?? 'Error cancelando';
    }
    return CancelacionResponse.fromJson(jsonDecode(r.body));
  }
}
```

---

## Widget reusable: botón + modal

`flutter/lib/widgets/cancelar_button.dart`:

```dart
import 'package:flutter/material.dart';
import '../services/cancelacion_service.dart';

class CancelarButton extends StatefulWidget {
  final int idAsignacion;
  final VoidCallback? onCancelado;
  const CancelarButton({super.key, required this.idAsignacion, this.onCancelado});

  @override
  State<CancelarButton> createState() => _CancelarButtonState();
}

class _CancelarButtonState extends State<CancelarButton> {
  bool _enviando = false;

  Future<void> _abrirModal() async {
    final motivoCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancelar servicio'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Indica el motivo (mínimo 3 caracteres):'),
            const SizedBox(height: 8),
            TextField(
              controller: motivoCtrl,
              decoration: const InputDecoration(
                hintText: 'Ej: Llegó mi seguro',
                border: OutlineInputBorder(),
              ),
              maxLength: 500,
              minLines: 2,
              maxLines: 4,
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              color: Colors.amber.shade50,
              child: const Row(children: [
                Icon(Icons.info_outline, size: 18),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Si el taller ya estaba en camino, recibirá una compensación por su desplazamiento.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ]),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Volver')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: motivoCtrl.text.trim().length < 3
                ? null
                : () => Navigator.pop(ctx, true),
            child: const Text('Cancelar servicio'),
          ),
        ],
      ),
    );

    if (ok != true) return;
    await _ejecutarCancelacion(motivoCtrl.text.trim());
  }

  Future<void> _ejecutarCancelacion(String motivo) async {
    setState(() => _enviando = true);
    try {
      final resp = await CancelacionService().cancelar(widget.idAsignacion, motivo);
      if (!mounted) return;
      await _mostrarConfirmacion(resp);
      widget.onCancelado?.call();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  Future<void> _mostrarConfirmacion(CancelacionResponse r) async {
    await showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Servicio cancelado'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.check_circle, color: Colors.green),
              const SizedBox(width: 8),
              Text('Estado: ${r.nuevoEstado}'),
            ]),
            const SizedBox(height: 16),
            if (r.compensacionMonto == 0)
              const Text('Sin compensación al taller (no había salido).')
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Compensación al taller: \$${r.compensacionMonto.toStringAsFixed(2)}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    r.compensacionPagada
                        ? 'Ya está pagada'
                        : 'Pendiente de cobro por el taller',
                    style: TextStyle(color: Colors.grey.shade700),
                  ),
                ],
              ),
          ],
        ),
        actions: [
          ElevatedButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Entendido'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.red,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 12),
        ),
        onPressed: _enviando ? null : _abrirModal,
        icon: _enviando
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : const Icon(Icons.cancel),
        label: const Text('Cancelar servicio', style: TextStyle(fontSize: 16)),
      ),
    );
  }
}
```

---

## Uso desde detalle de asignación

En `screens/tracking_screen.dart` o `detalle_asignacion_screen.dart`:

```dart
import '../widgets/cancelar_button.dart';

Column(
  children: [
    // ... otros widgets (mapa, ETA, info técnico)
    const Divider(),
    Padding(
      padding: const EdgeInsets.all(16),
      child: CancelarButton(
        idAsignacion: widget.idAsignacion,
        onCancelado: () {
          // navegar al historial o home
          Navigator.popUntil(context, ModalRoute.withName('/home'));
        },
      ),
    ),
  ],
)
```

---

## Validación manual

| Estado de la asignación al cancelar | Compensación esperada |
|---|---|
| `pendiente` (taller no aceptó) | $0 |
| `aceptada` (aceptó pero no salió) | 50% de su `tarifa_traslado` |
| `en_camino` o `llegado` | 100% de su `tarifa_traslado` |
| `completada` | 409 — no se puede |
| `cancelada` | 409 — ya cancelada |

Probar los 5 escenarios cambiando `id_estado_asignacion` en BD antes de tocar el botón.

## Checklist de cierre M3
- [ ] Modal con `TextField` validando ≥3 caracteres.
- [ ] Banner informativo de la regla de compensación.
- [ ] Botón "Cancelar servicio" deshabilitado mientras motivo < 3.
- [ ] Llamada al endpoint con manejo de 409 (snackbar).
- [ ] Modal de confirmación con monto formateado.
- [ ] Texto distinto si compensación = 0.
- [ ] Callback `onCancelado` permite cerrar la pantalla.
