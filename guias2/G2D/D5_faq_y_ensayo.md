# D5 — FAQ defensa + plan de ensayo

> **Documentación de preparación para la defensa.**
> Para la operativa (backup, tag git, dump BD, videos), ver [G2C3/F2_release_y_demo_ops.md](../G2C3/F2_release_y_demo_ops.md).
> **Esfuerzo:** 0.5 día (incluye 2 ensayos).

## Objetivo
- Memorizar respuestas a las preguntas técnicas previsibles.
- Ensayar la presentación al menos 2 veces.
- Definir roles y anti-patrones para la defensa del 9 de junio.

---

## 1. Preguntas frecuentes anticipadas (FAQ)

### Generales / arquitectura

**P1: ¿Por qué FastAPI y no Django / Flask?**
- Async nativo (necesario para WebSocket + pub/sub).
- Validación automática vía Pydantic (menos código).
- OpenAPI/Swagger automático (`/docs`).
- Performance superior en benchmarks (mismo orden que Node/Go).

**P2: ¿Por qué Angular en lugar de React?**
- Standalone components reducen boilerplate.
- HttpClient y Service Worker integrados (necesario para PWA).
- Tooling oficial para PWA (`ng add @angular/pwa`).
- Mejor para apps de "panel" con muchos formularios y rutas.

**P3: ¿Por qué Flutter y no React Native?**
- Un solo codebase para iOS + Android sin diferencias.
- Mejor performance en mapas y animaciones.
- Hot reload muy rápido para desarrollo.
- Mejor ecosistema para offline (sqflite, drift).

---

### Multi-tenant

**P4: ¿Por qué shared-schema con `tenant_id` y no schema-per-tenant?**
- Operaciones cross-tenant para super-admin y billing son triviales.
- Una sola migración Alembic para todos.
- Costo de infraestructura mucho menor.
- Trade-off: el aislamiento depende del código. Lo mitigamos con filtro global ORM.

**P5: ¿Cómo garantizan que un tenant no vea datos de otro?**
- Cada tabla "tenant-scoped" lleva `id_tenant` (FK + index).
- Middleware extrae `id_tenant` del JWT al iniciar el request, lo guarda en `ContextVar`.
- Listener `do_orm_execute` de SQLAlchemy inyecta `WHERE id_tenant=…` automáticamente con `with_loader_criteria` a todo query.
- Tests específicos (`test_tenant_isolation.py`) verifican el aislamiento.
- Endpoints que necesitan ver cross-tenant (super-admin, billing) hacen `current_tenant.set(0)` explícito como escape hatch.

**P6: ¿Qué pasa si alguien con rol admin pero de otro tenant intenta ver datos ajenos?**
- El admin no tiene tenant_id=0 automáticamente. Su JWT lleva su propio tenant. El filtro lo limita a su scope.
- Solo el super-admin global (rol=4) sin tenant en JWT puede ver todo.

**P7: ¿Por qué `taller.id_tenant NOT NULL` pero `incidente.id_tenant` nullable?**
- Taller siempre pertenece a un tenant (modelo de negocio).
- Incidente nace público (cliente reporta sin pertenecer a tenant). Adquiere `id_tenant` cuando un taller lo acepta. Es la única excepción.

---

### Tiempo real

**P8: ¿Qué pasa si Redis cae?**
- Los WebSockets siguen funcionando dentro de un solo worker (modo "local-only").
- Eventos entre workers se pierden pero la API sigue viva.
- Es degradación gradual, no caída total.
- En `app/realtime/pubsub.py` hay try/except con fallback local.

**P9: ¿Cómo escalan los WebSockets si hay 1000 talleres conectados?**
- Cada worker uvicorn mantiene N conexiones locales.
- Redis pub/sub sincroniza eventos entre workers.
- Escalar = más workers + Redis cluster eventualmente.
- Para >10k conexiones simultáneas, considerar separar el servicio WS en un proceso aparte.

