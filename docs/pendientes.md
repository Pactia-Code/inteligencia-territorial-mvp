# Pendientes abiertos

Registro único de lo que falta decidir. Consolida [PRD §10](prd.md),
[Addendum 01 §7](addendum-01-fuente-de-datos.md),
[Addendum 02](addendum-02-stack.md) y [Arquitectura §11](architecture.md).

**Actualizado:** 2026-09-21 (A6 caracterizado sobre las dos pasadas)

---

## Bloquean construcción

| # | Pendiente | Bloquea | Decide | Origen |
|---|---|---|---|---|
| **B1** | Clave, endpoint y **nombres de despliegue** de Azure OpenAI en el tenant | M2, M4, M6 — toda llamada a LLM | Área de Analítica | Addendum 02 |
| **A2** | **Diccionario de obra: confirmado y peor de lo que decía este pendiente.** El rango real es 15%–59% por municipio (13%–90% si se mide por municipio **y ciclo**), y la causa es mecánica, no de criterio: `via` casa **por subcadena sin límite de palabra** —«selección abreviada» 56 veces, «Viviana» 75, «previa», «lluvias»—, `ordenamiento` captura nombres de secretarías (673 marcas únicas), `puente` casó con el apellido «Puentes» y `lote` con números de lote de licitación. El 89,8% de Turbo son contratos de enfermeras marcados por «ampliación» de cobertura. **Se difiere a propósito hasta después de las dos pasadas**: cambia F1, F2 y F3, así que va como A7 — medir antes, versionar a **v3**, dejar el antes y el después conviviendo. **No tocar el Clasificador antes de las dos pasadas** **Conexión con A6, medida el 2026-09-21: el volteo NO lo causan los términos rotos por subcadena.** `via` voltea 17,8%, por debajo de la media de 22,3%, y `mejoramiento` voltea 0% sobre 74 señales. Lo causan `ampliacion` (36,8%), `infraestructura` (35,3%) y `adecuacion` (35,3%), que son ambiguos **en el significado, no en la cadena**. El prefiltro no distingue «hacer una vía» de «supervisar quien diseña una vía». **Arreglar solo las subcadenas rotas dejaría A6 intacto**: son defectos distintos, A2 mete ruido determinista y A6 es indecisión ante casos limítrofes | Precisión de F1, F2 y F3 | Área de Analítica | Addendum 01 · remedido 2026-09-18 |
| **A4** | **Consolidación del Clasificador.** Tras cuatro versiones del prompt sigue partiendo un mismo frente de obra en varios insights: en Carepa produjo cuatro insights de pavimentación que son un solo frente | Calidad del informe; infla el conteo de insights | Área de Analítica | Afinamiento de prompt |
| **A1 / 4** | Pesos definitivos del score (hay propuesta provisional en Addendum 01 D4) | Calibración de M5 | Gerencia General | PRD §10 · Addendum 01 |
| **A5** | **Escala del score.** Resuelto el umbral (queda en **50%**: la tabla de sensibilidad mostró que 33% y 50% dan idéntico resultado y que el 50% está en el centro de una meseta, no en un filo). **La escala absoluta no se ancla hoy**: habría que inventar los topes sin datos. Se persisten los valores crudos de cada factor en `score_municipio.valores_crudos` para construirla en la semana 8 con 3 ciclos de evidencia. Mientras tanto el score min-max es **ordinal dentro de su corrida** y no comparable entre ciclos | Comparabilidad del score entre ciclos | Área de Analítica | Implementación de M5 · decidido 2026-09-18 |
| **A8** | **El umbral de información castiga dos veces a los municipios sin ELIC.** A 67% caerían Carepa, Turbo y Chigorodó, que están al 62% porque les falta F4 — y les falta por el **piso de área de ELIC** (D4), no por falta de datos. Con el umbral en 50% no muerde, pero el defecto está ahí: un municipio pequeño pierde F4 por diseño y luego se le cuenta esa pérdida como falta de información | Solo si se sube el umbral por encima del 62% | Área de Analítica | Tabla de sensibilidad, 2026-09-18 |
| **A9** | **Con dos pasadas del mismo ciclo, cuál es la buena.** Nada marca hoy qué `corrida_agentes` es la canónica. **No muerde en el correlacionador ni en el scoring**: el correlacionador usa los insights de su propia pasada, que es correcto, y el scoring lee `senal_cruda`, no insights. **Muerde solo en el informe**, y el informe ya sabe congelar (`informe.id_corrida`). No se resuelve hoy a propósito: si las pasadas resultan casi idénticas basta con marcar una canónica, y si divergen como Chigorodó la pregunta es cuál es la buena — un criterio que no se puede fijar sin ver la divergencia sobre 18 municipios | Publicación del informe (M6) | Área de Analítica | Corridas append-only, 2026-09-18 |
| **A6** | **El Clasificador no es reproducible, y la causa no es la que se suponía.** *Medido sobre el ciclo 1 completo, corridas 7 y 8, misma cohorte 18/18 y mismos prompts verificados.* **Hechos:** 22,4% de las señales cambian de destino entre pasadas idénticas; **543 (19,5%)** aparecen en insight en una y no en la otra. El **top 3 es idéntico** y ningún municipio cambia de puesto — el scoring lee `senal_cruda`, no insights, así que es **inmune a A6 por construcción**. Pero **entre el 25% y el 50% del contenido del informe** del top 3 depende de qué pasada se publicó (criterio laxo y estricto). `sin_contabilizar`: 3,5% y 2,9%; solo 16 señales coinciden entre pasadas, o sea que **no hay un conjunto estable de señales que el modelo no sepa procesar**. **Causa, corregida:** la hipótesis del volumen queda **descartada por los datos** — Barranquilla 897 señales y 10% de volteo, Funza 40 y 87,5%. Lo que predice la inestabilidad es la **densidad de contratos de servicios profesionales que hablan de obra sin serlo**: Funza es casi todo de esa clase (señalización vial, supervisión de consultorías de diseño, mantenimiento de infraestructura eléctrica), Carepa son reconstrucciones viales inequívocas y voltea 0%. **El modelo no falla: duda ante casos genuinamente ambiguos** frente a la prueba de sustancia del prompt v4. **Consecuencias escritas:** (a) **no se mitiga con temperatura** — bajarla haría que elija siempre el mismo lado del filo, se vería como reproducibilidad pero el caso seguiría siendo ambiguo y la respuesta no sería mejor; descartado explícitamente. (b) Tampoco con lotes más pequeños: los datos lo descartan. (c) Lo que falta es un **criterio de frontera definido**, y es decisión de negocio: ¿un contrato de supervisión de diseños viales es señal de inversión inmobiliaria? Varios de esos casos están entre los 45 insights de las hojas de revisión. (d) **A6 toca H1, no H4.** La trazabilidad está intacta; lo que queda con banda de error es «≥30% de insights con promedio ≥4», porque **no existe EL conjunto de insights del ciclo sino una muestra de resultados posibles**. La compuerta de la semana 8 no debe decidirse sobre márgenes estrechos en H1. (e) **A6 y A4 son independientes.** Confirmado | H1 y el criterio de frontera | Área de Analítica | Medido y caracterizado 2026-09-21 |

