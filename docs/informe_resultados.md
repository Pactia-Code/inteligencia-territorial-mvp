# Informe de resultados — compuerta go/no-go

**Documento de trabajo. No es el informe final.** Se va llenando a medida que
se mide; hoy hay dos secciones vacías a propósito y una parcial, cada una con la
nota de qué falta y de qué depende.

**Actualizado:** 2026-09-21 · **Fase -1** · decide el paso a Fase 0

> Última medición incorporada: **reproducibilidad de M4** (corridas 11 y 12).

---

## Cómo leer las cifras

**Ninguna cifra de este documento la escribió un modelo.** Cada una lleva su
procedencia entre corchetes para que se pueda volver a comprobar:

| Marca | Significa |
|---|---|
| `[BD]` | Sale de una consulta a `data/territorial.db`. |
| `[pendientes]` | Registrada en [pendientes.md](pendientes.md), con la fecha en que se midió. |
| `[CLAUDE]` | Registrada en [CLAUDE.md](../CLAUDE.md). |
| `[PRD]` | Enunciado o criterio del [PRD](prd.md) — no es un resultado. |

Donde no hay medición, la sección dice **qué falta**, no una estimación.

### La regla de decisión, para tenerla delante

`[PRD §11]`

- **GO** — H2 y H4 cumplidos, y al menos dos de H1/H3/H5 en rango aceptable.
- **GO CONDICIONADO** — H4 cumplido pero H2 bajo. El problema es de adopción,
  no de tecnología.
- **NO-GO** — H4 incumplido, o H1 y H3 ambos por debajo del criterio.

Es decir: **H4 manda y H2 es la otra condición necesaria.** Hoy H4 tiene
evidencia parcial y H2 no tiene ninguna, y eso ya dice dónde está el riesgo.

---

## 0. Estado de las cinco hipótesis

| | Hipótesis | Criterio `[PRD §1]` | Estado hoy |
|---|---|---|---|
| **H1** | Los insights son relevantes para las gerencias | ≥30% con promedio ≥4 | ⬜ **Sin medir** — cero calificaciones |
| **H2** | Las 7 gerencias califican de forma sostenida | ≥50% promedio en ciclo 3 | ⬜ **Sin medir** — cero calificaciones |
| **H3** | Las fuentes públicas contienen señal accionable | ≥60% sobrevive al validador | 🟢 **Criterio cumplido con holgura**, cobertura parcial |
| **H4** | La cadena preserva la trazabilidad | 100%, **bloqueante** | 🟡 **Sin contraejemplo, muestra corta** |
| **H5** | El costo es viable a escala nacional | Extrapolación documentada | 🟢 **Documentada y con margen** |

**Lo que hay que entender de este cuadro:** las dos hipótesis que la regla de
decisión hace necesarias —H2 y H4— son justamente las dos que no están
resueltas, y por motivos distintos. H2 no depende de la ingeniería sino de que
exista el aplicativo y de que las gerencias respondan. H4 no tiene ningún
contraejemplo, pero tampoco una muestra que permita afirmarlo.

### Lo que sí está construido y corrido

`[BD]` Conteo por tabla:

| | |
|---|---|
| Municipios | **18** |
| Señales cargadas | **20.030** — SECOP II 19.640 · RSS 336 · Bing 54 |
| Ventanas de los 3 ciclos | **51, 84 y 239 días** |
| Corridas de agentes | **10** (2 completas del ciclo 1, 1 completa del ciclo 3) |
| Corridas de scoring | **21** |
| Insights persistidos | **1.132** |
| Descartes registrados | **5.731** |
| Trazas de agente | **266** |
| Calificaciones | **0** |
| Informes publicados | **0** |

**Nada se sobrescribe.** Cada ejecución inserta una corrida nueva, así que las
21 corridas de scoring y las 10 de agentes conviven y se pueden comparar entre
sí. Eso es lo que permitió medir A6, y lo que impide que un reproceso borre lo
que las gerencias hayan calificado. `[CLAUDE §4]`

---

## H1 — Los insights son relevantes para las gerencias

> ≥30% de insights con promedio ≥4 en la calificación de las 7 gerencias.

### ⬜ Sin medir

`[BD]` La tabla `calificacion` tiene **0 filas**, y `informe` y `usuario`
también. No hay nada que promediar.

**Qué falta, y de qué depende:**

1. **M7 (calificación) y M9 (aplicativo web) no tienen código.** `[CLAUDE §4]`
   Django no está instalado ni tiene versión fijada. Sin vista de informe y sin
   formulario de calificación no hay H1 que medir, y el PRD lo dice: son lo
   último que se sacrifica si hay retraso. `[PRD §7]`