**P10: ¿Por qué `with_for_update()` en `/aceptar` y no optimistic locking?**
- Carrera de "primer click gana" se resuelve mejor con pesimista.
- Volumen de aceptaciones simultáneas por incidente es bajo (5-10 max), no introduce contention.
- Optimistic locking devolvería 409 al perdedor sin garantizar cuál ganó.

---

### Tracking

**P11: ¿Por qué OSRM y no Google Maps?**
- OSRM es gratis y open source.
- Para producción podríamos hostearlo (`osrm-backend` en Docker).
- Tiene fallback a Haversine (geodésico simple) si OSRM falla.
- Google Maps requiere billing y key.

**P12: ¿Por qué 12 segundos de intervalo de GPS y no 5?**
- Balance batería del técnico vs UX del cliente.
- A 12s con velocidad típica urbana, el marker se mueve cada ~100m.
- Configurable si el taller lo requiere.

**P13: ¿Cómo manejan permisos de GPS en background?**
- En foreground durante la asignación activa (suficiente).
- Background tracking requiere foreground service en Android + capabilities en iOS. Está documentado como mejora futura.

---

### Offline

**P14: ¿Cómo resuelven conflictos cuando dos clientes editan offline?**
- Política last-write-wins implícita: gana el que sincroniza después.
- Para detección formal de conflictos, agregar `version` numérico y devolver 409 si el cliente envía versión vieja. No lo implementamos por simplicidad.

**P15: ¿Qué pasa si el outbox tiene 500 items pendientes cuando vuelve la conexión?**
- El drain procesa secuencialmente, máximo 5 reintentos por item.
- 4xx descarta (el server rechazó, retry no sirve).
- 5xx reintenta exponencialmente.
- Items con >7 días se eliminan (limpieza periódica).

**P16: ¿Qué pasa con las fotos en outbox si desinstalo la app?**
- Se pierden (están en directorio de la app).
- Esto se documenta como limitación conocida.

---

### IA

**P17: ¿La IA es genérica?**
- No. Prompts en español, dominio talleres bolivianos.
- Output restringido a 7 categorías oficiales del catálogo.
- Validación post-modelo descarta cualquier código inventado.
- Cache Redis 24h reduce gasto en >85%.
- Fallback heurístico (keywords) si Gemini no responde.

**P18: ¿Por qué no usan embeddings o RAG?**
- Para clasificación a 7 categorías, prompt directo es suficiente y barato.
- RAG agregaría latencia y costo sin mejorar precisión medible.
- Para reportes textuales largos (no implementado en este parcial), RAG sería ideal.

**P19: ¿Qué pasa si Gemini clasifica mal?**
- Si confianza < 0.5 → `requiere_revision_manual=True`.
- En esos casos el sistema notifica a TODOS los talleres compatibles (no filtra por categoría).
- El primer taller que acepta decide la categoría correcta implícitamente.

---

### Calidad

**P20: ¿Tests? ¿Cobertura?**
- 75+ tests pytest, 0 fallos.
- Cobertura ≥70% global, ≥90% en `app/core/tenant_*` (crítico de seguridad).
- Cada test se ejecuta en SAVEPOINT (rollback automático), no contamina BD.
- Fixtures de dominio (`tenant_factory`, `cliente_factory`, etc.) reutilizadas.

**P21: ¿Cómo despliegan?**
- Backend: container Docker → cualquier VPS o AWS ECS/Fargate.
- Frontend Angular: build static → Cloudflare Pages, Netlify, S3+CloudFront.
- BD: Postgres managed (RDS, Supabase, Neon).
- Para parcial trabajamos local; archivos `render.yaml`/`Dockerfile` listos para promoción.

**P22: ¿Y la seguridad de los JWT?**
- Algoritmo HS256 (HMAC con secret).
- Expiración 30 min configurable.
- Secret en `.env` (gitignored).
- Sin refresh token automático en este alcance — re-login al expirar.

---

### Negocio

**P23: ¿Por qué los talleres aceptarían pagar?**
- Plan free: 1 taller, 3 técnicos, 100 incidentes/mes. Gancho gratuito.
- Plan pro: más capacidad + KPIs avanzados + WebSocket priority.
- Plan enterprise: features de IA + multi-sucursal + soporte.

