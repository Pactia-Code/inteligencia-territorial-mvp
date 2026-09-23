# CLAUDE.md — MVP Inteligencia Territorial (Pactia)

Guía de trabajo para agentes sobre este repositorio.
**Actualizado:** 2026-09-22 · Neon en la nube · informe a top 10 · M4: **v1 es lo
publicado**, v2 candidata

---

## 1. Qué es este proyecto

Un **experimento acotado, no un producto.** Es la *Fase -1* del PRD de
Inteligencia Territorial v1.2 de Pactia: 8 semanas, 3 ciclos quincenales, para
decidir go/no-go sobre la Fase 0.

Comprueba si una cadena multiagente puede extraer señal inmobiliaria accionable
de fuentes públicas colombianas. El pipeline va de un snapshot de datos
(SECOP II, feed de noticias, Bing, TerriData) a un informe de los **10
municipios mejor puntuados** —CA-M5.4 decía 3; la desviación está en §7— que 7
gerencias califican de 1 a 5 durante 3 ciclos.

| Dato | Valor |
|---|---|
| Municipios | **18** — los que trae el snapshot, no los 25-30 que preveía el PRD §2.1 |
| Señales | 20.030, repartidas en 3 ciclos por la fecha de cada registro (D2) |
| LLM | Azure OpenAI, superficie v1 de Foundry, **Responses API** (no `chat.completions`) |
| Base | SQLAlchemy: SQLite en local, **Neon (PostgreSQL) en nube** (D8). Las dos con los mismos datos desde el 2026-09-21 |

Las hipótesis que valida son H1–H5 ([PRD §1](docs/prd.md)). **H4 — trazabilidad
al 100% — es bloqueante**: si falla, la arquitectura no es auditable y no puede
ir a producción. No se resuelve con más ingeniería.

> **Sobre H3 y el conteo «2 de 3 fuentes».** El PRD §2.3 lista SECOP II, el feed
> de noticias y TerriData como las tres fuentes, y eso induce a error al leer
> H3. **TerriData no es una fuente comparable**: es contexto estructural
> —población, economía, vivienda—, no señal de coyuntura, y no podría producir
> insights aunque estuviera cargada. De las fuentes que **sí pueden originar
> insights**, las dos están evaluadas: SECOP desde el principio y RSS desde el
> 2026-09-21, con un 98% de supervivencia al validador. **H3 está más cerca de
> respondido de lo que el conteo 2/3 sugiere.**

Documentos de referencia, en orden de autoridad: [PRD](docs/prd.md) ·
[Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) ·
[Addendum 02 — Stack](docs/addendum-02-stack.md) ·
[Arquitectura](docs/architecture.md) · [Pendientes](docs/pendientes.md) ·
[Design System](docs/design-system.md)

> **El [Design System](docs/design-system.md) es la autoridad de color y
> tipografía**, por encima de `especificacion_ui_inteligencia_territorial.md`.
> Está derivado de la plantilla Word corporativa real de Pactia (`theme1.xml`,
> `styles.xml`), así que es marca confirmada y no propuesta. **Léelo entero
> antes de escribir una línea de front.**
>
> Hay dos conflictos con la especificación de UI y el Design System gana en los
> dos. **Color:** la especificación proponía terracota como acento primario; el
> primario es **navy `#0F4761`**. **Tipografía:** la especificación pedía tres
> familias —serif, palo seco, monoespaciada— y Pactia no tiene ni serif ni
> monoespaciada. La fuente es **Aptos**, y los datos se distinguen con
> `font-variant-numeric: tabular-nums`, no con una segunda familia.
>
> La especificación de UI sigue siendo válida como referencia de **estructura**
> de pantallas, no de color ni de tipografía. **Ojo: ese documento tampoco está
> en el repositorio**, igual que el PRD v1.2 (pendiente 11.5), así que su
> autoridad sobre la estructura no se puede verificar desde aquí.
>
> Lo marcado `[provisional]` en el Design System —neutrales, semántica de
> estado, espaciado— **no es identidad de Pactia**: es deuda que se reemplaza
> cuando exista brandbook. No lo cites como marca.
>
> Su **Anexo** lista lo retirado respecto a la versión anterior del documento
> —alerta por correo, consola de Analítica, Admiralty, umbral de fatiga,
> revisión humana, umbral de score, fuentes degradadas—. **Eso es contexto de
> Fase 0, no deuda del MVP**: no estaba en alcance (§2.2 del PRD) y no se ha
> perdido nada.

El resultado acumulado se va escribiendo en
[docs/informe_resultados.md](docs/informe_resultados.md), organizado por H1–H5.
Es un **documento de trabajo**: cada cifra lleva de dónde salió, y lo que no se
ha medido está como sección vacía con la nota de qué falta. Al medir algo que
toque una hipótesis, actualízalo ahí además de en `pendientes.md`.

> El PRD principal v1.2 **no está en el repositorio** (pendiente 11.5). Varias
> referencias citadas en otros documentos vienen de ahí y no se pueden
> verificar. No inventes requisitos para cubrirlas.

---

## 1.1 Lo que este MVP **no** tiene

