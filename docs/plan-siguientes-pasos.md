# Plan de siguientes pasos

**Fecha:** 2026-09-23 · prioridades decididas por el dueño · esfuerzos tomados
de `docs/auditoria.md` (rama `audit/2026-09-22`, commit `c6f660b`)

El despliegue terminó (11 de 11, ver [estado-despliegue.md](estado-despliegue.md)).
Esto es lo que viene, en orden.

> **Los esfuerzos no se inventan.** Cada ítem lleva la subfase de la auditoría,
> su estimación y su verificación de cierre. Lo que la auditoría no estimó
> —porque no estaba en su plan— va marcado **sin estimar**, y no se rellena con
> un número plausible.

## Resumen

| | Bloque | Esfuerzo | Qué desbloquea |
|---|---|---:|---|
| **P0** | Ronda de calificación 1 a 1 | *actividad, no subfase* | H1 y H2: sin calificaciones no hay experimento |
| **P1** | Seguimiento de la ronda | *actividad* + script hecho | Saber a quién falta antes del corte |
| **P2** | F0b · prerrequisitos de la decisión | **5 d** | La compuerta go/no-go |
| **P3** | Capacidades del PRD no construidas | **6 d** + Sintetizador *sin estimar* | Cumplir lo que el PRD pide |
| **P4** | Antes de correr un ciclo nuevo | **7 d** (+ ~USD 3 de tokens) | Un ciclo 4, si se decide |
| **P5** | Interfaz | **3,1 d** | Legibilidad y uso |
| **P6** | Endurecimiento | **10,7 d** | Mantenimiento y deuda |

**Total con estimación: 31,8 d**, más el Sintetizador y 0,25 d sueltos (ver
«Lo que no quedó en ningún bloque»). Es esfuerzo de un desarrollador.

---

## P0 · Ronda de calificación 1 a 1

**Plazo: martes 2026-09-29.** El dueño se reúne con cada una de las 7 personas
calificadoras y **califican en esa sesión**.

Cómo se hace, y por qué así:

- **Cada gerente teclea su propio correo y emite sus propias calificaciones.**
  No las dicta ni las delega: `calificacion.id_usuario` registra quién tecleó, y
  si el dueño calificara por otro, ese registro diría algo falso.
- **El dueño explica la herramienta, no los insights.** La pregunta que H1 mide
  es si el insight le parece relevante a la gerencia, no si se entiende la
  pantalla.
- **No se comenta la calificación de nadie ante otro** (CA-M7.2): las
  calificaciones son independientes, y basta con mencionar «fulano le puso 5»
  para que dejen de serlo.
- **La versión móvil (H-044) deja de ser prerrequisito.** Con sesión acompañada
  y de escritorio, no bloquea; baja a P5.

**Congelamiento hasta el corte del martes.** No se republica el informe ni se
cambia nada que altere lo que ven los calificadores: ni el payload, ni los
textos, ni la selección pedida. **Solo se corrige un error que impida
calificar**, y si ocurre **queda registrado** en
[ronda-calificacion.md](ronda-calificacion.md), con qué se cambió y a quién
afectó.

> **Nota metodológica, y hay que llevarla hasta el informe.** Esta ronda se
> califica **acompañada**. **H2 del PRD mide calificación sostenida y sin
> acompañamiento**, así que la tasa de respuesta que salga de aquí **se reporta
> como lo que es —tasa en condición acompañada— y no se compara directamente
> con el criterio de éxito.** Una tasa alta aquí no demuestra H2; una baja sí
> sería mala señal, porque se obtuvo en la condición más favorable.

## P1 · Seguimiento de la ronda

- **`scripts/avance_calificacion.py`** — solo lectura, con su test. Muestra, por
  persona y por gerencia, cuántos de los **15 insights pedidos** lleva
  calificados cada quien. Los dos ejes están separados a propósito: la persona
  es quien tecleó, la gerencia es a quien se atribuye, y solo coinciden mientras
  haya una persona por gerencia.
- **[ronda-calificacion.md](ronda-calificacion.md)** — registro de sesiones:
  fecha, persona, gerencia y si fue acompañada.
- **Corte el martes 29 al final del día**: exportación de `calificacion` a CSV
  **fuera del repositorio**. Esa foto es la que se analiza. **La app no cierra
  el ciclo sola**: nada en el código impide calificar después del martes, así
  que el corte lo define la exportación, no el sistema.

## P2 · F0b — prerrequisitos de la decisión go/no-go · **5 d**

Puede avanzar **en paralelo a la ronda**: toca `informe_resultados.md` y los
scripts que lo generan, no lo que ven los calificadores.

