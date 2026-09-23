# CLAUDE.md — MVP Inteligencia Territorial (Pactia)

Guía de trabajo para agentes sobre este repositorio. **Breve a propósito:** lo
que ya está detallado en `docs/` se enlaza, no se repite.

**Actualizado:** 2026-09-23 · **en producción** · ciclo 3, informe 8 · ronda de
calificación hasta el martes 2026-09-29, **con el contenido congelado**

---

## 0. Antes de tocar nada

| | |
|---|---|
| **En producción** | <https://inteligencia-territorial-mvp.vercel.app>, desde `main`. Cada push a `main` despliega |
| **Publicado** | Informe **8**, ciclo 3, congelando scoring 24 y agentes 10 |
| **Base** | Neon PostgreSQL, base **`territorial`** — *nunca* `neondb`, que solo tiene tablas de `neon_auth` |
| **Pruebas** | 345, en verde |

**Las siete reglas de operación que rigen hoy.** No son de estilo: cada una
existe porque romperla estropea el experimento en curso.

1. **La base principal es de solo lectura por defecto.** Cualquier escritura
   —migración, carga, publicación— necesita **confirmación explícita del
   dueño**, en ese momento y para esa operación.
2. **Congelamiento hasta el corte del martes 29.** No se republica ni se cambia
   nada que altere lo que ven los calificadores. Republicar cambiaría los
   insights pedidos y las calificaciones ya emitidas dejarían de ser
   comparables. **Solo se corrige un error que impida calificar**, y se anota en
   [ronda-calificacion.md](docs/ronda-calificacion.md).
3. **No se corren ciclos nuevos** hasta cerrar el bloque **P4** del
   [plan](docs/plan-siguientes-pasos.md).
4. **Publicar es siempre `scripts/publicar_informe.py`**, empezando por
   `--seco`, que sí revierte. No hay otro camino.
5. **Se califica solo lo pedido**: 5 insights en cada uno de los 3 primeros
   municipios, 15 en total. El resto del informe se lee sin calificar.
6. **Fusionar siempre con merge commit, nunca squash**, para que el linaje del
   commit publicado siga siendo cierto.
7. **La documentación va a `main`.** `remediacion/f0` queda como referencia
   histórica; no se trabaja sobre ella.

---

## 1. Qué es este proyecto

Un **experimento acotado, no un producto.** Es la *Fase -1* del PRD de
Inteligencia Territorial v1.2 de Pactia: 8 semanas, 3 ciclos quincenales, para
decidir go/no-go sobre la Fase 0.

Comprueba si una cadena multiagente puede extraer señal inmobiliaria accionable
de fuentes públicas colombianas. El pipeline va de un snapshot de datos
(SECOP II, feed de noticias, Bing, TerriData) a un informe de los **10
municipios mejor puntuados** —CA-M5.4 decía 3; la desviación está en §7— que 7
gerencias califican de 1 a 5.

| Dato | Valor |
|---|---|
| Municipios | **18** — los que trae el snapshot, no los 25-30 que preveía el PRD §2.1 |
| Señales | 20.030, repartidas en 3 ciclos por la fecha de cada registro (D2) |
| LLM | Azure OpenAI, superficie v1 de Foundry, **Responses API** (no `chat.completions`) |
| Base | SQLAlchemy: SQLite en local, **Neon (PostgreSQL) en nube** (D8) |

Las hipótesis que valida son H1–H5 ([PRD §1](docs/prd.md)). **H4 — trazabilidad
al 100% — es bloqueante**: si falla, la arquitectura no es auditable y no puede
ir a producción. No se resuelve con más ingeniería.

**H1 y H2 se miden con las calificaciones de esta ronda**, y hasta el
2026-09-23 no había ninguna emitida fuera de la prueba de humo. Por eso la ronda
manda sobre todo lo demás.

> **Sobre H3 y el conteo «2 de 3 fuentes».** El PRD §2.3 lista SECOP II, el feed
> de noticias y TerriData como las tres fuentes, y eso induce a error al leer
> H3. **TerriData no es una fuente comparable**: es contexto estructural
> —población, economía, vivienda—, no señal de coyuntura. De las fuentes que
> **sí pueden originar insights**, las dos están evaluadas. **H3 está más cerca
> de respondido de lo que el conteo 2/3 sugiere.**

### El stack real

```
 snapshot ──► pipeline Python ──►  Neon (PostgreSQL)  ◄── app Next.js ──► Vercel
              determinista y agentes   base «territorial»       web/
```

**No hay Django y nunca lo hubo**: D5 lo eligió antes de que el hosting fuera
Vercel y no llegó a instalarse (desviación en el Addendum 02). **No hay API
intermedia**: el PRD §4.3 la prohíbe y la app lee Neon directamente.

