# F2 — Release + backup + setup operacional del demo

> **Pre-requisito:** F1 cerrado (hardening hecho).
> **Esfuerzo:** 0.5 día.

## Objetivo
Operativa pura: tener todo listo y respaldado para el día de la defensa. **Esta guía NO contiene narrativa ni documentación** — solo comandos y scripts ejecutables. Para la documentación (manual, guion, FAQ) ver [G2D/](../G2D/README.md).

Tres bloques:
1. **Release**: tag git + bundle del repo.
2. **Backup BD**: dump del estado con datos demo.
3. **Setup operacional del demo**: script seed + comandos de arranque + grabación de videos de respaldo.

---

## 1. Release del código

### 1.1 Tag de release en git

```bash
# Backend
cd Backend
git add -A
git commit -m "chore: release defensa-final"  # si hay cambios
git tag -a defensa-final -m "Estado entregable para defensa"
git push origin defensa-final  # si hay remoto

# Repetir para web/ y flutter/
```

### 1.2 Bundle git completo (incluye historia)

```bash
cd ..  # raíz que contiene Backend/, web/, flutter/
git -C Backend bundle create yary-backend-defensa.bundle --all
git -C web bundle create yary-web-defensa.bundle --all
git -C flutter bundle create yary-flutter-defensa.bundle --all
```

Copiar los `.bundle` a:
- USB físico.
- Google Drive / Dropbox personal.
- Otro disco externo si está disponible.

### 1.3 Verificar que el bundle se puede clonar

```bash
mkdir test-restore
git clone yary-backend-defensa.bundle test-restore/Backend
cd test-restore/Backend
git log --oneline | head -5  # debe mostrar los commits recientes
cd ../.. && rm -rf test-restore
```

---

## 2. Backup de Base de Datos

### 2.1 Con `pg_dump` (si está instalado)

```bash
pg_dump -h localhost -U postgres -d emergencias_vehiculares -F c -f yary-defensa.dump
```

Restaurar (en caso de necesidad):
```bash
createdb -U postgres yary_restored
pg_restore -h localhost -U postgres -d yary_restored yary-defensa.dump
```

### 2.2 Sin `pg_dump` (alternativa con Python)

Si no tienes `pg_dump` instalado, usar el script existente para schema y un script auxiliar para datos:

```bash
# Schema
.\venv\Scripts\python.exe -m scripts.dump_schema
# Output: app/guias/schema_postgresql.sql

# Datos: usar pg_dump via Docker
docker run --rm --network host -v "${PWD}:/out" postgres:16-alpine \
    pg_dump -h host.docker.internal -U postgres -d emergencias_vehiculares \
    -F c -f /out/yary-defensa.dump
```

### 2.3 Copiar backup BD al USB

Después de generar `yary-defensa.dump` (típicamente <10MB con datos de demo):
```bash
copy yary-defensa.dump E:\yary-backup\  # ajustar letra USB
```

---

## 3. Setup operacional del demo

### 3.0 Instalar dependencias (one-shot)

```powershell
.\venv\Scripts\pip.exe install -r requirements.txt
```

### 3.1 Comandos de arranque (one-shot)

Crear `scripts/start_demo.sh` (o `.bat` para Windows):

**Bash (Linux/Mac/WSL):**
```bash
#!/bin/bash
set -e

echo "== 1. Levantando Redis =="
docker compose up -d redis
docker exec yary-redis redis-cli ping || { echo "Redis no responde"; exit 1; }

echo "== 2. Verificando Postgres =="
psql -h localhost -U postgres -d emergencias_vehiculares -c "SELECT 1" || { echo "Postgres no responde"; exit 1; }

echo "== 3. Aplicando migraciones =="
./venv/Scripts/alembic.exe upgrade head

echo "== 4. Cargando datos demo =="
./venv/Scripts/python.exe -m scripts.seed_demo

echo "== 5. Arrancando backend =="
./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
echo "Backend PID: $!"

echo "LISTO. Acceder a http://localhost:8000/docs"
```

