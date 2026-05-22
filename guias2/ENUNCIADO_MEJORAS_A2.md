# Enunciado de Mejoras — Segundo Parcial
**Plataforma Inteligente para Talleres Vehiculares**

---

## Contexto General

Este examen es una continuación del primer parcial. Se trabaja sobre el **mismo stack tecnológico**:

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI (Python) |
| Frontend | Angular |
| Móvil | Flutter |
| IA | Servicio personalizado (no genérico, no sin modificar) |

> **Importante:** No se acepta el uso de IA sin personalización. No se acepta IA respondiendo en inglés ni sin adaptación al contexto del proyecto.

---

## Calendario de Entrega

| Evento | Fecha |
|--------|-------|
| Inicio del examen | 19 de mayo de 2026 |
| Primera presentación de documentos | Viernes 29 de mayo de 2026 |
| Segunda presentación de documentos | Domingo 7 de junio de 2026 |
| Defensa final (todos presentes) | Martes 9 de junio de 2026 |

**Duración total:** 3 semanas.

---

## Metodología

- Proceso Unificado + UML (continuación del parcial anterior).
- Se debe **actualizar el marco teórico** con todas las nuevas terminologías que se incorporan en este parcial.

---

## Características a Implementar

### 1. Módulo de Tiempo Real (WebSocket + Tracking)

**Tecnología requerida:** WebSocket obligatorio.

**Escenario:** Cuando un vehículo sufre un incidente (ej. pinchazo de llanta), el sistema envía una notificación de emergencia a todos los talleres cercanos disponibles. El primer taller que acepta toma el servicio; los demás reciben confirmación de que ya no está disponible.

**Funcionalidades:**
- Notificación masiva a talleres cercanos en tiempo real.
- Confirmación de toma de servicio (desactiva la solicitud para los demás).
- **Tracking en vivo del vehículo del taller** que va en camino (similar a apps de transporte):
  - Posición actual del vehículo.
  - Tiempo estimado de llegada (ETA).
  - Alertas de tráfico o congestión que afecten el tiempo.
- Visualización del movimiento del vehículo en el mapa.

---

### 2. Modo Offline (Sin Conexión a Internet)

**Aplica a:** App móvil (Flutter) **y** web (Angular).

**Escenario:** El usuario no tiene WiFi ni datos, pero la aplicación debe continuar operativa.

**Funcionalidades:**
- Permitir visualizar y gestionar solicitudes existentes sin conexión.
- Encolar solicitudes nuevas realizadas sin internet para sincronizarlas al recuperar conexión.
- Ambos entornos (móvil y web) deben soportar este escenario de manera funcional.

---

### 3. Dashboard de KPIs (Indicadores de Gestión)

**Propósito:** Panel de control con métricas clave del sistema.

**KPIs requeridos:**

| Indicador | Descripción |
|-----------|-------------|
| Tiempo promedio de asignación | Desde que se crea una solicitud hasta que un taller la acepta |
| Tiempo promedio de llegada | Desde la aceptación hasta la llegada al lugar del incidente |
| Incidentes por tipo | Clasificación de solicitudes según el tipo de servicio requerido |
| Talleres más eficientes | Ranking de talleres basado en tiempos y calificaciones |

---

### 4. SaaS Multi-Tenant

**Concepto clave:** Cada taller es un **tenant** independiente.

**Reglas de aislamiento:**
- El taller A (tenant 1) **no puede ver ni acceder** a datos del taller B (tenant 2).
- Cada tenant tiene sus propios recursos y base de datos.
- No es lo mismo multi-tenant que single-tenant — se debe comprender e implementar correctamente.

**Implicación en el registro de talleres:**
- Al registrar un taller, se deben especificar todos sus **servicios disponibles** (ver sección siguiente).
- Esta información es fundamental para el matching con el tipo de incidente del cliente.

---

## Tipos de Talleres y Servicios

Los talleres **no son todos iguales**. El sistema debe distinguirlos por especialidad. Al registrar un taller se deben declarar sus servicios.

| Tipo de Servicio | Descripción |
|-----------------|-------------|
| Servicio de llantas | Vulcanizado, parches, inflado de neumáticos |
| Mecánica general | Reparación de motor, transmisión, etc. |
| Servicio eléctrico | Sistema eléctrico del vehículo |
| Servicio electrónico | Diagnóstico por escáner, sistemas ECU, LED |
| Chapería y pintura | Reparación de carrocería, pintura, daños por colisión |
| Grúa / Auxilio vial | Remolque de vehículos que no arrancan |
| Servicio rutinario | Mantenimientos preventivos básicos |

> El sistema debe poder filtrar y mostrar **solo los talleres que proveen el servicio específico** que el cliente necesita según el tipo de incidente.

---

## Funcionalidad de Cotización

**Escenario:** Antes de confirmar un servicio, el cliente puede solicitar cotizaciones a varios talleres.

**Reglas:**
- No existe tarifa única; cada taller tiene sus propias tarifas.
- El cliente debe poder recibir **al menos 2 o 3 cotizaciones** comparativas.
- La cotización debe incluir el costo del servicio **y** de los repuestos si aplica.
- El cliente elige el taller basándose en precio, reputación y garantía ofrecida.
- Esta funcionalidad aplica cuando el servicio requiere trabajo interno al vehículo (no aplica para servicios simples como inflar una llanta).

---

## Funcionalidad de Cancelación de Servicio

**Escenario:** El cliente confirmó un taller, pero su seguro respondió y llegará antes.

**Reglas:**
- El cliente puede **cancelar un servicio confirmado**.
- Al cancelar, el taller que acudió debe recibir un **reconocimiento económico** por el desplazamiento realizado (costo de traslado/pasaje).
- Puede darse el caso de que ambos (taller y seguro) lleguen al mismo tiempo — el cliente elige quedarse con el seguro, pero el taller igual debe ser compensado.

---

## Resumen de Funcionalidades Nuevas

| # | Funcionalidad | Tecnología Principal |
|---|--------------|---------------------|
| 1 | Módulo de tiempo real con tracking | WebSocket + Mapas |
| 2 | Modo offline | Service Workers / Local Storage |
| 3 | Dashboard de KPIs | Gráficas / Analytics |
| 4 | SaaS Multi-tenant | Arquitectura de base de datos por tenant |
| 5 | Registro de servicios por taller | Modelo de datos extendido |
| 6 | Cotización de servicios | Flujo de solicitud/respuesta entre cliente y taller |
| 7 | Cancelación con reconocimiento | Lógica de negocio + notificaciones |

---

## Notas Finales

- El marco teórico debe incluir: **WebSocket**, **multi-tenant**, **SaaS**, **KPI**, **tracking**, **modo offline**.
- Cada grupo debe registrar talleres de prueba con distintos tipos de servicios para poder demostrar el filtrado correcto.
- La IA integrada debe estar **personalizada al contexto** del proyecto (talleres vehiculares, tipos de servicio, zonas geográficas).