Media docena de cosas que el PRD original describe y que **no existen**. Están
aquí porque tres documentos del repositorio las siguen describiendo como
vigentes, y construir sobre ellas es trabajo perdido.

| No existe | Qué hay en su lugar | Dónde se decidió |
|---|---|---|
| **Envío de correos** y canal de notificación | El enlace se comparte a mano, fuera del sistema. No hay código que mande nada | 11.4/3 |
| **Autenticación** (enlace mágico, SSO, contraseñas) | Leer es abierto con el enlace. Calificar pide el correo y lo valida contra la lista precargada de `usuario`; quien no esté, solo visualiza | 3b · `M9-acceso` |
| **Umbral de score** y «criterio de corte» | Tope fijo de **10** municipios | `P1` |
| **Umbral de información** que excluía municipios | Está en **0**: el informe muestra el score **y en qué se apoya**, y quien lee juzga | `P1` |
| **Revisión humana previa** a la distribución | El validador determinista más la marca «no validado» (CA-M6.5) | PRD §7, riesgo aceptado |
| **Umbral de fatiga**, supresiones, clasificación Admiralty | Nada: con ~6 alertas por ciclo no hay fatiga que suprimir | PRD §2.2 |
| **Django** | **Next.js sobre Vercel**, leyendo Neon. Y **Alembic es la única autoridad del esquema**: la app no migra nada | `M9-fw` · Addendum 02 D5 |
| **Terracota y tres familias tipográficas** | Navy `#0F4761` y Aptos, de la plantilla corporativa | [Design System](docs/design-system.md) §0 |

**Y la afirmación que ordena todo lo demás:** el **scoring es código
determinista y es lo único reproducible del sistema**. Todo lo que pasa por un
modelo —qué señales se ven, qué se agrupa con qué, qué se dice— varía entre el
19% y el 26% entre pasadas idénticas. La frontera de la reproducibilidad
coincide exactamente con la frontera entre la capa determinista y la agéntica.
Cualquier cosa que deba ser reproducible tiene que estar en código.

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

**Ninguna cifra de un informe o infografía puede provenir del LLM.** Todas se
componen desde el almacén de datos. El LLM redacta; los números los pone el
código. Esta regla no admite excepción ni atajo.

### 2.3 Corolarios que sostienen H4

- El validador (M3) es **código, nunca LLM**. Si un modelo decidiera qué
  evidencia es suficiente, el experimento perdería su ancla: un agente elocuente
  parece funcionar aunque invente. **Su tasa de rechazo es la tasa de
  alucinación medida** (CA-M3.3).
- **Bing nunca es evidencia** (Addendum 01, D1). Es contexto cualitativo: llega
  sin fecha y sin URL. El validador lo rechaza por la regla R2.
- Los prompts van **versionados** y se archivan en el almacén (D7). El linaje se
  registra; no se edita un prompt en sitio.

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
│   ├── reglas/      validador.py · prefiltro.py · cobertura.py · normalizacion.py
│   └── scoring/     M5 — F1–F6, pesos, ranking del top 3, persistencia
│
├── CAPA 2 — AGENTES (LLM)
│   ├── agentes/     fuentes · clasificador · correlacionador · sintetizador
│   ├── agentes/prompts/   Versionados (D7)
│   └── grafo/       EstadoCiclo y flujo LangGraph            [aún sin código]
│
├── CAPA 3 — SUPERFICIE
│   ├── web/         Next.js en Vercel (D5 revisado)          [aún sin código]
│   └── informes/    M6 — composición y publicación del informe
│
└── TRANSVERSAL
    ├── almacen/     blob.py · modelos.py · sesion.py
    ├── observabilidad/  Langfuse, trazas de ciclo            [aún sin código]
    ├── utiles/      divipola.py
    └── config.py