2. **Las hojas de revisión del equipo** —5 personas, 45 insights— están
   repartidas y sin devolver. No sustituyen a H1, porque son 5 revisores y no
   las 7 gerencias, pero dan la primera lectura de si los insights son
   correctos.

### Lo que ya se sabe, y condiciona cómo habrá que leer H1

**No existe *el* conjunto de insights del ciclo. Existe una muestra de
resultados posibles.** `[pendientes A6]`

Dos pasadas del mismo ciclo, con la misma cohorte de 18 municipios y el mismo
prompt verificado, producen conjuntos distintos:

| | Corrida 7 | Corrida 8 |
|---|---|---|
| Insights `[BD]` | **344** | **365** |
| Evidencias `[BD]` | 1.140 | 1.160 |

Y señal a señal `[pendientes A6]`:

- **22,4%** de las señales cambian de destino entre las dos pasadas.
- **543 (19,5%)** aparecen dentro de un insight en una pasada y no en la otra.
- **Entre el 25% y el 50%** del contenido del informe del top 3 depende de qué
  pasada se publicó, según se use el criterio laxo o el estricto.

Y **lo mismo pasa un eslabón más adelante**: el Correlacionador, con el mismo
prompt y los mismos insights, solo reproduce el **14,1%** de sus convergencias
(A11). La inestabilidad se compone sobre dos agentes encadenados.

**Consecuencia para H1:** el criterio «≥30% con promedio ≥4» hay que leerlo
**con banda de error**, porque lo que se califica es una muestra. Si el
resultado cae cerca del 30%, la compuerta no se puede decidir sobre esa
diferencia: otra pasada del mismo ciclo habría dado otro número. **La compuerta
no debe decidirse sobre márgenes estrechos en H1.**

---

## H2 — Las 7 gerencias califican de forma sostenida

> ≥50% de tasa de respuesta promedio en el ciclo 3.

### ⬜ Sin medir

`[BD]` Cero calificaciones y cero usuarios.

**Qué falta:**

1. **M7 y M9**, igual que H1. Deciden **Next.js sobre Vercel, sin
   autenticación**: se pide el correo antes de calificar y se resuelve la
   gerencia, que es el nivel al que `calificacion` atribuye y el que H2 necesita
   (`[pendientes M9-fw]`).
2. **El canal de notificación sigue sin decidir.** `[pendientes 11.4/3]` Se
   diseñó correo con enlace profundo; el PRD §2.2 excluye Teams.
3. **El compromiso de las 7 gerencias de calificar 3 ciclos no está
   confirmado.** `[pendientes 5]` Es una decisión de Gerencia General, no
   técnica, y es la dependencia crítica: **H2 es condición necesaria para el
   GO** y no hay nada que la ingeniería pueda hacer para cumplirla.

**Riesgo a señalar en la compuerta:** H2 es la única hipótesis necesaria cuyo
resultado no depende del sistema. Conviene que la fecha en que se pide el
compromiso no sea la misma semana en que se mide.

### Cómo se calculará la tasa, y por qué importa decirlo

`[pendientes M9-carga, decidido 2026-09-21]`

El informe pasa a mostrar **10 municipios**, pero la calificación **pedida** es
solo sobre los insights de los **3 primeros**. El resto queda calificable de
forma opcional.

**La tasa de respuesta se computa sobre la carga pedida, no sobre lo mostrado.**
No es un tecnicismo: con 10 municipios × 7 gerencias, una tasa baja **no
permitiría distinguir fatiga de desinterés**, que es justo la distinción que H2
existe para dar. Si el denominador fuera lo mostrado, un 40% podría significar
«no les interesa» o «era demasiado», y son dos conclusiones opuestas para la
Fase 0: la primera cuestiona el producto, la segunda solo el formato.

Lo calificado de forma opcional se cuenta **aparte**, y es señal de interés, no
de cumplimiento. Al publicar el resultado de H2 hay que decir explícitamente cuál
fue el denominador, o el número no será interpretable.

**El denominador se conoce antes de medir**, y eso no es menor: los usuarios
autorizados se precargan y quien no está en la lista no puede calificar
(`[pendientes M9-acceso]`). Así el universo queda fijado de antemano en vez de
descubrirse al final, que es la forma habitual de que una tasa de respuesta
acabe siendo indiscutible y a la vez incomparable.

### La atribución es declarativa, y eso hay que decirlo al publicar H2

`[pendientes M9-acceso, decidido 2026-09-22]`

