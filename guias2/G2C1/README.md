# Ciclo 1 — Fundamentos visibles (19 → 29 mayo)

> Sub-carpeta del plan general [PLAN_DE_MEJORA.md](../PLAN_DE_MEJORA.md).
> Guías de implementación pensadas para ser ejecutadas **en orden** por otro modelo (o developer humano).

---

## Objetivo del ciclo
Cerrar los puntos del enunciado que **NO** son tiempo real ni offline:
catálogo extendido de talleres por especialidad, cotización comparativa, y cancelación con compensación. Demostrable en la 1ra presentación (29 may).

## Orden de ejecución (dependencias)

```
F1 (servicios extendidos)  ─┬─► F2 (cotización)        ─┐
                            └─► F3 (cancelación)        ─► F4 (tests del ciclo)
```

| # | Archivo | Estima | Bloquea a |
|---|---|---|---|
| F1 | [F1_servicios_extendidos.md](./F1_servicios_extendidos.md) | 2 días | F2, F3 |
| F2 | [F2_cotizacion.md](./F2_cotizacion.md) | 3 días | F4 |
| F3 | [F3_cancelacion.md](./F3_cancelacion.md) | 2 días | F4 |
| F4 | [F4_tests.md](./F4_tests.md) | continuo | — |

---

## Convenciones (leer antes de implementar)

1. **Migraciones**: siempre Alembic. Nombre: `00NN_descripcion_corta`. Ejecutar:
   ```bash
   .\venv\Scripts\alembic.exe revision -m "00NN_descripcion"
   ```
   Editar el archivo generado en `alembic/versions/`. Aplicar:
   ```bash
   .\venv\Scripts\alembic.exe upgrade head
   ```

2. **Multi-tenant**: toda tabla con datos del taller lleva `id_tenant` (FK + index). El filtro global lo aplica automáticamente — solo asegúrate de **inyectar `id_tenant` al insertar** desde el contexto:
   ```python
   from app.core.tenant_context import current_tenant
   obj = MiModelo(..., id_tenant=current_tenant.get())
   ```

3. **Endpoints**: ubicar en `app/api/<recurso>.py`. Registrar router en `app/api/__init__.py` y `app/main.py`. Tags claros para Swagger.

4. **Schemas Pydantic**: en `app/schemas/<recurso>_schema.py`. Usar `ConfigDict(from_attributes=True)`.

5. **Lógica de negocio compleja**: a `app/services/<dominio>_service.py`, NO en el endpoint. El endpoint solo orquesta.

6. **Tests**: en `tests/test_<feature>.py`. Usar fixtures de `conftest.py` (`tenant_factory`, `taller_factory`, `taller_auth_headers`, `admin_headers`). Cada test rolls back automáticamente (SAVEPOINT).

7. **No tocar** los modelos `Tenant`, `Plan`, `Suscripcion`, `TenantUser`, `Taller.id_tenant` ni el middleware/filtro tenant — están finalizados.

---

## Criterios de cierre del ciclo
- [ ] `alembic upgrade head` aplica limpio en BD vacía.
- [ ] `pytest tests/` con **≥50 tests verdes** (los 25 actuales + ~25 nuevos).
- [ ] Swagger (`/docs`) muestra los nuevos endpoints documentados.
- [ ] 3 talleres seed con servicios distintos (llantas, chapería, grúa) demuestran filtrado.
- [ ] Demo grabada: cliente reporta incidente → recibe 2 cotizaciones → acepta una → cancela y se calcula compensación.

---

## Glosario

| Término | Definición |
|---|---|
| **Categoría** | Tipo de incidente reportado (llanta, motor, eléctrico…). Tabla `categoria_problema`. |
| **Servicio** | Lo que un taller declara que puede atender. Tabla `taller_servicio` (M:N taller ↔ categoría). |
| **Cotización** | Oferta económica de un taller para un incidente concreto, antes de aceptar. |
| **Compensación** | Pago al taller que se desplazó pero el cliente canceló. Calculado por taller (`tarifa_traslado`). |
| **Tenant** | Organización dueña de uno o más talleres. Ya implementado (no tocar). |