```

Al añadir código, respeta la capa. Una regla de negocio no vive en un prompt, y
una llamada a LLM no vive en `reglas/`.

---

## 4. Estado real por módulo

Diagnóstico verificado sobre el árbol de trabajo el 2026-09-21. Las **210
pruebas** de `tests/` pasan.

**Nada se sobrescribe.** Insights, descartes y scores cuelgan de una *corrida*
—`corrida_agentes` y `corrida_scoring`— y cada ejecución inserta una nueva. Dos
pasadas del mismo ciclo conviven, que es lo que A6 necesita para medirse y lo
que impide que un reproceso borre lo que las gerencias calificaron.

### Dos resultados que no conviene enterrar

**La fuente sin filtrar rinde mejor que la filtrada.** RSS entra al Clasificador
**sin prefiltro** y convierte el **46%** de sus señales en insight; SECOP, que
pasa por el diccionario de obra, convierte el **40%**. El prefiltro existe para
ahorrar coste, y resulta que lo que deja pasar convierte *peor* que lo que nunca
se filtró. No prueba que haya que quitarlo —SECOP son 19.640 señales y RSS 336—
pero sí que su calibración no está seleccionando mejor señal, y refuerza A2
desde un ángulo distinto al de las subcadenas rotas.

Y cierra la duda que quedaba sobre el formato: de los 136 descartes de RSS,
**128 son `sin_implicacion_inmobiliaria`**. El Clasificador no se atraganta con
los titulares — les aplica la prueba de sustancia del prompt v4, que es lo que
tiene que hacer.

**Los 15 insights que cruzan RSS con SECOP son la primera evidencia de que la
correlación multiagente produce algo que ninguna fuente sola produce.** Es
CA-M4.1 literal —cruzar señales de categorías distintas sobre el mismo
municipio— y con una sola fuente era **literalmente imposible**: M4 no
funcionaba mal, no tenía nada que cruzar. Si algo lleva a la semana 8, es esto.

| Módulo | Estado | Detalle |
|---|---|---|
| **M1** Ingesta por API (Agente Fuentes) | ✅ Funciona | Carga los 18 municipios y las 20.030 señales; `data/territorial.db` poblada. Conectores vivos diferidos a Fase 0 |
| **Prefiltro** (apoya M2 y M5) | 🟡 Implementado, sin validar | Reduce 61,2%. El diccionario de obra produce entre 13% y 90% según el municipio — rango demasiado ancho para confiar en él (**pendiente A2**) |
| **M2** Clasificación | 🟡 Cumple CA-M2.1, no es reproducible | Prompt **v4**, lotes de 50, descartes registrados (CA-M2.5). **CA-M2.1 medido sobre el ciclo 1 completo: 95,2% y 94,9%** en dos pasadas (B2 cerrado). Pero **una de cada cinco señales cambia de destino entre pasadas idénticas** (**A6**): 19,5% aparecen en insight en una y no en la otra. No afecta al ranking —el score lee `senal_cruda`, no insights— pero sí a lo que las gerencias leen. Ver §8 y §9 |
| **M3** Validación determinista | ✅ Funciona | 7 reglas R1–R7. Tasa de rechazo 0,0% tras corregir el falso positivo de puntuación de SECOP. **Muestra pequeña: insuficiente para concluir sobre H4** |
| **M4** Correlación | 🟡 Funciona; CA-M4.3 sin ejercitar y no es reproducible | **El informe publicado se compuso con el prompt v1, y v1 es también el valor por defecto** desde el 2026-09-22. v2 añade el contexto estructural bandeado (A10) y se promovió el 21, pero **ninguna corrida se ejecutó con él**: las corridas 10, 11 y 12 llevan `version_correlacionador = v1` y `prompt_version` no tiene fila de v2. Se devolvió el valor por defecto a v1 para que un ciclo nuevo no estrene un prompt sin comparación validada; v2 es **candidata** y se elige explícitamente, pendiente de F2.3 (P-1). Con v1, **el contexto estructural no viaja**. **No es reproducible: solo el 14,1% de las convergencias se repiten entre pasadas idénticas** (A11). Salida estructurada. CA-M4.1, CA-M4.2 y CA-M4.4 verificados contra el tenant. **La evidencia la une el código, no el modelo** (ver el encabezado de `agentes/correlacionador.py`). CA-M4.3 (bucle de aprendizaje) está implementado pero **no se puede probar**: no hay ni una calificación en la base |
| **M5** Scoring y priorización | ✅ Funciona con pesos provisionales | F1–F6 de D4, normalización por cohorte, winsorizado de F4, redistribución por cobertura, **top 10** y desglose. Los 3 ciclos puntúan y persisten. **El umbral de información está apagado**: el informe muestra el score junto a los factores que lo sostienen y los que no, en vez de excluir a quien tiene pocos (P1, §7). `VERSION_ALGORITMO` en **v3**. Los **pesos definitivos** los decide Gerencia General (**pendiente A1/4**). Rigen los de `config/pesos.json`, que llevan **F4 a la mitad** por decisión de Analítica del 2026-09-21 — ver §7. Las corridas de antes y después conviven, distinguidas por `version_scoring` |
| **M6** Síntesis y distribución | 🟡 Mitad determinista hecha; falta la prosa | **`informes/composicion.py` compone el payload desde el almacén** —cifras, factores con su fuente en castellano, contexto con año, insights con evidencia— y **`informes/publicacion.py` publica**: archiva el anterior del ciclo y congela **las dos** corridas, en la misma transacción. Un solo publicado por ciclo, por índice único parcial. **Ni una cifra del LLM** (CA-M6.3), por construcción: en ese módulo no hay llamada a modelo. Falta el **Sintetizador**, que rellenará `justificacion` y `sugerencias` (CA-M6.1) para los 10 municipios — y su costo es la cifra que falta para cerrar H5. **Sin canal de notificación** en el MVP (11.4/3 cerrado). Ver M6-src, M6-orden y M6-ctx |
| **M7** Calificación | ⬜ Sin código, **sin decisiones abiertas** | Depende de M9. Decidido: se piden calificaciones **solo sobre los 3 primeros** de los 10 mostrados y el resto queda opcional, porque con 10 × 7 gerencias una tasa baja no distinguiría fatiga de desinterés (**M9-carga**); **la tasa de H2 se computa sobre la carga pedida, no sobre lo mostrado**, y el denominador hay que declararlo. Usuarios **precargados**: quien no esté en la lista no califica (**M9-acceso**) |
| **M8** Trazabilidad y observabilidad | 🟡 Parcial | Linaje de dataset, **de prompts por contenido** (D7) y trazas por agente (CA-M8.2). Falta Langfuse y el checkpointing de CA-M8.4: instalados pero **sin cablear**, no hay `grafo/` |
| **M9** Aplicativo web | ⬜ Sin código | **Next.js en Vercel**, no Django: D5 eligió Django antes de que el hosting fuera Vercel, y Django nunca se instaló (desviación registrada en Addendum 02). **El sistema no envía ningún correo.** No hay canal de notificación (11.4/3) ni módulo que lo mande: el enlace se comparte a mano, fuera del sistema. Lo que sí hay es **identificación por correo**, que es otra cosa: **sin autenticación**, leer es abierto con el enlace, y al intentar calificar se pide el correo y se valida contra `usuario` para resolver la gerencia, que es el nivel al que `calificacion` atribuye. **Los autorizados se precargan y quien no esté no califica**, así que la app nunca escribe `usuario` y el denominador de H2 se conoce antes de medir. **Lee Neon directamente**: la regla 1 de D8 protege escrituras y esquema, no lecturas, y el PRD §4.3 prohíbe la API intermedia (ver §2.1). El panel de CA-M9.13 son cuatro consultas y una página, no un CRUD — el admin de Django habría servido para editar registros, que es justo lo que CA-M9.16 prohíbe. Playwright está por verificar: descarga binarios sin firmar que la política de esta máquina bloquea |

### El nomenclátor DIVIPOLA: 1.135 entidades, y cuatro rarezas

`entidad_divipola` es una **tabla maestra de referencia**. Se carga con
`scripts/cargar_divipola.py`, es idempotente y **no amplía el universo del
MVP**: los 18 municipios siguen en `municipio` y las dos tablas no están
enlazadas a propósito. El MVP valida el mecanismo, no la cobertura (PRD §7).

Códigos como los de TerriData, para que un `join` futuro no traduzca nada:
nacional `01001`, departamento `dd000`, municipio `ddmmm`. Verificado contra el
propio TerriData: su primer indicador tiene exactamente estas 1.135 entidades.

Cuatro cosas que van a descuadrarle el conteo a alguien:

- **Son 1.102 municipios, no 1.103.** Falta San Andrés (88001); del
  departamento 88 solo está Providencia (88564).
- **Bogotá aparece solo como municipio** (11001). No existe `11000`, así que los
  departamentos son **32 y no 33**.
- **Las áreas no municipalizadas no están.**
- **63 nombres se repiten entre departamentos** y afectan a 144 municipios, el
  **13%**. Hay cuatro «La Unión» y cuatro «Buenavista». El par (departamento,
  municipio) es obligatorio; resolver por nombre suelto no es una opción.

> **No midas la atribución cruzada (A3) buscando estos 1.102 nombres en texto
> libre.** Son dos fenómenos distintos: A3 es contratación departamental
> archivada en la capital y ejecutada fuera, no colisión de nombres. Con el 13%
> de nombres ambiguos, «La Unión», «Buenavista» o «El Carmen» aparecerían por
> razones ajenas al municipio y el número saldría inflado — pasaríamos de un
> piso inútil por bajo (0,64%) a un techo inútil por alto. Esa medición
> necesita diseño propio.

### Contexto estructural: quién ve el número y quién ve el adjetivo

`contexto_municipal` trae de TerriData seis indicadores de los 1.750, uno por
municipio, para los 1.102. Se carga con `scripts/cargar_contexto.py`, que lee el
zip de 3,31 GB **por streaming** y exporta un CSV pequeño a `data/` para no
volver a tocarlo (`--desde-csv`).

**Tres capas, tres responsabilidades. No las mezcles:**

| Capa | Qué ve | Por qué |
|---|---|---|
| **Scoring** | **nada** | Son indicadores anuales: idénticos en los 3 ciclos. Es el defecto de F4, que era una constante con el 18% del peso |
| **Correlacionador** | **bandas**: «déficit alto» | Una cifra real escrita por el modelo sigue siendo una cifra escrita por el modelo (CA-M6.3). El adjetivo lo calcula código |
| **Informe** (M6) | **los números** | CA-M6.3 no prohíbe el número: prohíbe que lo escriba el modelo. Se componen por código y con su año a la vista |

Las bandas son **nacionales sobre los 1.102**, nunca sobre los 18: un adjetivo
que cambia según quién más corrió es tan poco comparable como un score que
cambia según quién más corrió. Ver `reglas/contexto.py`.

**Dos indicadores no se bandean por cuartil, y es una corrección medida.** Con
cuartiles nacionales, población y valor agregado salían **«alto» para los 18 de
18**: la mediana municipal colombiana son 14.353 habitantes y el menor de los 18
es Carepa con 51.298, así que todos viven por encima del percentil 86. Se
corrige sin tocar el principio —los cortes siguen siendo fijos y ajenos a la
cohorte—: población va por **clases de tamaño de corte fijo** y valor agregado
**per cápita**, igual que el avalúo va **por predio**.

**La regla que hace segura la concesión de dejar que el modelo enuncie la
banda:** el contexto explica una convergencia, **nunca la crea**. Es ejecutable,
no declarativa — `scripts/comparar_correlacionador.py` **falla** si v2
correlaciona más que v1, y falla si aparece en la salida una cifra que no estaba
en los insights, incluidas las cifras reales de `contexto_municipal`.

> **v1 es el valor por defecto y es lo que hay publicado.** v2 se promovió el
> 2026-09-21 tras el control —sus 40 convergencias caen dentro del rango 39-42
> que v1 produce consigo mismo, y su tipología sube a 35 frente a un máximo de 24
> en tres pasadas de v1: once puntos por encima del ruido en el efecto buscado,
> dentro del ruido en el que preocupaba— **pero la promoción se quedó en la
> constante**. Ninguna corrida se ejecutó con v2, `prompt_version` no tiene fila
> suya y el informe publicado sale de la corrida 10, que es **v1**.
>
> **Desde el 2026-09-22 `VERSION_PROMPT` vuelve a `v1`**, para que el próximo
> ciclo no estrene un prompt sin comparación validada con linaje persistido. Esa
> comparación es la subfase **F2.3** de la remediación; cuando la pase, v2 vuelve
> a ser el valor por defecto.
>
> **v2 no se borra**: sigue en `prompts/correlacionador_v2.md` y se elige
> explícitamente con `version="v2"`. Y `tests/test_version_prompt.py` falla si la
> constante cambia sin actualizar `docs/decisiones-remediacion.md`, que es donde
> se decide.
>
> Cambiar `VERSION_PROMPT` **no republica nada**: hay que correr el ciclo y
> publicar.
>
> `VERSIONES_CON_CONTEXTO` decide qué versiones reciben el bloque, y solo está
> v2. Con v1 por defecto, **el contexto estructural no viaja hoy** — igual que
> en la corrida 10, la del informe publicado. Si añades una versión nueva del
> prompt, métela ahí o el contexto dejará de viajar en silencio.

### Pendientes que frenan el avance

- ~~**B2**~~ — cerrado. CA-M2.1 medido sobre el **ciclo 1 completo**: 95,2% y
  94,9% en dos pasadas, y 95,3% en el ciclo 3 con RSS. Muy por encima del 85%
  exigido y **estable entre pasadas**, lo que vuelve más llamativo que el destino
  de las señales individuales no lo sea (A6).
- **A4** — tras cuatro versiones del prompt, el Clasificador sigue partiendo un
  mismo frente de obra en varios insights (cuatro de pavimentación en Carepa).
  Infla el conteo y degrada el informe.
- **A3** — atribución geográfica (R8). El 0,5% de las señales SECOP nombran un
  municipio distinto al que están archivadas, y entran municipios fuera del MVP
  (caso Frontino). **El nomenclátor ya está cargado** —`entidad_divipola`, 1.135
  entidades— pero eso **no reabre A3**: buscar 1.102 nombres en texto libre
  inflaría la cifra por los 63 homónimos. Sigue fuera de alcance del MVP y la
  medición necesita diseño propio. Ver §4.
- ~~**B4**~~ — cerrado el 2026-09-17. **H5 tiene base y el costo no es una
  barrera**: USD 39/año el piloto, USD 2.160/año los 1.103 municipios. Tarifas
  en `config/tarifas.json`, cálculo en `scripts/estimar_costo.py`. El 89% del
  gasto es el Correlacionador, y el 84% del total es solo su salida de
  razonamiento. **No cuenta el Sintetizador (M6), que también corre sobre
  gpt-5** y podría no ser menor.
- **A5** — de las dos decisiones de M5 que D4 no cubre, el **umbral de
  información** dejó de ser una decisión: **está apagado** desde el 2026-09-21 y
  se sustituyó por mostrar el score con sus factores (P1). Sigue abierta la
  **escala común**: min-max por cohorte es ordinal dentro de su corrida y no
  comparable entre ciclos. Ver §7.

---

## 5. Problemas abiertos en el repositorio

*Cerrado 2026-09-22:* la tabla «Estado» del README estaba desactualizada —
declaraba M2 y M3 como pendientes— y además convivía con un bloque de estado más
nuevo, dos secciones contradiciéndose. Ahora el README abre con el estado
vigente y §4 de este archivo lleva el detalle por criterio.

*Cerrado 2026-09-17:* Alembic estaba instalado pero sin inicializar. Ya existe
`alembic/` con la migración de línea base `949a8ff9e15d`, la ingesta migra en
vez de llamar a `create_all` y la base de desarrollo quedó estampada en `head`.
Ver §6.1.

---

## 6. Entorno

El intérprete vive **fuera del repositorio**, porque la política corporativa
impide ejecutar binarios desde `Downloads`. `python` a secas resuelve al stub de
Microsoft Store y no sirve.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py scripts\cargar_snapshot.py                        # M1 ingesta
& $py scripts\correr_ciclo.py --ciclo 1 --municipio 05147   # M2→M3→M4, gasta tokens
& $py scripts\calcular_scores.py --ciclo 1              # M5, no gasta tokens
& $py scripts\verificar_llm.py                          # conexión al tenant
& $py -m pytest -q                                      # pruebas
```

