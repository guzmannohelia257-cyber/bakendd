# Guía de Actualización Flutter — Motor de Asignación Inteligente de Talleres

Versión: 1.0
Fecha: 2026-04-20
Backend asociado: Yary Backend v1.0 con Motor de Asignación Inteligente

---

## 1. ¿Qué es el Motor de Asignación?

Después de que la IA **clasifica** un incidente (`POST /incidencias/{id_incidente}/analizar-ia`), el backend **automáticamente**:

1. Busca **talleres cercanos** (radio: 30 km desde lat/lng del incidente)
2. Filtra por **especialidad** (que atiendan esa categoría)
3. Calcula **score** para cada uno:
   - **40%** distancia (más cercano = mejor)
   - **30%** capacidad disponible (incidentes activos vs. máxima capacidad)
   - **30%** disponibilidad de técnicos (cuántos técnicos están libres)
4. Guarda **top 10 candidatos** en `candidato_asignacion`
5. Marca el **mejor como `seleccionado=true`** y crea una `asignacion` automática

**Output:** El incidente ya llega a Flutter con **lista de talleres** (1 seleccionado + 9 alternativas).

---

## 2. Estructura de datos que recibe Flutter

**⚠️ IMPORTANTE:** Los candidatos se calculan **SOLO después** de que Flutter presiona "Analizar con IA".

**Cronología:**
1. `POST /incidencias/{id}` → Crea incidente (sin candidatos, `candidatos: null`)
2. `POST /incidencias/{id}/analizar-ia` → IA clasifica + Motor busca talleres → `candidatos: [...]` se calcula
3. `GET /incidencias/{id}` → Retorna incidente con candidatos ya incluidos

Cuando Flutter hace `GET /incidencias/{id_incidente}` **después del análisis**, **la respuesta incluye** los candidatos ya calculados en el modelo del incidente.

### Cambio en el modelo `Incidente` (si lo hace manualmente)

Agregue este campo en `lib/models/incidente.dart`:

```dart
class Incidente {
  // ... campos existentes ...
  
  final List<CandidatoAsignacion>? candidatos;  // ← NUEVO

  Incidente({
    // ... parámetros existentes ...
    this.candidatos,
  });

  factory Incidente.fromJson(Map<String, dynamic> json) {
    return Incidente(
      // ... parsing existente ...
      candidatos: (json['candidatos'] as List?)
          ?.map((c) => CandidatoAsignacion.fromJson(c as Map<String, dynamic>))
          .toList(),
    );
  }
}
```

### Nuevo modelo `CandidatoAsignacion`

Cree `lib/models/candidato_asignacion.dart`:

```dart
class CandidatoAsignacion {
  final int idCandidato;
  final int idIncidente;
  final int idTaller;
  final double? distanciaKm;
  final double? scoreTotal;
  final bool seleccionado;
  
  final TallerMini taller;

  CandidatoAsignacion({
    required this.idCandidato,
    required this.idIncidente,
    required this.idTaller,
    this.distanciaKm,
    this.scoreTotal,
    required this.seleccionado,
    required this.taller,
  });

  factory CandidatoAsignacion.fromJson(Map<String, dynamic> json) {
    return CandidatoAsignacion(
      idCandidato: json['id_candidato'],
      idIncidente: json['id_incidente'],
      idTaller: json['id_taller'],
      distanciaKm: (json['distancia_km'] as num?)?.toDouble(),
      scoreTotal: (json['score_total'] as num?)?.toDouble(),
      seleccionado: json['seleccionado'] ?? false,
      taller: TallerMini.fromJson(json['taller']),
    );
  }
}

class TallerMini {
  final int idTaller;
  final String nombre;
  final String? direccion;
  final String? telefono;

  TallerMini({
    required this.idTaller,
    required this.nombre,
    this.direccion,
    this.telefono,
  });

  factory TallerMini.fromJson(Map<String, dynamic> json) {
    return TallerMini(
      idTaller: json['id_taller'],
      nombre: json['nombre'],
      direccion: json['direccion'],
      telefono: json['telefono'],
    );
  }
}
```

---

## 3. Respuesta JSON del backend (POST /incidencias/{id}/analizar-ia)

