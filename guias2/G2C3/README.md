# Ciclo 3 — Hardening + release (8 → 9 junio)

> **No empezar hasta que el [Ciclo 2](../G2C2/README.md) esté cerrado.**

## Alcance del ciclo
**Solo implementación/operación**: cerrar deuda técnica del backend y dejar todo listo y respaldado para el día de la defensa.

La **documentación** (marco teórico, UML, manual, guion de demo, FAQ) vive en [G2D/](../G2D/README.md) — se trabaja en paralelo durante todo el proyecto, no es exclusiva de este ciclo.

---

## Fases

| # | Archivo | Tipo | Esfuerzo | Cuándo |
|---|---|---|---|---|
| F1 | [F1_hardening_backend.md](./F1_hardening_backend.md) | Implementación | 0.5 día | Lunes 8 mañana |
| F2 | [F2_release_y_demo_ops.md](./F2_release_y_demo_ops.md) | Operación | 0.5 día | Lunes 8 noche / Martes 9 mañana |

Total: 1 día-persona de trabajo técnico.

## En paralelo, equipo de docs ataca G2D:
- [G2D/D1 — Marco teórico](../G2D/D1_marco_teorico.md)
- [G2D/D2 — Diagramas UML](../G2D/D2_diagramas_uml.md)
- [G2D/D3 — Manual de usuario](../G2D/D3_manual_usuario.md)
- [G2D/D4 — Guion de demo](../G2D/D4_guion_demo.md)
- [G2D/D5 — FAQ + ensayo](../G2D/D5_faq_y_ensayo.md)

---

## Pre-requisitos
- [ ] Ciclo 2 cerrado: 75+ tests verdes, demo C2 funcional.
- [ ] `pg_dump` instalado (o Docker disponible como alternativa).
- [ ] Capacidad de grabar pantalla (OBS, Xbox Game Bar, QuickTime).
- [ ] USB con ≥1GB libres para backup.

---

## Checklist final pre-defensa (mañana del 9 jun)

Resumen del checklist operacional. Detalle completo en [F2 §6](./F2_release_y_demo_ops.md#6-checklist-operacional-final).

### Hora -3h
- [ ] `docker compose ps` → Redis healthy.
- [ ] `python -m scripts.preflight_demo` → 0 (verde).
- [ ] Backend, web Angular, Flutter cliente+técnico arriba.
- [ ] 3 navegadores con 3 talleres distintos logueados.
- [ ] Token super-admin copiado.

### Hora -1h
- [ ] USB con bundles + dump + videos conectado.
- [ ] Cargador laptop, adaptador HDMI.
- [ ] Ensayo final cronometrado (ver [G2D/D5](../G2D/D5_faq_y_ensayo.md#3-plan-de-ensayo)).

### Hora 0
- [ ] WiFi del aula andando.
- [ ] Pantalla extendida, notificaciones silenciadas.
- [ ] Tabs pinneadas: `/docs`, dashboard taller, terminal logs.

---

## Anti-patrones del ciclo

- ❌ Refactorizar masivamente a último momento.
- ❌ Agregar features nuevos en el Ciclo 3.
- ❌ Probar `start_demo.ps1` por primera vez el día de la defensa.
- ❌ Hacer backup solo en USB (sin nube de respaldo).
- ❌ Confundir documentación (G2D) con implementación (G2C3) — son cosas distintas con audiencias distintas.

---

## Después de la defensa
- [ ] Tag `defensa-final` pusheado a remoto.
- [ ] Bundle + dump archivados a almacenamiento permanente.
- [ ] Si se prometió un fix en vivo: cumplir en 24h.
- [ ] Celebrar 🎉
