# Guía de Actualización — App Móvil del Técnico (Flutter)

> **Contexto importante**: la app del técnico es **nueva**. Antes no existía porque los técnicos no tenían login propio. Esta guía cubre lo que **ya está listo en backend** (autenticación) y cómo dejar preparada la estructura del app para cuando lleguen el resto de endpoints.

---

## 1. Estado actual del backend

### ✅ Listo para consumir HOY

| Método | Ruta | Uso |
|---|---|---|
| POST | `/tecnicos/login` | Autenticación del técnico con email + password |

Eso es **todo** lo que tiene endpoint propio para el token del técnico.

### ⏳ Pendiente de implementar (próxima iteración)

El backend **aún no expone** estos endpoints con token de técnico. Cuando lleguen se activarán las pantallas correspondientes:

| Método | Ruta | Uso futuro |
|---|---|---|
| GET | `/tecnicos/mi-perfil` | Ver mis datos |
| GET | `/tecnicos/mis-asignaciones?estado=...` | Listar mis trabajos |
| GET | `/tecnicos/mis-asignaciones/{id}` | Detalle de un trabajo |
| PUT | `/tecnicos/mi-ubicacion` | Reportar GPS actual (tracking) |
| PUT | `/tecnicos/mis-asignaciones/{id}/iniciar-viaje` | Técnico marca que sale |
| PUT | `/tecnicos/mis-asignaciones/{id}/completar` | Técnico marca que terminó |

**Recomendación:** construir el app con todas las pantallas ya diseñadas pero poniendo placeholder en las que necesitan endpoints pendientes. Cuando el backend los publique, solo conectás el servicio y listo — no hay que reescribir.

---

## 2. Cómo se crea el acceso del técnico

El técnico **no se registra solo**. El gerente del taller lo crea desde su panel web con email + password inicial:

```
POST /talleres/mi-taller/tecnicos  (token del gerente)
{
  "nombre": "Juan Pérez",
  "telefono": "+591 70000000",
  "email": "juan.tecnico@taller.com",
  "password": "juan123!"
}
```

El gerente le comunica las credenciales al técnico por un canal externo (verbal, WhatsApp, papel). El técnico luego hace login en la app.

**Campos email/password son opcionales** en la creación del técnico. Si no se asignan, el técnico queda como "registro operativo" sin login (como funcionaba antes). Si el gerente después quiere darle acceso, usa `PUT /talleres/mi-taller/tecnicos/{id}` con `email` y `password`.

---

## 3. Modelos Dart

### 3.1 Login

```dart
// lib/models/tecnico_auth.dart

class TecnicoLoginRequest {
  final String email;
  final String password;

  TecnicoLoginRequest({required this.email, required this.password});

  Map<String, dynamic> toJson() => {
    'email': email,
    'password': password,
  };
}

class TecnicoTokenResponse {
  final String accessToken;
  final String tokenType;     // siempre "bearer"
  final TecnicoResponse tecnico;

  TecnicoTokenResponse.fromJson(Map<String, dynamic> j)
    : accessToken = j['access_token'],
      tokenType = j['token_type'],
      tecnico = TecnicoResponse.fromJson(j['tecnico']);
}
```

### 3.2 Técnico

```dart
class TecnicoResponse {
  final int idTecnico;
  final int idTaller;
  final String nombre;
  final String? email;
  final String? telefono;
  final bool disponible;
  final double? latitud;
  final double? longitud;
  final bool activo;
  final DateTime createdAt;

  TecnicoResponse.fromJson(Map<String, dynamic> j)
    : idTecnico = j['id_tecnico'],
      idTaller = j['id_taller'],
      nombre = j['nombre'],
      email = j['email'],
      telefono = j['telefono'],
      disponible = j['disponible'],
      latitud = (j['latitud'] as num?)?.toDouble(),
      longitud = (j['longitud'] as num?)?.toDouble(),
      activo = j['activo'],
      createdAt = DateTime.parse(j['created_at']);
}
```

### 3.3 Asignación (para cuando lleguen los endpoints)

