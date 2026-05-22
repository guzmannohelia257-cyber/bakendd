# D3 — Manual de usuario

> **Documentación dirigida al usuario final**, no al developer.
> **Esfuerzo:** 0.25 día.

## Objetivo
Producir `MANUAL_USUARIO.pdf` (≤8 páginas) para acompañar la entrega académica.
Sirve para que cualquier persona (incluido el evaluador) entienda cómo usar el sistema sin leer código.

---

## Cómo usar esta guía
Crear `guias2/MANUAL_USUARIO.md` con el contenido de la sección siguiente.
Renderizar a PDF al final.

```bash
# Opción 1: pandoc
pandoc guias2/MANUAL_USUARIO.md -o guias2/MANUAL_USUARIO.pdf --pdf-engine=xelatex

# Opción 2: VSCode con "Markdown PDF" extension
# Ctrl+Shift+P -> Markdown PDF: Export (pdf)
```

---

# Contenido del manual

> Copiar todo lo que está abajo en `guias2/MANUAL_USUARIO.md` y exportar.

```markdown
# Yary — Manual de Usuario

## ¿Qué es Yary?
Yary es una plataforma SaaS que conecta a conductores con talleres
mecánicos cercanos en situaciones de emergencia vehicular. Cada taller
opera como un tenant independiente con su propio panel.

---

## Tres tipos de usuario

| Rol | Cómo entra | Para qué sirve |
|---|---|---|
| **Cliente** (conductor) | App móvil Flutter | Reporta incidentes, recibe cotizaciones, ve el técnico en mapa |
| **Taller** (panel de gerencia) | Web Angular | Recibe emergencias, responde cotizaciones, gestiona técnicos |
| **Técnico** | App móvil Flutter | Acepta asignaciones, envía su ubicación, completa servicios |

---

## Para CLIENTES (Flutter)

### Registrarse
1. Abrir la app.
2. Toque "Crear cuenta".
3. Ingresar nombre, email, contraseña, teléfono.
4. Verificar email (link enviado).
5. Agregar al menos un vehículo: placa, marca, modelo, año.

### Reportar una emergencia
1. Pantalla principal → **"Reportar emergencia"**.
2. Permitir acceso a GPS y micrófono.
3. Describir el problema:
   - Por **texto**: escribir qué pasó (ej: "se me pinchó la llanta delantera derecha")
   - Por **audio**: presionar el botón rojo y grabar
   - Por **foto**: tomar foto del problema
4. La IA clasifica automáticamente el problema en una de 7 categorías.
5. Confirmar y enviar.
6. La app muestra "Buscando taller cercano…".
7. Cuando un taller acepta, recibes notificación con sus datos.

### Cotizar (servicios que requieren trabajo de taller)
Para categorías como **chapería**, **mecánica general**, **eléctrico**, **electrónico**,
después de reportar el incidente, la app ofrece **Pedir cotizaciones**.

1. Confirmar la búsqueda (radio 20 km por defecto).
2. Esperar 1-2 minutos a que los talleres respondan.
3. Comparar las cotizaciones recibidas:
   - Precio total (servicio + repuestos)
   - Días de garantía
   - Calificación promedio del taller
4. Elegir una y tocar **"Aceptar"**.

### Seguir al técnico en vivo
Una vez asignado un taller:
1. Tocar "Ver en mapa".
2. Verás el marker del técnico moviéndose en tiempo real.
3. ETA actualizado cada 12 segundos.
4. Cuando el técnico esté a menos de 100 m, recibes alerta de llegada.

### Cancelar
1. Si tu seguro respondió y prefieres su servicio, toca **"Cancelar"**.
2. Indica el motivo.
3. La app te muestra la compensación al taller:
   - $0 si aún no aceptó
   - 50% de tarifa de traslado si aceptó pero no salió
   - 100% si ya estaba en camino o llegó

### Modo sin internet
- Puedes ver tu historial de incidentes sin conexión.
- Si reportas un incidente sin internet, la app lo guarda como **"pendiente local"**.
- Al recuperar conexión, se sincroniza automáticamente.

---

## Para TALLERES (Web Angular)

### Registrar mi taller (signup)
1. Ir a `https://yary.app/signup` (o tu dominio local).
2. Llenar:
   - Slug del tenant (subdominio identificador, ej: `mecanica-lopez`)
   - Nombre del tenant y del taller
   - Email, contraseña, teléfono
   - Dirección y ubicación GPS en mapa
