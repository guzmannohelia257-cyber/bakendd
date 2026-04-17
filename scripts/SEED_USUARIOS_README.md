# 🌱 Script de Población de Usuarios

Script que crea automáticamente 4 usuarios de ejemplo para pruebas según los roles definidos en `LOGIN_POR_ROLES.md`.

---

## 📋 Usuarios que se crean

| Rol | Email | Contraseña | Cliente |
|-----|-------|-----------|---------|
| **Cliente** (id_rol=1) | `conductor@ejemplo.com` | `miPassword123!` | 📱 Flutter |
| **Técnico** (id_rol=3) | `tecnico.juan@taller.com` | `password456!` | 📱 Flutter |
| **Taller** (id_rol=2) | `gerente@tallerexcelente.com` | `gerente789!` | 🌐 Angular |
| **Admin** (id_rol=4) | `admin@plataforma.com` | `admin2026!` | 🌐 Angular |

---

## 🚀 Cómo ejecutar

### Opción 1️⃣: Windows PowerShell

```powershell
cd c:\Users\Isael Ortiz\Documents\yary\Backend

# Ejecutar el script batch
.\seed_usuarios.bat
```

O directamente:
```powershell
.\venv\Scripts\python.exe -m scripts.seed_usuarios
```

### Opción 2️⃣: Linux/Mac

```bash
cd ~/ruta/a/Backend

# Dar permisos de ejecución
chmod +x seed_usuarios.sh

# Ejecutar
./seed_usuarios.sh
```

O directamente:
```bash
python -m scripts.seed_usuarios
```

### Opción 3️⃣: Cualquier sistema (directo con Python)

```bash
python -m scripts.seed_usuarios
```

---

## ✅ Salida esperada

```
============================================================
🌱 SCRIPT DE POBLACIÓN DE USUARIOS
============================================================

✓ Verificando roles...
✓ Encontrados 4 roles
✓ 👨 Cliente (Conductor) - Flutter
  📧 conductor@ejemplo.com
  🔑 Contraseña: miPassword123!

✓ 🔧 Técnico (Mecánico) - Flutter
  📧 tecnico.juan@taller.com
  🔑 Contraseña: password456!

✓ 🏭 Taller (Gerente) - Angular
  📧 gerente@tallerexcelente.com
  🔑 Contraseña: gerente789!

✓ 👨‍💼 Admin (Sistema) - Angular
  📧 admin@plataforma.com
  🔑 Contraseña: admin2026!

✅ 4 usuario(s) creado(s) exitosamente

============================================================
📋 USUARIOS EN LA BASE DE DATOS
============================================================
ID: 1 | Carlos López
   📧 carlos@ejemplo.com
   👤 Rol: cliente
   ✓ Activo: Sí

ID: 2 | Juan Conductor
   📧 conductor@ejemplo.com
   👤 Rol: cliente
   ✓ Activo: Sí

... (más usuarios)

============================================================
🎉 ¡Usuarios listos para pruebas!
============================================================

📱 FLUTTER - Prueba con:
   1. Cliente: conductor@ejemplo.com / miPassword123!
   2. Técnico: tecnico.juan@taller.com / password456!

🌐 ANGULAR - Prueba con:
   1. Taller: gerente@tallerexcelente.com / gerente789!
   2. Admin: admin@plataforma.com / admin2026!

🔗 URL de login: POST http://localhost:8000/usuarios/login
📖 Documentación: http://localhost:8000/docs
```

---

## 🔍 Detalles técnicos

- **Ubicación:** `scripts/seed_usuarios.py`
- **BD:** PostgreSQL
- **Hasheo:** Argon2
- **Validaciones:**
  - Verifica que existan los roles antes de crear usuarios
  - Evita duplicados (no crea si el email ya existe)
  - Hashea automáticamente las contraseñas

---

## 📖 Próximos pasos

1. ✅ Ejecutar el script: `./seed_usuarios.bat` (Windows) o `./seed_usuarios.sh` (Linux/Mac)
2. ✅ Abrir Swagger: http://localhost:8000/docs
3. ✅ Click en **"Authorize"** (botón arriba a la derecha)
4. ✅ Hacer login con cualquier usuario
5. ✅ Copiar el `access_token` en el campo de autorización
6. ✅ Probar endpoints protegidos

---

## ⚠️ Errores comunes

### Error: "No hay roles en la base de datos"
**Solución:** Primero corre `init_roles.sql` (ver guías)

### Error: "Email ya existe"
**Solución:** El script detecta duplicados y no los crea de nuevo. Esto es OK.

### Error: "ModuleNotFoundError"
**Solución:** Asegúrate de estar en la carpeta correcta y que el venv esté activado

### La BD no está conectada
**Solución:** Verifica que PostgreSQL está corriendo y que el `.env` tiene los datos correctos

---

## 🔐 Seguridad

- ✅ Las contraseñas se hashean con **Argon2**
- ✅ Nunca se almacenan en texto plano
- ✅ El script es **solo para desarrollo local**
- ⚠️ En producción, cambiar todas las credenciales

---

**¡Listo para usar!** 🎉