No hay autenticación: se pide el correo antes de calificar y se resuelve la
gerencia contra la lista precargada. **Cualquiera puede teclear un correo
ajeno.** El riesgo viene de la decisión de no autenticar, no de recordar el
correo en cookie —sin cookie el riesgo sería idéntico y además se romperían los
≤2 clics de CA-M7.1—.

La consecuencia concreta al leer la tasa: **un 80% en una gerencia podría ser
una persona calificando por dos.** No invalida H2 ni obliga a descartar el
número, pero convierte la tasa en un límite superior de participación real, no
en una medida exacta. Si el resultado de H2 cae cerca del 50% exigido, esa
holgura importa tanto como la de H1.

---

## H3 — Las fuentes públicas contienen señal accionable

> ≥60% de insights que sobreviven al validador.

### 🟢 El criterio se cumple con holgura. La cobertura de fuentes es parcial.

Hay que separar dos cosas que al leer H3 se confunden.

**El criterio del PRD está medido y cumplido.** Supervivencia al validador
`[pendientes B7, medido sobre el ciclo 3]`:

| Fuente | Sobrevive al validador | Criterio |
|---|---|---|
| RSS | **98% y 100%** | ≥60% |
| SECOP II | **99%** | ≥60% |

El validador es **código determinista, nunca un LLM** `[CLAUDE §2.3]`, así que
esta cifra es una medición y no la opinión de un modelo sobre sí mismo.

**La cobertura es de dos fuentes, no de tres, y la precisión importa.**
`[CLAUDE §1]` El PRD §2.3 lista SECOP II, el feed de noticias y TerriData, lo
que induce a leer H3 como «2 de 3». Pero **TerriData no es una fuente
comparable**: es contexto estructural —población, economía, vivienda—, no señal
de coyuntura, y no podría originar insights aunque estuviera cargada. De las
fuentes que **sí pueden originar insights**, las dos están evaluadas.

Bing queda fuera por decisión, no por falta de medición: llega sin fecha y sin
URL, el validador lo rechaza por la regla R2 y D1 lo declara contexto
cualitativo. `[CLAUDE §2.3]`

### El resultado que más pesa aquí: la fuente sin filtrar rinde mejor

`[pendientes B7, ciclo 3]`

| Fuente | ¿Pasa por el prefiltro? | Convierte en insight |
|---|---|---|
| RSS | **No** | **46%** |
| SECOP II | Sí, diccionario de obra | **40%** |

El prefiltro existe para ahorrar coste. Resulta que **lo que deja pasar
convierte peor que lo que nunca se filtró.** No prueba que haya que quitarlo
—SECOP son 19.640 señales y RSS 336 `[BD]`— pero sí que su calibración no está
seleccionando mejor señal, y refuerza el pendiente A2 desde un ángulo distinto
al de los términos rotos por subcadena.

Y cierra la duda sobre el formato: de los 136 descartes de RSS, **128 son
`sin_implicacion_inmobiliaria`** `[pendientes B7]`. El Clasificador no se
atraganta con los titulares; les aplica la prueba de sustancia.

### La correlación multiagente produjo algo que ninguna fuente sola produce

**15 insights cruzan RSS con SECOP** `[pendientes B7]`: prensa y contratación
sobre el mismo hecho. Es CA-M4.1 literal, y con una sola fuente era
**literalmente imposible** — M4 no funcionaba mal, no tenía nada que cruzar.

La corrida 10 (ciclo 3, pipeline p2) produce **364 insights sobre 1.382
evidencias** `[BD]`, frente a las 1.140 evidencias de la corrida 7 con solo
SECOP.

### Qué falta para cerrar H3

- Medir la supervivencia al validador sobre los **tres ciclos**, no solo el 3.
- La tasa de rechazo del validador es **0,0%** `[CLAUDE §4]`, pero sobre una
  **muestra pequeña**. Un rechazo del 0% no distingue «el modelo no alucina» de
  «el validador no aprieta», y esa distinción es la que H4 necesita.

---

## H4 — La cadena preserva la trazabilidad · **BLOQUEANTE**

> 100% de insights con evidencia completa hasta la fuente.

### 🟡 Sin contraejemplo, pero la muestra no permite afirmarlo

**Lo que está construido y verificado:**

- **Linaje de dataset y de prompts.** Los prompts se anclan por hash de
  contenido; editar uno sin subir la versión levanta `PromptDivergente`.
  `[CLAUDE §2.3, D7]`
- **Trazas por agente** (CA-M8.2): **266 trazas** con tokens de entrada, de
  salida, duración y hashes de entrada y de salida. `[BD]`
