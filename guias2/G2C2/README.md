# Ciclo 2 — Tiempo real, KPIs y offline (30 mayo → 7 junio)

> **No empezar hasta que el [Ciclo 1](../G2C1/README.md) esté cerrado**
> (todos sus criterios de aceptación cumplidos y tests verdes).

## Objetivo del ciclo
Demostrar para la 2da presentación el "lado premium" del producto: emergencias en tiempo real con broadcast a múltiples talleres, tracking GPS en vivo en mapa, dashboard de KPIs, modo offline web y mobile, e IA personalizada al contexto.

---

## Fases (en orden recomendado)

| # | Archivo | Esfuerzo | Bloquea a | Puede ir en paralelo con |
|---|---|---|---|---|
| F1 | [F1_redis_websocket_infra.md](./F1_redis_websocket_infra.md) | 1 día | F2, F3 | — (primera) |
| F2 | [F2_broadcast_emergencia.md](./F2_broadcast_emergencia.md) | 2 días | — | F4, F5, F6, F7 |
| F3 | [F3_tracking_gps.md](./F3_tracking_gps.md) | 2 días | — | F4, F5, F6, F7 |
| F4 | [F4_dashboard_kpis.md](./F4_dashboard_kpis.md) | 2 días | — | F2/F3/F5/F6/F7 |
| F5 | [F5_offline_web_angular.md](./F5_offline_web_angular.md) | 1.5 días | — | resto |
| F6 | [F6_offline_flutter.md](./F6_offline_flutter.md) | 1.5 días | — | resto |
| F7 | [F7_ia_personalizada.md](./F7_ia_personalizada.md) | 1 día | — | resto |
| F8 | [F8_tests.md](./F8_tests.md) | continuo | — | continuo |

## Dependencias visualizadas

```
F1 (Redis+WS) ─┬─► F2 (broadcast)
               └─► F3 (tracking)

F4 (KPIs)        independiente, se hace sobre datos de C1
F5 (offline web)  independiente (frontend)
F6 (offline mobile) independiente (frontend)
F7 (IA)           usa catalogo de C1.F1 (codigos categorias)
F8 (tests)        cada fase agrega los suyos + E2E al final
```

## Plan sugerido por días

| Día | Lo que se hace | Equipo idealmente |
|---|---|---|
| 1 (vie 30 may) | F1 backend; F5 setup PWA en web | 2 personas |
| 2 (sab 31 may) | F1 finaliza tests; F6 setup sqflite mobile | 2 personas |
| 3 (lun 2 jun)  | F2 broadcast emergencia | 2 personas |
| 4 (mar 3 jun)  | F2 finaliza + F4 KPIs backend | 2-3 personas |
| 5 (mie 4 jun)  | F3 tracking GPS | 2 personas |
| 6 (jue 5 jun)  | F4 dashboard Angular; F7 IA prompts | 2 personas |
| 7 (vie 6 jun)  | F5/F6 offline finalizar + E2E manual | 2 personas |
| 8 (sab 7 jun)  | F8 E2E suite + entrega 2da presentación | todos |

Si son **solos / 2 personas**: recortar F4 a solo 2 KPIs (asignación + categorías), y F7 puede quedar con heurística + cache sin Gemini real (es válido para la defensa si se explica).

---

## Pre-requisitos antes de arrancar
- [ ] Ciclo 1 totalmente cerrado (tests verdes, demo OK).
- [ ] Redis instalado:
  ```yaml
  # docker-compose.yml en raiz del Backend
  services:
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
  ```
  ```bash
  docker compose up -d redis
  ```
- [ ] `REDIS_URL=redis://localhost:6379/0` en `.env`.
- [ ] Decisión: ¿Google Maps API (key gratis) o OSRM público? (la guía F3 asume OSRM público por defecto).
- [ ] (Frontend) Acceso `npm` instalado en `web/`. `flutter pub get` funcional en `flutter/`.

---

## Criterios de cierre del ciclo (verificar el 7 junio)
- [ ] Demo: 3 talleres conectados por WS reciben emergencia simultánea; primer click gana, los demás ven "tomada".
- [ ] Cliente Flutter ve técnico moviéndose en mapa con ETA actualizándose cada ~12s.
- [ ] Cuando el técnico entra en 100m del incidente, estado pasa a "llegado" automáticamente.
- [ ] Dashboard Angular muestra los 4 KPIs del enunciado con datos reales del tenant.
- [ ] Web Angular instalable como PWA (Lighthouse PWA score > 80), lista incidentes con WiFi apagado.
- [ ] App Flutter crea incidente sin internet (badge "pendiente_local") y lo sincroniza al reconectar (badge desaparece).
- [ ] IA clasifica 5 frases en español boliviano a los códigos oficiales correctamente.
- [ ] `pytest tests/` → **≥75 tests verdes**.
- [ ] Cobertura ≥ 60%.
- [ ] Marco teórico actualizado con secciones WebSocket, tracking, KPI, offline (en `guias2/MARCO_TEORICO.md` o donde corresponda).