**P24: ¿Cómo monetiza la plataforma?**
- Suscripción mensual del taller (recurrente).
- Comisión del 10% sobre cada pago (taller recibe 90%).
- Compensación de cancelaciones genera tarifa también.

---

## 2. Top-10 a memorizar de verdad

Si solo tienes tiempo de memorizar 10: P4, P5, P6 (multi-tenant — siempre las preguntan), P8, P9 (Redis/escalabilidad), P14, P15 (offline), P17, P19 (IA), P20 (tests).

---

## 3. Plan de ensayo

### Sesión 1 (lunes 8 jun, tarde)
- Equipo completo presente.
- Demo de principio a fin sin pausas.
- Cronometrar cada escenario.
- Identificar el punto débil (en cuál tartamudean más).
- Al final: 10 minutos de Q&A simulado (alguien hace de evaluador).

### Sesión 2 (martes 9 jun, mañana, 2h antes)
- Solo demo + preguntas clave.
- Practicar transición entre escenarios.
- Verificar setup operacional (ver G2C3/F2).
- Cerrar todo lo que no se usa (Slack, Discord, notificaciones).

---

## 4. Roles durante la defensa

| Rol | Responsabilidad |
|---|---|
| **Presentador principal** | Narra los escenarios, mira a la audiencia |
| **Operador técnico** | Hace clicks/comandos (puede ser el mismo) |
| **Q&A lead** | Responde preguntas (el de más dominio técnico) |
| **Backup** | Tiene videos y datos a mano por si falla algo |

Si son 1-2 personas, asumir múltiples roles. Lo importante: alguien siempre mirando los logs por si aparece error.

---

## 5. Anti-patrones (NO HACER)

- ❌ "Esto fue muy difícil pero…" → empezar con disculpas baja autoridad.
- ❌ Leer las slides → mirar a la audiencia y al código.
- ❌ "No tuvimos tiempo para…" → mostrar solo lo que funciona, omitir lo faltante salvo que pregunten.
- ❌ Improvisar comandos en terminal mientras hablas → preparado o no se hace.
- ❌ Discutir con el evaluador si dice algo "incorrecto" → "buena observación, lo revisamos" y seguir.
- ❌ Hacer la demo desde cero → siempre con datos semilla preparados.
- ❌ Reír nervioso o decir "este código no es el mejor" → autoridad cero.

---

## 6. Reglas de oro

- La defensa **no** es sobre lo perfecto que es el sistema. Es sobre demostrar que **entiendes lo que construiste**.
- Si te preguntan algo que no sabes: decir "no lo sé, pero lo investigaré" es mejor que improvisar mal.
- El examinador valora **claridad arquitectónica** y **decisiones explicables** sobre cantidad de features.
- Frases preparadas para situaciones incómodas:
  - "Buena observación, lo evaluamos para la siguiente iteración."
  - "Esa decisión la tomamos por X, pero efectivamente Y sería una alternativa válida."
  - "Permítame mostrar el siguiente escenario y volvemos a su pregunta."

---

## 7. Después de la defensa

- [ ] Marcar memoria pendiente: ¿qué pregunta no supe responder bien? (aprendizaje para futuro)
- [ ] Si se prometió un fix en vivo: cumplir en 24h.
- [ ] Celebrar 🎉

---

## Checklist de cierre D5

- [ ] FAQ revisada y top-10 memorizadas.
- [ ] 2 sesiones de ensayo completas hechas (sin pausas).
- [ ] Roles asignados por persona (si trabajan en equipo).
- [ ] Anti-patrones leídos en voz alta antes del ensayo.
- [ ] Frases preparadas para situaciones incómodas memorizadas.

## Notas
- **Cobertura, ranking, tests** son las 3 métricas que más impresionan a evaluadores académicos. Tenerlas en la punta de la lengua.
- **Si la defensa la das tú solo**, recortar 1 escenario menos crítico y hablar más despacio.
- **Toma agua** antes de empezar — la voz se quiebra cuando estás nervioso.