### Documentos, en orden de autoridad

[PRD](docs/prd.md) · [Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) ·
[Addendum 02 — Stack](docs/addendum-02-stack.md) ·
[Design System](docs/design-system.md) · [Pendientes](docs/pendientes.md)

Y lo que dice qué pasa ahora:

| Documento | Para qué |
|---|---|
| [**Plan de siguientes pasos**](docs/plan-siguientes-pasos.md) | **Qué viene y en qué orden** (P0–P6), con el esfuerzo de cada bloque |
| [Ronda de calificación](docs/ronda-calificacion.md) | La ronda en curso, el congelamiento y el corte |
| [Estado del despliegue](docs/estado-despliegue.md) | Los 11 pasos y lo que quedó abierto |
| [Decisiones de remediación](docs/decisiones-remediacion.md) | Lo que decidió el dueño, riesgos aceptados e incidentes |
| **Auditoría** | 51 hallazgos y la matriz de los 59 CA. **No está en `main`**: `git show audit/2026-09-22:docs/auditoria.md` |
| [Informe de resultados](docs/informe_resultados.md) | Lo medido por hipótesis, para la compuerta de la semana 8 |

> El **[Design System](docs/design-system.md) es la autoridad de color y
> tipografía**, derivado de la plantilla Word corporativa real. **Léelo entero
> antes de escribir una línea de front.** El primario es **navy `#0F4761`**, no
> terracota, y la fuente es **Aptos**: los datos se distinguen con
> `font-variant-numeric: tabular-nums`, no con una segunda familia. Lo marcado
> `[provisional]` **no es identidad de Pactia**: es deuda, no lo cites como
> marca.
>
> El PRD principal v1.2 y la especificación de UI **no están en el
> repositorio** (pendiente 11.5). No inventes requisitos para cubrirlos.

---

## 1.1 Lo que este MVP **no** tiene

| No existe | Qué hay en su lugar | Dónde se decidió |
|---|---|---|
| **El Sintetizador** | El informe se compone **de forma determinista**: cifras, factores y citas las pone el código. `justificacion` y `sugerencias` viajan vacías y la pantalla pinta el hueco. Falta la prosa | P3 del plan — **único ítem sin estimación** |
| **Envío de correos** y canal de notificación | El enlace se comparte a mano, fuera del sistema | 11.4/3 |
| **Autenticación** | Leer es abierto con el enlace; calificar pide el correo y lo valida contra `usuario`. Riesgo **R-A2** | 3b · `M9-acceso` |
| **Histórico, panel de métricas y trazabilidad en pantalla** | Nada todavía | P3 del plan |
| **La infografía** | **Retirada formalmente** del MVP. No es deuda | F0.8 · P-4 |
| **Umbral de score** y «criterio de corte» | Tope fijo de **10** municipios | `P1` |
| **Umbral de información** que excluía municipios | Está en **0**: el informe muestra el score **y en qué se apoya** | `P1`, §7 |
| **Revisión humana previa** a la distribución | El validador determinista más la marca «MVP» | PRD §7, riesgo aceptado |
| **Umbral de fatiga**, supresiones, Admiralty | Nada: con ~6 alertas por ciclo no hay fatiga que suprimir | PRD §2.2 |
| **Django** | **Next.js sobre Vercel**, leyendo Neon | `M9-fw` · Addendum 02 D5 |

**Y la afirmación que ordena todo lo demás:** el **scoring es código
determinista y es lo único reproducible del sistema**. Todo lo que pasa por un
modelo varía entre el 19% y el 26% entre pasadas idénticas. La frontera de la
reproducibilidad coincide exactamente con la frontera entre la capa determinista
y la agéntica. Cualquier cosa que deba ser reproducible tiene que estar en
código.

### Riesgos aceptados por el dueño

Registrados en [decisiones-remediacion.md](docs/decisiones-remediacion.md):

- **R-A1** — la credencial de la base estuvo expuesta; se acepta el residual en
  vez de rotarla durante la ventana del experimento.
- **R-A2** — **la identidad es declarativa**: un correo tecleado contra la lista
  precargada (H-012 abierto). La firma impide falsificar la cookie, no teclear
  el correo de otro. **Hay que decirlo al publicar H1 y H2.**
- **P-6** — no se consulta a jurídica antes de cargar usuarios, pese a que la
  base contiene datos personales de SECOP.

---

## 2. Reglas de obligado cumplimiento

### 2.1 Datos — consecuencia de D8 (SQLite local / PostgreSQL nube)

