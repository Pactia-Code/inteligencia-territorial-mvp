# Informe de resultados — compuerta go/no-go

> **Este documento se genera con `scripts/informe_resultados.py`. No se edita a
> mano**: cualquier cambio se hace en la plantilla
> (`src/territorial/informes/plantilla_resultados.md`) o en las mediciones, y se
> regenera. Escribirlo a mano es lo que la auditoría encontró roto (H-034).

| Parámetro de la generación | Valor |
|---|---|
| Commit del código y de las consultas | {{p_commit}} |
| Corte de la ronda principal | {{p_corte_principal}} |
| Corte de la ronda extendida | {{p_corte_extendida}} · {{p_estado_extendida}} |
| Informe calificado | El publicado del ciclo 3, con la corrida de agentes publicada y su scoring |

---

## Cómo leer este documento

**Cada cifra lleva su procedencia**: `[consulta: <función> · <corridas> · <commit>]`.
La función está en `src/territorial/informes/mediciones.py`, `costo.py` o
`reglas/tasa_rechazo.py`; las corridas son los ids sobre los que se calculó; el
commit es el del código que la produjo. **Con eso cualquier cifra se puede
volver a calcular**, que es lo que la versión anterior, escrita a mano, no
permitía: la mayoría de sus procedencias apuntaban a otro documento y ninguna a
una consulta (H-034).

**Lo que no tiene productor no lleva cifra.** Va marcado como *afirmación sin
medición* o se retira, y la lista de lo retirado está al final.

**Este documento reporta valores contra criterios. No da veredictos.** Que una
hipótesis se dé por cumplida, refutada o sin concluir lo decide la evaluación
del piloto (`docs/prompts/evaluacion-piloto.md`), contra el tablero congelado en
`docs/javelin.md`.

**Cinco correcciones respecto a la versión escrita a mano**, todas de la
auditoría:

- **H-028** — la tasa de rechazo que publicaba era falsa (ver H3).
- **H-027** — las trazas no tienen hash de salida (ver H4).
- **H-030** — la cifra de cuánto contenido del top 3 dependía de la pasada se
  **retira** por decisión del dueño: no tenía método, y no se inventa uno a
  posteriori.
- **H-031** — el inventario era de otro estado de la base.
- **H-032** — la compuerta está en el PRD **§9**, no en §11, que no existe.

### La regla de decisión, para tenerla delante

`[PRD §9]`

- **GO** — H2 y H4 cumplidos, y al menos dos de H1/H3/H5 en rango aceptable.
- **GO CONDICIONADO** — H4 cumplido pero H2 bajo.
- **NO-GO** — H4 incumplido, o H1 y H3 ambos por debajo del criterio.

---

## 0. Las cinco hipótesis: valor medido frente a criterio

| | Hipótesis | Criterio `[PRD §1]` | Ronda principal | Ronda extendida |
|---|---|---|---|---|
| **H1** | El pipeline agéntico produce insights que las gerencias consideran relevantes | ≥30% de insights con promedio ≥4 **[EST]** | {{h1p_prd}} | {{h1e_prd}} |
| **H2** | Las 7 gerencias califican de forma sostenida | ≥50% promedio en ciclo 3 **[EST]** | {{h2p_promedio}} | {{h2e_promedio}} |
| **H3** | Las fuentes públicas con API contienen señal accionable | ≥60% **[EST]** | {{h3_superv_10}} | — |
| **H4** | La cadena multiagente preserva la trazabilidad | 100% (bloqueante) | {{h4_insights}} | — |
| **H5** | El costo por ciclo es viable a escala nacional | Extrapolación documentada | USD {{h5_total_k1}} al año con *k* = 1 | — |

H3, H4 y H5 no dependen de la ronda, así que solo tienen una columna. **Cómo se
calcula cada valor está fijado en `docs/javelin.md`**, congelado antes de ver los
datos, y cada sección de abajo lo repite.

---

## Inventario

