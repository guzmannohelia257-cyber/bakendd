# D1 — Marco teórico (entrega final)

> **Pre-requisito:** Ciclos 1 y 2 cerrados (necesitas saber qué construiste para teorizarlo).
> **Esfuerzo:** 0.5 día.

## Objetivo (del enunciado)
> "Se debe actualizar el marco teórico con todas las nuevas terminologías que se incorporan en este parcial."
> Nuevos términos requeridos: **WebSocket, multi-tenant, SaaS, KPI, tracking, modo offline**.

## Formato sugerido
Crear archivo `guias2/MARCO_TEORICO.md` (o anexarlo al PDF del primer parcial). Aquí dejamos las **secciones ya redactadas** que puedes adaptar a tu plantilla institucional (Word/LaTeX).

> Las plantillas que siguen están en estilo académico neutral. Citar fuentes según tu universidad.

---

## Plantilla: secciones a copiar

### 1. Arquitectura SaaS Multi-tenant

**Software as a Service (SaaS)** es un modelo de distribución de software en el que el proveedor mantiene la infraestructura, el código y los datos de todos sus clientes (tenants), exponiendo el producto a través de internet. El usuario no instala nada localmente; accede vía navegador o app móvil mediante autenticación.

Un **tenant** es una unidad organizacional aislada dentro de una aplicación SaaS — típicamente una empresa, equipo u organización cliente. Cada tenant tiene sus propios usuarios, datos y configuración, y **no debe poder ver ni modificar los datos de otro tenant**.

Existen tres estrategias principales de **aislamiento de datos** en arquitecturas multi-tenant:

| Estrategia | Aislamiento | Costo | Operación |
|---|---|---|---|
| Database-per-tenant | Total | Alto | Backup/migración por tenant |
| Schema-per-tenant | Alto | Medio | Una BD, N esquemas |
| Shared-schema con `tenant_id` | Lógico | Bajo | Una BD, una tabla, filtro por columna |

El presente sistema implementa la estrategia **shared-schema con `tenant_id`**, que es la más usada en SaaS de tamaño pequeño-mediano (Notion, Slack, Linear, etc. usan variantes). Sus ventajas: una sola migración para todos los tenants, costo de infraestructura bajo, consultas cross-tenant posibles para super-admin y billing. Su principal desventaja: el aislamiento depende de que el código siempre filtre por `tenant_id`, lo que se mitiga con un **filtro global en la capa ORM**.

Concretamente, se utiliza el evento `do_orm_execute` de SQLAlchemy 2.0 junto con `with_loader_criteria`, que intercepta toda consulta SELECT/UPDATE/DELETE sobre modelos que declaran la columna `id_tenant` y le añade automáticamente `WHERE id_tenant = <actual>`. El "tenant actual" se propaga por request mediante un `ContextVar` de Python, poblado por un middleware que extrae el `id_tenant` del JWT del usuario autenticado.

> Cita conceptual: Microsoft Patterns & Practices, *Multi-tenant SaaS database tenancy patterns*; AWS Whitepaper, *SaaS Tenant Isolation Strategies*.

---

### 2. WebSocket y comunicación bidireccional en tiempo real

**WebSocket** (RFC 6455) es un protocolo de comunicación full-duplex sobre una única conexión TCP, diseñado para sustituir patrones de polling HTTP en escenarios donde el servidor necesita empujar datos al cliente con baja latencia.

A diferencia de HTTP request/response, donde el cliente debe preguntar repetidamente "¿hay novedades?", WebSocket permite que cualquiera de los dos extremos envíe mensajes sin que el otro lo solicite. La conexión se establece con un *handshake* HTTP 1.1 que incluye los headers `Upgrade: websocket` y `Connection: Upgrade`, y luego se mantiene abierta durante toda la sesión.

En el contexto de plataformas de atención de emergencias, WebSocket habilita:

- **Broadcast de eventos**: cuando se crea una emergencia, todos los talleres compatibles conectados al sistema lo reciben simultáneamente, en menos de un segundo.
- **Tracking en vivo**: el técnico envía su posición GPS cada 10-15 segundos al servidor, que la reenvía al cliente a través de la conexión persistente, permitiendo visualizar el desplazamiento en mapa sin recargar.
- **Atomicidad first-accept-wins**: aunque varios talleres reciban la misma emergencia, el primero que envía POST `/aceptar` gana la asignación gracias a un bloqueo pesimista a nivel de fila (`SELECT … FOR UPDATE`), y a los demás se les notifica el evento `incidente.tomado`.

Para soportar múltiples procesos servidor (necesario para escalar), se introduce un broker de mensajes basado en **Redis Pub/Sub**, que reenvía cualquier evento publicado en un canal a todos los workers suscritos. Sin este componente, dos talleres conectados a workers distintos no compartirían eventos.

> Cita conceptual: Fette & Melnikov, RFC 6455; Carlson, *Redis in Action*, cap. 8 (Pub/Sub).

---

