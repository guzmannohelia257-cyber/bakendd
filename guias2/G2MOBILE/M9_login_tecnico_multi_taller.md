# M9 — Login técnico con selector de taller (pre-login)

> **Backend requerido:** endpoints nuevos en `app/api/tecnicos.py` (especificados abajo).
> **Esfuerzo:** 0.5 día (backend) + 0.5 día (Flutter).

## Por qué esta guía existe

El técnico (rol=3) puede tener vínculo con **múltiples talleres** vía la tabla `usuario_taller` (M:N). En el JWT actual NO viaja `id_tenant`, así que el backend usa `.first()` arbitrario.

**Solución elegida**: el técnico **elige el taller ANTES del login**. El login le manda email + password + id_taller. El backend valida vínculo y devuelve token con `id_tenant` del taller elegido. A partir de ahí el filtro global tenant funciona automáticamente.

> Para el **cliente** (rol=1) no hay cambio: es público, sin tenant.
> Para el **taller web** tampoco: ya tiene `id_tenant` en el JWT.

---

## 1. Backend — nuevos endpoints

Agregar a `app/api/tecnicos.py`:

```python
from app.core.security import create_access_token, verify_password
from app.core.tenant_context import current_tenant
from app.models.usuario import Usuario
from app.models.taller import Taller
from app.models.usuario_taller import UsuarioTaller
from pydantic import BaseModel, EmailStr, Field


class TallerPublicoMini(BaseModel):
    id_taller: int
    nombre: str
    direccion: str | None = None
    latitud: float | None = None
    longitud: float | None = None

    class Config:
        from_attributes = True


@router.get(
    "/talleres-publicos",
    response_model=List[TallerPublicoMini],
    summary="Lista publica de talleres (para selector pre-login del tecnico)",
)
def talleres_publicos(db: Session = Depends(get_db)):
    """
    Publico (sin auth). Devuelve solo info no sensible: id, nombre, direccion,
    coordenadas. Lo consume Flutter en la pantalla de seleccion pre-login.
    """
    # Bypass del filtro tenant (no hay contexto)
    return (
        db.query(Taller)
        .filter(Taller.activo.is_(True))
        .order_by(Taller.nombre)
        .all()
    )


class TecnicoLoginRequest(BaseModel):
    email: EmailStr
    password: str
    id_taller: int = Field(..., gt=0)


@router.post(
    "/login",
    summary="Login del tecnico contra un taller especifico (pre-login)",
)
def login_tecnico(body: TecnicoLoginRequest, db: Session = Depends(get_db)):
    """
    Valida que:
      - email+password coinciden con un usuario rol=3.
      - usuario tiene vinculo activo con el taller indicado.
    Si todo OK, emite token con id_tenant del taller (filtro tenant queda activo).
    """
    # Bypass tenant filter para localizar usuario y vinculo
    tok = current_tenant.set(0)
    try:
        usuario = db.query(Usuario).filter(Usuario.email == body.email).first()
        if not usuario or not verify_password(body.password, usuario.password_hash):
            raise HTTPException(401, "Credenciales invalidas")
        if usuario.id_rol != 3:
            raise HTTPException(403, "Esta cuenta no es de tecnico")
        if not usuario.activo:
            raise HTTPException(403, "Cuenta desactivada")

        vinculo = (
            db.query(UsuarioTaller)
            .join(Taller, Taller.id_taller == UsuarioTaller.id_taller)
            .filter(
                UsuarioTaller.id_usuario == usuario.id_usuario,
                UsuarioTaller.id_taller == body.id_taller,
                UsuarioTaller.activo.is_(True),
            )
            .first()
        )
        if not vinculo:
            raise HTTPException(403, "No estas vinculado a este taller")

        taller = vinculo.taller
    finally:
        current_tenant.reset(tok)

    # Token con id_tenant -> filtro global aplica
    token = create_access_token(
        subject_id=usuario.id_usuario,
        tipo="usuario",
        extra_claims={
            "id_tenant": taller.id_tenant,
            "id_taller_activo": taller.id_taller,
        },
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id_usuario": usuario.id_usuario,
            "nombre": usuario.nombre,
            "email": usuario.email,
        },
        "taller_activo": {
            "id_taller": taller.id_taller,
            "id_tenant": taller.id_tenant,
            "nombre": taller.nombre,
        },
    }
```