1. **Todo acceso a datos pasa por SQLAlchemy.** Nunca SQL crudo de un motor.

   **Alcance, precisado el 2026-09-21: la regla protege las escrituras y el
   esquema, no las lecturas.** Existe para que nada corrompa la evidencia que el
   experimento mide, y **una app que solo lee no puede corromper nada**. Lo que
   sí amenazaría es una app que escriba sobre el pipeline o que traiga su propio
   ORM con migraciones.

   Así que el aplicativo web (Next.js, ver `M9-fw`) **puede leer Neon
   directamente**. Es lo que el PRD §4.3 ya pedía —«una sola app sobre la misma
   Postgres del pipeline, **sin API intermedia ni segundo almacén**»— y meter una
   API Python por delante habría contradicho esa línea, además de añadir un
   despliegue a un MVP de 8 semanas con un desarrollador.

   Dos condiciones que lo hacen seguro, y sin las dos la regla sí se rompe:

   - **Las escrituras de la app pasan por Python, o su forma se verifica contra
     `modelos.py`.** Son las tres de CA-M9.16 —calificación, comentario y
     seguimiento— y viven en dos tablas: `calificacion` (el comentario es una
     columna suya) y `seguimiento`.

     **Resuelto generando, no duplicando.** `scripts/generar_contrato_ts.py` lee
     `modelos.py` y emite `web/lib/contrato.generado.ts` con las columnas, los
     tipos, la nulabilidad y los valores de los CHECK — el `estado` del
     seguimiento sale como unión de tipos, así que una errata es error de
     compilación y no un 500 en la ventana de calificación. **Y
     `tests/test_contrato.py` falla si alguien toca `modelos.py` sin
     regenerar**, que es lo que vuelve imposible «un campo cambia y nadie se
     entera». Mismo papel que `alembic check`, sobre el lenguaje que no comparte
     el modelo. Una lista escrita a mano en TypeScript habría sido una segunda
     fuente de verdad que envejece en silencio.
   - **La app no genera migraciones nunca**, ni para sus propias tablas. Si M9
     necesita algo —sesiones de acceso por correo, por ejemplo— esa tabla nace en
     Alembic.

   **El riesgo de desacople no es el lenguaje: es que la forma de las tablas viva
   en dos sitios.** Mientras Alembic mande y las escrituras sean tres y estén
   acotadas, TypeScript leyendo Neon es una decisión de despliegue, no de
   arquitectura de datos.
2. **El esquema se gobierna con Alembic** desde la primera migración.
3. **Las columnas JSON usan el tipo `JSON` portátil.** Nunca operadores JSONB de
   PostgreSQL (`->>`, `@>`, `jsonb_path_query`): no existen en SQLite y rompen
   el entorno local.

### 2.2 Bloqueante — CA-M6.3

**Ninguna cifra de un informe puede provenir del LLM.** Todas se
componen desde el almacén de datos. El LLM redacta; los números los pone el
código. Esta regla no admite excepción ni atajo.

### 2.3 Corolarios que sostienen H4

- El validador (M3) es **código, nunca LLM**. Si un modelo decidiera qué
  evidencia es suficiente, el experimento perdería su ancla: un agente elocuente
  parece funcionar aunque invente. **Su tasa de rechazo mide la fidelidad de
  cita contra el contenido ingerido, no la veracidad respecto del mundo**
  (H-029; CA-M3.3).
- **Bing nunca es evidencia** (Addendum 01, D1). Es contexto cualitativo: llega
  sin fecha y sin URL. El validador lo rechaza por la regla R2.
- Los prompts van **versionados** y se archivan en el almacén (D7). El linaje se
  registra; no se edita un prompt en sitio.

  > **Hoy esta regla está incumplida para el Correlacionador v2**, que se
  > promovió sin fila en `prompt_version` (**H-036**). La regla no cambia: lo
  > que falla es el cumplimiento, y **lo cierra F2.3**. Mientras tanto, el
  > valor por defecto es v1, que sí tiene linaje y es lo publicado.

### 2.4 Toda compuerta necesita su piso de ruido medido

**Antes de poner una compuerta automática sobre la salida de un agente, mide su
piso de ruido corriéndolo contra sí mismo.** No es una recomendación: es un
requisito para cualquier compuerta futura, no solo para la del Correlacionador.

Una comprobación que no conoce su piso **no mide un efecto: mide varianza y le
pone una etiqueta de aprobado o suspenso.** Y lo hace con toda la autoridad de
un número.

Pasó aquí. La primera compuerta del Correlacionador exigía que la versión nueva
no correlacionara más que la vieja **en ningún municipio**, y suspendió a v2. El
control v1 contra v1 —mismo prompt, mismos 322 insights— demostró que esa
compuerta **habría suspendido a v1 contra sí mismo**, con 14 de 18 municipios
moviéndose y el agregado subiendo de 39 a 42.

Las tres reglas que salen de ahí:

1. **El criterio va sobre el agregado**, no elemento a elemento. Municipio a
   municipio no significa nada cuando el agente se mueve solo.