### A qué base apunta: `DATABASE_URL`

Una sola variable decide contra qué base corre todo, y **no hay ninguna URL de
entorno escrita en el código**. Se acepta el nombre antiguo `URL_BASE_DATOS` con
menos prioridad, así que si borras `DATABASE_URL` **vuelve a SQLite sin avisar**.

```powershell
$env:DATABASE_URL = "sqlite:///data/territorial.db"                       # local
$env:DATABASE_URL = "postgresql://...neon.tech/territorial?sslmode=require&connect_timeout=3"
```

**Neon está poblada desde el 2026-09-21** con las mismas 29.969 filas que la
local, copiadas por `scripts/copiar_base.py` y comprobadas con
`scripts/verificar_copia.py`. Tres cosas que cuesta descubrir solas y están en el
[README](README.md):

- **Neon publica dos hosts.** El `-pooler` va por PgBouncer y **no sirve para
  migrar**; `exigir_directa()` se niega a arrancar por ahí, y lo comprueban los
  dos caminos a Alembic (código y línea de comandos).
- **Si conectar se cuelga sin error, es IPv6.** El DNS de Neon devuelve IPv6
  primero y esta red no la rutea, así que libpq agota el timeout del sistema
  antes de caer a IPv4. Por eso la cadena lleva **`&connect_timeout=3`**, y va
  permanente.
