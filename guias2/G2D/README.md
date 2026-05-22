# G2D — Guías de Documentación

> Documentación transversal a todos los ciclos. Separada del código y la operativa para que cada audiencia (académica, evaluador, usuario final) tenga su entregable claro.

## Cuándo abrir esta carpeta
- **D1 (Marco teórico)**: se empieza a redactar durante el Ciclo 3, pero el contenido viene de lo construido en C1+C2. Idealmente arrancar a tomar notas desde el final del Ciclo 1.
- **D2 (UML)**: actualizar cada vez que se mete una migración nueva. Cierre formal al final del Ciclo 2.
- **D3 (Manual usuario)**: redactar al cierre del Ciclo 2, cuando todas las features estén funcionando.
- **D4 (Guion demo)**: preparar al inicio del Ciclo 3.
- **D5 (FAQ + ensayo)**: día previo a la defensa.

---

## Archivos

| # | Archivo | Audiencia | Esfuerzo |
|---|---|---|---|
| D1 | [D1_marco_teorico.md](./D1_marco_teorico.md) | Profesor / evaluador académico | 0.5 día |
| D2 | [D2_diagramas_uml.md](./D2_diagramas_uml.md) | Profesor / evaluador académico | 0.5 día |
| D3 | [D3_manual_usuario.md](./D3_manual_usuario.md) | Usuario final / evaluador | 0.25 día |
| D4 | [D4_guion_demo.md](./D4_guion_demo.md) | Presentador (interno) | 0.25 día |
| D5 | [D5_faq_y_ensayo.md](./D5_faq_y_ensayo.md) | Presentador (interno) | 0.5 día |

Total: **~2 días-persona** de trabajo de documentación pura, distribuidos en C2/C3.

---

## Convención
- Las guías de **documentación** (esta carpeta) producen **PDFs / impresos / diapositivas / videos**.
- Las guías de **implementación** ([G2C1](../G2C1/), [G2C2](../G2C2/), [G2C3/F1](../G2C3/F1_hardening_backend.md)) producen **código / migraciones / tests**.
- Las guías de **operación** ([G2C3/F2](../G2C3/F2_release_y_demo_ops.md)) producen **scripts ejecutables / backups / configuración**.

No mezclar. Si una guía de doc tiene que decir "ejecuta este comando antes", debe linkear al doc operacional correspondiente, no copiar.

---

## Entregables finales esperados

Al cierre del proyecto, esta carpeta debería producir:

| Archivo final | Origen | Para qué |
|---|---|---|
| `guias2/MARCO_TEORICO.pdf` | D1 | Entrega académica oficial |
| `guias2/uml/*.png` (6 imágenes) | D2 | Insertar en marco teórico + presentación |
| `guias2/MANUAL_USUARIO.pdf` | D3 | Entrega académica + demo |
| `guias2/SCRIPT_DEMO.md` (impreso) | D4 | Mano del presentador durante defensa |
| Memorización FAQ + roles | D5 | Defensa fluida |

---

## Reglas de oro

1. **El marco teórico se redacta DESPUÉS de implementar**: las decisiones técnicas reales del código son la base para las secciones teóricas. Si lo redactas antes, te toca reescribir.
2. **Los diagramas UML se mantienen al día con cada migración**: si Ciclo 2 agrega una tabla, actualizar el `.puml` ese mismo día.
3. **El manual de usuario NO menciona bugs ni cosas pendientes**: solo lo que funciona bien. Es marketing del producto, no changelog.
4. **El guion de demo NUNCA improvisa**: cada palabra que dirás, cada click, cronometrado.
5. **La FAQ se ensaya en voz alta**: leer las respuestas no sirve, hay que poder decirlas con naturalidad cuando alguien te interrumpe.

---

## Plan rápido

Si llegan al Ciclo 3 con el tiempo apretado, **prioridad de documentación**:

1. **OBLIGATORIO**: D1 marco teórico (sin esto puede no aprobarse) + D5 FAQ (sin esto la defensa se cae).
2. **Muy recomendado**: D2 UML (un evaluador serio los pide).
3. **Bonus**: D3 manual, D4 guion impreso.

Lo bonito de tener todo separado por archivo: pueden trabajar 3 personas en paralelo en distintos `D*.md`.