| Subfase | Resuelve | Esfuerzo | Cierre |
|---|---|---:|---|
| **F0b.1** | H-034 (causa raíz), H-027, H-030; arrastra H-031, H-032, H-033 | **3 d** | `python scripts/informe_resultados.py` produce el archivo commiteado sin diferencias |
| **F0b.2** | H-035 (+ H-006 en lo que toca a H5) | **1 d** | Dos ejecuciones sobre el mismo corte dan las mismas cifras |
| **F0b.3** | H-028, **H-010 desglosado por regla** | **0,5 d** | `SELECT` da 4/326 para la corrida 10 y el documento lo publica |
| **F0b.4** | H-030 | **0,5 d** | La cifra tiene script o no aparece |

**H-010 se reporta desglosado por regla**, no como un porcentaje único: R1–R7
son fidelidad de cita y **R8 es cifra sin fuente**, que son fallos distintos del
modelo. Está registrado en [decisiones-remediacion.md](decisiones-remediacion.md).

**Depende de P-5**, la tarifa real de `gpt-5.4-mini`: sin ella, F0b.2 publica el
costo con un factor declarado en vez de una cifra cerrada.

## P3 · Capacidades del PRD no construidas · **6 d** + *sin estimar*

Salen de la matriz de conformidad de la auditoría: CA en **No cumple**, más los
**Parcial** cuyo hallazgo es una Brecha que la remediación no cerró. **Nada de
esto se hace antes del corte del martes.**

| Capacidad | Criterios | Subfase | Esfuerzo | Cierre |
|---|---|---|---:|---|
| **Sintetizador**: justificación y sugerencias de acción por municipio | CA-M6.1 (Parcial) | *ninguna* | **sin estimar** | — |
| **Panel de métricas** para administrador | CA-M9.13, CA-M9.14, CA-M9.15, **CA-M7.5** | F4.2 (H-014 métricas + H-010 en interfaz) | **3 d** | Cuatro métricas y CSV visibles solo con `rol=administrador` |
| **Histórico** de informes publicados | CA-M9.7, y CA-M9.3 en su tercera vista | F4.3 (H-014 histórico) | **1 d** | Ruta 200 con los publicados |
| **Trazabilidad en pantalla** | CA-M9.5 | F4.4 (H-017) | **2 d** | Desde cualquier cita se llega a la señal y su trayecto |

**El Sintetizador es el hueco grande y el único sin estimación.** La auditoría no
lo planificó porque no es un defecto: es trabajo pendiente documentado. Hoy
`justificacion` y `sugerencias` viajan vacías en el payload y la pantalla pinta
el hueco. Dos cosas que hay que decidir antes de estimarlo: **el tono de voz no
existe** (pendiente `MARCA-tono`, sin criterio de aceptación para la prosa) y su
costo **no está en la cifra de H5**, que solo cuenta Clasificador y
Correlacionador.

**La infografía (CA-M6.2) no está aquí a propósito:** se **retiró formalmente**
del MVP en F0.8. No es una capacidad pendiente.

## P4 · Antes de correr un ciclo nuevo · **7 d** + ~USD 3

**Supuesto: el experimento se evalúa con el ciclo 3.** Si el dueño decide un
**ciclo 4**, este bloque sube de prioridad y pasa a ser prerrequisito.

| Subfase | Resuelve | Esfuerzo | Cierre |
|---|---|---:|---|
| **F1.1** | H-037 — una corrida interrumpida queda «completa» y es publicable | **3 d** | Corrida interrumpida → `parcial`, no publicable, reanudable sin llamadas repetidas |
| **F1.2** | H-038 — `correr_ciclo.py --seco` escribe y gasta tokens | **0,5 d** | `--seco` deja `corrida_agentes` sin filas nuevas |
| **F1.3** | H-039 — sin bloqueo; las corridas 9 y 10 se solaparon | **0,5 d** | Un segundo `correr_ciclo.py` concurrente se niega |
| **F2.1** | H-006 — linaje de ejecución no atribuible | **1,5 d** | Trazas con los seis campos; costo por corrida y agente |
| **F2.2** | H-021 — `contexto_no_verificado` nunca se escribe | **0,5 d** | Consolidados nuevos con la marca; test |
| **F2.3** | H-022, H-023 (resto), H-036 — **validar v2 con linaje persistido** | **1 d + ~USD 3** | `prompt_version` con fila v2; `PISO_RUIDO` derivado de corridas registradas |