- **Para la app en Vercel la cadena será la del pooler**, no esta: las funciones
  serverless abren muchas conexiones cortas. Son dos cadenas para dos usos
  opuestos.

`correr_ciclo.py` sin `--municipio` procesa los 18, que son 18 llamadas al
Clasificador más las del Correlacionador. **Prueba siempre primero con uno.**
`--seco` corre y revierte.

Scripts de calibración: `medir_prefiltro.py`, `probar_clasificador.py`
(prefiltro → Clasificador → Validador en miniatura) y `comparar_prompts.py`,
que mide dos versiones de prompt sobre el mismo lote.

### 6.1 Migraciones (regla 2 de D8)

```powershell
& $py -m alembic current                              # en qué revisión está
& $py -m alembic upgrade head                         # aplicar pendientes
& $py -m alembic revision --autogenerate -m "motivo"  # tras tocar modelos.py
& $py -m alembic check                                # ¿el esquema y los modelos concuerdan?
& $py scripts\generar_contrato_ts.py                  # tras tocar calificacion o seguimiento
& $py scripts\generar_contrato_ts.py --check          # ¿el contrato TS concuerda?
```

Cuatro cosas que ahorran un rato:

- **`aplicar_migraciones()` en `almacen/sesion.py` es el camino desde código.**
  La ingesta lo llama; ya no existe `crear_esquema`. `create_all` quedó
  prohibido porque crea lo que falta y calla ante lo que cambió.