2. **El umbral es el rango observado de la versión contra sí misma**, no un
   margen relativo sobre la pasada A. Un margen sobre A tiene un filo: si A cae
   en el fondo de su rango y B en lo alto, el mismo prompt se suspende. Con las
   cifras medidas no es hipotético — v1 dio 39 y 42 en dos pasadas seguidas.
3. **Sin piso medido para ese corpus, la compuerta se niega a juzgar** en vez de
   dar un veredicto sin base. Está implementado así.

El invariante está probado en `tests/test_compuertas.py`: **una compuerta nunca
puede suspender a la línea base que la calibró.** Si lo hace, está midiendo
ruido.

**Y lo mismo vale para una detección, no solo para una compuerta.** La
comprobación de cifras de CA-M6.3 acusó a Carepa de inventarse un «80» que era
«calles 76 y 80», un nombre de calle que sí estaba en su entrada: capturaba el
punto final de la frase en una orilla y no en la otra. **Medir las dos orillas
con varas distintas produce violaciones inventadas, y eso es peor que no
detectar nada** — lleva a desconfiar de salidas correctas, que es justo la
confianza que CA-M6.3 existe para construir. Vive en `reglas/cifras.py`, con
pruebas.

Re-verificarlo costó **cero tokens**, sobre las corridas 11 y 12 ya persistidas.
Es la mejor demostración de para qué sirve la persistencia por corrida: una
medición que se puede repetir sin volver a pagarla.

---

## 3. Separación de capas

La frontera entre capas es lo que sostiene H4:
**lo determinista nunca depende de un LLM, y lo agéntico nunca decide qué es
evidencia suficiente** (PRD §3.1).

```
src/territorial/
│
├── CAPA 1 — DETERMINISTA (código, nunca LLM)
│   ├── ingesta/     Carga, particionado por ciclo, deduplicación
│   ├── reglas/      validador · prefiltro · cobertura · contexto · normalizacion · cifras
│   └── scoring/     M5 — F1–F6, pesos, ranking del top 10, persistencia
│
├── CAPA 2 — AGENTES (LLM)
│   ├── agentes/     fuentes · clasificador · correlacionador
│   └── agentes/prompts/   Versionados (D7)
│
├── CAPA 3 — SUPERFICIE
│   ├── informes/    M6 — composicion · seleccion · publicacion · gerencias
│   └── web/         Next.js en Vercel (fuera de src/)
│
└── TRANSVERSAL
    ├── almacen/     blob.py · modelos.py · sesion.py
    ├── utiles/      divipola.py
    └── config.py
```

Al añadir código, respeta la capa. Una regla de negocio no vive en un prompt, y
una llamada a LLM no vive en `reglas/`. **No existen `grafo/` ni
`observabilidad/`**: Langfuse y el checkpointing de CA-M8.4 están instalados
pero sin cablear, y son deuda, no cuello de botella.

---

## 4. Estado real por módulo

**Nada se sobrescribe.** Insights, descartes y scores cuelgan de una *corrida*
—`corrida_agentes` y `corrida_scoring`— y cada ejecución inserta una nueva. Dos
pasadas del mismo ciclo conviven, que es lo que impide que un reproceso borre lo
que las gerencias calificaron.

| Módulo | Estado | Detalle |
|---|---|---|
| **M1** Ingesta | ✅ | 18 municipios y 20.030 señales. Conectores vivos diferidos a Fase 0 |
| **Prefiltro** | 🟡 Sin validar | Reduce 61,2%, pero el diccionario de obra da entre 13% y 90% según el municipio (**A2**) |
| **M2** Clasificación | 🟡 No reproducible | Prompt **v4**, lotes de 50. CA-M2.1: 95,2% y 94,9% en dos pasadas. Pero **una de cada cinco señales cambia de destino entre pasadas idénticas** (**A6**). No afecta al ranking —el score lee `senal_cruda`— pero sí a lo que las gerencias leen |
| **M3** Validación | ✅ Funciona | 7 reglas R1–R7, **código puro**. **Su tasa de rechazo está pendiente de F0b.3** y no debe citarse hasta entonces: ver el aviso de abajo |
| **M4** Correlación | 🟡 No reproducible | **v1 es lo publicado y el valor por defecto**; v2 es **candidata** hasta F2.3. Solo el 14,1% de las convergencias se repiten entre pasadas idénticas (**A11**). CA-M4.3 implementado pero sin ejercitar |
| **M5** Scoring | ✅ | F1–F6, normalización por cohorte, **top 10** y desglose. `VERSION_ALGORITMO` en **v3**. Pesos provisionales: los definitivos los decide Gerencia General (**A1/4**) |
| **M6** Síntesis | 🟡 | Composición y publicación hechas, **ni una cifra del LLM** por construcción. **Falta el Sintetizador** |
| **M7** Calificación | ✅ En producción | Se califica **solo lo pedido** (15 insights). Usuarios precargados: quien no esté no califica |
| **M8** Trazabilidad | 🟡 | Linaje de dataset, de prompts por contenido y trazas por agente. Falta Langfuse y el checkpointing de CA-M8.4 |
| **M9** Aplicativo | 🟡 En producción | Rutas: `/`, `/ciclo/[id]` y `/priorizados`. **Faltan histórico y métricas** (P3). Lee Neon directamente; escribe solo `calificacion`, `seguimiento` e `identificacion` |