| | |
|---|---|
| Municipios | {{inv_municipios}} |
| Señales cargadas | {{inv_senales}} — SECOP II {{inv_secop}} · RSS {{inv_rss}} · Bing {{inv_bing}} |
| Días de los tres ciclos | {{inv_dias}} |
| Corridas de agentes | {{inv_corridas_agentes}} |
| Corridas de scoring | {{inv_corridas_scoring}} |
| Insights persistidos | {{inv_insights}} |
| Descartes registrados | {{inv_descartes}} |
| Trazas de agente | {{inv_trazas}} |
| Informes | {{inv_informes}} |
| Calificaciones de la ronda principal | {{inv_calif_principal}} |

**Nada se sobrescribe**: cada ejecución inserta una corrida nueva, y las de
antes conviven con las de después. Es lo que permite medir A6 y A11 sin volver a
pagar tokens. **Las calificaciones no se cuentan sin corte**: crecen mientras
dure la ronda extendida, y un conteo sin corte haría este documento
irreproducible.

**La ronda principal se verifica contra su exportación** antes de calcular nada:
mismo número de filas que el manifiesto, mismo sha256 del CSV y, fila a fila,
mismos valores. Una corrección posterior al corte no cambia `creado_en` (H-008),
así que un filtro por fecha no la vería; la comparación con la foto sí, y si la
encuentra el script se niega a generar.

---

## H1 — Los insights son relevantes para las gerencias

> ≥30% de insights con promedio ≥4 **[EST]** `[PRD §1]`

### Cómo se calcula, fijado en `docs/javelin.md`

- Sobre **los insights pedidos** del informe publicado —{{h1_pedidos}}—, no
  sobre todo lo que muestra.
- El promedio de cada insight usa **las calificaciones de las gerencias «prd»**.
- **Un insight cuenta solo si tiene al menos 2 calificaciones «prd».** Si no, es
  *insuficiente* y queda fuera, ni en el numerador ni en el denominador.
- Se reporta también **con las adicionales**, sobre los **mismos** insights.

### Valores

| | Ronda principal | Ronda extendida |
|---|---|---|
| Insights que cuentan | {{h1p_cuentan}} | {{h1e_cuentan}} |
| Insuficientes | {{h1p_insuficientes}} | {{h1e_insuficientes}} |
| Con promedio «prd» ≥ 4 | {{h1p_prd}} | {{h1e_prd}} |
| Con promedio ≥ 4, incluyendo adicionales | {{h1p_adic}} | {{h1e_adic}} |

### Lo que condiciona cómo leer H1

**Lo que se califica es una muestra de lo que el sistema pudo haber dicho.** Dos
pasadas del Clasificador sobre el mismo ciclo, con el mismo prompt, produjeron
{{a6_insights}} insights, con {{a6_evidencias}} evidencias. Señal a señal:

- {{a6_cambian}} de las señales cambian de destino entre las dos pasadas.
- {{a6_vuelcan}} están dentro de un insight en una pasada y no en la otra (A6).

**Un eslabón más adelante pasa lo mismo**: el Correlacionador, con el mismo
prompt y los mismos insights, solo repite {{a11_identicas}} de sus
convergencias (A11). La inestabilidad se compone sobre dos agentes encadenados.

**Y lo que las gerencias califican lo eligió el scoring.** Los municipios
pedidos son los tres primeros del ranking, y ese ranking depende en buena parte
del diccionario de obra del prefiltro, que no está validado (A2, H-011). Una
calificación baja puede hablar del insight o de la elección del municipio, y
este documento no las separa (H-033).

**El bucle de aprendizaje de CA-M4.3 no se ha ejercitado**: está implementado,
pero ninguna corrida se ha hecho después de que existieran calificaciones.

---

## H2 — Las 7 gerencias califican de forma sostenida

> ≥50% promedio en ciclo 3 **[EST]** `[PRD §1]`

### Cómo se calcula, fijado en `docs/javelin.md`

- **Tasa por gerencia = insights pedidos calificados ÷ insights pedidos**
  ({{h1_pedidos}}).
- El promedio es **sobre las gerencias «prd»** de la lista congelada en el
  informe. Las adicionales se listan aparte.