- **La URL no está en `alembic.ini`.** Sale de `DATABASE_URL` vía
  `Config.url_base_datos` y `env.py`. No la escribas en el `.ini` o local y nube
  se separarán sin aviso.
- **Hay dos caminos hasta Alembic y los dos comprueban el host.**
  `aplicar_migraciones()` desde código y `alembic upgrade head` por línea de
  comandos, que resuelve el motor en `env.py`. Los dos llaman a
  `exigir_directa()`: por el endpoint `-pooler` no se migra. Durante un tiempo
  solo el primero comprobaba, que era justo el que no se usa a mano.
- **`render_as_batch=True` está activo**, y es obligatorio: SQLite no sabe
  eliminar una columna ni cambiarle el tipo con un `ALTER TABLE` normal.
- **`--autogenerate` compara contra la base a la que apuntes.** Si esa base ya
  tiene las tablas, la migración sale vacía. Genera contra una base limpia:
  `URL_BASE_DATOS="sqlite:///$env:TEMP\vacia.db"`.

Corre `alembic check` antes de abrir una PR que toque `modelos.py`: falla si el
modelo y las migraciones se desincronizaron.

### El `upgrade` no prueba nada. `alembic check` sí

**Corre `alembic check` después de cada `upgrade`.** No es redundante: es la
verificación real.

El 2026-09-18 una migración imprimió `Running upgrade ... -> a6ac249fcec9` y
**falló a continuación**, dejando la base en la revisión anterior. La causa fue
un `create_foreign_key(None, ...)` que autogenerate rinde sin nombre y que en
modo batch revienta; el error salió por stderr y un `grep` del comando se lo
comió. El log decía que había subido y no había subido.

`alembic check` compara el esquema real contra los modelos, así que contradice
al `upgrade` cuando el `upgrade` miente. Fue lo único que lo detectó.

Y **nombra siempre las claves foráneas** en las migraciones. Autogenerate las
deja sin nombre y avisa en un `UserWarning` fácil de pasar por alto; en SQLite,
donde todo pasa por modo batch, sin nombre no funcionan.


**Ni la ingesta ni la capa determinista necesitan la clave** — solo los agentes.
`.env` nunca se sube a git; `.env.example` sí.

### Notas del tenant, verificadas por llamada real

- Cliente `OpenAI` con `base_url`, **no** `AzureOpenAI`. `api_version` no aplica
  en esta superficie.
- Despliegues asignados: clasificador `gpt-5.4-mini`, correlacionador `gpt-5`,
  sintetizador `gpt-5`. El criterio salió de una medición de tokens, no de una
  preferencia.