Reusá los modelos `Asignacion`, `EstadoAsignacion`, `IncidenteParaTaller` que ya tenés en el código compartido (son los mismos que usa el taller web). Si tu app del técnico es un proyecto separado, copiá esos modelos de la guía del taller.

---

## 4. Servicio de autenticación

```dart
// lib/services/tecnico_auth_service.dart
class TecnicoAuthService {
  final Dio _dio;
  final FlutterSecureStorage _storage;

  TecnicoAuthService(this._dio, this._storage);

  Future<TecnicoTokenResponse> login(String email, String password) async {
    final r = await _dio.post(
      '/tecnicos/login',
      data: TecnicoLoginRequest(email: email, password: password).toJson(),
    );
    final token = TecnicoTokenResponse.fromJson(r.data);

    // Guardar en almacenamiento seguro
    await _storage.write(key: 'tecnico_token', value: token.accessToken);
    await _storage.write(key: 'tecnico_id', value: token.tecnico.idTecnico.toString());

    return token;
  }

  Future<void> logout() async {
    await _storage.delete(key: 'tecnico_token');
    await _storage.delete(key: 'tecnico_id');
  }

  Future<String?> tokenGuardado() => _storage.read(key: 'tecnico_token');
}
```

**Dio interceptor** para agregar el token automáticamente:

```dart
// lib/main.dart (o donde configures Dio)
dio.interceptors.add(InterceptorsWrapper(
  onRequest: (options, handler) async {
    final token = await FlutterSecureStorage().read(key: 'tecnico_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  },
  onError: (e, handler) async {
    // Si token expiró → forzar logout
    if (e.response?.statusCode == 401) {
      await FlutterSecureStorage().deleteAll();
      // navegar a login
    }
    handler.next(e);
  },
));
```

---

## 5. Pantallas listas para construir AHORA

### 5.1 Login

```dart
class TecnicoLoginScreen extends StatefulWidget {
  @override State<TecnicoLoginScreen> createState() => _TecnicoLoginState();
}

class _TecnicoLoginState extends State<TecnicoLoginScreen> {
  final _emailCtrl = TextEditingController();
  final _pwdCtrl = TextEditingController();
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.build_circle, size: 80, color: Colors.orange),
          const SizedBox(height: 24),
          const Text('Panel del Técnico', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 32),
          TextField(
            controller: _emailCtrl,
            decoration: const InputDecoration(
              labelText: 'Email',
              prefixIcon: Icon(Icons.email),
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _pwdCtrl,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Contraseña',
              prefixIcon: Icon(Icons.lock),
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : _iniciarSesion,
            child: _loading
              ? const CircularProgressIndicator()
              : const Text('Iniciar sesión'),
          ),
          const SizedBox(height: 16),
          const Text(
            'Las credenciales te las entrega tu gerente del taller.',
            style: TextStyle(color: Colors.grey, fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ]),
      ),
    );
  }

  Future<void> _iniciarSesion() async {
    setState(() => _loading = true);
    try {
      final tok = await context.read<TecnicoAuthService>()
        .login(_emailCtrl.text.trim(), _pwdCtrl.text);

      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(
        builder: (_) => HomeScreen(tecnico: tok.tecnico),
      ));
    } on DioException catch (e) {
      final msg = e.response?.data?['detail'] ?? 'Error al iniciar sesión';
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg.toString())),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
}
```

### Errores del login

| Código | Mensaje del backend | Causa |
|---|---|---|
| 401 | `Email o contraseña incorrectos` | Credenciales inválidas, o el técnico no tiene password configurado |
| 403 | `El técnico ha sido desactivado` | El gerente dio de baja al técnico (`activo=false`) |

### 5.2 Home (post-login)

Mostrá bienvenida + info del técnico + accesos rápidos. Mientras las pantallas de trabajos y GPS no tengan backend, usá placeholders.

