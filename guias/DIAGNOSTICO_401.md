# 🔧 Diagnóstico: Error 401 al obtener vehículos

## El Problema

```
INFO: 127.0.0.1:63197 - "GET /vehiculos/mis-autos HTTP/1.1" 401 Unauthorized
```

El servidor devuelve **401** porque **el token JWT no se está enviando** en el header `Authorization`.

---

## ¿Por qué pasa?

### Opción 1: Token NO se guardó después del login ❌
Si el `AuthService.login()` **no está guardando el token** en SharedPreferences, entonces:
- `VehiculoService._getToken()` retorna `null`
- La petición se envía **sin** header Authorization
- Servidor rechaza con 401

### Opción 2: Token se perdió (sesión expirada) ⏰
Si el token se guardó pero tiene corta duración, puede haber expirado.

### Opción 3: La URL es incorrecta 🌐
Si en el emulador no estás usando `10.0.2.2:8000`, el servidor no responde.

---

## 🔍 Verificación Paso a Paso

### Paso 1: Verifica que el login funciona
En el Flutter app, después del login, agrega este debug:

```dart
import 'package:shared_preferences/shared_preferences.dart';

// Después del login exitoso
final prefs = await SharedPreferences.getInstance();
final savedToken = prefs.getString('access_token');
print('✅ Token guardado: ${savedToken?.substring(0, 20)}...');
```

**Resultado esperado:** Debería imprimir parte del token
**Si imprime `null`:** El AuthService NO está guardando el token

---

### Paso 2: Reemplaza tu VehiculoService

Copia el archivo `VEHICULO_SERVICE_DEBUG.dart` de esta carpeta y reemplázalo:

**De:**
```
lib/services/vehiculo_service.dart  (versión anterior)
```

**A:**
```
lib/services/vehiculo_service.dart  (versión con debug)
```

---

### Paso 3: Ejecuta y revisa los logs

Cuando llames a `listarMisVehiculos()`:

**Si ves esto:**
```
✅ Token encontrado: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
📤 [PETICIÓN] GET http://10.0.2.2:8000/vehiculos/mis-autos
📥 [RESPUESTA] Status Code: 200
✅ [ÉXITO] Vehículos cargados: 0 encontrados
```
→ **TODO ESTÁ BIEN** ✅

**Si ves esto:**
```
❌ [ERROR] Token es NULL - Usuario no está guardado en SharedPreferences
💡 [INFO] ¿Se ejecutó correctamente el login?
```
→ **PROBLEMA EN EL LOGIN** (ver solución abajo)

**Si ves esto:**
```
✅ Token encontrado...
📥 [RESPUESTA] Status Code: 401
❌ [ERROR 401] Unauthorized - Token inválido o expirado
```
→ **TOKEN EXPIRADO** (hacer login de nuevo)

---

## 🛠️ Soluciones Específicas

### SOLUCIÓN 1: AuthService NO guarda token

**Verifica tu `lib/services/auth_service.dart`:**

❌ **MALO** - No guarda token:
```dart
Future<void> login(String email, String password) async {
  final response = await http.post(...);
  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    // ❌ No guarda el token!
  }
}
```

✅ **CORRECTO** - Guarda token:
```dart
Future<void> login(String email, String password) async {
  final response = await http.post(...);
  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    final token = data['access_token'];
    
    // ✅ Guarda en SharedPreferences
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
    
    // ✅ Guarda usuario
    await prefs.setString('user_id', data['usuario']['id_usuario'].toString());
    await prefs.setString('user_name', data['usuario']['nombre']);
  }
}
```

---

### SOLUCIÓN 2: Verificar URL correcta para emulador

**En `VehiculoService`:**

```dart
// ✅ CORRECTO para emulador Android
static const String baseUrl = "http://10.0.2.2:8000";

// ❌ NO funciona (localhost no existe en emulador)
static const String baseUrl = "http://localhost:8000";

// ✅ Para dispositivo físico (reemplaza con tu IP)
static const String baseUrl = "http://192.168.1.100:8000";
```

---

### SOLUCIÓN 3: Token expirado

El servidor genera tokens con expiración. Para extender:

**En el servidor `app/core/config.py`:**

```python
# Aumenta de 24 horas
TOKEN_EXPIRE_HOURS = 24  # Cambiar a 168 (una semana) o 720 (un mes)
```

---

## 📊 Checklist de Debugging

- [ ] ¿El login muestra "✅ Autenticado: true"? 
  - Sí → Token se obtuvo del servidor
  - No → Problema en login

- [ ] ¿El token se guardó en SharedPreferences?
  - Sí → AuthService está correcto
  - No → Agregar `prefs.setString('access_token', token)`

- [ ] ¿La URL es `10.0.2.2:8000` (emulador)?
  - Sí → Correcto
  - No → Cambiar URL

- [ ] ¿El debug muestra "Status Code: 200"?
  - Sí → Conexión OK, datos cargados
  - No → Verificar logs del servidor

- [ ] ¿El servidor recibe las peticiones?
  - Revisa la terminal donde ejecutaste `uvicorn app.main:app --reload`

---

## 🚀 Próximos Pasos

1. **Reemplaza** `VehiculoService` con versión debug
2. **Verifica** que el login guarda el token
3. **Ejecuta** el app y revisa los logs
4. **Comparte** los logs (print statements) si aún hay problemas

---

## 📝 Logs del Servidor para Verificar

Cuando ejecutes la app, deberías ver en la terminal del servidor:

**Login correcto:**
```
INFO:     127.0.0.1:63197 - "POST /usuarios/login HTTP/1.1" 200 OK
```

**Petición a vehículos SIN token (401):**
```
INFO:     127.0.0.1:63197 - "GET /vehiculos/mis-autos HTTP/1.1" 401 Unauthorized
```

**Petición a vehículos CON token (200) ✅:**
```
INFO:     127.0.0.1:63197 - "GET /vehiculos/mis-autos HTTP/1.1" 200 OK
```

---

Si aún tienes 401 después de esto, **revisa que el token tenga 4 partes separadas por puntos**:
```
header.payload.signature.signature
```

¿Ves la estructura correcta? Si no, hay problema en el servidor generando el JWT.