- Un `max_output_tokens` bajo **corta a los modelos de razonamiento antes de que
  emitan texto, y la llamada vuelve vacía sin error.** El techo está en **16384**
  para todos los agentes (`max_tokens_salida` y `max_tokens_salida_razonamiento`
  en `config.py`). Empezó en 4096 y hubo que subirlo dos veces: ver §9.

---

## 7. Dos decisiones de M5 que no vienen de D4

Están implementadas, documentadas en el código y son configurables, pero
**nadie las ha aprobado**. Si tocas el scoring, léelas antes.

**La escala común de los factores.** D4 fija cómo se calcula cada factor y
cuánto pesa, pero no en qué escala se suman, y sin eso los pesos no significan
nada: F1 vive en [0, 1], F4 va de -65% a +900% y F2 son miles de millones de
pesos. Se normaliza **min-max dentro de la cohorte del ciclo**. El costo: los
scores **no son comparables entre ciclos**, solo dentro de uno. Para el top 3
por ciclo da igual; para una serie temporal del score, habría que rehacerlo.

**El umbral de información, y por qué hoy está apagado.** D4 manda redistribuir
el peso de los factores sin cobertura para no castigar al municipio truncado.
Sobre el snapshot aparece el efecto contrario: en el ciclo 3, Ibagué tiene **3 de
239 días cubiertos**, conserva solo F4 y F5, y sale **primero con 0,8560**.
Armenia igual, con 0 días. La redistribución acaba premiando al que no tiene
datos, y encima con ELIC, que es constante en los 3 ciclos.

Durante unos días eso se resolvió **excluyéndolos** del informe por debajo del
50% de peso respaldado. **Desde el 2026-09-21 se resuelve al revés: exponiendo.**
`Config.umbral_informacion` está en **0** y el informe muestra el score **junto a
los factores que lo sostienen y los que no** — Ibagué aparece primero y a su lado
se lee «apoyado en F4+F5». Quien lee juzga; el sistema no decide quién merece
verse.

Lo que forzó el cambio fue un caso que la exclusión no sabía tratar:
**Barranquilla tiene 12 insights de prensa que pasaron el validador** y quedaba
invisible. Y bajar el umbral no servía: las fracciones informadas del ciclo 3 son
**20,10% o 77,80%, sin nada en medio**, así que cualquier umbral por debajo de
20,10% no dispara nunca y cualquiera por encima se comporta como el 50%. No había
punto intermedio; la decisión era guarda o no guarda.

**El mecanismo se conserva entero**: `fraccion_informada` se sigue calculando y
persistiendo como auditoría, y subir el umbral lo reactiva. Hay pruebas de las
dos cosas.

**Y el tope del informe pasa de 3 a 10** (`Config.tope_top`). CA-M5.4 decía «top
3 fijo»: es una desviación deliberada. Sigue siendo un número fijo y no un «todos
los que pasen de X», que es lo que ese criterio quería evitar.

> **Al usuario final no se le enseñan códigos de factor.** «Apoyado en F4+F5» es
> correcto y no significa nada para una gerencia. Al presentarlo hay que traducir
> a **fuentes**, y no es cosmético: F1, F2 y F3 salen los tres de SECOP, así que
> cinco factores colapsan en tres fuentes. `F1/F2/F3` → contratación pública ·
> `F4` → licencias de construcción · `F5` → prensa · `F6` → calificaciones de las
> gerencias. «F4+F5» se lee **«licencias y prensa, sin contratación»**, y ahí lo
> que falta informa más que lo que hay. Pendiente **M6-src**; el código interno no
> cambia.

**La fracción informada mide dato, no puntuación** (decisión 2 de Analítica,
2026-09-21). `ValorFactor` separa `disponible` —¿el factor puntúa?— de
`hay_dato` —¿existe el dato subyacente?—. Coinciden salvo en un caso: el piso
de área de ELIC, donde el dato existe pero el porcentaje no es fiable sobre una
base tan pequeña. Antes eso descontaba dos veces: del score, que es correcto, y
de la fracción informada, que no. El piso sigue sin puntuar y sin entrar en la
escala de la cohorte; lo único que cambia es que cuenta como informado y el
crudo se conserva para el informe.

### Los pesos que corren no son los de `pesos.py`

`config/pesos.json` **está en el repositorio** y manda sobre
`PESOS_POR_DEFECTO`. Lleva **F4 a la mitad** —15% en el ciclo 1, 9% en los
otros dos, con lo liberado repartido en proporción— aprobado por Analítica el
2026-09-21.

F4 es **idéntico en los tres ciclos para los 18 municipios**: Apartadó marca
−43,5% en el 1, en el 2 y en el 3. No es un factor lento, es una constante por
municipio, y con el 18% del peso desplazaba a todos de forma fija sin que nadie
pudiera subir ni bajar por él. A la mitad y no a cero porque con F4 en cero F5
pasa a dominar el ciclo 3 con el 37% —donde SECOP está truncado— y Barranquilla
sale primera con un 1,0000 sacado de un solo factor: la patología se mudaba, no
se arreglaba.

Las pruebas **no** leen ese archivo: `tests/conftest.py` las fija a los pesos de
D4. Si no, cada recalibración de Gerencia rompería el suite por algo que no es
un defecto.

### La trampa que ya ha aparecido seis veces