- **Condición de la ronda**: invitación personal del dueño de unos 5 minutos y
  calificación autónoma, sin su presencia. **H2 del PRD suponía notificación por
  correo**, así que esta tasa se reporta con su condición y **no se compara
  directamente con el criterio de éxito**.
- **Con menos de 10 gerencias, la tasa es indicativa**, no concluyente.

### Ronda principal

Promedio «prd»: {{h2p_promedio}}

{{h2p_tabla}}

### Ronda extendida

Promedio «prd»: {{h2e_promedio}}

{{h2e_tabla}}

**La ronda extendida es acumulada**: incluye las calificaciones de la principal,
porque su corte se aplica sobre la misma tabla. Se reporta aparte para que se
vea qué añadió el plazo extra.

### Lo que H2 puede decir con una ronda

La hipótesis dice «de forma sostenida» y el criterio se mide «en ciclo 3». Con
una ronda sobre un ciclo, lo que hay es **una tasa puntual, no sostenida**. Y la
identidad es declarativa (R-A2): quien conozca un correo autorizado puede
calificar por esa persona, así que la tasa es un **límite superior** de la
participación real.

---

## H3 — Las fuentes públicas contienen señal accionable

> ≥60% **[EST]** de insights que sobreviven al validador `[PRD §1]`

### Supervivencia al validador

**La tasa {{h3_frase}}.** Una cita fiel a una fuente equivocada pasa las siete
reglas. Se calcula sobre **los insights del Clasificador**: los consolidados del
Correlacionador no pueden fallar, porque su evidencia la une el código, y
meterlos solo diluiría la cifra.

{{h3_tabla}}

**En la corrida publicada sobrevive {{h3_superv_10}}.**

**R8 —ninguna cifra de la prosa sin fuente— no se evaluó en {{h3_r8}}**: la
regla se añadió en F0.2, después de que corrieran todas. Su columna vacía
significa «sin medir», **no** «ninguna cifra inventada».

### Por fuente

| Fuente | Sobrevive al validador | Corrida |
|---|---|---|
| RSS | {{h3_rss_10}} | publicada |
| SECOP II | {{h3_secop_10}} | publicada |
| RSS | {{h3_rss_9}} | anterior del ciclo 3 |

### La fuente sin filtrar convierte mejor que la filtrada

| Fuente | ¿Pasa por el prefiltro? | Señales enviadas que acaban en un insight validado |
|---|---|---|
| RSS | No | {{h3_conv_rss}} |
| SECOP II | Sí, diccionario de obra | {{h3_conv_secop}} |

El prefiltro existe para ahorrar coste, y **lo que deja pasar convierte peor que
lo que nunca se filtró**. No prueba que haya que quitarlo, pero sí que su
calibración no está seleccionando mejor señal (A2). De los descartes de señales
RSS en la corrida publicada, {{h3_desc_rss}} llevan el motivo exacto
`sin_implicacion_inmobiliaria`: el Clasificador no se atraganta con los
titulares, les aplica la prueba de sustancia.

### La correlación produjo algo que ninguna fuente sola produce

**{{h3_cruces}} consolidados de la corrida publicada cruzan RSS con SECOP II**:
prensa y contratación sobre el mismo hecho. Es CA-M4.1 literal, y con una sola
fuente era imposible. La corrida publicada tiene {{h3_vol_10}}, frente a las
{{h3_evid_7}} evidencias de una pasada del ciclo 1 con solo SECOP.

**TerriData no es una fuente comparable**: es contexto estructural, no señal de
coyuntura, y no podría originar insights. **Bing queda fuera por decisión** (D1):
llega sin fecha y sin URL y el validador lo rechaza por R2.

---

## H4 — La cadena preserva la trazabilidad · **BLOQUEANTE**

> 100% (bloqueante) de insights con evidencia completa hasta la fuente `[PRD §1]`

### La traza del informe publicado

Recorre **señal → insight → validación → correlación → score → informe** sobre
**todos** los insights del informe que calificaron las gerencias, con las
comprobaciones de la auditoría §4.7:

| Comprobación | Resultado |
|---|---|
| Insights sin ningún fallo | {{h4_insights}} — {{h4_tipos}} |
| Citas localizables en el contenido ingerido | {{h4_citas}} |
| Señales citadas idénticas a su registro del snapshot | {{h4_snapshot}} |
| Score y puesto del municipio iguales al payload | {{h4_scores}} |
| Fallos | {{h4_fallos}} |

El snapshot contra el que se compara está {{h4_anclado}}, y cada señal se
reconstruye con la misma función que usó la ingesta. **La cadena llegó hasta la
calificación**: {{inv_calif_principal}} calificaciones de la ronda principal
cuelgan de insights de este informe.

### Lo que hay y lo que no, en la observabilidad

- **Trazas por agente** (CA-M8.2): {{h4_trazas}} con tokens y duración. Con
  hash de entrada, {{h4_hash_in}}. **Con hash de salida, {{h4_hash_out}}**: la
  versión anterior de este documento afirmaba que lo tenían todas, y era falso
  (H-027).
- **Descartes registrados** (CA-M2.5): {{h4_desc_decl}} declarados y
  {{h4_desc_nodecl}} no declarados —señales que el modelo ni mencionó, y que
  quedan registradas en vez de desaparecer—.
- **Linaje de prompts por contenido** (D7): en `version_prompt` hay
  {{h4_prompts}}. **No hay fila del Correlacionador v2**, que nunca corrió (H-036).
- **Langfuse y el checkpointing de CA-M8.4** están instalados y sin cablear.

**A6 y A11 tocan H1, no H4.** Que dos pasadas den insights distintos no rompe la
trazabilidad: cada insight de cada pasada conserva su evidencia hasta la fuente.
Lo que tiene banda de error es *qué* se publica, no si se puede auditar.

---

## H5 — El costo es viable a escala nacional

> Extrapolación documentada `[PRD §1]`

### La proyección, como condicional

Año nacional, con {{h5_nacional}} municipios:

- **Correlacionador**: USD {{h5_corr}} al año.
- **Clasificador**: USD {{h5_clas}} al año, multiplicado por *k*.
- **Total con *k* = 1**: USD {{h5_total_k1}} al año. El Correlacionador es
  {{h5_parte_corr}} del total.

El piloto de {{inv_municipios}} municipios saldría a USD {{h5_piloto}} al año.

> **Advertencia (P-5).** La tarifa del Clasificador está **sin verificar**: se
> cotizó para `gpt-5-mini` y el despliegue es `gpt-5.4-mini`. *k* es cuántas
> veces la tarifa real supera a la aplicada. **Hasta que haya tarifa real, *k* =
> 1**; cuando la haya, se cambia `config/tarifas.json` y se regenera este
> documento.

**Lo que la proyección arrastra, y hay que leerlo con ella:**

- El Clasificador escala con una constante de **{{h5_constante_quincena}} señales por
  quincena que no tiene productor** (*afirmación sin medición*, auditoría 8b.1). La regla que la
  documenta —tasa diaria por 14— da otra cosa sobre el snapshot:
  {{h5_prefiltro}} señales SECOP pasan el prefiltro en {{h5_dias_snapshot}} días,
  que son **{{h5_tasa_diaria}} por quincena**. Las dos no cuadran y hay que
  resolverlo antes de cerrar H5.
- Los tokens por señal del Clasificador son una tasa medida el 2026-09-17 sobre
  un municipio y un ciclo. La base da otros valores según la corrida.
- El Correlacionador se promedia sobre **todas** las trazas: la traza no lleva
  corrida (H-006). Lo arregla F0b.2.
- **No incluye el Sintetizador**, que no existe y correría sobre `gpt-5`, el
  mismo modelo que hoy es la mayor parte del costo.

### Consumo medido

{{h5_tabla_consumo}}

Del ciclo 1, que se corrió varias veces: {{h5_ciclo1}}. **Ese total no se
reparte por pasada**: la traza no lleva corrida, así que dividirlo sería
suponer cuántas veces se corrió y con qué peso cada una.

---

## Hipótesis 4 y 5 del tablero — hacia adelante, sin datos

El tablero de `docs/javelin.md` añade dos hipótesis de viabilidad que **no se
evalúan con los datos de este piloto**:

| | Hipótesis | Criterio, del dueño | Datos |
|---|---|---|---|
| **4** | El Área de Analítica puede operar el sistema con la capacidad que tiene | ≤ 8 horas-persona por ciclo | **Hacia adelante, sin datos**: las horas no se registraron |
| **5** | Los municipios priorizados producen acción, no solo lectura | ≥ 1 de los 3 municipios del top 3 sale de `priorizado` por ciclo | **Hacia adelante, sin datos**: el tablero de seguimiento no tiene cambios de estado |

---

## Hallazgos no previstos

### 1. El Clasificador no es reproducible, y no por el volumen

**El ranking es estable y el contenido no.** El scoring lee `senal_cruda`, no
insights, así que es inmune a A6 por construcción; lo que cambia entre pasadas
es lo que las gerencias leen.

**La causa no es el volumen.** Barranquilla vuelca {{a6_barranquilla}} de sus
señales y Funza {{a6_funza}}. Lo que predice la inestabilidad es la densidad de
contratos que hablan de obra sin serlo. Los motivos de descarte más frecuentes
de toda la base, contados por motivo exacto, son {{hz_motivos}}.

**Lo que falta no es ingeniería, es una decisión de negocio**: un criterio de
frontera definido. Bajar la temperatura no lo resolvería —haría que el modelo
eligiera siempre el mismo lado de un caso que sigue siendo ambiguo—.

### 2. El Correlacionador tampoco, y es más inestable que el Clasificador

Dos pasadas con el mismo prompt v1 sobre los mismos insights validados:

| | |
|---|---|
| Convergencias idénticas entre pasadas | {{a11_identicas}} |
| Insights que entran en una convergencia en una pasada y no en la otra | {{a11_agrupados}} |
| Municipios que se mueven | {{a11_municipios}} |
| Convergencias en cada pasada | {{a11_convergencias}} |
| Implicaciones que se mojan con una tipología | {{a11_tipologia}} |

**Lo inestable es qué se agrupa con qué, no cuánto ni de qué calidad.** Contar
convergencias lo habría dado por estable.

### 3. La frontera de la reproducibilidad es la frontera entre código y modelo

| Qué decide | Quién | Cuánto varía entre pasadas idénticas |
|---|---|---|
| El ranking | Código (M5) | {{scoring_identico}} municipios con score distinto entre dos corridas de scoring gemelas |
| Qué señales se ven | Clasificador | {{a6_vuelcan}} |
| Qué se agrupa con qué | Correlacionador | {{a11_agrupados}} |

**Cualquier cosa que deba ser reproducible tiene que estar en código.**

### 4. Una compuerta sin piso de ruido mide varianza

La primera compuerta del Correlacionador habría suspendido a v1 contra sí mismo.
Las dos pasadas de v1 que están persistidas dan {{hz_pisoruido_11}} y
{{hz_pisoruido_12}} (convergencias y tipología). **La pasada 1 de v1 y la única
pasada de v2, con las que se promovió v2, no se persistieron**: sus cifras son
*afirmaciones sin medición* (H-036), y por eso v2 sigue siendo candidata hasta
F2.3.

### 5. F4 era una constante con peso de factor

F4 —dinámica de licencias— vale {{hz_f4_apartado}} en Apartadó, y es **idéntico en los tres ciclos para {{hz_f4_constante}}
municipios**. Los factores que sí varían entre ciclos: {{hz_f_varian}}. Por eso
Analítica lo bajó a la mitad. Efecto en el top 3:

{{hz_top_tabla}}

### 6. «Ausencia de SECOP» se ha leído como «ausencia de actividad» seis veces

Las seis están en `CLAUDE.md`. La sexta sigue abierta: Barranquilla tiene
{{hz_barranquilla}} insights validados con evidencia solo de prensa, y la
fracción informada del propio sistema dice que no sabe casi nada de ella. La
versión anterior decía «12 de prensa» sin distinguir: son las dos cosas.

### 7. El sistema dejó de decidir quién merece verse