3. Elegir plan (free / pro / enterprise).
4. Al confirmar, te logueas automáticamente.

### Declarar mis servicios
Sin esto, no apareces en búsquedas de clientes.

1. Menú → **"Servicios"**.
2. Marca las categorías que atiendes (de las 7 oficiales).
3. Para cada una, indica:
   - Si ofreces servicio móvil (vas al cliente)
   - Tarifa base (orientativa)
4. Guardar.

### Recibir emergencias en vivo
En el dashboard principal, sección **"Emergencias entrantes"**:
- Aparecen en tiempo real las emergencias compatibles con tus servicios.
- Cada tarjeta muestra: descripción del cliente, ubicación, prioridad.
- Botón **"ACEPTAR"** — el primer taller que acepta gana.
- Si otro lo toma, la tarjeta queda gris ("Ya fue tomado").

### Responder cotizaciones
Menú → **"Cotizaciones pendientes"**:
- Cada solicitud espera tu respuesta antes de la hora de validez.
- Llenar: monto del servicio, monto de repuestos, garantía en días, nota.
- Enviar. El cliente verá tu oferta y la comparará con otras 1-2.

### Gestionar técnicos
Menú → **"Técnicos"**:
- Crear cuenta para cada técnico (rol=3).
- Asignarles permisos.
- Ver su ubicación actual cuando están en viaje.

### Dashboard de KPIs
Menú → **"Indicadores"**:
- Tiempo promedio de aceptación de mis emergencias
- Tiempo promedio de llegada
- Mis incidentes por tipo de servicio
- Ranking comparativo con otros talleres de mi tenant (si tengo varios)

### Configurar tarifa de traslado
La compensación que recibes cuando un cliente cancela depende de esto.

1. Menú → **"Mi taller"** → **"Tarifa de traslado"**.
2. Ingresar monto en USD.
3. Guardar.

---

## Para TÉCNICOS (Flutter)

### Recibir asignación
Cuando tu taller te asigna un trabajo:
1. Recibes notificación push.
2. Abrir la app → ver detalles del incidente.
3. Tocar **"Iniciar viaje"**.

### Enviar ubicación en vivo
- La app envía tu GPS automáticamente cada 12 segundos.
- Mantén la app abierta durante el viaje.
- El cliente te ve moverse en su mapa.

### Llegar al sitio
- Cuando estés a menos de 100 m, la app cambia tu estado a **"Llegado"** automáticamente.
- El cliente recibe alerta.

### Completar el servicio
1. Tocar **"Completar"**.
2. Subir evidencias (fotos del trabajo).
3. Confirmar costo final.

---

## Preguntas frecuentes (usuario)

**¿Necesito siempre internet?**
No para ver tu información. Sí para reportar emergencias en tiempo real
(aunque puedes encolarlas si estás offline).

**¿Cuánto cuesta?**
Cliente: gratis. Taller: según plan (free $0, pro $49/mes, enterprise $199/mes).

**¿Qué pasa si mi taller cancela?**
El cliente puede elegir otro y tú no recibes compensación.

**¿La IA siempre clasifica bien?**
Tiene confianza ≥0.5 en >85% de casos. Si está por debajo, marca
"requiere revisión manual" y se envía a todos los talleres compatibles
para que ellos decidan.
```

---

## Checklist de cierre D3
- [ ] `guias2/MANUAL_USUARIO.md` creado con el contenido completo.
- [ ] Renderizado a PDF (`guias2/MANUAL_USUARIO.pdf`).
- [ ] PDF revisado: capítulos completos, sin errores tipográficos.
- [ ] Capturas de pantalla agregadas (opcional pero recomendado para defensa).

## Notas
- **Capturas**: agregar screenshots de las pantallas más importantes mejora mucho. Insertar como `![texto alt](ruta.png)` en el markdown.
- **Idioma**: español neutro. Sin modismos extremos. El evaluador puede no ser boliviano.
- **No mostrar errores**: si la app tiene un bug conocido, NO documentarlo aquí. Es manual de usuario, no changelog.