- **Persistencia append-only.** Insights, descartes y scores cuelgan de una
  corrida y nada se sobrescribe, así que un informe publicado se puede
  reconstruir tal como se publicó. `[CLAUDE §4]`
- **Los descartes se registran** (CA-M2.5): **5.455 declarados** y **276 no
  declarados** `[BD]`. Los 276 son señales que el modelo no mencionó ni en
  insights ni en descartes, y **quedan registradas como tales** en vez de
  desaparecer sin rastro.
- **Ninguna cifra del informe viene del LLM** (CA-M6.3): el score se compone
  desde el almacén. `[CLAUDE §2.2]`
- **La evidencia la une el código, no el modelo**, en el Correlacionador.
  `[CLAUDE §4]`

**Lo que falta:**

1. **La tasa de rechazo del validador es 0,0% sobre una muestra pequeña.**
   `[CLAUDE §4]` Insuficiente para concluir.
2. **Langfuse y el checkpointing de CA-M8.4 están instalados pero sin cablear.**
   No existe `grafo/`. `[CLAUDE §4]`
3. **No hay informes publicados**, así que la cadena completa
   insight → informe → calificación no se ha recorrido entera ni una vez.

### A6 toca H1, no H4

Conviene dejarlo escrito porque es el malentendido fácil. Que dos pasadas
produzcan insights distintos **no rompe la trazabilidad**: cada insight de cada
pasada conserva su evidencia completa hasta la fuente, y las dos pasadas
conviven en el almacén. Lo que queda con banda de error es **qué** se publica,
no si se puede auditar. `[pendientes A6]`

**El pendiente A9 es la consecuencia práctica:** con dos pasadas del mismo
ciclo, nada marca hoy cuál es la canónica. No muerde en el scoring —que lee
`senal_cruda`, no insights— ni en el Correlacionador. Muerde solo al publicar, y
el informe ya sabe congelar su corrida.

---

## H5 — El costo es viable a escala nacional

> Tokens y costo por ciclo, extrapolados a 1.103 municipios, documentados.

### 🟢 Documentada, y el costo no es la barrera

`[pendientes B4, cerrado 2026-09-17]` Con tarifas del tenant (Global Standard,
TRM 3.128,46), en `config/tarifas.json` y calculado por `scripts/estimar_costo.py`:

| | USD/año |
|---|---|
| Piloto (18 municipios) | **39** |
| Nacional (1.103 municipios) | **2.160** |

**El Correlacionador es el 89% del gasto**, y su salida de razonamiento sola es
el 84% del total. Batch (−50%) y bajarlo a mini (−71%) se acumulan hasta −86%.

### Consumo real medido

`[BD]` Agregado de `traza_agente`:

| Agente | Modelo | Llamadas | Tokens entrada | Tokens salida | Minutos |
|---|---|---|---|---|---|
| Clasificador | gpt-5.4-mini | 215 | 1.759.734 | 459.192 | 39,5 |
| Correlacionador | gpt-5 | 51 | 140.172 | 264.562 | 48,6 |

Del ciclo 1, que se corrió **dos veces** `[BD]`: 170 llamadas, 1.276.657 tokens
de entrada y 441.861 de salida en 53,6 minutos — o sea **~638K de entrada y
~221K de salida por pasada, ~27 minutos cada una**. Concuerda con los ~628K y
217K y los 27 y 25,5 minutos registrados por pasada. `[pendientes B2]`

### La corrección que más mueve H5

**La extrapolación previa estaba inflada al doble, y por una razón
estructural.** `[CLAUDE §8]`

El snapshot cubre 374 días y **no es un ciclo de operación**:

| | Señales tras el prefiltro |
|---|---|
| Carga inicial (el snapshot, un año) | **7.628** |
| Una quincena en operación | **~615** |

Dimensionar con las cifras del snapshot **sobredimensiona por un factor de 12**.
Para extrapolar H5 hay que usar la tasa diaria por 14, no los totales:
multiplicar el costo de un ciclo del MVP por 1.103 municipios sobreestima el
régimen permanente en un orden de magnitud.

### Qué falta para cerrar H5

- **El Sintetizador (M6) no está contado**, y corre sobre gpt-5. `[pendientes B4]`
  Podría no ser menor: el otro agente sobre gpt-5 es el 89% del gasto actual.

---

## Hallazgos no previstos

Ocho cosas que no estaban en ninguna hipótesis y que cambian cómo hay que leer
el resto.

### 1. El Clasificador no es reproducible, y la causa no era la que se suponía

`[pendientes A6, medido sobre el ciclo 1 completo]`