```dart
class HomeScreen extends StatelessWidget {
  final TecnicoResponse tecnico;
  const HomeScreen({required this.tecnico, super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Hola, ${tecnico.nombre.split(" ").first}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<TecnicoAuthService>().logout();
              if (!context.mounted) return;
              Navigator.pushReplacement(context, MaterialPageRoute(
                builder: (_) => TecnicoLoginScreen(),
              ));
            },
          ),
        ],
      ),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Card(
          child: ListTile(
            leading: CircleAvatar(child: Text(tecnico.nombre[0])),
            title: Text(tecnico.nombre),
            subtitle: Text(tecnico.email ?? ''),
            trailing: Chip(
              label: Text(tecnico.disponible ? 'Disponible' : 'Ocupado'),
              backgroundColor: tecnico.disponible ? Colors.green.shade100 : Colors.grey.shade300,
            ),
          ),
        ),
        const SizedBox(height: 24),

        // PENDIENTE — habilitar cuando exista GET /tecnicos/mis-asignaciones
        _buildMenuCard(
          icon: Icons.assignment,
          title: 'Mis trabajos',
          subtitle: 'Próximamente',
          enabled: false,
          onTap: () {},
        ),

        // PENDIENTE — habilitar cuando exista PUT /tecnicos/mi-ubicacion
        _buildMenuCard(
          icon: Icons.my_location,
          title: 'Compartir mi ubicación',
          subtitle: 'Próximamente',
          enabled: false,
          onTap: () {},
        ),
      ]),
    );
  }

  Widget _buildMenuCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool enabled,
    required VoidCallback onTap,
  }) => Opacity(
    opacity: enabled ? 1 : 0.4,
    child: Card(
      child: ListTile(
        leading: Icon(icon, size: 32),
        title: Text(title),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: enabled ? onTap : null,
      ),
    ),
  );
}
```

---

## 6. Pantallas futuras (scaffold preparado)

Dejá estos archivos creados con TODOs. Cuando el backend publique los endpoints, solo conectás el servicio.

### 6.1 Mis trabajos

```dart
// lib/screens/mis_trabajos_screen.dart
// PENDIENTE: requiere GET /tecnicos/mis-asignaciones
class MisTrabajosScreen extends StatefulWidget {
  @override State<MisTrabajosScreen> createState() => _MisTrabajosState();
}

class _MisTrabajosState extends State<MisTrabajosScreen> {
  // TODO: llamar a service.misAsignaciones(estado: filtro)
  // List<Asignacion> _trabajos = [];

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Mis trabajos')),
    body: const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.construction, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text(
            'Pantalla en desarrollo.\nPronto podrás ver tus trabajos asignados.',
            textAlign: TextAlign.center,
          ),
        ]),
      ),
    ),
  );
}
```

### 6.2 Detalle de trabajo

Cuando exista `GET /tecnicos/mis-asignaciones/{id}`, esta pantalla mostrará:
- Datos del cliente (nombre, teléfono)
- Datos del vehículo (placa, marca, modelo)
- Ubicación GPS del incidente (botón "abrir en Google Maps")
- Categoría y prioridad
- Resumen de la IA
- Botón "Iniciar viaje" cuando estado = `aceptada`
- Botón "Completar" cuando estado = `en_camino`

### 6.3 Tracking de ubicación

Cuando exista `PUT /tecnicos/mi-ubicacion`, esta pantalla:
- Pide permiso de geolocalización
- Corre un `Timer.periodic` cada 15-30s que obtiene lat/lng y hace PUT
- Botón "Dejar de compartir" cuando el trabajo esté completado

```dart
// Placeholder mostrando el flujo esperado
Timer.periodic(const Duration(seconds: 20), (_) async {
  final pos = await Geolocator.getCurrentPosition();
  await _dio.put('/tecnicos/mi-ubicacion', data: {
    'latitud': pos.latitude,
    'longitud': pos.longitude,
  });
});
```

---

## 7. Consideraciones de UX para producción