### Fix del `/me/ubicacion` existente

Reemplazar `vinculo = ... .first()` por uso del contexto tenant:

```python
@router.post("/me/ubicacion", ...)
async def reportar_ubicacion(body: UbicacionPing, ...):
    if current_user.id_rol != 3:
        raise HTTPException(403, "Solo tecnicos")

    tid = current_tenant.get()
    if tid is None:
        raise HTTPException(
            400,
            "Token sin id_tenant. Loguea via POST /tecnicos/login indicando id_taller.",
        )

    # Buscar el vinculo ESPECIFICO de este taller (el del token)
    vinculo = (
        db.query(UsuarioTaller)
        .join(Taller)
        .filter(
            UsuarioTaller.id_usuario == current_user.id_usuario,
            Taller.id_tenant == tid,
            UsuarioTaller.activo.is_(True),
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(403, "Tu token no corresponde a un taller donde trabajes")

    # ... resto del codigo original (insertar UbicacionTecnico, broadcast, etc.)
```

### Endpoint para cambiar taller en runtime (opcional)

```python
@router.post(
    "/me/cambiar-taller/{id_taller}",
    summary="Tecnico cambia taller activo sin re-loguearse",
)
def cambiar_taller_activo(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.id_rol != 3:
        raise HTTPException(403, "Solo tecnicos")
    tok = current_tenant.set(0)
    try:
        vinculo = (
            db.query(UsuarioTaller)
            .join(Taller)
            .filter(
                UsuarioTaller.id_usuario == current_user.id_usuario,
                UsuarioTaller.id_taller == id_taller,
                UsuarioTaller.activo.is_(True),
            )
            .first()
        )
    finally:
        current_tenant.reset(tok)
    if not vinculo:
        raise HTTPException(404, "No estas vinculado a ese taller")
    taller = vinculo.taller
    return {
        "access_token": create_access_token(
            subject_id=current_user.id_usuario,
            tipo="usuario",
            extra_claims={"id_tenant": taller.id_tenant, "id_taller_activo": id_taller},
        ),
        "taller_activo": {
            "id_taller": id_taller,
            "id_tenant": taller.id_tenant,
            "nombre": taller.nombre,
        },
    }
```

---

## 2. Flutter — modelos

`flutter/lib/models/taller_publico.dart`:

```dart
class TallerPublico {
  final int idTaller;
  final String nombre;
  final String? direccion;
  final double? latitud;
  final double? longitud;

  TallerPublico({
    required this.idTaller,
    required this.nombre,
    this.direccion,
    this.latitud,
    this.longitud,
  });

  factory TallerPublico.fromJson(Map<String, dynamic> j) => TallerPublico(
    idTaller: j['id_taller'],
    nombre: j['nombre'],
    direccion: j['direccion'],
    latitud: (j['latitud'] as num?)?.toDouble(),
    longitud: (j['longitud'] as num?)?.toDouble(),
  );
}
```

`flutter/lib/models/taller_activo.dart`:

```dart
class TallerActivo {
  final int idTaller;
  final int idTenant;
  final String nombre;
  TallerActivo({required this.idTaller, required this.idTenant, required this.nombre});

  factory TallerActivo.fromJson(Map<String, dynamic> j) => TallerActivo(
    idTaller: j['id_taller'],
    idTenant: j['id_tenant'],
    nombre: j['nombre'],
  );
}
```

---

## 3. Flutter — `tecnico_auth_service.dart` (refactor)