**PowerShell (Windows):**
```powershell
# scripts/start_demo.ps1
Write-Host "== 1. Levantando Redis =="
docker compose up -d redis
docker exec yary-redis redis-cli ping
if (-not $?) { Write-Error "Redis no responde"; exit 1 }

Write-Host "== 2. Verificando Postgres =="
$env:PGPASSWORD = "12345678"
psql -h localhost -U postgres -d emergencias_vehiculares -c "SELECT 1"

Write-Host "== 3. Aplicando migraciones =="
.\venv\Scripts\alembic.exe upgrade head

Write-Host "== 4. Cargando datos demo =="
.\venv\Scripts\python.exe -m scripts.seed_demo

Write-Host "== 5. Arrancando backend =="
Start-Process -NoNewWindow -FilePath ".\venv\Scripts\python.exe" `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"

Write-Host "LISTO. Acceder a http://localhost:8000/docs"
```

### 3.2 Script seed de datos demo

`scripts/seed_demo.py`:

```python
"""
Carga datos demo para la defensa.
Idempotente: si ya existen los datos, no falla.

Crea:
  - 3 tenants/talleres con servicios distintos (llantas, mecánica, chapería)
  - 1 cliente demo con vehículo
  - 1 técnico demo vinculado al taller de llantas
  - 1 super-admin

Todas las credenciales: password demo1234 (admin: admin1234)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.catalogos import CategoriaProblema
from app.models.taller import Taller, TallerServicio
from app.models.tenant import Plan, Suscripcion, Tenant
from app.models.usuario import Usuario, Vehiculo
from app.models.usuario_taller import UsuarioTaller


TENANTS = [
    {
        "slug": "demo-llantas",
        "nombre": "Llantería El Sol",
        "email": "llanteria@demo.com",
        "lat": -16.5000, "lng": -68.1500,
        "categorias": ["llantas", "grua_auxilio"],
        "tarifa_traslado": 10,
    },
    {
        "slug": "demo-mecanica",
        "nombre": "Mecánica Central",
        "email": "mecanica@demo.com",
        "lat": -16.5020, "lng": -68.1490,
        "categorias": ["mecanica_general", "electrico", "rutinario"],
        "tarifa_traslado": 15,
    },
    {
        "slug": "demo-chaperia",
        "nombre": "Chapería Express",
        "email": "chaperia@demo.com",
        "lat": -16.4980, "lng": -68.1520,
        "categorias": ["chaperia_pintura", "electronico"],
        "tarifa_traslado": 20,
    },
]


def main() -> int:
    db = SessionLocal()
    try:
        plan_free = db.query(Plan).filter_by(codigo="free").one()

        # ---- Tenants + Talleres ----
        for cfg in TENANTS:
            if db.query(Tenant).filter_by(slug=cfg["slug"]).first():
                print(f"Tenant {cfg['slug']} ya existe, skip")
                continue

            t = Tenant(slug=cfg["slug"], nombre=cfg["nombre"], email_contacto=cfg["email"])
            db.add(t); db.flush()
            db.add(Suscripcion(id_tenant=t.id_tenant, id_plan=plan_free.id_plan, estado="activa"))

            taller = Taller(
                id_tenant=t.id_tenant, nombre=cfg["nombre"],
                email=cfg["email"], password_hash=hash_password("demo1234"),
                latitud=cfg["lat"], longitud=cfg["lng"],
                tarifa_traslado=cfg["tarifa_traslado"],
                verificado=True, disponible=True,
            )
            db.add(taller); db.flush()

            for cod in cfg["categorias"]:
                cat = db.query(CategoriaProblema).filter_by(codigo=cod).first()
                if cat:
                    db.add(TallerServicio(
                        id_taller=taller.id_taller,
                        id_categoria=cat.id_categoria,
                        servicio_movil=True,
                        tarifa_base=100,
                    ))
            print(f"Creado: {cfg['nombre']} ({cfg['slug']})")

        # ---- Cliente demo ----
        if not db.query(Usuario).filter_by(email="cliente@demo.com").first():
            cliente = Usuario(
                id_rol=1, nombre="Cliente Demo",
                email="cliente@demo.com", password_hash=hash_password("demo1234"),
                telefono="+591 70000000",
            )
            db.add(cliente); db.flush()
            db.add(Vehiculo(
                id_usuario=cliente.id_usuario,
                placa="DEMO-001", marca="Toyota", modelo="Hilux", anio=2020, color="blanco",
            ))
            print("Cliente demo creado")

        # ---- Tecnico demo ----
        if not db.query(Usuario).filter_by(email="tecnico@demo.com").first():
            tec = Usuario(
                id_rol=3, nombre="Tecnico Demo",
                email="tecnico@demo.com", password_hash=hash_password("demo1234"),
            )
            db.add(tec); db.flush()
            taller_llantas = db.query(Taller).filter_by(email="llanteria@demo.com").first()
            db.add(UsuarioTaller(
                id_usuario=tec.id_usuario, id_taller=taller_llantas.id_taller, activo=True,
            ))
            print("Tecnico demo creado")

        # ---- Super-admin ----
        if not db.query(Usuario).filter_by(email="admin@demo.com").first():
            adm = Usuario(
                id_rol=4, nombre="Super Admin",
                email="admin@demo.com", password_hash=hash_password("admin1234"),
            )
            db.add(adm)
            print("Super-admin creado")

        db.commit()
        print("\nLISTO. Credenciales todas con password: demo1234 (admin: admin1234)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
```

Correr antes de la defensa:
```bash
.\venv\Scripts\python.exe -m scripts.seed_demo
```

### 3.3 Verificación post-seed

Script `scripts/verify_demo.py` (opcional pero útil):

```python
"""Verifica que los datos demo existen y son consistentes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.taller import Taller
from app.models.tenant import Tenant
from app.models.usuario import Usuario


