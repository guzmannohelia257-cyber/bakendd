# D4 — Guion de demo (narrativa para la defensa)

> **Documentación de presentación**, no operación.
> Para la parte operacional (seed de datos, levantar servicios, backup), ver [G2C3/F2_release_y_demo_ops.md](../G2C3/F2_release_y_demo_ops.md).
> **Esfuerzo:** 0.25 día (redacción) + ensayo (en D5).

## Objetivo
Tener un script narrativo cronometrado (12-15 min, 10 escenarios) para la defensa.
Imprimirlo o tenerlo en una pantalla secundaria durante la presentación.

---

## Cómo usar
1. Antes de la defensa: ejecutar el setup operacional (G2C3/F2).
2. Imprimir esta guía o tenerla en una segunda pantalla.
3. Seguir los escenarios en orden — cada uno tiene la frase para decir, la acción para hacer, y lo que mostrar.

---

# SCRIPT DE DEMO — 12 minutos

> Copiar el bloque siguiente en `guias2/SCRIPT_DEMO.md` y imprimirlo.

```markdown
# Demo de defensa Yary — 12 min

## Pre-condiciones (debe estar listo ANTES)
- Backend, Redis, Postgres corriendo.
- Datos demo cargados (ver G2C3/F2).
- Web Angular en localhost:4200.
- 2 dispositivos Flutter logueados (cliente + técnico).
- 3 navegadores con sesión de tres talleres distintos.

---

## Escenario 1 — Multi-tenant + signup (1 min)

> **Decir**: "Yary es SaaS multi-tenant. Cada taller es un tenant aislado. Veamos cómo se onboardea uno nuevo."

1. Ir a `/signup` en navegador limpio (modo incógnito).
2. Llenar form rápido (datos preparados en post-it).
3. Click "Crear cuenta".
4. **Mostrar**: redirección a dashboard del nuevo tenant.

---

## Escenario 2 — Servicios diferenciados (1 min)

> "Cada taller declara qué tipo de problemas atiende. Esto controla quién recibe cada emergencia."

1. En el dashboard del taller nuevo: ir a "Servicios".
2. Marcar 2 categorías (ej: llantas + grúa).
3. Guardar.

---

## Escenario 3 — Reporte de emergencia con IA (2 min)

> "El cliente reporta. La IA clasifica en español, dominio-específico."

1. En Flutter cliente: "Reportar emergencia".
2. Escribir: **"Se me pinchó la llanta delantera, estoy parado en la avenida"**
3. Submit.
4. **Mostrar**: la app dice "categoría: llantas, prioridad: media".

---

## Escenario 4 — Broadcast a 3 talleres + first-accept-wins (2 min) — **CLAVE**

> "Aquí está la magia del tiempo real."

1. **Acomodar pantalla**: 3 navegadores con los talleres compatibles en grid.
2. Cliente Flutter submite la emergencia.
3. **Mostrar**: las 3 pantallas se actualizan al mismo tiempo (<2s).
4. Click rápido en uno → otros 2 dicen "tomada".

---

## Escenario 5 — Cotización comparativa (2 min)

> "Para servicios complejos, el cliente compara antes de elegir."

1. Cliente reporta incidente de chapería ("me chocaron por atrás").
2. App muestra "Pedir cotizaciones" → confirmar.
3. **Cambiar a los 2-3 talleres de chapería**: cada uno llena su oferta diferente.
4. Volver al cliente: comparativa lado a lado.
5. Aceptar la mejor → asignación creada.

---

## Escenario 6 — Tracking GPS en vivo (2 min) — **CLAVE**

> "El cliente sigue al técnico como en Uber."

1. Técnico en Flutter: "Iniciar viaje".
2. Mover el dispositivo (o emular GPS con DevTools).
3. **Mostrar**: en la pantalla del cliente, el marker se mueve cada 12s.
4. Mover técnico hacia el punto del incidente.
5. Al entrar al radio de 100m → diálogo "Técnico llegó".

---

## Escenario 7 — Cancelación con compensación (1 min)

> "El seguro del cliente llegó primero. Cancela, pero el taller no se va con las manos vacías."

1. Cliente: botón rojo "Cancelar".
2. Motivo: "Llegó mi seguro".
3. **Mostrar**: alert "Compensación al taller: $15".
4. En el panel del taller: aparece la asignación cancelada con "compensación pendiente $15".

---

## Escenario 8 — KPIs (1 min)

> "El gerente del taller mide su operación."

1. En cualquier taller: menú "Indicadores".
2. **Mostrar**: dashboard con 4 KPIs y gráfico de incidentes por categoría.

---

## Escenario 9 — Modo offline (1 min) — **CLAVE**

> "Sin internet, la app sigue funcionando."

1. Activar modo avión en el celular.
2. Flutter cliente: reportar incidente nuevo.
3. **Mostrar**: badge "pendiente local" en la lista.
4. Desactivar modo avión.
5. **Mostrar**: badge desaparece, queda como incidente normal.

---

## Escenario 10 — Aislamiento multi-tenant (1 min) — **CLAVE PARA PREGUNTA TÉCNICA**

> "Demostremos que un tenant no ve datos de otro."

1. Login como taller A → ver sus incidentes.
2. Login como taller B en otro navegador → ver SUS incidentes (distintos).
3. Si quieren ir más fuerte: usar curl con token de A para intentar `GET /talleres/{id_de_B}` → 403 o 404.
4. Mostrar el test `test_filtro_aisla_incidentes_entre_tenants` corriendo en verde.

---

## Plan B si algo falla

| Si falla… | Hacer esto |
|---|---|
| El WebSocket no conecta en vivo | Cambiar a video pregrabado del escenario 4 y 6 |
| OSRM no responde | Decir "estamos usando fallback Haversine, ETA es aproximada" |
| Gemini sin cuota | Hacer escenario 3 con texto que matchee heurística (mencionar "llanta") |
| Postgres se queda colgado | `docker compose restart postgres` (tener el comando a mano) |
| Pasa algo raro impredecible | "Lo dejamos como pregunta, sigamos al siguiente escenario" |

---

## Reglas de oro durante la demo

- **NUNCA improvisar nuevos comandos** durante el demo. Solo lo del script.
- Si pierdes el hilo: "permítame mostrar lo siguiente" + escenario siguiente.
- Si una pregunta interrumpe: terminar el escenario actual y luego responder.
- Mantener una pestaña con `/docs` (Swagger) abierta para mostrar API si lo piden.
```

