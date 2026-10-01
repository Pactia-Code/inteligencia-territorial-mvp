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
| **P1** | Seguimiento de la ronda | *actividad* + script hecho | Saber a quién falta antes de cada corte |
| **P2** | F0b · prerrequisitos de la decisión | **1 d** pendiente (F0b.2); F0b.1, F0b.3 hechos y F0b.4 sin objeto | La compuerta go/no-go |
| **P3** | Capacidades del PRD no construidas | **6 d** + Sintetizador *sin estimar* | Cumplir lo que el PRD pide |
| **P4** | Antes de correr un ciclo nuevo | **7 d** (+ ~USD 3 de tokens) | Un ciclo 4, si se decide |
| **P5** | Interfaz | **3,1 d** | Legibilidad y uso |
| **P6** | Endurecimiento | **10,7 d** | Mantenimiento y deuda |

**Total pendiente con estimación: 27,8 d**, más el Sintetizador. Es esfuerzo
de un desarrollador. Los 0,25 d sueltos de H-029 se cerraron con F0b.1.

**El 2026-10-01 salen 4 d de P2**: F0b.1 (3 d) y F0b.3 (0,5 d) hechos en
`feat/f0b`, y F0b.4 (0,5 d) sin objeto al retirarse la cifra de H-030.

Eran 33,05 d; **P0.5 se cerró el 2026-09-24 y sus 1,25 d salen del total.** Lo
que queda son P2 a P6, que es lo mismo que había antes de que apareciera P0.5.