### 3. Indicadores Clave de Desempeño (KPI)

Un **KPI (Key Performance Indicator)** es una métrica cuantitativa que mide el grado de cumplimiento de un objetivo de negocio crítico. A diferencia de métricas técnicas (latencia, throughput), los KPIs se orientan a decisiones gerenciales y comparaciones entre periodos.

Los KPIs implementados en el sistema responden a las preguntas operativas más relevantes para un taller mecánico:

| KPI | Pregunta de negocio | Fórmula |
|---|---|---|
| Tiempo promedio de asignación | ¿Cuán rápido un taller responde a las emergencias entrantes? | `avg(asignacion.created_at − incidente.created_at)` en minutos |
| Tiempo promedio de llegada | ¿Cuánto tarda el técnico en llegar después de aceptar? | `avg(historial.estado_llegado − historial.estado_aceptada)` |
| Incidentes por tipo | ¿Qué tipo de problema vehicular es más frecuente? | `count(*) group by categoria_problema.codigo` |
| Talleres más eficientes | ¿Cuáles talleres operan mejor? Ranking compuesto | `0.5·rating + 0.3·tasa_aceptacion + 0.2·log(completadas+1)` |

Estos indicadores se calculan **on-the-fly** mediante agregaciones SQL respetando el filtro multi-tenant (un taller solo ve sus propios KPIs). Si en el futuro el volumen crece, se puede precalcular en una tabla `kpi_diario_taller` actualizada por una tarea programada (cron), o usar **vistas materializadas** de PostgreSQL.

> Cita conceptual: Parmenter, *Key Performance Indicators: Developing, Implementing, and Using Winning KPIs*, 4th ed.

---

### 4. Tracking en tiempo real y geofencing

**Tracking** se refiere al seguimiento continuo de la posición geográfica de un activo móvil (vehículo, técnico) y su visualización para terceros autorizados. Los datos típicos transmitidos por punto son: latitud, longitud, precisión (`accuracy_m`), velocidad y *timestamp*.

El cálculo del **ETA (Estimated Time of Arrival)** puede hacerse de dos formas:

1. **Heurístico**: distancia geodésica (fórmula de **Haversine**) dividida por una velocidad promedio supuesta (~40 km/h en ciudad). Es instantáneo y no depende de servicios externos.
2. **Routing real**: una API de routing como OSRM (Open Source Routing Machine, [http://project-osrm.org](http://project-osrm.org)) o Google Directions, que considera la red vial y devuelve la distancia y duración reales por carretera. Es más preciso pero introduce latencia y dependencia externa.

El sistema usa la opción 2 con fallback a la opción 1 si el servicio externo no responde.

**Geofencing** es la técnica de definir una zona geográfica virtual (típicamente un círculo de radio R) alrededor de un punto, y disparar acciones cuando un activo móvil entra o sale de esa zona. En este sistema, cuando el técnico entra en un radio de 100 metros del incidente reportado, el estado de la asignación cambia automáticamente a `llegado` sin requerir acción manual del técnico.

> Cita conceptual: Veness, *Calculate distance, bearing and more between Latitude/Longitude points* (Haversine). Reck & Axhausen, *Mode choice, substitution patterns and environmental impacts of shared and on-demand mobility services*.

---

### 5. Modo offline y arquitectura local-first

El **modo offline** es la capacidad de una aplicación de seguir siendo útil cuando no hay conectividad de red, mediante una combinación de cache local de datos previamente sincronizados y encolado de operaciones de escritura para enviarlas cuando se recupere la conexión.

Componentes técnicos por plataforma:

**Web (Angular):**
- **Service Worker** (estándar W3C) intercepta solicitudes HTTP y devuelve respuestas cacheadas cuando no hay red. La configuración se hace con `@angular/pwa` y `ngsw-config.json`.
- **IndexedDB** (a través de la librería Dexie.js) provee una base de datos transaccional persistente en el navegador para datos del dominio.
- **Outbox pattern**: una tabla local de mutaciones pendientes que se drena cuando vuelve la conexión.

**Mobile (Flutter):**
- **SQLite local** (paquete `sqflite`) para cache de entidades y outbox.
- **`connectivity_plus`** para detectar cambios de conectividad y disparar sincronización.
- Mismo patrón de outbox que en web.

La **resolución de conflictos** entre cambios locales y remotos sigue la política **last-write-wins** (gana el último que sincroniza). Para detectar conflictos formalmente se puede agregar un campo `version` a las entidades y devolver `HTTP 409` cuando el cliente envía una versión obsoleta; este sistema no lo implementa por simplicidad.

La **idempotencia** de las mutaciones (necesaria porque un cliente puede reenviar el mismo POST si no recibió la respuesta) se logra mediante el header `X-Client-Id` con un UUID generado localmente, que el servidor usa para deduplicar.

> Cita conceptual: Hood, *Designing Data-Intensive Applications*, cap. 5 (Replication); Kleppmann, *Local-first software: You own your data, in spite of the cloud*, Onward! 2019.

---

### 6. Inteligencia artificial personalizada al dominio

La integración de un Large Language Model (LLM) como Google Gemini en un sistema vertical requiere **personalización al dominio**: prompts en el idioma del usuario, restricción del espacio de salida a categorías oficiales del catálogo, y validación estricta de las respuestas para protegerse de alucinaciones.

En este sistema se aplican las siguientes técnicas:

1. **Prompts versionados**: los prompts se almacenan en archivos Markdown dentro del repositorio (`app/ai_modules/prompts/*.md`), permitiendo versionado por Git y revisión por equipo no técnico.
2. **Salida estructurada**: se exige al modelo responder en JSON con un esquema fijo (`codigo`, `confianza`, `resumen`, `prioridad`, `requiere_revision_manual`).
3. **Validación post-modelo**: cualquier `codigo` que no pertenezca al conjunto oficial de 7 categorías es normalizado a `mecanica_general` con `requiere_revision_manual=True`. La confianza fuera del rango `[0, 1]` se clamp-ea.
4. **Cache de respuestas** en Redis con TTL de 24h: solicitudes con texto idéntico no consumen tokens.
5. **Fallback heurístico**: si Gemini no está disponible, un clasificador basado en *keywords* en español boliviano clasifica con confianza reducida y marca para revisión manual.

> Cita conceptual: Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*; OpenAI, *GPT best practices: structured outputs*.

---

## 7. Glosario consolidado

| Término | Definición |
|---|---|
| Asignación | Vinculación entre incidente y taller (eventualmente, técnico) con estado y costo |
| Backfill | Proceso de poblar datos preexistentes con un nuevo campo introducido en migración |
| Broadcast | Envío de un mensaje a múltiples destinatarios simultáneamente |
| Candidato (asignación) | Taller compatible al que se le ofreció una emergencia, antes de saber quién acepta |
| ContextVar | Variable de Python con scope por contexto async / por request |
| Cotización | Oferta económica con monto, garantía y validez que un taller envía al cliente antes de aceptar |
| ETA | *Estimated Time of Arrival*: tiempo estimado restante para que el técnico llegue |
| Filtro global ORM | Mecanismo que inyecta condiciones WHERE a todas las queries automáticamente |
| First-accept-wins | Estrategia donde el primer agente que responde gana, sin negociación posterior |
| Geofence | Zona geográfica virtual que dispara acciones al entrar o salir |
| IndexedDB | Base de datos transaccional persistente del navegador |
| JWT | *JSON Web Token*: token firmado con claims, usado para autenticación stateless |
| KPI | *Key Performance Indicator*: métrica de cumplimiento de objetivo de negocio |
| Last-write-wins | Política de resolución de conflictos donde el último cambio sobrescribe |
| Multi-tenant | Arquitectura donde múltiples clientes comparten infraestructura con aislamiento lógico |
| Outbox pattern | Cola local de mutaciones pendientes de sincronizar |
| Pub/Sub | Patrón de mensajería donde publicadores emiten y suscriptores reciben sin conocerse |
| Pydantic | Librería Python para validación de datos con tipado estático |
| PWA | *Progressive Web App*: web instalable, con SW y offline |
| Redis | Base de datos en memoria con soporte de pub/sub, cache y locks |
| SaaS | *Software as a Service*: software entregado vía internet bajo suscripción |
| Service Worker | Script de navegador que corre fuera del thread principal e intercepta requests |
| SQLAlchemy | ORM de Python |
| Tenant | Cliente organizacional dentro de un SaaS multi-tenant |
| Tracking | Seguimiento continuo de posición geográfica |
| Vinculación técnico-taller | Relación M:N entre `usuario` (rol técnico) y `taller` vía tabla `usuario_taller` |
| WebSocket | Protocolo TCP bidireccional persistente para tiempo real |

---

## Checklist de cierre D1

- [ ] Sección "Arquitectura SaaS Multi-tenant" en el documento del marco teórico.
- [ ] Sección "WebSocket y tiempo real" incluida.
- [ ] Sección "KPIs" con tabla de 4 indicadores.
- [ ] Sección "Tracking y geofencing".
- [ ] Sección "Modo offline".
- [ ] Sección "IA personalizada".
- [ ] Glosario consolidado al final.
- [ ] Citas a fuentes técnicas verificadas (RFC, libros, papers).
- [ ] Documento exportado a PDF y guardado en `guias2/MARCO_TEORICO.pdf`.

## Notas
- **Si tu plantilla es LaTeX**: usar `\begin{table}` para las tablas. Los bloques de código en Markdown se mapean a `verbatim`.
- **Si es Word**: copiar las tablas directamente del Markdown renderizado en VSCode (Ctrl+Shift+V → "Open Preview").
- **Citas reales**: si tu universidad exige formato APA/IEEE, incluir las referencias completas en la última sección. Las que se mencionan aquí son orientativas.
- **No copiar y pegar literalmente** en plagiar: parafrasea y adapta al nivel de tu curso.