**El ranking es estable y el contenido no.** Esa asimetría es el hallazgo:

- **Top 3 idéntico** entre las dos pasadas, y **ningún municipio cambia de
  puesto**. El scoring lee `senal_cruda`, no insights, así que es **inmune a A6
  por construcción**.
- Pero **entre el 25% y el 50%** del contenido del informe del top 3 cambia.

Las gerencias verían **los mismos municipios con razones distintas.**

**La causa no es el volumen.** La hipótesis se descarta con los datos:
Barranquilla, 897 señales, voltea el **10%**; Funza, 40 señales, voltea el
**87,5%**. Lo que predice la inestabilidad es la **densidad de contratos de
servicios profesionales que hablan de obra sin serlo**.

Esto se corrobora de forma independiente en la base: `servicios_profesionales`
es **el motivo de descarte más frecuente de todos, con 1.618** `[BD]`, por
delante de `duplicado` (911) y `evento_capacitacion` (798). La frontera ambigua
no es un caso raro: es la clase de señal más numerosa que el Clasificador tiene
que decidir.

**Dos mitigaciones descartadas, con su razón** `[pendientes A6]`:

- **Bajar la temperatura no sirve.** Haría que el modelo elija siempre el mismo
  lado del filo. Se vería como reproducibilidad, pero el caso seguiría siendo
  ambiguo y la respuesta no sería mejor.
- **Lotes más pequeños tampoco.** Los datos lo descartan, y el lote grande
  degrada por otra vía: a 100 señales el JSON cabe de sobra pero 4 de 7 insights
  salieron sin categorizar. `[CLAUDE §9]`

**Lo que falta no es ingeniería, es una decisión de negocio:** un **criterio de
frontera definido**. ¿Un contrato de supervisión de diseños viales es señal de
inversión inmobiliaria? Varios de esos casos están entre los 45 insights de las
hojas de revisión.

### 2. M4 tampoco es reproducible, y es peor que el Clasificador

`[pendientes A11, control medido 2026-09-21]`

Dos pasadas del Correlacionador con **el mismo prompt v1** sobre **los mismos
322 insights validados** y los mismos 18 municipios (corridas 11 y 12):

| | |
|---|---|
| Convergencias idénticas entre pasadas | **10 de 71** — 14,1% |
| Insights que entran en una convergencia en una pasada y no en la otra | **85 de 322 — 26,4%** |
| Municipios que se mueven | **14 de 18** |
| Convergencias totales | 39 y 42 |
| Implicaciones con tipología | 23 y 24 |

**El Correlacionador es más inestable que el agente que lo alimenta**: 26,4%
frente al 19,5% del Clasificador (A6). Y la inestabilidad **se compone** — un
insight puede voltear en M2 y su convergencia volver a voltear en M4.

Lo que **no** se mueve es igual de informativo: el conteo agregado y la calidad
—medida como implicaciones que se mojan con una tipología— son casi idénticos.
**Lo inestable es qué se agrupa con qué, no cuánto ni de qué calidad.** Contar
convergencias lo habría dado por estable; se detectó comparando el conjunto de
insights de cada convergencia, que es el mismo criterio con el que se midió A6.

**Y se compone.** Un insight puede voltear en M2 y su convergencia volver a
voltear en M4. **La inestabilidad del pipeline no es la de su peor agente: es
acumulativa.** Cualquier lectura que trate el 19,5% o el 26,4% como «el margen de
error del sistema» lo subestima, porque son dos sorteos encadenados sobre el
mismo contenido.

**Consecuencia:** como A6, toca **H1 y no H4**. Cada convergencia conserva su
evidencia completa hasta la fuente y las dos pasadas conviven en el almacén. Lo
que se amplía es la banda de error de lo que las gerencias leen.

### 3. La línea no está entre agentes buenos y malos: está entre código y modelo

Es la lectura que estos dos hallazgos, juntos, obligan a hacer.

| Qué decide | Quién lo hace | Cuánto varía entre pasadas idénticas |
|---|---|---|
| El top 3 y el ranking | **Código** (M5 lee `senal_cruda`) | **0%** — idéntico, 0 de 18 municipios cambian de puesto |
| Qué señales se ven | LLM (Clasificador) | **19,5%** |
| Qué se agrupa con qué | LLM (Correlacionador) | **26,4%** |
| Qué se dice de ello | LLM | entre el 25% y el 50% del contenido del informe |