Las fracciones informadas de la corrida publicada son {{hz_fracciones}}, sin
nada en medio, así que ningún umbral intermedio distinguía nada. Por debajo de
la mitad quedan {{hz_fraccion_baja}}. **Se resolvió exponiendo en vez de excluyendo**: el
informe muestra el score con las fuentes que lo sostienen.

{{hz_top5}}

Ibagué encabeza el ciclo con {{hz_ibague_dias}} días de contratación cubiertos.
La línea de fuentes tiene que ir junto al puesto: si va al pie, el lector ya leyó
el puesto 1 como prioridad del ciclo.

### 8. Atribución cruzada

Contratación departamental archivada en la capital y ejecutada en otro
municipio (A3). **Las cifras que traía este documento se retiran**: no tenían
método declarado, y medirlo buscando nombres en texto libre las inflaría por
los homónimos. Necesita diseño propio y queda fuera del MVP.

---

## Lo retirado: afirmaciones sin medición

| Afirmación de la versión anterior | Por qué sale |
|---|---|
| «Entre el 25 % y el 50 % del contenido del top 3 depende de la pasada» | **H-030.** Sin método. Retirada por decisión del dueño; si se quiere, el método se define antes de calcular |
| «La salida de razonamiento del Correlacionador es el 84 % del total» | La traza no guarda tokens de razonamiento |
| «~615 señales por quincena» y «factor 12» | Constante sin productor; ver H5 |
| «~282 / ~111 tokens por señal» | Tres valores distintos en tres sitios, ninguno elegido |
| v1 pasada 1 y v2 en la compuerta del Correlacionador | **H-036.** No persistidas |
| «Con F4 a cero, F5 domina el ciclo 3 y Barranquilla sale con 1,0000» | Variante no persistida |
| Atribución cruzada y sus pares | Sin método declarado |
| «USD 39 / 2.160 al año» y «89 % del gasto» | Dependían de las trazas acumuladas en otro momento; sustituidas por la proyección condicional de H5 |
| «Tasa de rechazo del 0,0 %» | **H-028.** Falsa; ver H3 |
| «Hashes de entrada y de salida» | **H-027.** Falsa; ver H4 |
| Descartes «1.618 / 911 / 798» | Ningún método los reproduce; ver el hallazgo 1 |
| «Ibagué encabeza con 0 de 239 días de contratación» | El payload publicado dice otra cifra; ver el hallazgo 7 |

---

## Anexo — CA-M2.1, reducción del Clasificador

> Criterio: ≥85% de reducción `[PRD, CA-M2.1]`

| Pasada | Reducción |
|---|---|
| Ciclo 1, pasada 1 | {{m21_7}} |
| Ciclo 1, pasada 2 | {{m21_8}} |
| Ciclo 3, publicada | {{m21_10}} |

Estable entre pasadas en el agregado, aunque el destino de cada señal no lo sea.

---

## Qué falta para cerrar la compuerta

| Qué | Bloquea | Depende de |
|---|---|---|
| **El cierre de la ronda extendida** y la regeneración de este documento | H1 y H2 de la extendida | El corte del 2026-10-08 |
| **La evaluación del piloto** contra el tablero | El veredicto de cada hipótesis | Este documento regenerado |
| **La tarifa real del Clasificador** | La cifra de H5 sin condicional | P-5 |
| **F0b.2**: costo por corrida, no sobre trazas acumuladas | H5 reproducible por corrida | F2.1 |
| **La constante de señales por quincena** | El término del Clasificador en H5 | Un productor, o retirarla |
| **El costo del Sintetizador** | H5 completo | Que exista |
| **El criterio de frontera del Clasificador** | La lectura de H1 | Analítica |

---

## Cómo regenerar

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py scripts\informe_resultados.py --commit <commit>          # escribe docs/informe_resultados.md
& $py scripts\informe_resultados.py --commit <commit> --check  # falla si difiere de lo commiteado
```

Solo lectura: la conexión se abre en modo READ ONLY. Necesita la exportación de
la ronda principal en `C:\dev\respaldos\corte-ronda-2026-09-29\` y el snapshot
versionado en `docs/`.
