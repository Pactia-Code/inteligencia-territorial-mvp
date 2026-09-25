# Plan de siguientes pasos

**Fecha:** 2026-09-23, con P0.5 y la Fase 0 añadidas el **2026-09-24** ·
prioridades decididas por el dueño · esfuerzos tomados de `docs/auditoria.md`
(rama `audit/2026-09-22`, commit `c6f660b`), salvo los de P0.5, que son
estimación propia y van marcados como tal

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
| ~~**P0.5**~~ | ~~Correcciones visibles durante la ronda~~ | **hecho** | Desplegado el 2026-09-24 (PR #2 y #3) |
| **P1** | Seguimiento de la ronda | *actividad* + script hecho | Saber a quién falta antes del corte |
| **P2** | F0b · prerrequisitos de la decisión | **5 d** | La compuerta go/no-go |
| **P3** | Capacidades del PRD no construidas | **6 d** + Sintetizador *sin estimar* | Cumplir lo que el PRD pide |
| **P4** | Antes de correr un ciclo nuevo | **7 d** (+ ~USD 3 de tokens) | Un ciclo 4, si se decide |
| **P5** | Interfaz | **3,1 d** | Legibilidad y uso |
| **P6** | Endurecimiento | **10,7 d** | Mantenimiento y deuda |

**Total pendiente con estimación: 31,8 d**, más el Sintetizador y 0,25 d
sueltos (ver «Lo que no quedó en ningún bloque»). Es esfuerzo de un
desarrollador.

Eran 33,05 d; **P0.5 se cerró el 2026-09-24 y sus 1,25 d salen del total.** Lo
que queda son P2 a P6, que es lo mismo que había antes de que apareciera P0.5.

Todo esto está **antes** del go/no-go o lo acompaña. Lo que viene **después**,
si la compuerta sale GO, es la [Fase 0 del PRD](#y-después-la-fase-0-del-prd).

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

> **Nota metodológica, y hay que llevarla hasta el informe.** Esta ronda es de
> **condición mixta**: se diseñó como sesiones acompañadas, pero parte de las
> calificaciones se emiten sin acompañamiento. **Cada sesión se etiqueta
> acompañada o no** en [ronda-calificacion.md](ronda-calificacion.md), y **H2 se
> reporta separado por condición**, nunca como una tasa agregada — H2 del PRD
> mide calificación sostenida **sin** acompañamiento, así que mezclarlas da un
> número que no responde a la hipótesis.
>
> **El tiempo entre calificaciones de una misma persona se conserva como dato
> del análisis, y ninguna calificación se descarta por rápida.** Que alguien
> responda en segundos es una observación sobre cómo se usa la herramienta, no
> un motivo para tirar el dato: descartarlo sería decidir de antemano qué
> cuenta como una calificación legítima.

## ~~P0.5~~ · Correcciones visibles durante la ronda · **HECHO y desplegado**

**Cerrado el 2026-09-24.** Las tres partes están fusionadas y en producción, y
**ninguna cambió el informe ni cómo se califica**: ni el payload, ni los
insights pedidos, ni las reglas de alcance.

| Parte | Cómo llegó | Verificado |
|---|---|---|
| `/priorizados` y «cambiar estado» | **PR #2** (`fix/p0-5-correcciones`), merge `100f7b1` | Branch de Neon desechable + navegador del dueño |
| «Próximamente» en `/historico` y `/metricas` | **PR #2** | Mismo |
| Pantalla de entrada con correo y logo | **PR #3** (`feat/login-correo`), merge `45ec4d2` | Branch desechable, navegador local y **producción** el 2026-09-24 |

Producción sirve `45ec4d2`. El detalle de cada verificación está en
[estado-despliegue.md](estado-despliegue.md) y la bitácora en
[ronda-calificacion.md](ronda-calificacion.md).

> **Lo que se llevó 1,25 d de esfuerzo estimado ya no cuenta en el total.** Se
> conserva el desglose porque el diagnóstico sigue siendo útil: dice por qué
> `/priorizados` se caía y por qué tres comprobaciones en verde no lo vieron.

<details>
<summary>El diagnóstico y lo que se hizo, para consulta</summary>

| # | Qué | Esfuerzo estimado |
|---|---|---:|
| 1 | **`/priorizados` reventaba en el navegador** — y con ella el botón «cambiar estado» | **0,25 d** |
| 2 | **«Próximamente»** en `/historico` y en cualquier entrada de navegación sin construir | **0,25 d** |
| 3 | **Pantalla de entrada** con correo y logo de Pactia | **0,75 d** |

### 1. `/priorizados` y «cambiar estado»: un solo fallo, no dos · 0,25 d

**Causa única, y está en una línea de importación.**
`web/app/priorizados/CambiarEstado.tsx:13` es un componente de cliente
(`"use client"`) que importa `EXIGEN_NOTA` desde `@/lib/tablero`;
`web/lib/tablero.ts:15` importa `./db`, y `web/lib/db.ts:15-21` **lanza en el
cuerpo del módulo** si no hay `DATABASE_URL`. En el navegador nunca la hay
—Next solo expone las `NEXT_PUBLIC_*`—, así que el chunk revienta al
evaluarse, React sube el error y **`error.tsx` pinta «Algo falló al cargar esta
página»** encima de una página que el servidor había compuesto bien.

Comprobado sobre el propio bundle: el chunk de cliente
`.next/static/chunks/app/priorizados/page-*.js` contiene, en el nivel del
módulo, `let n = ...env.DATABASE_URL; if(!n) throw Error("Falta DATABASE_URL...")`
seguido del array de `EXIGEN_NOTA` — lo único que hacía falta importar. Por eso
la ruta pesa **43,8 kB** de JavaScript de cliente frente a los 2,52 kB de
`/ciclo/[id]`: el driver de Neon entero viaja al navegador.

**Y explica los dos síntomas a la vez.** La página no «falla al cargar»: falla
al hidratar, y el botón nunca llega a funcionar porque su componente está
muerto. No es fallo de las reglas de alcance de F0.4, ni de identidad, ni de
esquema — los tres se verificaron y están bien.

**No hay filtración de credenciales.** El bundle trae el *nombre* de la
variable y el driver, no el valor: `neon.tech`, `npg_` y la cadena de conexión
no aparecen en nada de lo servido al navegador, y el valor de `COOKIE_SECRET`
tampoco.

**Arreglo:** sacar `EXIGEN_NOTA` a un módulo sin dependencias de base —
`web/lib/estados.ts`— e importarlo desde `tablero.ts` y desde el componente.
**Y dejar la guarda**, que es lo que impide que vuelva: una comprobación tras
`next build` que falle si algún chunk de `static/` contiene `Falta DATABASE_URL`
o el driver. Sin ella, cualquier importación futura repite el fallo y **`tsc`
no lo ve**.

> **Por qué no se detectó antes.** `curl` sobre la ruta devuelve **200 con el
> HTML correcto**, en dev y en build de producción: el servidor renderiza bien y
> `curl` no ejecuta JavaScript. Solo falla en un navegador de verdad. Una
> comprobación que no ejecute el cliente **no puede ver este fallo**.

### 2. «Próximamente» en las rutas sin construir · 0,25 d

`web/app/Nav.tsx:16` enlaza a **`/historico`** y, para el administrador,
`Nav.tsx:22` enlaza a **`/metricas`**. **Ninguna de las dos existe**: bajo
`web/app/` solo hay `page.tsx`, `ciclo/[id]/` y `priorizados/`. Las dos dan 404
de Next, que durante la ronda se lee como que el sistema está roto.

Son **H-014** (histórico y métricas, P3) y no se construyen ahora. Lo que se
hace es una página «Próximamente» que diga qué irá ahí y que leer el informe no
depende de ello.

### 3. Pantalla de entrada con correo y logo · 0,75 d

Hoy **el informe se lee sin identificarse**. La pantalla de entrada pide el
correo antes de entrar, con el logo de Pactia sobre fondo claro.

**Mejora privacidad e imagen, no la atribución.** Quien conozca un correo
autorizado sigue pudiendo usarlo: **R-A2 y H-012 siguen abiertos** como riesgo
aceptado, y hay que decirlo igual al publicar H1 y H2. Ver
[decisiones-remediacion.md](decisiones-remediacion.md).

</details>

---

## P1 · Seguimiento de la ronda

- **`scripts/avance_calificacion.py`** — solo lectura, con su test. Muestra, por
  persona y por gerencia, cuántos de los **15 insights pedidos** lleva
  calificados cada quien. Los dos ejes están separados a propósito: la persona
  es quien tecleó, la gerencia es a quien se atribuye, y solo coinciden mientras
  haya una persona por gerencia.
- **[ronda-calificacion.md](ronda-calificacion.md)** — registro de sesiones:
  fecha, persona, gerencia y si fue acompañada.
- **Corte: martes 2026-09-29 a las 23:59, hora de Bogotá (UTC−5)**, que en la
  base es **2026-09-30 a las 04:59 UTC**. La exportación de `calificacion` a CSV
  va **fuera del repositorio**, **se ejecuta después de esa hora** y filtra por
  `creado_en <= '2026-09-30 04:59:59+00'`. Esa foto es la que se analiza.

  **El instante va en los dos husos a propósito.** La base guarda en UTC y
  Bogotá va cinco horas por detrás, así que un corte definido solo como «el
  martes» se aplicaría mal por cinco horas — y se llevaría por delante las
  calificaciones de última hora, que son las más probables. Ya pasó con la
  segunda sesión de Herrera, que figura con fecha 25 siendo del 24 en local.

  **La app no cierra el ciclo sola**: nada en el código impide calificar después
  del martes, así que el corte lo define la exportación, no el sistema. Lo que
  llegue después existirá en la base y no en la foto, y la diferencia hay que
  declararla al reportar. El detalle está en
  [ronda-calificacion.md](ronda-calificacion.md).

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

---

## Y después: la Fase 0 del PRD

**Esto no es parte del MVP y no compite con P0–P6.** Es lo que empieza **si la
compuerta de la semana 8 sale GO**, y se lista aquí para que el plan no termine
en el go/no-go como si no hubiera nada detrás.

El MVP es la *Fase -1*: comprueba que el mecanismo funciona, **no que cubre el
país**. La Fase 0 es la que convierte el experimento en algo operable:

| Qué cambia | Del MVP a la Fase 0 |
|---|---|
| **Fuentes** | Del **snapshot** a **conectores vivos**. Hoy los 18 municipios y las 20.030 señales salen de un archivo; en Fase 0 hay que ingerir de verdad, con reintentos y aislamiento de fallos por fuente |
| **Cobertura** | De **18 municipios** a la cobertura que se decida. El nomenclátor con los **1.102** ya está cargado y el contexto estructural también, así que el mecanismo está probado sobre el universo completo aunque el MVP no lo use |
| **Operación** | De **correr un script a mano** a un ciclo programado, con el checkpointing de CA-M8.4 y Langfuse cableados — hoy instalados y sin conectar |
| **Reproducibilidad** | Es **la deuda que la Fase 0 hereda**: A6 y A11 dicen que ni el Clasificador ni el Correlacionador repiten resultados. Lo que deba ser reproducible tiene que bajar a código determinista |
| **Costo** | De **USD 39/año** el piloto a **USD 2.160/año** los 1.103 municipios, **sin contar el Sintetizador**. Hay que rehacer la cuenta con la tasa diaria, no con los totales del snapshot |

**Nada de esto se estima aquí.** La Fase 0 tiene su propio alcance en el PRD y
su propia planificación; ponerle días desde el MVP sería inventarlos.