**Todo lo que pasa por un modelo tiene entre un 19% y un 26% de variación. Todo
lo que pasa por código tiene cero.** No es que unos agentes estén mejor ajustados
que otros: es que la frontera de la reproducibilidad coincide exactamente con la
frontera entre la capa determinista y la agéntica.

Esto es, a la vez, la mejor noticia y la advertencia más seria del experimento:

- **La mejor noticia** — la decisión que el sistema entrega, que es el top 3, no
  la toma un modelo. La arquitectura que el PRD §3.1 exige —lo determinista no
  depende de un LLM— no es una preferencia de estilo: es lo único que hace el
  entregable reproducible.
- **La advertencia** — todo lo que la gerencia *lee* para entender por qué, sí
  lo escribe un modelo, y eso no es reproducible. El informe es estable en su
  conclusión e inestable en su argumento.

Para la Fase 0 la consecuencia es directa: **cualquier cosa que deba ser
reproducible tiene que estar en código.** Cada vez que se mueva una decisión de
la capa determinista a un prompt, se está comprando variación del 20% al 26%.

### 4. Una compuerta automática sin piso de ruido no mide nada

`[pendientes A10]`

Se construyó una comprobación que **fallaba** —no reportaba— si el prompt v2 del
Correlacionador producía más convergencias que v1 en algún municipio. La idea
era impedir que el contexto estructural, que es constante en los tres ciclos,
empezara a crear convergencias en vez de explicarlas: el defecto de F4 entrando
por otra puerta.

Falló. Y el control demostró que **habría suspendido a v1 contra sí mismo**.

| | Convergencias | Tipología |
|---|---|---|
| v1, pasada 1 | 42 | 20 |
| v1, pasada 2 | 39 | 23 |
| v1, pasada 3 | 42 | 24 |
| **v2** | **40** | **35** |

Las 40 convergencias de v2 están **dentro** del rango de v1. Su tipología está
**muy por encima**. El efecto que v2 buscaba es real; el que la compuerta midió
era varianza.

**Desenlace:** la compuerta se rediseñó y **v2 se promovió en el código**.
**Ojo con lo que eso significa y lo que no** (precisión del 2026-09-22, P-1):
la promoción cambió el valor por defecto de `VERSION_PROMPT`, y **ahí se quedó**. Ninguna corrida se ha ejecutado con v2 —las corridas 10, 11 y 12 llevan `version_correlacionador = v1`— y **el informe publicado se compuso con v1**. Las cifras de esta sección salen de una comparación **sin linaje persistido**: `prompt_version` no tiene fila de v2. v2 es candidata, no lo publicado. El criterio va
ahora sobre el agregado, el umbral es el rango observado de la versión contra sí
misma —no un margen sobre la pasada A, que tiene filo: si A cae en el fondo de
su rango y B en lo alto, el mismo prompt se suspende— y **sin piso medido para
ese corpus la compuerta se niega a juzgar** en vez de dar un veredicto sin base.

La lección es general y vale para la Fase 0: **antes de poner una compuerta
sobre la salida de un agente, córrela contra sí misma.** Una comprobación que no
conoce su piso de ruido no mide un efecto — mide varianza y le pone una etiqueta
de aprobado o suspenso, con toda la autoridad de un número.

**Y lo mismo vale para una detección.** La comprobación de cifras de CA-M6.3
acusó a Carepa de inventarse un «80» que era **«calles 76 y 80»**, un nombre de
calle que sí estaba en su entrada: capturaba el punto final de la frase en una
orilla y no en la otra. **Medir las dos orillas con varas distintas produce
violaciones inventadas de CA-M6.3, y eso es peor que no detectar nada** — lleva a
desconfiar de salidas correctas, que es justo la confianza que la regla existe
para construir.

Re-verificarlo costó **cero tokens**, sobre las corridas 11 y 12 ya persistidas.
Es la mejor demostración de para qué sirve la persistencia por corrida: una
medición que se puede repetir sin volver a pagarla.

### 5. F4 era una constante ocupando el 18% del peso del score

`[pendientes A1/4, medido 2026-09-21]`

**F4 —dinámica de licencias, ELIC— es idéntico en los tres ciclos para los 18
municipios.** Apartadó marca −43,5% en el ciclo 1, en el 2 y en el 3. No es un
factor lento: es una constante por municipio. Con el 18% del peso desplazaba a
todos de forma fija sin que nadie pudiera subir ni bajar por él, que es lo
contrario de un score que prioriza por lo que pasa en la ventana.

**Corregido al escenario mitad** —15% en el ciclo 1, 9% en los otros dos— en
`config/pesos.json`. Efecto medido, corridas 16/8/18 → 19/20/21 `[BD]`:

| Ciclo | Antes | Después |
|---|---|---|
| 1 | Carepa, Barranquilla, Armenia | Barranquilla, Carepa, **Pereira** |
| 2 | Ibagué, Carepa, Buenaventura | Carepa, Ibagué, Buenaventura — mismos tres |
| 3 | Funza, Buenaventura, Facatativá | **sin cambio** |

Ningún municipio cruza el umbral de información. El peso liberado va a F1, F3 y
F5, que **sí varían entre ciclos** —18, 15 y 18 de 18 municipios—, así que no se
sustituye un factor estructural por otro.

**No se llevó a cero** porque entonces F5 pasaba a dominar el ciclo 3 con el 37%
—justo donde SECOP está truncado para cinco municipios— y Barranquilla salía
primera con un 1,0000 sacado de un único factor siendo la menos informada de las
18. La patología no se arreglaba: se mudaba de F4 a F5. `[pendientes, variante C]`

### 6. «Ausencia de SECOP» se ha leído como «ausencia de actividad» seis veces

`[CLAUDE §7]` Está escrito en D4 y el sistema lo ha violado seis veces, siempre
por el mismo motivo: SECOP es la fuente más rica, todo acaba calculándose desde
ella, y el municipio que no contrata obra queda indistinguible del que no existe.

1. **F5** dividía por días cubiertos, que salían solo de fechas de SECOP.
2. **El corte de cohorte** propagaba el NULL al conjunto si a un municipio le
   faltaba SECOP.
3. **El piso de área de ELIC** se descontaba de la fracción informada.
4. **El prefiltro** no ve nada que no tenga forma de objeto contractual.
5. **RSS no llegaba al Clasificador**: una de las tres barreras era el
   diccionario de obra, calibrado sobre objetos de SECOP.
6. **La fracción informada** es casi toda peso derivado de SECOP.

Las cinco primeras están corregidas. **La sexta está abierta** y es el pendiente
P1: Barranquilla tiene 12 insights de prensa que pasaron el validador, y la
métrica del propio sistema dice que no sabe nada de Barranquilla.

**Para la Fase 0 esto es un requisito de diseño, no una anécdota.** Seis
repeticiones del mismo error no son seis descuidos.

### 7. El sistema decidía quién merecía verse, y se cambió por mostrarlo todo

`[pendientes P1, resuelto 2026-09-21]`

En el ciclo 3, cinco municipios quedaban fuera del informe por fracción
informada: Ibagué, Armenia, Barranquilla, Pereira y Cartagena. La guarda era
correcta —impedía que un score alto saliera de un único factor— pero producía un
efecto que nadie quería: **Barranquilla tiene 12 insights de prensa que pasaron
el validador y no existía para el lector.** «No hay suficiente información» no es
lo mismo que «aquí hay algo, pero solo lo veo por un lado».

**No se arregló con umbrales, y se midió por qué no.** Las fracciones informadas
del ciclo 3 son **20,10% o 77,80%, sin nada en medio**: cualquier umbral por
debajo de 20,10% no dispara nunca —equivale a apagarlo, pareciendo una
salvaguarda— y cualquiera por encima se comporta igual que el 50%. Ampliar a un
top 10 tampoco servía: la exclusión era por información, no por puesto, así que
se habrían publicado diez municipios **sin** el segundo mejor score del ciclo.

**Se resolvió al revés: exponiendo en vez de excluyendo.** El informe muestra
`tope_top` municipios —10— con su score **y los factores que lo sostienen**:

```
 1. Ibagué         0.8560   apoyado en F4+F5
 2. Armenia        0.6399   apoyado en F4+F5
 3. Funza          0.5951   apoyado en F1+F2+F3+F4+F5
 4. Barranquilla   0.5696   apoyado en F4+F5
 5. Buenaventura   0.5458   apoyado en F1+F2+F3+F4+F5
```

Ibagué sigue primero, pero al lado se lee de qué está hecho ese primer puesto.
**El sistema deja de decidir qué merece verse y pasa a decir en qué se apoya lo
que muestra.** Es la misma información que la guarda usaba para excluir, puesta
delante de quien lee en vez de aplicada por detrás.

Lo que esto cuesta y conviene tener presente: el municipio que encabeza el ciclo
3 lo hace con **0 de 239 días de contratación**. La transparencia lo hace
legible, no lo hace desaparecer, y por eso **el orden de lectura es parte de la
decisión**: la línea de fuentes —«licencias y prensa, sin contratación»— tiene
que ir junto al nombre y al puesto, con el mismo peso visual. Si va como nota al
pie, para cuando se lee el lector ya interpretó el puesto 1 como prioridad del
ciclo, y el desglose deja de informar para pasar a justificar a posteriori
(`[pendientes M6-orden]`).