Todo esto está **antes** del go/no-go o lo acompaña. Lo que viene **después**,
si la compuerta sale GO, es la [Fase 0 del PRD](#y-después-la-fase-0-del-prd).

---

## La hoja de ruta, en orden

**Decidida por el dueño el 2026-09-25.** Los bloques P0–P6 dicen *qué* hay que
hacer; esto dice **en qué orden y qué espera a qué**.

| # | Qué | Cuándo | Bloque |
|---|---|---|---|
| **1** | **La ronda**: principal, **cerrada** el 29; extendida, hasta el 8 | Principal ✅ · extendida hasta el **2026-10-08** | P0 · P1 |
| **2** | **F0b, en paralelo**: construir el script que regenera `informe_resultados.md` | **Desde el 2026-10-01**, se ejecuta el 9 | P2 |
| **3** | **Análisis de la ronda**, de las dos por separado | El **9** | **nuevo**, ver abajo |
| **4** | **Presentación y decisión go/no-go** | El **13** | — |
| **5** | Si GO: **P4 y el Sintetizador**, antes del ciclo 4 | **Después del 13** | P4 · P3 |
| **6** | **Producto**: histórico, métricas, trazabilidad en pantalla, azul corporativo, móvil | Después | P3 · P5 |
| **7** | **Fase 0 del PRD** | Horizonte | — |

**P6 (endurecimiento) se intercala**, no espera turno: son 10,7 d de deuda que
se van metiendo entre lo demás según haya hueco.

### El calendario hasta la presentación

**Decidido por el dueño el 2026-10-01: la presentación pasa al 13.** Las
calificaciones posteriores al corte del 29 se aceptan como **ronda extendida**,
y las dos rondas se reportan por separado.

| Fecha | Qué |
|---|---|
| **mar 2026-09-29** | ✅ Corte de la **ronda principal**, 23:59 de Bogotá |
| **jue 2026-10-01** | ✅ **Exportación de la ronda principal**: 66 filas, en `C:\dev\respaldos\corte-ronda-2026-09-29\` · empieza **F0b.1** |
| **jue 2026-10-01** | ✅ **Tablero Javelin congelado** por decisión del dueño, una semana antes del cierre de la extendida |
| **jue 2026-10-01** | ✅ **F0b.1** terminado en `feat/f0b`: el informe se genera por script |
| **jue 2026-10-08** | Cierre de la **ronda extendida**, 23:59 de Bogotá (`2026-10-09 04:59:59+00`) |
| **vie 2026-10-09** | **Exportación de la extendida**, en `C:\dev\respaldos\corte-ronda-extendida-2026-10-08\` · **análisis** de las dos rondas · **se ejecuta el script** de F0b.1 |
| **vie 9 – sáb 10** | **Evaluación del piloto** contra el tablero y el PRD |
| **sáb 10 – dom 11** | **Preparación de la presentación** |
| **lun 2026-10-12** | *Festivo en Colombia* |
| **mar 2026-10-13** | **Presentación** |
| *después del 13* | **Sintetizador** y **ciclo 4**, si sale GO |

**F0b.1 tiene del 1 al 9: seis días hábiles para 3 d de estimación.** Holgura
hay, pero el script tiene que estar terminado **antes** del 9, porque ese día
se ejecuta: el margen es para probarlo, no para escribirlo.

**Y el 9 concentra tres cosas que dependen unas de otras**: sin la exportación
no hay análisis, y sin análisis el script no tiene qué poner en H1 y H2. Por eso
la exportación se hace a primera hora, y por eso el script tiene que poder
regenerarse en cuanto el análisis termine.

### El tablero Javelin, y por qué se congeló antes del cierre

El tablero salió de [`docs/prompts/javelin.md`](prompts/javelin.md) y está en
[`docs/javelin.md`](javelin.md). **Se congeló el 2026-10-01**, por decisión del
dueño: estaba previsto para el 6 y se adelantó, así que queda fijo **una semana
antes de que cierre la ronda extendida**, por la misma razón por la que F0b.1 se escribe antes
de ejecutarse: un criterio elegido después de ver los datos se elige —aunque sea
sin querer— para que el resultado cuadre.

Tres reglas que lo mantienen honesto, y están en la plantilla:

- **H1–H5 se copian del PRD con su criterio de éxito original.** Ningún umbral
  se toca.
- **Las hipótesis añadidas** para completar dos por dimensión van marcadas como
  **«experimento hacia adelante»** y **no se evalúan con los datos actuales**.
- **Cada hipótesis dice si ya tiene datos del MVP o no.**

La evaluación del 9 y el 10 sale de
[`docs/prompts/evaluacion-piloto.md`](prompts/evaluacion-piloto.md), y mide el
piloto contra ese tablero congelado y contra el PRD.

### 2. Por qué F0b se construye antes del corte y se ejecuta después

**Lo que tarda es escribir el script, no correrlo.** Son 3 d de F0b.1 y la
ronda dura 4 días: hacerlos en serie llegaría tarde a la decisión sin ninguna
necesidad.

Y hay una razón mejor que la de calendario: **el script tiene que estar escrito
antes de conocer los resultados de H1 y H2**. Si se escribe después, cada
consulta se elige —aunque sea sin querer— sabiendo qué número produce. Fijar el
método antes de ver el dato es lo que hace que la cifra signifique algo.

### 3. Análisis de la ronda · *nuevo, el 9*

Sobre las **dos exportaciones**, no sobre la base en vivo, y **cada ronda por
separado**: la principal (cerrada el 29) y la extendida (cerrada el 8).
**Alimenta F0b**: es lo que llena las secciones de H1 y H2 que hoy están vacías.

| Qué | Por qué |
|---|---|
| **H1: distribución de calificaciones por gerencia**, con y sin las adicionales | El núcleo son las 5 `prd`; `administrativa` y `analitica` van aparte (F0.1b) y pueden mover la media |
| **H2: tasa por la condición registrada** | Invitación personal y calificación autónoma. **No se compara directamente con el criterio**, que suponía notificación por correo |
| **Acuerdo entre gerencias** | Un insight que todas puntúan alto dice algo distinto de uno que divide. Sin esto, la media esconde el desacuerdo |
| **Tiempos por sesión** | Ya medidos: de 13,4 a 21,7 minutos para 15 insights. Es el dato de esfuerzo que H2 necesita |
| **Comentarios** | 13 hasta ahora, muy concentrados. Son lo único cualitativo que la ronda produce |

### 5. Si sale GO: qué va antes del ciclo 4

**P4 (fiabilidad del pipeline) y el Sintetizador, los dos antes de correr.** No
es orden caprichoso: el **ciclo 4 sería el primero que aprende de calificaciones
reales** (CA-M4.3), que hoy está implementado y **no se puede probar porque no
había ni una calificación**. Estrenarlo sobre un pipeline que aún marca como
completas las corridas interrumpidas (H-037) sería medir el aprendizaje y el
fallo a la vez.

### Decisiones del dueño que esta hoja de ruta espera

| Decisión | Qué depende de ella |
|---|---|
| **¿Hay ciclo 4?** | Si no, P4 deja de ser prerrequisito y el paso 5 desaparece |
| **Plan de Vercel** (Hobby / Pro) | La observabilidad: los errores de runtime dan 403 en Hobby |
| **Azul corporativo y logo**, con comunicaciones | El token `color-navy-700` frente al `#1D2559` del logo, y la versión transparente del principal |
| **Tarifa real de `gpt-5.4-mini` (P-5)** | Cerrar H5 con una cifra en vez de la condicional `1.586 + 239·k` |

---

## P0 · Ronda de calificación

**Ronda principal cerrada el martes 2026-09-29** en 66 de 105; **ronda
extendida hasta el jueves 2026-10-08**. El dueño hace una **invitación personal de unos 5
minutos** a cada gerencia, y **después cada quien califica por su cuenta**, sin
él delante.

Cómo se hace, y por qué así:

- **Cada gerente teclea su propio correo y emite sus propias calificaciones.**
  No las dicta ni las delega: `calificacion.id_usuario` registra quién tecleó, y
  si el dueño calificara por otro, ese registro diría algo falso.
- **En la invitación se explica la herramienta, no los insights.** La pregunta
  que H1 mide es si el insight le parece relevante a la gerencia, no si se
  entiende la pantalla.
- **No se comenta la calificación de nadie ante otro** (CA-M7.2): las
  calificaciones son independientes, y basta con mencionar «fulano le puso 5»
  para que dejen de serlo.
- **La versión móvil (H-044) deja de ser prerrequisito.** No bloquea; baja a P5.

**El congelamiento terminó** con el corte de la ronda principal, el 29.
Mientras duró no se republicó el informe y solo entraron las correcciones de
P0.5; el registro está en [ronda-calificacion.md](ronda-calificacion.md). La
ronda extendida se califica sobre el mismo informe 8.

> **Nota metodológica, y hay que llevarla hasta el informe.** **La ronda tiene
> una sola condición**: la tasa de respuesta se obtiene **con invitación
> personal y calificación autónoma**. Ninguna sesión fue acompañada, así que no
> hay nada que separar al reportar.
>
> **H2 del PRD suponía notificación por correo**, así que la tasa **se reporta
> con esta condición y no se compara directamente con el criterio de éxito.** La
> invitación personal no es acompañamiento, pero tampoco es un correo: está en
> medio, y nombrarla es más honesto que asimilarla a cualquiera de los dos.
>
> La sesión de `analitica` va aparte por ser la **prueba de humo** del operador
> del pipeline, no por su condición.
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
  fecha, persona, gerencia, condición y horas de inicio y fin.
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
  llegó después es de la **ronda extendida**, que se reporta aparte.

  ✅ **Exportada el 2026-10-01**: 66 filas en
  `C:\dev\respaldos\corte-ronda-2026-09-29\`, con manifiesto y sha256. **Se
  reconstruyó por `creado_en` dos días después del corte**, así que una
  corrección o un comentario añadido en ese intervalo no se vería (H-008); la
  evidencia y su alcance están en [ronda-calificacion.md](ronda-calificacion.md).
- **Corte de la ronda extendida: jueves 2026-10-08 a las 23:59 de Bogotá**
  (`2026-10-09 04:59:59+00`). Se exporta **el 9**, a
  `C:\dev\respaldos\corte-ronda-extendida-2026-10-08\` — **el mismo día**, para
  que la ventana sin marca de tiempo sea de horas y no de días.

## P2 · F0b — prerrequisitos de la decisión go/no-go · **1 d pendiente** de 5

Puede avanzar **en paralelo a la ronda**: toca `informe_resultados.md` y los
scripts que lo generan, no lo que ven los calificadores.

| Subfase | Resuelve | Esfuerzo | Cierre |
|---|---|---:|---|
| ~~**F0b.1**~~ | H-034 (causa raíz), H-027, H-030; arrastra H-031, H-032, H-033 | **hecho** | ✅ `--check` da «sin diferencias»; las 19 cifras de la auditoría salen idénticas. Rama `feat/f0b` |
| **F0b.2** | H-035 (+ H-006 en lo que toca a H5) | **1 d** | Dos ejecuciones sobre el mismo corte dan las mismas cifras |
| ~~**F0b.3**~~ | H-028, **H-010 desglosado por regla** | **hecho** | ✅ 4/326 en la corrida 10, todo R6, publicado en el informe. Rama `feat/f0b` |
| ~~**F0b.4**~~ | H-030 | **sin objeto** | La cifra se retiró por decisión del dueño (2026-10-01) |

**H-010 se reporta desglosado por regla**, no como un porcentaje único: R1–R7
son fidelidad de cita y **R8 es cifra sin fuente**, que son fallos distintos del
modelo. Está registrado en [decisiones-remediacion.md](decisiones-remediacion.md).

**Depende de P-5**, la tarifa real de `gpt-5.4-mini`: sin ella, F0b.2 publica el
costo con un factor declarado en vez de una cifra cerrada.

## P3 · Capacidades del PRD no construidas · **6 d** + *sin estimar*

Salen de la matriz de conformidad de la auditoría: CA en **No cumple**, más los
**Parcial** cuyo hallazgo es una Brecha que la remediación no cerró. **Nada de
esto se hace antes de la presentación del 13.**

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
| ~~**H-029**~~ | **F3.1, cerrado con F0b.1** (2026-10-01): el informe regenerado publica la tasa de rechazo con la frase de que mide fidelidad de cita contra lo ingerido, no veracidad |

## Cerrado por la remediación (no vuelve a aparecer arriba)

**H-005, H-009, H-013, H-015, H-016, H-019, H-020, H-045.** Además, **H-040** en
lo esencial —queda 0,1 d de documentación en F2.4— y **H-023** en su parte
documental, con la comparación pendiente en F2.3.

## Decisiones pendientes del dueño

**Están arriba**, en [la hoja de ruta](#decisiones-del-dueño-que-esta-hoja-de-ruta-espera):
ciclo 4, plan de Vercel, azul y logo con comunicaciones, y la tarifa real
(P-5). Se listan allí y no aquí para que no haya dos listas que se
desincronicen.

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