```dart
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/taller_publico.dart';
import '../models/taller_activo.dart';
import 'realtime_service.dart';


class TecnicoAuthService {
  static final TecnicoAuthService _i = TecnicoAuthService._();
  factory TecnicoAuthService() => _i;
  TecnicoAuthService._();

  final _storage = const FlutterSecureStorage();

  Future<List<TallerPublico>> listarTalleresPublicos() async {
    final r = await http.get(Uri.parse('${ApiConfig.baseUrl}/tecnicos/talleres-publicos'));
    if (r.statusCode != 200) throw 'Error cargando talleres';
    return (jsonDecode(r.body) as List).map((j) => TallerPublico.fromJson(j)).toList();
  }

  /// Login con email+password+id_taller. Si OK, persiste token y conecta WS.
  Future<TallerActivo> login({
    required String email,
    required String password,
    required int idTaller,
  }) async {
    final r = await http.post(
      Uri.parse('${ApiConfig.baseUrl}/tecnicos/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password, 'id_taller': idTaller}),
    );
    if (r.statusCode == 401) throw 'Email o contrasena incorrectos';
    if (r.statusCode == 403) {
      final detail = jsonDecode(r.body)['detail'] ?? 'No autorizado';
      throw detail.toString();
    }
    if (r.statusCode != 200) throw 'Error en login';

    final data = jsonDecode(r.body) as Map<String, dynamic>;
    final token = data['access_token'] as String;
    final tallerActivo = TallerActivo.fromJson(data['taller_activo']);
    final usuario = data['usuario'] as Map<String, dynamic>;

    await _storage.write(key: 'token', value: token);
    await _storage.write(key: 'tipo', value: 'tecnico');
    await _storage.write(key: 'id_usuario', value: usuario['id_usuario'].toString());
    await _storage.write(key: 'id_taller_activo', value: tallerActivo.idTaller.toString());
    await _storage.write(key: 'nombre_taller_activo', value: tallerActivo.nombre);
    await _storage.write(key: 'id_tenant', value: tallerActivo.idTenant.toString());

    // Conectar WebSocket con el nuevo token
    RealtimeService().connect(token);
    RealtimeService().subscribe('usuario:${usuario['id_usuario']}');
    RealtimeService().subscribe('tenant:${tallerActivo.idTenant}');

    return tallerActivo;
  }

  Future<void> logout() async {
    RealtimeService().disconnect();
    await _storage.deleteAll();
  }

  Future<TallerActivo?> tallerActivoActual() async {
    final id = await _storage.read(key: 'id_taller_activo');
    if (id == null) return null;
    return TallerActivo(
      idTaller: int.parse(id),
      idTenant: int.parse(await _storage.read(key: 'id_tenant') ?? '0'),
      nombre: await _storage.read(key: 'nombre_taller_activo') ?? '',
    );
  }
}
```

---

## 4. Flutter — pantallas

### `seleccionar_taller_login_screen.dart` (pre-login)

```dart
import 'package:flutter/material.dart';
import '../models/taller_publico.dart';
import '../services/tecnico_auth_service.dart';
import 'tecnico_login_screen.dart';

class SeleccionarTallerLoginScreen extends StatefulWidget {
  const SeleccionarTallerLoginScreen({super.key});

  @override
  State<SeleccionarTallerLoginScreen> createState() => _State();
}

class _State extends State<SeleccionarTallerLoginScreen> {
  final _svc = TecnicoAuthService();
  bool _cargando = true;
  String? _error;
  List<TallerPublico> _talleres = [];

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() { _cargando = true; _error = null; });
    try {
      _talleres = await _svc.listarTalleresPublicos();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _cargando = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Selecciona tu taller')),
      body: _build(),
    );
  }

  Widget _build() {
    if (_cargando) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.error_outline, color: Colors.red, size: 48),
        Text(_error!),
        TextButton(onPressed: _cargar, child: const Text('Reintentar')),
      ]));
    }
    return Column(children: [
      const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          '¿En qué taller trabajas? Después ingresarás tu email y contraseña.',
          textAlign: TextAlign.center,
        ),
      ),
      Expanded(
        child: ListView.separated(
          itemCount: _talleres.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (_, i) {
            final t = _talleres[i];
            return ListTile(
              leading: const CircleAvatar(child: Icon(Icons.business)),
              title: Text(t.nombre),
              subtitle: t.direccion != null ? Text(t.direccion!) : null,
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                Navigator.push(context, MaterialPageRoute(
                  builder: (_) => TecnicoLoginScreen(taller: t),
                ));
              },
            );
          },
        ),
      ),
    ]);
  }
}
```

### `tecnico_login_screen.dart` (refactor)