Y al usuario final no se le muestran códigos de factor sino **nombres de
fuente**: F1, F2 y F3 son los tres SECOP, así que cinco factores colapsan en tres
fuentes (`[pendientes M6-src]`).

Sobre la carga: pasar de 3 a 10 municipios la multiplicaría por tres, así que
**la calificación pedida se acota a los 3 primeros** y el resto queda opcional.
Ver la nota de H2.

### 8. Atribución cruzada: contratación departamental archivada en la capital

`[pendientes A3, cerrado como fuera de alcance del MVP]`

El patrón **no es ruido**: es capital departamental → municipio menor del mismo
departamento. Manizales→La Dorada 31, Barranquilla→Puerto Colombia 20,
Pereira→Dosquebradas 10, Apartadó→Chigorodó 8. Es contratación departamental
archivada en la capital y **ejecutada fuera**.

**El 0,64% medido es un piso, no la cifra real:** solo detecta menciones a los
otros 17 municipios del MVP. Resolverlo exige un nomenclátor DIVIPOLA de los
1.103 municipios que el snapshot no trae, así que queda para la Fase 0.

---

## Anexo — CA-M2.1, reducción del Clasificador

> Criterio: ≥85% de reducción.

| Medición | Resultado | Fuente |
|---|---|---|
| Ciclo 1 completo, pasada 1 | **95,2%** | `[pendientes B2]` |
| Ciclo 1 completo, pasada 2 | **94,9%** | `[pendientes B2]` |
| Ciclo 3, con RSS incorporado | **95,3%** | `[pendientes]` |

Se cumple con holgura y **de forma estable entre pasadas** — lo que vuelve más
llamativo que el destino de las señales individuales no lo sea. El agregado es
reproducible aunque el detalle no.

---

## Qué falta para poder cerrar la compuerta

Ordenado por lo que bloquea, no por esfuerzo.

| # | Qué falta | Bloquea | Depende de |
|---|---|---|---|
| 1 | **M7 y M9** — aplicativo web y calificación | **H1 y H2**, las dos | Ingeniería; Django sin instalar |
| 2 | **Compromiso de las 7 gerencias** de calificar 3 ciclos | **H2**, necesaria para el GO | Gerencia General `[pendientes 5]` |
| 3 | **Criterio de frontera** del Clasificador | Interpretación de H1 | Analítica `[pendientes A6]` |
| 4 | **M6** — síntesis, e informes publicados | Cierre de la cadena para H4 | Canal sin decidir `[pendientes 11.4/3]` |
| 5 | **Costo del Sintetizador** | Cifra final de H5 | Correr M6 `[pendientes B4]` |
| 6 | **Validador sobre muestra mayor** | Afirmar H4, no solo no refutarlo | Correr los 3 ciclos |
| 7 | **Hojas de revisión** de las 5 personas | Primera lectura de calidad | Devolución del equipo |
| 8 | **Pesos definitivos** del score | Calibración de M5 | Gerencia General `[pendientes A1/4]` |

### Resultado de las hojas de revisión del equipo

### ⬜ Pendiente de devolución

45 insights, 5 revisores, diseño ciego con dos bloques: insights **estables**
—presentes en las dos pasadas con el mismo conjunto de señales— mezclados con
insights que **voltearon**, sin marcar cuál es cuál. La clave está aparte y no
se repartió.

De una sola pasada del equipo salen tres respuestas, y **las tres están
pendientes**:

1. Si los insights estables son correctos — calidad de base.
2. Si los que voltearon son genuinamente ambiguos para un humano, o el modelo
   duda de casos que una persona resuelve sin pestañear.
3. El acuerdo entre las cinco personas **dentro de cada grupo**. Si el
   desacuerdo humano se concentra en los que voltearon, queda confirmado que A6
   no es un defecto del modelo sino una **frontera mal definida**, que es
   justamente lo que hay que decidir.

### Y una advertencia sobre cómo se decide

**H4 es bloqueante y H2 es necesaria.** `[PRD §11]` Hoy H4 no tiene ningún
contraejemplo pero tampoco muestra suficiente, y H2 no tiene ni un dato. Las
tres cosas que mejor pinta tienen —H3, H5 y la reducción del Clasificador— son
precisamente las que **no bastan** para un GO.

Y sobre H1: si el resultado cae cerca del 30%, **ese margen no es decidible**.
Otra pasada del mismo ciclo habría dado otro número.
