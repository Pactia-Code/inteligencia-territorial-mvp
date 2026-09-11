# Pendientes abiertos

Registro único de lo que falta decidir. Consolida [PRD §10](prd.md),
[Addendum 01 §7](addendum-01-fuente-de-datos.md),
[Addendum 02](addendum-02-stack.md) y [Arquitectura §11](architecture.md).

**Actualizado:** 2026-09-11

---

## Bloquean construcción

| # | Pendiente | Bloquea | Decide | Origen |
|---|---|---|---|---|
| **B1** | Clave, endpoint y **nombres de despliegue** de Azure OpenAI en el tenant | M2, M4, M6 — toda llamada a LLM | Área de Analítica | Addendum 02 |
| **B4** | Rehacer la estimación de costo tras el cambio a Azure OpenAI: verificar disponibilidad de batch, mecanismo de caching y tarifas reales del tenant | **H5** — la extrapolación a 1.103 municipios quedó sin base | Área de Analítica | Addendum 02 D6.3 |
| **A2** | Validar el diccionario de palabras clave de obra sobre el campo `objeto` de SECOP | Precisión de F1, F2 y F3 del scoring | Área de Analítica | Addendum 01 |
| **A1 / 4** | Pesos definitivos del score (hay propuesta provisional en Addendum 01 D4) | Calibración de M5 | Gerencia General | PRD §10 · Addendum 01 |
| **B2** | Confirmar que el despliegue del Clasificador alcanza CA-M2.1. El prefiltro solo reduce 61,2%, así que el Clasificador debe descartar otro **61,4%** de lo que recibe — no es un ajuste fino | Calibración de M2 | Área de Analítica | Addendum 02 |

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
| **B3** | Instalar Python en la máquina de desarrollo | Python 3.12.14 vía uv, sorteando el MSI que bloquea la política corporativa |
| **2** | Lista definitiva de municipios del MVP | Resuelto de facto: los **18** que trae el snapshot, no los 25-30 que preveía §2.1 |
| **§6 Add. 01** | Diseño del scoring sin TerriData | Addendum 01 **D4**: seis factores de composición y tasa, normalizados por cobertura real |