> ### La tasa de rechazo del validador: no la cites todavía
>
> **La cifra «0,0%» que este documento traía era falsa** y la auditoría la marcó
> como tal. La tasa real **está pendiente de F0b.3**, que exige persistirla y
> reportarla **desglosada por regla** —R1–R7 son fidelidad de cita y R8 es cifra
> sin fuente, que son fallos distintos del modelo—. **Hasta que F0b.3 cierre, no
> uses ninguna tasa de rechazo en un informe ni en una conclusión sobre H4.**

### Dos resultados que no conviene enterrar

**La fuente sin filtrar rinde mejor que la filtrada.** RSS entra al Clasificador
**sin prefiltro** y convierte el **46%** de sus señales en insight; SECOP, que
pasa por el diccionario de obra, convierte el **40%**. El prefiltro existe para
ahorrar coste, y lo que deja pasar convierte *peor* que lo que nunca se filtró.
No prueba que haya que quitarlo —SECOP son 19.640 señales y RSS 336— pero sí que
su calibración no está seleccionando mejor señal (**A2**).

**Los 15 insights que cruzan RSS con SECOP son la primera evidencia de que la
correlación multiagente produce algo que ninguna fuente sola produce.** Es
CA-M4.1 literal, y con una sola fuente era **literalmente imposible**: M4 no
funcionaba mal, no tenía nada que cruzar.

### El nomenclátor DIVIPOLA: 1.135 entidades, y cuatro rarezas

`entidad_divipola` es una **tabla maestra de referencia**. Se carga con
`scripts/cargar_divipola.py`, es idempotente y **no amplía el universo del
MVP**: los 18 municipios siguen en `municipio` y las dos tablas no están
enlazadas a propósito. Códigos como los de TerriData: nacional `01001`,
departamento `dd000`, municipio `ddmmm`.

Cuatro cosas que van a descuadrarle el conteo a alguien: son **1.102
municipios**, falta San Andrés (88001) · **Bogotá aparece solo como municipio**
(11001), así que hay **32 departamentos y no 33** · las áreas no
municipalizadas no están · **63 nombres se repiten entre departamentos** y
afectan al **13%** de los municipios. Hay cuatro «La Unión». **El par
(departamento, municipio) es obligatorio.**

> **No midas la atribución cruzada (A3) buscando estos 1.102 nombres en texto
> libre.** A3 es contratación departamental archivada en la capital y ejecutada
> fuera, no colisión de nombres. Con el 13% de nombres ambiguos el número
> saldría inflado. Esa medición necesita diseño propio, y sigue fuera del
> alcance del MVP.

### Contexto estructural: quién ve el número y quién ve el adjetivo

`contexto_municipal` trae de TerriData seis indicadores para los 1.102
municipios (`scripts/cargar_contexto.py`, que lee el zip de 3,31 GB por
streaming y exporta un CSV a `data/` para no volver a tocarlo, `--desde-csv`).

**Tres capas, tres responsabilidades. No las mezcles:**

| Capa | Qué ve | Por qué |
|---|---|---|
| **Scoring** | **nada** | Son indicadores anuales: idénticos en los 3 ciclos. Es el defecto de F4, que era una constante con el 18% del peso |
| **Correlacionador** | **bandas**: «déficit alto» | Una cifra real escrita por el modelo sigue siendo una cifra escrita por el modelo (CA-M6.3). El adjetivo lo calcula código |
| **Informe** (M6) | **los números** | CA-M6.3 no prohíbe el número: prohíbe que lo escriba el modelo. Se componen por código y con su año a la vista |

Las bandas son **nacionales sobre los 1.102**, nunca sobre los 18. Población va
por **clases de tamaño de corte fijo** y valor agregado **per cápita**, porque
con cuartiles nacionales los 18 salían «alto» los 18. Ver `reglas/contexto.py`.

**La regla que hace segura la concesión:** el contexto explica una convergencia,
**nunca la crea**. Es ejecutable, no declarativa —
`scripts/comparar_correlacionador.py` falla si aparece en la salida una cifra
que no estaba en los insights.