## Bloquean alcance

| # | Pendiente | Bloquea | Decide | Origen |
|---|---|---|---|---|
| **11.5** | **El PRD principal v1.2 no está en el repositorio.** Varias referencias citadas (§8.1, RN-13, CA1.6, CA1.7, CA2.6, CA6.7) parecen venir de ahí | Cierra de una vez 11.1, 11.4 y 11.6 | — | Arquitectura §11 |
| **11.4 / 3** | Canal de notificación. Se diseñó correo + enlace profundo; §2.2 del PRD excluye Teams | M6, M7 | Área de Analítica | PRD §10 · Arquitectura §11 |
| **11.6** | Rol "colaborador que aporta fuentes primarias": no existe en el PRD del MVP y §2.2 excluye las fuentes primarias | Modelo de roles y autenticación | — | Arquitectura §11 |
| **11.7** | Set de evaluación: el PRD no define contra qué referencia se evalúa | Carpeta `evaluacion/` | — | Arquitectura §11 |
| **11.3** | "Las 10 capacidades": el PRD define 9 módulos (M1–M9) | Cobertura de jobs y endpoints | — | Arquitectura §11 |

## Decisiones técnicas diferidas

| # | Pendiente | Cuándo | Origen |
|---|---|---|---|
| **11.1** | Frecuencia de ingesta por fuente. El PRD fija un ciclo quincenal único para las tres | Fase 0 | Arquitectura §11 |
| **11.2** | Alcance de la deduplicación. CA-M1.3 dice "entre ciclos", la restricción implementada es por ciclo porque Bing se replica a propósito | Fase 0, si la ingesta pasa a continua | Arquitectura §11 |
| **3b** | Método de autenticación del aplicativo web y hosting aprobado por TI | Semana 5 | PRD §10 |
| **3c** | Definición de los estados de seguimiento y responsable de mantenerlos | Semana 6 | PRD §10 |