**Ausencia de SECOP no es ausencia de actividad.** Está escrito en D4 y aun así
el sistema lo ha violado seis veces, siempre igual: SECOP es la fuente más rica,
así que todo acaba calculándose desde ella, y el municipio que no contrata
obra queda indistinguible del que no existe.

1. **F5** dividía por días cubiertos, que salían solo de fechas de SECOP.
   Barranquilla con 47 noticias se quedaba sin densidad mediática (A7).
2. **El corte de cohorte** propagaba el NULL al conjunto si a un municipio le
   faltaba SECOP, dejando el ciclo 3 sin fecha de auditoría (`_corte`).
3. **El piso de área de ELIC** se descontaba de la fracción informada, como si
   una base pequeña fuera un dato ausente (A8).
4. **El prefiltro** marca como obra los contratos de servicios profesionales
   que hablan de obra sin serlo, y no ve nada que no tenga forma de objeto
   contractual (A2).
5. **RSS no llegaba al Clasificador**: una de las tres barreras era el
   diccionario de obra, calibrado sobre objetos de SECOP (B7).
6. **La fracción informada** es casi toda peso derivado de SECOP. Al bajar F4,
   los cinco municipios truncados del ciclo 3 pasan de 28% a **20%** informados
   — Barranquilla entre ellos, con 12 insights de prensa que pasaron el
   validador. El sistema sabe cosas de Barranquilla y su propia métrica dice
   que no sabe nada (P1).

Antes de escribir cualquier cosa que divida, filtre o cuente, pregúntate qué
pasa con el municipio que tiene noticias y no tiene contratos.

## 8. Carga inicial y operación no son lo mismo

El snapshot cubre **374 días** y sus tres ciclos duran **51, 84 y 239 días**. No
son quincenales, pese a que el PRD los llame así: D2 los partió por terciles de
volumen SECOP. **El ciclo 3 son 17 quincenas.**

| | Señales tras el prefiltro |
|---|---|
| Carga inicial (el snapshot, un año) | **7.628** |
| Una quincena en operación | **~615** |

La tasa real agregada es de 43,9 señales al día en los 18 municipios. En régimen
normal **13 de los 18 no llegan a 20 señales por quincena**; solo Barranquilla
(204), Armenia (92), Pereira (61), Cartagena (50) e Ibagué (48) pasan de 40.

Dos consecuencias, y la segunda es la que importa:

- Dimensionar el troceo con las cifras del snapshot sobredimensiona el sistema
  por un factor de 12.
- **H5 no se puede extrapolar con los totales del snapshot.** Multiplicar el
  costo de un ciclo del MVP por 1.103 municipios sobreestima el régimen
  permanente en un orden de magnitud. Para el pendiente B4 hay que usar la tasa
  diaria por 14, no los totales. Medido: el Clasificador gasta ~282 tokens de
  entrada y ~111 de salida por señal.

## 9. Tres cosas que cortan una llamada sin avisar

**El techo de tokens puede depender del agente, aunque hoy no difiera.**
`cliente.techo_de()` devuelve `max_tokens_salida_razonamiento` para los agentes
de `AGENTES_QUE_RAZONAN` (Correlacionador y Sintetizador) y `max_tokens_salida`
para el resto. **Ambos valen 16384 hoy**, así que la función no cambia nada: se
conserva como el punto donde separarlos si vuelven a divergir. Si añades un
agente sobre un modelo de razonamiento, mételo en ese conjunto.

Con el techo en 4096 el Correlacionador se cortó en seco en Barranquilla —6
insights sobre 5 categorías— y **la llamada volvió vacía y sin error**, que es
la forma más difícil de diagnosticar.

*Detalle menor pendiente:* el Clasificador llama a `cfg.max_tokens_salida`
directamente en vez de a `techo_de("clasificador")`. Hoy da el mismo número, así
que no cambia nada; si algún día los valores divergen, ese es el sitio que se
queda atrás.

**El Clasificador se truncaba, y fallaba distinto** (pendiente B5, cerrado). Su
techo era de texto, no de razonamiento: a ~111 tokens de salida por señal, 40
señales daban 4.243 y el corte estaba en 4.096, así que el JSON llegaba cortado
a media cadena. Ahora el techo es 16.384 y `Config.senales_por_lote` trocea de
50 en 50. **No subas el lote por velocidad**: con 100 señales cabe de sobra pero
4 de 7 insights salieron sin categorizar. El límite práctico es la calidad, no
los tokens, y se degrada en silencio — el JSON sigue siendo válido.

**El Clasificador no es reproducible entre corridas.** El mismo lote de 20
señales de Carepa dio 3 insights una vez y 6 otra. Importa para H4 y para
cualquier medición de prompts: `comparar_prompts.py` mide una muestra de uno.

## 10. Al cambiar el prompt de un agente

No lo afines a ojo. Crea una versión nueva en `agentes/prompts/`, córrela contra
la anterior sobre el mismo lote con `comparar_prompts.py` y reporta las métricas
(reducción, tasa de rechazo, señales sin contabilizar, insights duplicados,
tokens). Las versiones que resultan peores **se conservan como registro**: v3
está en el repo porque documenta una hipótesis que resultó incorrecta.