> **v1 es el valor por defecto y es lo que hay publicado.** `VERSION_PROMPT` es
> `v1` desde el 2026-09-22, para que un ciclo nuevo no estrene un prompt sin
> comparación validada con linaje persistido. **v2 es candidata**: se promovió
> tras el control de ruido, pero **ninguna corrida se ejecutó con ella** y
> `prompt_version` no tiene fila suya. Vuelve a ser el valor por defecto cuando
> pase **F2.3**.
>
> **v2 no se borra**: sigue en `prompts/correlacionador_v2.md` y se elige con
> `version="v2"`. `tests/test_version_prompt.py` falla si la constante cambia
> sin actualizar `docs/decisiones-remediacion.md`.
>
> `VERSIONES_CON_CONTEXTO` decide qué versiones reciben el bloque de contexto y
> solo está v2, así que **con v1 el contexto estructural no viaja hoy**. Si
> añades una versión nueva, métela ahí o el contexto dejará de viajar en
> silencio. Y cambiar `VERSION_PROMPT` **no republica nada**.

### Pendientes que frenan el avance

El registro completo y priorizado está en
[plan-siguientes-pasos.md](docs/plan-siguientes-pasos.md). Los que más
condicionan lo que escribas:

- **A2** — el prefiltro no está validado y su diccionario decide buena parte del
  score (H-011, congelado por Analítica).
- **A4** — el Clasificador parte un mismo frente de obra en varios insights
  (cuatro de pavimentación en Carepa). Infla el conteo y degrada el informe.
- **A6 y A11** — ni el Clasificador ni el Correlacionador son reproducibles.
- **A5** — sigue abierta la **escala común**: min-max por cohorte es ordinal
  dentro de su corrida y **no comparable entre ciclos**. Ver §7.
- **H5 tiene base y el costo no es barrera**: USD 39/año el piloto, USD 2.160/año
  los 1.103 municipios. **No cuenta el Sintetizador**, que corre sobre gpt-5 y
  podría no ser menor.

---

## 5. Entorno y operación en esta máquina