## Organizacionales — fuera del control técnico

| # | Pendiente | Decide | Origen |
|---|---|---|---|
| **1** | Quién construye el MVP (interno, contratación o proveedor). Sigue abierto; es el riesgo alto no resuelto de §7 | Gerencia General | PRD §10 |
| **5** | Confirmación de que las 7 gerencias se comprometen a calificar 3 ciclos | Gerencia General | PRD §10 |

---

## Cerrados

| # | Pendiente | Cómo se cerró |
|---|---|---|
| **B2** | **CA-M2.1 sobre el ciclo completo.** | Cerrado 2026-09-18: **95,2% y 94,9%** de reducción sobre los 18 municipios del ciclo 1, en dos pasadas independientes, muy por encima del 85% exigido. El "falta descartar otro 61,4%" salía de lotes de 20-25 señales y nunca se sostuvo. Falta medir los ciclos 2 y 3, pero el criterio se cumple con holgura y de forma estable entre pasadas. Coste real: 628.000 tokens de entrada y 217.000 de salida por pasada, 27 minutos |
| **A3** | **Atribución geográfica (R8).** | **Fuera de alcance del MVP**, decidido 2026-09-18. TerriData **no está cargado** —cero menciones en el snapshot crudo— y D4 lo dejó como requisito de Fase 0, así que no hay nomenclátor del que sacar los 1.103 municipios. Hallazgo documentado para la Fase 0: el patrón no es ruido sino **capital departamental → municipio menor del mismo departamento** (Manizales→La Dorada 31, Barranquilla→Puerto Colombia 20, Pereira→Dosquebradas 10, Apartadó→Chigorodó 8), o sea contratación departamental archivada en la capital y ejecutada fuera. El **0,64% medido es un piso**, no la cifra real: solo detecta menciones a los otros 17 del MVP |
| **A7** | **F5 se anulaba por ausencia de datos de SECOP.** | Cerrado 2026-09-18. El divisor pasa de días cubiertos —que salían solo de fechas de SECOP II— a la **ventana del ciclo**, determinista y nunca cero. Barranquilla con 47 noticias, Armenia con 17 y Cartagena con 2 dejan de quedarse sin F5 por no haber contratado obra. Sube a `v2` en `VERSION_ALGORITMO`: ningún peso cambió, así que la huella no se movió y sin subirla a mano dos algoritmos distintos habrían quedado indistinguibles. **El antes y el después conviven en la base**: ciclo 1 sin cambio; ciclo 2 cambia el primer puesto (Carepa↔Ibagué); ciclo 3 entra Buenaventura y sale Dosquebradas, con 11 de 18 municipios moviéndose. Comparable corrida a corrida porque los pesos son idénticos |
| **B4** | **Estimación de costo y base de H5.** | Cerrado 2026-09-17 con tarifas del tenant (Global Standard, TRM 3.128,46), en `config/tarifas.json`. Verificadas contra los volúmenes medidos: cuadran al céntimo. **Piloto: USD 39/año. Nacional 1.103 municipios: USD 2.160/año.** El costo no es una barrera para la Fase 0. El Correlacionador es el 89% del gasto y su salida de razonamiento sola es el 84%; Batch (−50%) y bajarlo a mini (−71%) se acumulan hasta −86% |
| **B3** | Instalar Python en la máquina de desarrollo | Python 3.12.14 vía uv, sorteando el MSI que bloquea la política corporativa |
| **2** | Lista definitiva de municipios del MVP | Resuelto de facto: los **18** que trae el snapshot, no los 25-30 que preveía §2.1 |
| **B5** | **El Clasificador se truncaba con lotes grandes.** | Cerrado 2026-09-17: el techo era de texto, no de razonamiento. A ~111 tokens de salida por señal, 40 señales daban 4.243 y el corte estaba en 4.096. Techo a 16.384 y troceo de 50 en 50 ordenando por objeto normalizado. Barranquilla c2 completa: 284 señales, 6 lotes, sin truncar |
| **B6** | **M2 no persistía nada.** | Cerrado 2026-09-17: `agentes/persistencia.py` y `ciclo.py` guardan insights, consolidados y trazas. Migración `5ae7d724433d` añade el linaje de origen. Verificado sobre Carepa: 9 insights y 2 trazas en la base |
| **§6 Add. 01** | Diseño del scoring sin TerriData | Addendum 01 **D4**: seis factores de composición y tasa, normalizados por cobertura real |