**Después de analizar con IA**, la respuesta incluye:
- ✅ Campos de clasificación IA (`resumen_ia`, `clasificacion_ia_confianza`, `requiere_revision_manual`)
- ✅ Categoría y prioridad detectadas
- ✅ **Top 10 candidatos de talleres** con scores y datos del taller

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
  "descripcion_usuario": "Mi auto no enciende",
  "resumen_ia": "Batería descargada o falla de alternador. Requiere reemplazo o recarga. Cliente en zona urbana segura.",
  "clasificacion_ia_confianza": 0.92,
  "requiere_revision_manual": false,
  "created_at": "2026-04-20T15:30:00Z",
  "updated_at": "2026-04-20T15:32:15Z",
  
  "estado": { "id_estado": 1, "nombre": "pendiente" },
  "categoria": { "id_categoria": 2, "nombre": "Batería" },
  "prioridad": { "id_prioridad": 2, "nivel": "media", "orden": 2 },
  
  "candidatos": [
    {
      "id_candidato": 1,
      "id_incidente": 12,
      "id_taller": 5,
      "distancia_km": 2.5,
      "score_total": 87.3,
      "seleccionado": true,
      "taller": {
        "id_taller": 5,
        "nombre": "Taller Veloz",
        "direccion": "Calle 123, Esquina Av. Principal",
        "telefono": "555-1234"
      }
    },
    {
      "id_candidato": 2,
      "id_incidente": 12,
      "id_taller": 8,
      "distancia_km": 5.1,
      "score_total": 74.2,
      "seleccionado": false,
      "taller": {
        "id_taller": 8,
        "nombre": "Taller Rápido",
        "direccion": "Av. Secundaria 456",
        "telefono": "555-5678"
      }
    },
    {
      "id_candidato": 3,
      "id_incidente": 12,
      "id_taller": 12,
      "distancia_km": 8.3,
      "score_total": 68.5,
      "seleccionado": false,
      "taller": {
        "id_taller": 12,
        "nombre": "Taller Express",
        "direccion": "Zona Industrial, Lote 7",
        "telefono": "555-9999"
      }
    }
    {\n      "id_candidato": 4,
      "id_incidente": 12,
      "id_taller": 15,
      "distancia_km": 12.1,
      "score_total": 52.3,
      "seleccionado": false,
      "taller": {
        "id_taller": 15,
        "nombre": "Taller Central",
        "direccion": "Centro de la ciudad",
        "telefono": "555-4444"
      }
    }
    // ... hasta 10 candidatos total (ordenados por score descendente)
  ]
}
```

**Notas sobre la respuesta:**
- El **primer candidato** (`candidatos[0]`) siempre tiene `seleccionado: true` → ya se creó una `asignacion` automática
- Los **demás candidatos** (`[1]...[9]`) tienen `seleccionado: false` → son alternativas
- Si el incidente **aún NO fue analizado** → `candidatos: null` o `candidatos: []`
- Los candidatos están **ordenados por score descendente** (mejor primero)

---

## 4. Integración en Flutter UI

### 4.1 En la pantalla de detalle del incidente

Después de mostrar la sección de IA, agrega una sección **"Talleres Disponibles"**:

```dart
if (incidente.candidatos != null && incidente.candidatos!.isNotEmpty) ...[
  const Divider(height: 32),
  Row(
    children: [
      const Icon(Icons.apartment, color: Colors.blue, size: 20),
      const SizedBox(width: 8),
      const Text(
        'Talleres Disponibles',
        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
      ),
    ],
  ),
  const SizedBox(height: 12),
  ListView.builder(
    shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(),
    itemCount: incidente.candidatos!.length,
    itemBuilder: (ctx, idx) {
      final candidato = incidente.candidatos![idx];
      return _buildCandidatoCard(candidato, idx);
    },
  ),
],
```

### 4.2 Widget para cada tarjeta de taller

```dart
Widget _buildCandidatoCard(CandidatoAsignacion candidato, int posicion) {
  final esSeleccionado = candidato.seleccionado;
  
  return Container(
    margin: const EdgeInsets.symmetric(vertical: 8),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: esSeleccionado ? Colors.blue.shade50 : Colors.grey.shade50,
      border: Border.all(
        color: esSeleccionado ? Colors.blue : Colors.grey.shade300,
        width: esSeleccionado ? 2 : 1,
      ),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Encabezado con posición y badge
        Row(
          children: [
            // Número de posición
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: esSeleccionado ? Colors.blue : Colors.grey,
              ),
              child: Center(
                child: Text(
                  '${posicion + 1}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            
            // Nombre del taller
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    candidato.taller.nombre,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    candidato.taller.direccion ?? 'Ubicación no disponible',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            
            // Badge "Seleccionado" o score
            if (esSeleccionado)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  '✓ Asignado',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              )
            else
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.orange.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${candidato.scoreTotal?.toStringAsFixed(0)}% match',
                  style: TextStyle(
                    color: Colors.orange.shade700,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
          ],
        ),
        
        const SizedBox(height: 12),
        
        // Detalles (distancia, teléfono, etc.)
        Row(
          children: [
            Expanded(
              child: Row(
                children: [
                  Icon(Icons.location_on, size: 14, color: Colors.grey.shade600),
                  const SizedBox(width: 4),
                  Text(
                    '${candidato.distanciaKm?.toStringAsFixed(1)} km',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ),
            if (candidato.taller.telefono != null)
              Expanded(
                child: Row(
                  children: [
                    Icon(Icons.phone, size: 14, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        candidato.taller.telefono!,
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey.shade600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
        
        const SizedBox(height: 12),
        
        // Botón de contacto (solo si no está seleccionado)
        if (!esSeleccionado)
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              icon: const Icon(Icons.phone),
              label: const Text('Contactar'),
              onPressed: () {
                // TODO: Abrir dialer o chat
                _contactarTaller(candidato);
              },
            ),
          ),
      ],
    ),
  );
}
```

---

## 5. Lógica auxiliar

### 5.1 Método para contactar al taller

```dart
void _contactarTaller(CandidatoAsignacion candidato) {
  final phone = candidato.taller.telefono;
  if (phone == null || phone.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Teléfono no disponible')),
    );
    return;
  }

  // Opción 1: Abrir dialer
  launchUrl(Uri(scheme: 'tel', path: phone));
  
  // Opción 2: Abrir WhatsApp (si lo implementas)
  // launchUrl(Uri.parse('https://wa.me/+$phone'));
}
```

### 5.2 Método para cambiar de taller (futuro)

Si quieres permitir que el cliente cambie el taller seleccionado:

```dart
Future<void> _cambiarATaller(CandidatoAsignacion nuevoTaller) async {
  // Llamar a: PUT /incidencias/{id_incidente}/cambiar-taller
  // (endpoint que se implementará en el backend después)
  
  final token = await AuthService.getToken();
  final response = await http.put(
    Uri.parse('$baseUrl/incidencias/${widget.incidente.idIncidente}/cambiar-taller'),
    headers: {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      'id_candidato': nuevoTaller.idCandidato,
    }),
  );

  if (response.statusCode == 200) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Taller cambiado correctamente'),
        backgroundColor: Colors.green,
      ),
    );
    // Refrescar incidente
    _cargarIncidente();
  } else {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Error al cambiar taller'),
        backgroundColor: Colors.red,
      ),
    );
  }
}
```

---

## 6. Checklist de implementación

- [ ] Modelo `CandidatoAsignacion` creado en `lib/models/candidato_asignacion.dart`
- [ ] Modelo `Incidente` actualizado con campo `candidatos`
- [ ] `Incidente.fromJson()` parsea correctamente la lista de candidatos
- [ ] Widget `_buildCandidatoCard()` implementado
- [ ] Sección "Talleres Disponibles" aparece en pantalla de detalle
- [ ] El primer candidato (seleccionado=true) aparece resaltado en verde
- [ ] Los demás candidatos muestran su score y distancia
- [ ] Botón "Contactar" funciona (abre dialer o whatsapp)
- [ ] Se muestran hasta 10 opciones de taller
- [ ] Los datos de taller se muestran correctamente (nombre, dirección, teléfono)

---

## 7. Procedimiento de prueba end-to-end

1. **Login** con usuario de prueba
2. **Crear vehículo** (si no tienes)
3. **Reportar incidente** con descripción
4. **Subir 1-2 fotos** como evidencia
5. **Presionar "Analizar con IA"** → espera 3-8 segundos
6. **En pantalla de detalle**, desplázate hacia abajo
7. **Verifica que aparezca sección "Talleres Disponibles"** con:
   - 🏆 **Primer taller** (score mayor, badge "✓ Asignado" en verde)
   - 🏪 **Talleres 2-10** (score menor, badge "% match" en naranja)
   - 📍 Distancia en km
   - 📞 Teléfono
   - 🔘 Botón "Contactar"
8. **Presiona "Contactar"** → abre dialer o WhatsApp

---

## 8. Algoritmo de scoring (referencia)

Backend calcula:

```
score_distancia = 1 - (distancia / 30)  → [0..1]
score_capacidad = (capacidad_max - incidentes_activos) / capacidad_max  → [0..1]
score_disponibilidad = min(1, tecnicos_disponibles / 2)  → [0..1]

