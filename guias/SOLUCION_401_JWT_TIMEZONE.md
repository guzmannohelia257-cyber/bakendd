# ✅ SOLUCIÓN: Error 401 en GET /vehiculos (RESUELTO)

## Problema Identificado

El cliente recibía **401 Unauthorized** al intentar obtener los vehículos:
```
❌ ERROR 401 - Unauthorized
El servidor rechazó el token. Posibles causas:
1. Token expirado
2. Token inválido o corrupto  
3. Formato incorrecto en Authorization header
```

## Causa Raíz

**Bug de zona horaria en Windows** al generar tokens JWT:
- Cuando `datetime.utcnow().timestamp()` se ejecuta en Windows con zona horaria EDT (-4)
- El cálculo del timestamp producía valores incorrectos
- Los tokens se generaban con expiración en el pasado (ejemplo: -3.5 horas)
- PyJWT rechazaba todos los tokens como expirados

## Solución Implementada

### 1. **Archivo: `app/core/security.py`**
Cambié la generación del token para usar `calendar.timegm()` en lugar de `.timestamp()`:

**Antes (INCORRECTO):**
```python
expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
to_encode["exp"] = expire  # ❌ Problema con zona horaria
```

**Después (CORRECTO):**
```python
import calendar
...
expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
to_encode["exp"] = calendar.timegm(expire.timetuple())  # ✅ UTC puro
```

### 2. **Archivo: `app/api/diagnostico.py`**
Cambié la validación del token para usar la misma función UTC pura:

```python
# Antes (INCORRECTO):
now_timestamp = datetime.utcnow().timestamp()  # ❌

# Después (CORRECTO):
now_timestamp = calendar.timegm(datetime.utcnow().timetuple())  # ✅
```

## ✅ Verificación

Después de la solución:

```
Login exitoso
GET /vehiculos/mis-autos: Status 200 ✅
Vehículos encontrados: 0
no_expirado: True ✅
Tiempo restante: 30 minutos ✅
```

## 🚀 Próximos Pasos

1. **En Flutter, haz login nuevamente** para obtener un token fresco
   - El token anterior era inválido
   - El nuevo token será generado correctamente

2. **Prueba los endpoints de vehículos:**
   - POST /vehiculos/ (registrar vehículo)
   - GET /vehiculos/mis-autos (listar)
   - PUT /vehiculos/{id} (editar)
   - DELETE /vehiculos/{id} (eliminar)

3. **Si aún ves 401:**
   - Asegúrate de estar usando `10.0.2.2:8000` en emulador
   - Borra la caché de SharedPreferences y haz login nuevo
   - Verifica que el token se está enviando en el header Authorization

## 📊 Resumen del Fix

| Aspecto | Antes | Después |
|---------|-------|---------|
| Expiración token | -3.5 horas (inválido) | +30 minutos (válido) ✅ |
| Response endpoint vehículos | 401 Unauthorized ❌ | 200 OK ✅ |
| Test de token | no_expirado: False ❌ | no_expirado: True ✅ |

## 🔧 Detalles Técnicos (Opcional)

El problema ocurría porque `datetime.timestamp()` en Windows interpreta la fecha como hora local primero, luego la convierte. Con UTC datetime:

```
datetime.utcnow().timestamp()  # ❌ Problema zona horaria
calendar.timegm(datetime.utcnow().timetuple())  # ✅ Siempre UTC
```

`calendar.timegm()` es la función correcta para convertir struct_time UTC a timestamp, sin ambigüedades de zona horaria.

---

**Estado:** ✅ FUNCIONANDO - El servidor ahora genera y valida tokens JWT correctamente en Windows