def main() -> int:
    db = SessionLocal()
    checks = []

    # 3 tenants
    n_tenants = db.query(Tenant).filter(Tenant.slug.like("demo-%")).count()
    checks.append(("3 tenants demo", n_tenants == 3, f"hay {n_tenants}"))

    # 3 talleres
    n_talleres = db.query(Taller).join(Tenant).filter(Tenant.slug.like("demo-%")).count()
    checks.append(("3 talleres demo", n_talleres == 3, f"hay {n_talleres}"))

    # Cliente demo
    cliente = db.query(Usuario).filter_by(email="cliente@demo.com").first()
    checks.append(("cliente demo", cliente is not None, "no existe" if not cliente else "OK"))

    # Tecnico
    tec = db.query(Usuario).filter_by(email="tecnico@demo.com").first()
    checks.append(("tecnico demo", tec is not None and tec.id_rol == 3, "no existe o rol incorrecto"))

    # Admin
    admin = db.query(Usuario).filter_by(email="admin@demo.com").first()
    checks.append(("super-admin", admin is not None and admin.id_rol == 4, "no existe o rol incorrecto"))

    print("\n== Verificacion datos demo ==")
    ok = True
    for nombre, passed, detail in checks:
        icon = "OK" if passed else "FALLO"
        print(f"  [{icon}] {nombre} -- {detail}")
        if not passed:
            ok = False

    db.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 4. Grabación de videos de respaldo

Si la red de la defensa falla, queremos tener videos para proyectar. Usar **OBS Studio** o el grabador nativo del SO.

| Video | Duración | Escenario | Cuándo proyectar |
|---|---|---|---|
| `demo_broadcast.mp4` | ~30s | 3 talleres reciben, primero gana | si WebSocket no conecta en vivo |
| `demo_tracking.mp4` | ~45s | técnico moviéndose + geofence | si GPS no funciona en demo |
| `demo_offline.mp4` | ~30s | modo avión + reconexión | si WiFi del aula es errática |
| `demo_completo.mp4` | ~12 min | TODO el script de demo | si todo falla |

### Comandos OBS rápidos

1. Abrir OBS → Source → Display Capture (toda la pantalla) o Window Capture (app específica).
2. Configurar output: MP4 a 30 fps, 1080p.
3. Antes de grabar: cerrar notificaciones, Slack, etc.
4. Grabar cada escenario por separado.
5. Si quieren cortar/editar: usar `ffmpeg` o **DaVinci Resolve** (gratis).