---

## Distribución de tiempo (resumen)

```
Escenario 1  (multi-tenant)        1 min  ░
Escenario 2  (servicios)           1 min  ░
Escenario 3  (IA)                  2 min  ░░
Escenario 4  (broadcast) **CLAVE** 2 min  ░░
Escenario 5  (cotizacion)          2 min  ░░
Escenario 6  (tracking) **CLAVE**  2 min  ░░
Escenario 7  (cancelacion)         1 min  ░
Escenario 8  (KPIs)                1 min  ░  ← sacrificable si vamos largos
Escenario 9  (offline) **CLAVE**   1 min  ░
Escenario 10 (aislamiento) **CLAVE** 1 min ░
────────────────────────────────────────
TOTAL                              14 min
```

Si pasan de 15 min: omitir escenario 8 (KPIs es lo más fácil de sacrificar, lo cubren videos de respaldo).

---

## Checklist de cierre D4
- [ ] `guias2/SCRIPT_DEMO.md` creado con el bloque arriba.
- [ ] Impreso o disponible en pantalla secundaria.
- [ ] Distribución de tiempo entendida por el presentador.
- [ ] Plan B memorizado.
- [ ] Ensayo completo realizado (ver D5).

## Notas
- **Datos en español, sin "lorem ipsum"**: el evaluador nota inmediatamente si parece improvisado.
- **Demo en vivo > video**: pero si hay riesgo de WiFi inestable en la sala, los videos de respaldo (escenarios 4, 6, 9) ya están grabados — proyectar si falla.
- **Acomodar pantallas antes**: si la demo requiere 3 navegadores en grid, configurar el snap layout antes de la defensa. Perder 30s acomodando pantallas en vivo da mala impresión.