El intérprete vive **fuera del repositorio**, porque la política corporativa
impide ejecutar binarios desde `Downloads`. `python` a secas resuelve al stub de
Microsoft Store y no sirve.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py -m pytest -q                                      # 345 pruebas, aisladas
& $py scripts\calcular_scores.py --ciclo 3              # M5, no gasta tokens
& $py scripts\avance_calificacion.py                    # ronda, solo lectura
& $py scripts\verificar_llm.py                          # conexión al tenant
```

**El [README](README.md) tiene el detalle** de `DATABASE_URL`, los dos hosts de
Neon, el cuelgue por IPv6 y qué hace cada script. No se repite aquí.

> ### `correr_ciclo.py --seco` **no es seco**
>
> **Escribe y gasta tokens** (H-038, abierto). Este documento decía lo
> contrario y era falso. **No lo uses.** El `--seco` de `publicar_informe.py`
> sí revierte, y ese es el que hay que usar antes de publicar.
>
> Y `correr_ciclo.py` sin `--municipio` procesa los 18. Hoy, además, **no se
> corren ciclos nuevos** hasta cerrar P4.

### Cinco cosas propias de esta máquina y esta red

1. **El push a GitHub lo hace el dueño desde su terminal.** La red de la sesión
   falla contra GitHub. No intentes rodeos: deja los commits en local y avisa.
2. **`pg_dump` está bloqueado por política** y no se puede ejecutar. El respaldo
   es una **exportación lógica en Python** a CSV, fuera del repositorio, con
   manifiesto y sha256. El procedimiento de restauración —incluido el reinicio
   de secuencias— va en el README del respaldo.
3. **Cuidado con el escape de rutas de Windows al escribir documentos.** Ya ha
   corrompido texto tres veces: `\v` y `\b` desaparecen y dejan `scriptserificar`
   o `pgsqlin`. Construye esas rutas sin escapes o verifícalas después.
4. **La cadena del `.env` ya trae `connect_timeout`.** No se lo añadas otra vez:
   libpq recibe dos valores y falla con `bad value for connect_timeout`.
5. **Playwright está por verificar**: descarga binarios sin firmar que la
   política bloquea.

> **Regla de reintento, decidida por el dueño.** Un error que falla **antes** de
> conectar a la base se puede reintentar **una vez**, tras comprobar que el
> estado no cambió. Cualquier error que **ya tocó la base**: detente y reporta.

### 5.1 Migraciones (regla 2 de D8)

```powershell
& $py -m alembic current
& $py -m alembic upgrade head
& $py -m alembic revision --autogenerate -m "motivo"   # tras tocar modelos.py
& $py -m alembic check                                 # ¿esquema y modelos concuerdan?
& $py scripts\generar_contrato_ts.py --check           # ¿el contrato TS concuerda?
```

- **`alembic check` después de cada `upgrade`, siempre.** El `Running upgrade`
  del log no prueba nada: ya ocurrió una migración que lo imprimió y **falló
  después**, dejando la base en la revisión anterior. `check` compara el esquema
  real contra los modelos y fue lo único que lo detectó.
- **`aplicar_migraciones()` en `almacen/sesion.py` es el camino desde código.**
  `create_all` quedó prohibido: crea lo que falta y calla ante lo que cambió.
- **La URL no está en `alembic.ini`**, sale de `DATABASE_URL`. **Por el endpoint
  `-pooler` no se migra**, y los dos caminos a Alembic lo comprueban.
- **`render_as_batch=True` es obligatorio** (SQLite no sabe eliminar una columna
  con un `ALTER TABLE` normal) y **nombra siempre las claves foráneas**: sin
  nombre, en modo batch, revientan.
- **`--autogenerate` compara contra la base a la que apuntes.** Genera contra
  una base limpia o la migración saldrá vacía.

### 5.2 Vercel y Neon

| | |
|---|---|
| **Root Directory** | `web` — vive **solo en el panel**, no se deduce del repositorio |
| **Variables de base y `COOKIE_SECRET`** | **Solo en Production.** En Preview expondrían la base real a cualquier rama |
| **Integración de Neon** | Sus variables, **solo en Development** |
| **Errores de runtime** | **No se pueden leer por API en el plan Hobby** (403). Es una decisión pendiente del dueño |

> **Nunca borres el store de Neon ni la integración desde Vercel.** Puede
> arrastrar el **proyecto de Neon entero**. Si hay que desconectar algo,
> pregunta primero.

### Notas del tenant, verificadas por llamada real

- Cliente `OpenAI` con `base_url`, **no** `AzureOpenAI`. `api_version` no aplica.
- Despliegues: clasificador `gpt-5.4-mini`, correlacionador `gpt-5`,
  sintetizador `gpt-5`.
- Un `max_output_tokens` bajo **corta a los modelos de razonamiento antes de que
  emitan texto, y la llamada vuelve vacía sin error.** El techo está en **16384**
  para todos. Ver §8.

---

## 6. Dos decisiones de M5 que no vienen de D4

Están implementadas, documentadas en el código y son configurables, pero
**nadie las ha aprobado**. Si tocas el scoring, léelas antes.

**La escala común de los factores.** D4 fija cómo se calcula cada factor y
cuánto pesa, pero no en qué escala se suman, y sin eso los pesos no significan
nada: F1 vive en [0, 1], F4 va de -65% a +900% y F2 son miles de millones. Se
normaliza **min-max dentro de la cohorte del ciclo**. El costo: los scores **no
son comparables entre ciclos**, solo dentro de uno.

**El umbral de información está apagado.** D4 manda redistribuir el peso de los
factores sin cobertura, y sobre el snapshot aparece el efecto contrario: Ibagué,
con **3 de 239 días cubiertos**, salía **primero**. La redistribución premia al
que no tiene datos. Durante unos días se resolvió **excluyendo**; desde el
2026-09-21 se resuelve **exponiendo**: `Config.umbral_informacion` está en **0**
y el informe muestra el score **junto a los factores que lo sostienen y los que
no**. Quien lee juzga.

Lo que forzó el cambio: **Barranquilla tiene 12 insights de prensa que pasaron
el validador** y quedaba invisible. Y bajar el umbral no servía — las fracciones
informadas del ciclo 3 son **20,10% o 77,80%, sin nada en medio**. El mecanismo
se conserva entero: `fraccion_informada` se sigue calculando como auditoría y
subir el umbral lo reactiva.

**Y el tope del informe es 10** (`Config.tope_top`). CA-M5.4 decía «top 3 fijo»:
desviación deliberada, pero sigue siendo un número fijo y no un «todos los que
pasen de X».

> **Al usuario final no se le enseñan códigos de factor.** «Apoyado en F4+F5» es
> correcto y no significa nada para una gerencia. `F1/F2/F3` → contratación
> pública · `F4` → licencias · `F5` → prensa · `F6` → calificaciones. «F4+F5» se
> lee **«licencias y prensa, sin contratación»**, y ahí lo que falta informa más
> que lo que hay.

**La fracción informada mide dato, no puntuación.** `ValorFactor` separa
`disponible` —¿el factor puntúa?— de `hay_dato` —¿existe el dato subyacente?—.
Coinciden salvo en el piso de área de ELIC, donde el dato existe pero el
porcentaje no es fiable. Antes eso descontaba dos veces.

### Los pesos que corren no son los de `pesos.py`

`config/pesos.json` **está en el repositorio** y manda sobre
`PESOS_POR_DEFECTO`. Lleva **F4 a la mitad**, aprobado por Analítica el
2026-09-21: F4 es **idéntico en los tres ciclos para los 18 municipios**, así que
con el 18% del peso desplazaba a todos de forma fija. A la mitad y no a cero
porque con F4 en cero F5 domina el ciclo 3 y la patología se mudaba.

**Las pruebas no leen ese archivo**: `tests/conftest.py` las fija a los pesos de
D4, para que una recalibración de Gerencia no rompa el suite.

### La trampa que ya ha aparecido seis veces

**Ausencia de SECOP no es ausencia de actividad.** Está escrito en D4 y aun así
el sistema lo ha violado seis veces, siempre igual: SECOP es la fuente más rica,
así que todo acaba calculándose desde ella, y el municipio que no contrata obra
queda indistinguible del que no existe.

1. **F5** dividía por días cubiertos, que salían solo de fechas de SECOP.
2. **El corte de cohorte** propagaba el NULL al conjunto.
3. **El piso de área de ELIC** se descontaba de la fracción informada.
4. **El prefiltro** no ve nada que no tenga forma de objeto contractual.
5. **RSS no llegaba al Clasificador**: el diccionario de obra, calibrado sobre
   objetos de SECOP, era una de las tres barreras.
6. **La fracción informada** es casi toda peso derivado de SECOP: el sistema
   sabe cosas de Barranquilla y su propia métrica dice que no sabe nada.

Antes de escribir cualquier cosa que divida, filtre o cuente, pregúntate qué
pasa con el municipio que tiene noticias y no tiene contratos.

---

## 7. Carga inicial y operación no son lo mismo

El snapshot cubre **374 días** y sus tres ciclos duran **51, 84 y 239 días**. No
son quincenales, pese a que el PRD los llame así: D2 los partió por terciles de
volumen SECOP. **El ciclo 3 son 17 quincenas.**

| | Señales tras el prefiltro |
|---|---|
| Carga inicial (el snapshot, un año) | **7.628** |
| Una quincena en operación | **~615** |

En régimen normal **13 de los 18 municipios no llegan a 20 señales por
quincena**. Dos consecuencias, y la segunda es la que importa:

- Dimensionar el troceo con las cifras del snapshot sobredimensiona el sistema
  por un factor de 12.
- **H5 no se puede extrapolar con los totales del snapshot.** Hay que usar la
  tasa diaria por 14, no los totales.

---

## 8. Tres cosas que cortan una llamada sin avisar

**El techo de tokens puede depender del agente, aunque hoy no difiera.**
`cliente.techo_de()` devuelve `max_tokens_salida_razonamiento` para los agentes
de `AGENTES_QUE_RAZONAN` (Correlacionador y Sintetizador) y `max_tokens_salida`
para el resto. **Ambos valen 16384 hoy.** Si añades un agente sobre un modelo de
razonamiento, mételo en ese conjunto.

Con el techo en 4096 el Correlacionador se cortó en seco en Barranquilla y **la
llamada volvió vacía y sin error**, que es la forma más difícil de diagnosticar.

**No subas `Config.senales_por_lote` por velocidad.** Con 100 señales cabe de
sobra en tokens pero 4 de 7 insights salieron sin categorizar. **El límite
práctico es la calidad, no los tokens**, y se degrada en silencio: el JSON sigue
siendo válido. 50 es el punto probado.

**El Clasificador no es reproducible entre corridas.** El mismo lote de 20
señales de Carepa dio 3 insights una vez y 6 otra. Importa para H4 y para
cualquier medición de prompts.

---

## 9. Al cambiar el prompt de un agente

No lo afines a ojo. Crea una versión nueva en `agentes/prompts/`, córrela contra
la anterior sobre el mismo lote con `comparar_prompts.py` y reporta las métricas
(reducción, tasa de rechazo, señales sin contabilizar, insights duplicados,
tokens). Las versiones peores **se conservan como registro**: `clasificador_v3`
está en el repo porque documenta una hipótesis que resultó incorrecta.

**Y antes de poner una compuerta sobre la salida, mide su piso de ruido** — §2.4
lo explica y `tests/test_compuertas.py` lo prueba.

---

## 10. Los tres choques de §2, cerrados

**Decididos por el dueño el 2026-09-23 y ya aplicados.** No los reabras; el
registro está en [decisiones-remediacion.md](docs/decisiones-remediacion.md).

- **§2.2** — fuera la mención a la infografía, retirada en F0.8.
- **§2.3** — la tasa de rechazo **mide fidelidad de cita contra lo ingerido, no
  veracidad respecto del mundo** (H-029). La regla ya lo dice así.
- **§2.3, linaje de prompts** — **la regla se mantiene sin cambios.** Lleva una
  nota de que hoy está incumplida para el Correlacionador v2 y de que la cierra
  F2.3.
