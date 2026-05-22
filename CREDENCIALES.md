# Credenciales de prueba

Cuentas seedeadas en la base local. Si alguna no funciona, alguien las cambió en BD — corré los seeders abajo para reconstruirlas.

## Talleres (login en `POST /talleres/login`)

| Taller | Email | Password | Tenant slug | id_tenant | id_taller | Origen |
|---|---|---|---|---|---|---|
| Llanteria El Sol | `llanteria@demo.com` | `demo1234` | `demo-llantas` | 414 | 330 | `scripts/seed_demo.py` |
| Mecanica Central | `mecanica@demo.com` | `demo1234` | `demo-mecanica` | 415 | 331 | `scripts/seed_demo.py` |
| Chaperia Express | `chaperia@demo.com` | `demo1234` | `demo-chaperia` | 416 | 332 | `scripts/seed_demo.py` |
| Taller Excelente | `gerente@tallerexcelente.com` | `taller123!` | `gerente` | 8 | 1 | `seeders/seed_full.py` |
| Mecánica Central SC | `mecanica.central@talleres.test` | `taller123!` | `mecanica-central` | 9 | 2 | `seeders/seed_full.py` |
| Llantería El Cristo | `llanteria.cristo@talleres.test` | `taller123!` | `llanteria-cristo` | 10 | 3 | `seeders/seed_full.py` |

> En la BD también existen talleres `rltest-*` — son artefactos de pruebas de rate-limit, ignorarlos.

## Clientes (login en `POST /usuarios/login`)

| Nombre | Email | Password | Origen |
|---|---|---|---|
| Cliente Demo | `cliente@demo.com` | `demo1234` | `scripts/seed_demo.py` |
| Juan Conductor | `conductor@ejemplo.com` | `cliente123!` | `seeders/seed_full.py` |
| Ana Cliente | `ana.cliente@ejemplo.com` | `cliente123!` | `seeders/seed_full.py` |
| Pedro Cliente | `pedro.cliente@ejemplo.com` | `cliente123!` | `seeders/seed_full.py` |
| María Cliente | `maria.cliente@ejemplo.com` | `cliente123!` | `seeders/seed_full.py` |
| Carlos Cliente | `carlos.cliente@ejemplo.com` | `cliente123!` | `seeders/seed_full.py` |

## Técnicos (login en `POST /usuarios/login`, rol=3)

| Nombre | Email | Password | Taller asignado |
|---|---|---|---|
| Técnico Demo | `tecnico@demo.com` | `demo1234` | Llanteria El Sol |
| Juan Pérez | `tecnico.juan@taller.com` | `tecnico123!` | Taller Excelente |
| Carlos Gómez | `tecnico.carlos@taller.com` | `tecnico123!` | Taller Excelente |
| Luis Rodríguez | `tecnico.luis@taller.com` | `tecnico123!` | Mecánica Central SC |
| Mario López | `tecnico.mario@taller.com` | `tecnico123!` | Mecánica Central SC |
| Pedro Vargas | `tecnico.pedro@taller.com` | `tecnico123!` | Llantería El Cristo |
| Diego Mamani | `tecnico.diego@taller.com` | `tecnico123!` | Llantería El Cristo |

## Super-admin (rol=4)

| Email | Password |
|---|---|
| `admin@demo.com` | `admin1234` |

---

## Cómo probar un login rápido

PowerShell:

```powershell
$body = @{ email = 'llanteria@demo.com'; password = 'demo1234' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/talleres/login' -ContentType 'application/json' -Body $body
```

El `access_token` que devuelve trae adentro `id_tenant` — ese es el que filtra los datos del taller.

## Si una password no anda

Reseedeá:

```powershell
.\venv\Scripts\python.exe -m scripts.seed_demo          # los 3 demo-*
.\venv\Scripts\python.exe -m seeders.seed_full          # gerente@, mecanica.central@, llanteria.cristo@
```

Ambos son idempotentes: no rompen si los registros ya existen, pero **no resetean passwords** de cuentas que ya estaban. Si necesitás forzar el reset:

```powershell
.\venv\Scripts\python.exe -c "from app.core.security import hash_password; from app.db.session import SessionLocal; from app.models.taller import Taller; from app.core.tenant_context import current_tenant; db = SessionLocal(); current_tenant.set(0); t = db.query(Taller).filter_by(email='llanteria@demo.com').first(); t.password_hash = hash_password('demo1234'); db.commit()"
```
