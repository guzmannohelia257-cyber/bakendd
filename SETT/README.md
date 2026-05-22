# SETT — Seed-Estados-Total Toolkit

Carpeta unica para poblar la base de datos en cada despliegue.
Reemplaza al historico `seeders/seed_full.py` con un layout modular que
cubre **todos los estados** del sistema y deja la BD lista para demostrar
cada flujo desde el primer login.

## Ejecucion

```bash
python -m SETT.run_all
```

En produccion (Render): el script `despliegue/start.sh` lo invoca
automaticamente cuando `SEED_ON_STARTUP=true`.

## Estructura

```
SETT/
  config.py              # datos estaticos: catalogos, credenciales, talleres, clientes
  utils.py               # helpers (Ctx, truncate_all, resumen, ensure_tables)
  catalogos/
    roles.py             # 4 roles (cliente, taller, tecnico, admin)
    estados.py           # estado_incidente / asignacion / pago / cotizacion
    categorias.py        # categoria_problema, prioridad, tipo_evidencia, metodo_pago
  entidades/
    planes.py            # 3 planes SaaS (free, pro, enterprise)
    admin.py             # 1 admin
    talleres.py          # 3 talleres (cada uno con tenant + suscripcion + servicios)
    tecnicos.py          # 6 tecnicos (2 por taller, via usuario_taller)
    clientes.py          # 15 clientes + vehiculos (1 por escenario)
  escenarios/
    _base.py             # helper crear_escenario(): incidente + asignacion + ...
    e01_pendiente.py
    e02_aceptada.py
    e03_rechazada.py
    e04_en_camino.py
    e05_llegado.py
    e06_atendido.py
    e07_cancelado.py
    e08_cot_pendiente.py
    e09_cot_enviada.py
    e10_cot_aceptada.py
    e11_cot_rechazada.py
    e12_cot_expirada.py
    e13_pago_procesando.py
    e14_pago_fallido.py
    e15_pago_reembolsado.py
    e16_pago_pendiente.py
  run_all.py             # orquestador
```

## Cobertura de estados

| Escenario | Cliente                  | Estado incidente | Estado asignacion | Cotizacion | Pago        |
| --------- | ------------------------ | ---------------- | ----------------- | ---------- | ----------- |
| 01        | cli.pendiente            | pendiente        | pendiente         |  -         |  -          |
| 02        | cli.aceptada             | pendiente        | aceptada          |  -         |  -          |
| 03        | cli.rechazada            | pendiente        | rechazada         |  -         |  -          |
| 04        | cli.encamino             | en_proceso       | en_camino         |  -         |  -          |
| 05        | cli.llegado              | en_proceso       | llegado           |  -         |  -          |
| 06        | cli.atendido             | atendido         | completada        |  -         | completado  |
| 07        | cli.cancelado            | cancelado        | cancelada         |  -         |  -          |
| 08        | cli.cotpendiente         | pendiente        | pendiente         | pendiente  |  -          |
| 09        | cli.cotenviada           | pendiente        | pendiente         | enviada    |  -          |
| 10        | cli.cotaceptada          | en_proceso       | en_camino         | aceptada   |  -          |
| 11        | cli.cotrechazada         | cancelado        | cancelada         | rechazada  |  -          |
| 12        | cli.cotexpirada          | cancelado        | cancelada         | expirada   |  -          |
| 13        | cli.pagoprocesando       | atendido         | completada        |  -         | procesando  |
| 14        | cli.pagofallido          | atendido         | completada        |  -         | fallido     |
| 15        | cli.pagoreembolso        | cancelado        | cancelada         |  -         | reembolsado |
| 16        | cli.pagopendiente        | atendido         | completada        |  -         | pendiente   |

## Credenciales

Todas con passwords amigables para pruebas. Ver `config.py` para los
emails exactos. Pattern:

- Admin:    `admin@plataforma.com` / `admin123!`
- Talleres: `gerente@tallerexcelente.com`, `mecanica.central@talleres.test`, `llanteria.cristo@talleres.test` / `taller123!`
- Tecnicos: `tecnico.<nombre>@taller.com` / `tecnico123!`
- Clientes: `cli.<estado>@yary.test` / `cliente123!`

## Como anyadir un escenario nuevo

1. Agregar un cliente nuevo en `config.CLIENTES` con un `key` unico.
2. Crear `SETT/escenarios/eNN_<descripcion>.py` que llame a
   `crear_escenario(db, ctx, EscenarioInput(...))`.
3. Registrar el modulo en `SETT/run_all.ESCENARIOS`.

## Idempotencia

`run_all` ejecuta TRUNCATE CASCADE en todas las tablas operativas antes
de sembrar. Esto significa que **borra todo** y vuelve a generar desde
cero. Si quieres CONGELAR los datos en produccion, pon
`SEED_ON_STARTUP=false` en Render.