---

## Convenciones (repaso del Ciclo 1)
1. Toda migración pasa por Alembic. Próximas numeradas: `0007_ubicacion_tecnico` (F3), no necesita más.
2. Toda tabla con datos del taller lleva `id_tenant` con FK + index.
3. Endpoints públicos (cliente final) NO requieren tenant. Tests cubren ambos casos.
4. Lógica compleja a `app/services/`. Endpoints solo orquestan.
5. **Nuevo en C2**: endpoints que disparan broadcasts deben ser `async def`. Si un endpoint existente debe pasar a async, hacerlo en commit aparte para que el diff sea revisable.

## Estructura técnica resultante (post-ciclo 2)

```
Backend/
├── docker-compose.yml          (Redis)
├── alembic/versions/
│   ├── 0001...0006             (Ciclo 1)
│   └── 0007_ubicacion_tecnico.py
├── app/
│   ├── api/
│   │   ├── kpis.py             (F4)
│   │   └── (existentes...)
│   ├── ai_modules/             (F7 - refactor)
│   │   ├── classifier.py
│   │   ├── cache.py
│   │   └── prompts/*.md
│   ├── realtime/               (F1)
│   │   ├── ws_manager.py
│   │   ├── pubsub.py
│   │   ├── auth.py
│   │   └── endpoints.py
│   ├── services/
│   │   ├── matching_service.py     (F2)
│   │   ├── broadcast_service.py    (F2)
│   │   ├── notify_service.py       (F1)
│   │   ├── tracking_service.py     (F3)
│   │   └── kpi_service.py          (F4)
│   ├── models/
│   │   └── ubicacion.py            (F3)
│   └── schemas/
│       ├── kpi_schema.py
│       └── tracking_schema.py
└── tests/
    ├── test_ws_infra.py        (F1)
    ├── test_broadcast.py       (F2)
    ├── test_tracking.py        (F3)
    ├── test_kpis.py            (F4)
    ├── test_ia_classifier.py   (F7)
    ├── test_e2e_ciclo2.py      (F8)
    └── test_smoke_ciclo2.py    (F8)
```

```
web/ (Angular)
├── ngsw-config.json            (F5)
├── manifest.webmanifest        (F5)
└── src/app/
    ├── dashboards/taller/
    │   ├── emergencias/        (F2 UI)
    │   └── kpis/               (F4 UI)
    ├── shared/
    │   ├── services/realtime.service.ts  (F1 UI)
    │   └── offline/
    │       ├── local-db.ts             (F5)
    │       ├── outbox.service.ts       (F5)
    │       ├── offline.interceptor.ts  (F5)
    │       └── offline-banner.component.ts
```

```
flutter/ (Mobile)
└── lib/
    ├── screens/
    │   ├── esperando_taller_screen.dart  (F2 UI cliente)
    │   └── tracking_screen.dart          (F3 UI mapa)
    ├── services/
    │   ├── realtime_service.dart         (F1)
    │   ├── location_sender.dart          (F3 tecnico)
    │   └── offline/
    │       ├── local_db.dart             (F6)
    │       ├── outbox_service.dart       (F6)
    │       └── incidente_repository.dart (F6)
    └── widgets/
        └── offline_banner.dart           (F6)
```

---

## Riesgos del ciclo (mitigación)

| Riesgo | Mitigación |
|---|---|
| Permisos GPS Android en background | Solo en foreground durante asignación activa, documentar en defensa |
| Conflictos de sync offline | Last-write-wins explícito + idempotencia via `X-Client-Id` |
| OSRM público con rate-limit | Cache de ETAs por origen-destino con TTL 60s |
| Quota Gemini al hacer demo | Pre-cargar cache con respuestas conocidas + heurística de respaldo |
| WS no funciona detrás de proxy corporate en demo | Probar con `ws://` directo a IP local, no detrás de túnel |
| Tests lentos por SAVEPOINT con datos en BD | Si pasa 30s, revisar fixtures que no commitean innecesariamente |

---

## Próximo
Cuando este ciclo cierre, abrir [G2C3/README.md](../G2C3/README.md) para hardening + defensa.
