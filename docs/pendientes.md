# Pendientes abiertos

Registro único de lo que falta decidir. Consolida [PRD §10](prd.md),
[Addendum 01 §7](addendum-01-fuente-de-datos.md),
[Addendum 02](addendum-02-stack.md) y [Arquitectura §11](architecture.md).

**Actualizado:** 2026-09-18

---

## Bloquean construcción

| # | Pendiente | Bloquea | Decide | Origen |
|---|---|---|---|---|
| **B1** | Clave, endpoint y **nombres de despliegue** de Azure OpenAI en el tenant | M2, M4, M6 — toda llamada a LLM | Área de Analítica | Addendum 02 |
| **A2** | Validar el diccionario de palabras clave de obra sobre el campo `objeto` de SECOP | Precisión de F1, F2 y F3 del scoring | Área de Analítica | Addendum 01 |
| **A3** | **Atribución geográfica (R8).** 0,5% de las señales SECOP hablan de un municipio distinto al que están archivadas, y el caso de Frontino muestra que también entran municipios fuera del MVP. Detectarlo exige un nomenclátor DIVIPOLA de los 1.103 municipios | Credibilidad del informe del top 3 | Área de Analítica | Addendum 01 §4.2 |
| **A4** | **Consolidación del Clasificador.** Tras cuatro versiones del prompt sigue partiendo un mismo frente de obra en varios insights: en Carepa produjo cuatro insights de pavimentación que son un solo frente | Calidad del informe; infla el conteo de insights | Área de Analítica | Afinamiento de prompt |
| **A1 / 4** | Pesos definitivos del score (hay propuesta provisional en Addendum 01 D4) | Calibración de M5 | Gerencia General | PRD §10 · Addendum 01 |
| **A5** | **Dos decisiones de M5 que D4 no cubre.** (a) La **escala común** en que se suman los factores: se implementó min-max por cohorte del ciclo, con el costo de que los scores no son comparables entre ciclos. (b) El **umbral de información** para entrar al top 3: en el ciclo 3, redistribuir el peso deja a Armenia con 0 de 239 días de cobertura, un solo factor vivo y score perfecto — la redistribución premia al que no tiene datos. Se fijó en 50%, configurable | Credibilidad del top 3 del ciclo 3 | Área de Analítica | Implementación de M5, 2026-09-17 |
| **A7** | **F5 se anula por ausencia de datos de SECOP, y mueve el top 3.** La densidad mediática es `n_noticias / dias_cubiertos`, y `dias_cubiertos` sale **solo de fechas de SECOP II** ([agregacion.py:108](../src/territorial/scoring/agregacion.py#L108) solo añade fechas dentro de `if s.fuente == FUENTE_CONTRATOS`). En el ciclo 3, Barranquilla con 47 noticias, Armenia con 17 y Cartagena con 2 tienen F5 no disponible porque no contrataron obra. Son fuentes independientes, y contradice el principio de D4 que el propio módulo cita: «ausencia de dato no es ausencia de actividad». **Medido el 2026-09-18** recalculando los 3 ciclos con `F5 = n_noticias / dias_ventana`: ciclo 1 sin cambio; **ciclo 2 cambia el primer puesto** (Carepa↔Ibagué); **ciclo 3 cambia la composición del top 3** (entra Buenaventura, sale Dosquebradas) y se mueven 11 de 18 municipios — Pereira del 4 al 13, Barranquilla del 17 al 9. Los `no_priorizable` no cambian: los cinco del ciclo 3 siguen fuera. **El arreglo no es cambiar el divisor a días cubiertos por RSS**, que mueve la división por cero en vez de eliminarla (Cartagena tiene 2 noticias que pueden caer el mismo día): la densidad debe calcularse sobre la **ventana temporal del ciclo**, que es determinista y nunca cero. **No se aplica todavía a propósito.** Sobre el esquema actual, `guardar()` hace upsert por `(id_ciclo, divipola)` y sobrescribiría el ranking publicado sin dejar rastro — con calificaciones emitidas eso es la pérdida de trazabilidad que H4 declara bloqueante. Va **después** del cambio a corridas append-only, que deja el antes y el después auditables | Credibilidad del top 3 de los ciclos 2 y 3 | Área de Analítica | Medición de M5, 2026-09-18 |
| **B2** | Confirmar que el Clasificador alcanza CA-M2.1 **sobre el ciclo completo**. Primera medición sobre un municipio entero (Barranquilla c2, 284 señales en 6 lotes): **94,6% de reducción**, por encima del 85%. El "falta otro 61,4%" salía de lotes de 20-25 señales y no se sostiene al procesar el volumen real. Falta medirlo en los 18 municipios de los 3 ciclos | Calibración de M2 | Área de Analítica | Addendum 02 · remedido 2026-09-17 |
| **A6** | **El Clasificador no es reproducible.** El mismo lote de 20 señales de Carepa dio 3 insights en una corrida y 6 en otra. Afecta a H4 y deja sin base la comparación de prompts: `comparar_prompts.py` mide una muestra de uno por versión | Credibilidad de H4 y del afinamiento de prompts | Área de Analítica | Prueba de M4, 2026-09-17 |

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
| **B4** | **Estimación de costo y base de H5.** | Cerrado 2026-09-17 con tarifas del tenant (Global Standard, TRM 3.128,46), en `config/tarifas.json`. Verificadas contra los volúmenes medidos: cuadran al céntimo. **Piloto: USD 39/año. Nacional 1.103 municipios: USD 2.160/año.** El costo no es una barrera para la Fase 0. El Correlacionador es el 89% del gasto y su salida de razonamiento sola es el 84%; Batch (−50%) y bajarlo a mini (−71%) se acumulan hasta −86% |
| **B3** | Instalar Python en la máquina de desarrollo | Python 3.12.14 vía uv, sorteando el MSI que bloquea la política corporativa |
| **2** | Lista definitiva de municipios del MVP | Resuelto de facto: los **18** que trae el snapshot, no los 25-30 que preveía §2.1 |
| **B5** | **El Clasificador se truncaba con lotes grandes.** | Cerrado 2026-09-17: el techo era de texto, no de razonamiento. A ~111 tokens de salida por señal, 40 señales daban 4.243 y el corte estaba en 4.096. Techo a 16.384 y troceo de 50 en 50 ordenando por objeto normalizado. Barranquilla c2 completa: 284 señales, 6 lotes, sin truncar |
| **B6** | **M2 no persistía nada.** | Cerrado 2026-09-17: `agentes/persistencia.py` y `ciclo.py` guardan insights, consolidados y trazas. Migración `5ae7d724433d` añade el linaje de origen. Verificado sobre Carepa: 9 insights y 2 trazas en la base |
| **§6 Add. 01** | Diseño del scoring sin TerriData | Addendum 01 **D4**: seis factores de composición y tasa, normalizados por cobertura real |