```dart
import 'package:flutter/material.dart';
import '../models/taller_publico.dart';
import '../services/tecnico_auth_service.dart';
import 'tecnico_home.dart';

class TecnicoLoginScreen extends StatefulWidget {
  final TallerPublico taller;
  const TecnicoLoginScreen({super.key, required this.taller});

  @override
  State<TecnicoLoginScreen> createState() => _State();
}

class _State extends State<TecnicoLoginScreen> {
  final _svc = TecnicoAuthService();
  final _email = TextEditingController();
  final _pass = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _login() async {
    setState(() { _loading = true; _error = null; });
    try {
      await _svc.login(
        email: _email.text.trim(),
        password: _pass.text,
        idTaller: widget.taller.idTaller,
      );
      if (!mounted) return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const TecnicoHome()),
        (_) => false,
      );
    } catch (e) {
      setState(() => _error = e.toString());
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.taller.nombre)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(
            padding: const EdgeInsets.all(12),
            color: Colors.blue.shade50,
            child: Row(children: [
              const Icon(Icons.info_outline),
              const SizedBox(width: 8),
              Expanded(child: Text('Vas a entrar como técnico de ${widget.taller.nombre}')),
            ]),
          ),
          const SizedBox(height: 24),
          TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email')),
          const SizedBox(height: 12),
          TextField(controller: _pass, obscureText: true,
                    decoration: const InputDecoration(labelText: 'Contraseña')),
          if (_error != null) Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _loading ? null : _login,
            child: Text(_loading ? 'Ingresando...' : 'Ingresar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Volver, elegir otro taller'),
          ),
        ]),
      ),
    );
  }
}
```

### Chip en `tecnico_home.dart`

```dart
// En el AppBar del home tecnico:
FutureBuilder<TallerActivo?>(
  future: TecnicoAuthService().tallerActivoActual(),
  builder: (_, snap) {
    if (!snap.hasData || snap.data == null) return const SizedBox.shrink();
    return Chip(
      avatar: const Icon(Icons.business, size: 16),
      label: Text(snap.data!.nombre, overflow: TextOverflow.ellipsis),
    );
  },
),
```

Y un botón "Cambiar taller" → logout + volver a `SeleccionarTallerLoginScreen`.

---

## 5. Ruta y entrypoint

`main.dart`:
```dart
routes: {
  '/login-tecnico': (_) => const SeleccionarTallerLoginScreen(),
  // ... otras existentes
}
```

En la pantalla de selección de tipo (cliente vs técnico) — botón "Soy técnico" → navega a `/login-tecnico` (que es el selector de taller).

---

## 6. Validación manual

1. Tener 2 talleres demo con el mismo técnico vinculado:
   ```sql
   INSERT INTO usuario_taller (id_usuario, id_taller, activo) VALUES
     (TEC_ID, TALLER_A, TRUE),
     (TEC_ID, TALLER_B, TRUE);
   ```
2. Abrir app Flutter como técnico.
3. Lista debe mostrar Taller A y Taller B (entre otros).
4. Login en Taller A → token devuelto tiene `id_tenant=A`.
5. Reportar ubicación → se atribuye al vínculo de A, no B.
6. Cerrar sesión, abrir app de nuevo, login en Taller B → ahora todo se atribuye a B.

## Checklist M9
- [ ] 3 endpoints backend creados (`/talleres-publicos`, `/tecnicos/login`, `/tecnicos/me/cambiar-taller`).
- [ ] Fix `/me/ubicacion` para usar `current_tenant.get()` en vez de `.first()`.
- [ ] Modelos `TallerPublico` y `TallerActivo` en Flutter.
- [ ] `TecnicoAuthService` refactorizado para llamar el nuevo `/tecnicos/login` con `id_taller`.
- [ ] `RealtimeService().connect()` se llama tras login técnico (no solo cliente).
- [ ] Suscripción automática a `usuario:{id}` y `tenant:{id}` tras login.
- [ ] Pantalla `SeleccionarTallerLoginScreen` con lista de talleres públicos.
- [ ] `TecnicoLoginScreen` recibe `TallerPublico` y pasa `id_taller` al login.
- [ ] Chip en AppBar del home técnico muestra taller activo.
- [ ] Botón "Cambiar taller" hace logout + vuelve al selector.
- [ ] Validado manualmente con técnico de 2 talleres.

## Notas
- **No requiere migración** — solo endpoints nuevos.
- **No rompe el cliente** — el cliente sigue usando `/usuarios/login` igual que siempre.
- **No rompe el web** — los talleres en panel web siguen usando `/talleres/login`.
- **Idempotente**: si el técnico solo tiene 1 taller, la lista tiene 1 elemento; tap → login → listo.