### Guardar en múltiples lugares

- USB físico (mismo del backup).
- Carpeta `videos/` en el laptop principal (escritorio).
- Subir a Google Drive sin compartir (privado).

---

## 5. Pre-flight final automático

Script `scripts/preflight_demo.py` que junta todo:

```python
"""Pre-flight para la defensa: corre todas las verificaciones."""
import subprocess
import sys


def step(name: str, cmd: list[str]) -> bool:
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd)
    ok = result.returncode == 0
    print(f"-> {'OK' if ok else 'FALLO'}")
    return ok


def main():
    results = {
        "alembic_head": step("Alembic en head", ["alembic", "current"]),
        "seed_demo":    step("Seed datos demo", [sys.executable, "-m", "scripts.seed_demo"]),
        "verify_demo":  step("Verificar datos", [sys.executable, "-m", "scripts.verify_demo"]),
        "tests":        step("Tests pytest", [sys.executable, "-m", "pytest", "tests/", "-q"]),
    }

    print("\n========= PRE-FLIGHT =========")
    for name, ok in results.items():
        print(f"  {name:20s} {'OK' if ok else 'FALLO'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Correr la mañana del día de la defensa:
```bash
$env:DEBUG="False"
.\venv\Scripts\python.exe -m scripts.preflight_demo
```

---

## 6. Checklist operacional final

### Hora -3h del día de la defensa
- [ ] `docker compose ps` muestra Redis healthy.
- [ ] `python -m scripts.preflight_demo` retorna 0.
- [ ] Backend levantado: `curl http://localhost:8000/health` → 200.
- [ ] Web Angular levantado en localhost:4200.
- [ ] Flutter cliente + técnico instalados y logueados en 2 dispositivos.
- [ ] 3 navegadores con sesión iniciada en 3 talleres distintos.
- [ ] Token super-admin copiado en clipboard manager.

### Hora -1h
- [ ] USB con `*.bundle` + `*.dump` + videos conectado.
- [ ] Cargador del laptop.
- [ ] Adaptador HDMI / cable.
- [ ] Plan B videos en carpeta `videos/` del escritorio.

### Hora 0 (entrando al aula)
- [ ] WiFi del aula conectado y andando.
- [ ] Pantalla extendida configurada.
- [ ] Notificaciones del SO en silencio.
- [ ] Tabs pinneadas: `/docs`, dashboard taller, terminal con logs.

---

## 7. Después de la defensa

```bash
# Push del tag al remoto si no se hizo antes
git push origin defensa-final

# Subir bundle a almacenamiento permanente (Drive, etc)
# Mantener el .dump de BD por si se necesita auditoría
```

---

## Checklist de cierre F2
- [ ] Tag `defensa-final` en los 3 repos (Backend, web, flutter).
- [ ] Bundles `.bundle` generados y guardados en USB + nube.
- [ ] `yary-defensa.dump` generado y guardado en USB + nube.
- [ ] `scripts/seed_demo.py` ejecutable y verificado.
- [ ] `scripts/verify_demo.py` y `scripts/preflight_demo.py` creados.
- [ ] `scripts/start_demo.ps1` (o `.sh`) funciona end-to-end.
- [ ] 3-4 videos de respaldo grabados y guardados en USB.
- [ ] Checklist hora -3h / -1h / 0 impreso para llevarlo en papel.

## Notas operativas
- **No probar `start_demo.ps1` por primera vez el día de la defensa**: correrlo al menos 2 veces antes del día D para detectar problemas raros (firewall, permisos, etc).
- **`pg_dump` en Windows**: si no lo tienes, instalar PostgreSQL client local (no necesitas el server, solo el bin de tools).
- **Tamaño total backup**: ~50-100 MB todo (bundles + dump + videos). USB de 1GB sobra.
- **No incluir `.env` en bundles**: ya está gitignored, los bundles solo traen lo versionado. Para defensa, el `.env` queda en el laptop o se entrega aparte si el evaluador lo pide.