- **Permisos de ubicación:** pedirlos al iniciar viaje, no antes. Explicar por qué.
- **Modo background:** la app debe seguir enviando GPS mientras el técnico maneja. Evaluar `flutter_background_service` o similar.
- **Consumo de batería:** si el intervalo de GPS es muy bajo (< 10s) se drena rápido. 20-30s es sano.
- **Sin conexión:** cachear el último trabajo visto para que el técnico no quede en blanco si pierde internet al llegar.
- **Confirmaciones antes de acciones destructivas:** diálogo antes de `completar` (no se puede revertir).

---

## 8. Checklist de implementación

### Lo que podés terminar ahora

- [ ] Modelos `TecnicoLoginRequest`, `TecnicoTokenResponse`, `TecnicoResponse`
- [ ] `TecnicoAuthService` con login + logout + token en `FlutterSecureStorage`
- [ ] Interceptor Dio que inyecta el Bearer token y maneja 401
- [ ] `TecnicoLoginScreen` funcional con validación de errores
- [ ] `HomeScreen` mostrando datos del técnico post-login
- [ ] Navegación: si hay token guardado al abrir, ir directo a Home; sino a Login
- [ ] Pantalla "Próximamente" para Mis trabajos y Compartir ubicación

### Lo que queda dependiendo del backend

- [ ] Listar mis asignaciones (`GET /tecnicos/mis-asignaciones`)
- [ ] Filtro por estado (pendiente, aceptada, en_camino, completada)
- [ ] Detalle de trabajo con info del cliente + ubicación del incidente
- [ ] Botón "abrir mapa" con la lat/lng del incidente (Google Maps / Waze)
- [ ] Iniciar viaje desde el app del técnico
- [ ] Servicio de GPS periódico (20-30s) mientras estado = `en_camino`
- [ ] Completar trabajo con formulario (costo + resumen)

---

## 9. Credenciales de prueba

Hoy los técnicos de seed **no tienen credenciales** (se crearon cuando la columna no existía). Para probar el login, el gerente debe agregar credenciales a uno existente o crear uno nuevo.

**Ejemplo — crear técnico con credenciales (desde el panel del gerente o con curl):**

```bash
curl -X POST http://localhost:8000/talleres/mi-taller/tecnicos \
  -H "Authorization: Bearer <TOKEN_GERENTE>" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Tecnico Demo",
    "telefono": "+591 70000000",
    "email": "demo.tec@example.com",
    "password": "demo123!"
  }'
```

Luego en el app del técnico:
- Email: `demo.tec@example.com`
- Password: `demo123!`

---

## 10. Preguntas frecuentes

**¿Por qué no hay registro abierto?**
Decisión de seguridad: solo el gerente puede crear técnicos. Evita que cualquiera se registre y reciba asignaciones.

**¿El técnico puede cambiar su contraseña?**
Hoy no. Tiene que pedirle al gerente que la reinicie con `PUT /talleres/mi-taller/tecnicos/{id}` + nuevo password. En el futuro se podría agregar `PUT /tecnicos/mi-password`.

**¿Qué pasa si el gerente me desactiva (`activo=false`)?**
El siguiente intento de usar el token dará 403 `El técnico ha sido desactivado`. El interceptor debe cerrar sesión y redirigir al login.

**¿Puedo usar la app del técnico con el token del gerente/taller?**
No. Los endpoints `/tecnicos/*` validan `tipo="tecnico"` en el JWT. Un token de taller falla con 401.

**¿La app del técnico necesita backend nuevo o reusa lo del taller?**
Necesita endpoints propios. Hoy el taller tiene `GET /mi-taller/tecnicos/{id}/asignaciones` que el **gerente** puede consultar — pero el técnico no puede usar ese endpoint con su token. Esa duplicación es intencional: el gerente ve todos los técnicos, el técnico solo ve lo suyo.

**¿Y si no tengo login configurado todavía (el gerente no me dio password)?**
Tu cuenta existe en el taller pero no podés usar el app. Pedile al gerente que te configure acceso con `PUT /talleres/mi-taller/tecnicos/{mi_id}` + email + password.

**¿Cuándo estarán los endpoints pendientes?**
Próxima iteración. Esta guía se actualiza cuando se publiquen.