**F2.3 es el que desbloquea v2.** Hasta que pase, `VERSION_PROMPT` está en **v1**
—lo publicado— y `tests/test_version_prompt.py` impide cambiarlo sin actualizar
la decisión.

## P5 · Interfaz · **3,1 d**

| Subfase | Resuelve | Esfuerzo | Cierre |
|---|---|---:|---|
| **F4.5** | H-018 — ficha sin insights acumulados ni promedio (CA-M9.11) | **1 d** | Ficha completa |
| **F5.1** | H-044 — 0 `@media`; dos columnas fijas en móvil (CA-M9.18) | **1,5 d** | Render a 375 px conforme al DS §6 |
| **F5.2** | H-046 — sin zona de sugerencias, vacío sin fecha, sin `loading` | **0,5 d** | Archivos presentes; vacío con fecha |
| **F5.4** | H-047 — el Design System se contradice sobre un token | **0,1 d** | DS sin contradicción |

**Dos avisos sobre este bloque.** **H-017 aparece también en la lista de P5 del
dueño, pero es CA-M9.5**, la trazabilidad en pantalla, así que **se cuenta una
sola vez, en P3**; contarlo aquí sumaría 2 d dos veces. Y **de H-014 no queda
nada para P5**: sus dos mitades, métricas e histórico, están en P3.

## P6 · Endurecimiento · **10,7 d**

| Subfase | Resuelve | Esfuerzo |
|---|---|---:|
| **F6.1** | H-050 — sin tests para `snapshot.py`, `agregacion.py`, `procesar_municipio` ni `web/` | **3 d** |
| **F6.2** | H-049 — sin lockfile; saltos de major en dependencias | **1 d** |
| **F6.3** | H-048 — PII de SECOP sin política de tratamiento | **0,5 d** |
| **F6.4** | H-051, H-024, H-025, H-026, H-041 — código muerto y scripts desalineados | **1,5 d** |
| **F6.5** | H-002 — `EstadoCiclo` no existe como contrato | **0,5 d** |
| **F6.6** | H-008 — una calificación corregida conserva `creado_en` | **0,1 d** |
| **F4.7** | H-011 — el diccionario por subcadena decide el 54 % del score | **2 d** |
| **F2.4** | H-040 (resto) — documentar que los informes 2–5 no llevan commit | **0,1 d** |
| **F2.5** | H-003, H-042 — contadores de `ciclo` en 0; traza de ingesta solo en stdout | **0,5 d** |
| **F2.6** | H-004 — `seguimiento` sin `responsable` | **0,5 d** |
| **F2.7** | H-001 — el hash ancla el dataset, no cada señal | **0,5 d** |
| **F2.8** | H-043 — nomenclátor y contexto no regenerables desde el repo | **0,5 d** |
| — | H-007 — URL verificada solo por sintaxis | **0** (sin acción en el MVP) |

**F4.7 (H-011) merece una nota**: es el único de este bloque que **cambia
cifras**. Recalibrar el diccionario mueve F1, F2 y F3, así que hay que medir
antes y después y versionar `VERSION_ALGORITMO`, y **está congelado por decisión
de Analítica** (pendiente A2).

## Lo que no quedó en ningún bloque

| H-ID | Por qué |
|---|---|
| **H-012** | **Riesgo aceptado (R-A2).** El dueño no adopta el token, así que queda **abierto y sin subfase**. F0.3 redujo el residual —cookie firmada, solo correos registrados, rastro— pero la identidad sigue siendo declarativa, y hay que decirlo al publicar H1 y H2 |
| **H-029** | **F3.1, 0,25 d.** La tasa de rechazo mide fidelidad de cita contra lo ingerido, no veracidad, y el documento no lo declara. Depende de F0b.1 y se cierra con él, así que en la práctica viaja dentro de P2 |

## Cerrado por la remediación (no vuelve a aparecer arriba)

**H-005, H-009, H-013, H-015, H-016, H-019, H-020, H-045.** Además, **H-040** en
lo esencial —queda 0,1 d de documentación en F2.4— y **H-023** en su parte
documental, con la comparación pendiente en F2.3.

## Decisiones pendientes del dueño

| | Decisión | Bloquea |
|---|---|---|
| **Plan de Vercel** | Hobby frente a Pro | La observabilidad —los errores de runtime dan 403 en Hobby— y «Only Preview Deployments» |
| **P-5** | Tarifa real de `gpt-5.4-mini` | Cerrar H5 con una cifra en vez de un factor declarado (F0b.2) |
| **Ciclo 4** | ¿Se corre uno nuevo? | Si sí, **P4 sube a prerrequisito** |