score_total = (
  score_distancia * 0.40 +
  score_capacidad * 0.30 +
  score_disponibilidad * 0.30
) * 100
```

**Resultado:** Score 0-100, ordenado descendente. Top 10 se guardan.

---

## 9. Notas importantes

- ⚠️ **Los candidatos se calculan SOLO después del análisis con IA.** Si aún no llamaste a `analizar-ia`, el array `candidatos` estará vacío.
- ⚠️ **El backend busca talleres en 30 km de radio**. Si hay menos de 3 en esa área, retorna los que encuentre (o error si no hay ninguno).
- ⚠️ **El taller "mejor" (score mayor) siempre tiene `seleccionado=true`** y ya se creó una `asignacion` automática con él.
- ✅ **Futura mejora:** Endpoint para cambiar de taller sin necesidad de reportar de nuevo.

---

## 10. Resumen ultrarrápido

| Acción | Dónde |
|--------|-------|
| Crear modelo `CandidatoAsignacion` | `lib/models/candidato_asignacion.dart` |
| Actualizar modelo `Incidente` | `lib/models/incidente.dart` |
| Mostrar lista de talleres | `lib/screens/detalle_incidente_screen.dart` |
| Widget para tarjeta de taller | `_buildCandidatoCard()` en detalle |
| Botón "Contactar" | Llamada a `launchUrl()` o chat |

Total: **~200 líneas de Dart** repartidas en 2-3 archivos. Sin dependencias nuevas.
