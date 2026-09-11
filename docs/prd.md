# PRD — MVP Inteligencia Territorial
## Pactia · Validación de capacidades agénticas

**Versión:** 1.0 (MVP)
**Fecha:** Septiembre 2026
**Estado:** Borrador para validación
**Relación con el PRD principal:** Este documento define la **Fase -1** del PRD de Inteligencia Territorial v1.2. Es un experimento acotado, no un producto. Su objetivo es validar hipótesis antes de comprometer la Fase 0.
**Duración:** 8 semanas · 3 ciclos quincenales
**Equipo mínimo:** 1 desarrollador (construcción) + 7 gerencias (calificación, ~10 min por ciclo cada una)

---

## 0. Por qué existe este MVP

El PRD principal describe una capacidad de $20.023 M COP/año de impacto potencial, pero descansa sobre supuestos no verificados: que un sistema agéntico puede extraer señal accionable de fuentes públicas colombianas, que las gerencias van a calificar de forma sostenida, y que el Área de Analítica tiene capacidad para operarlo.

Este MVP **compra esos datos antes de construir la capacidad completa.** No busca generar valor de negocio directo; busca eliminar incertidumbre.

**Restricción de origen:** Pactia no dispone de personal para operar el proceso manualmente. Por tanto el MVP debe correr de forma autónoma desde el primer ciclo — lo que se recorta es el alcance de datos y la sofisticación, no la automatización.

---

## 1. Hipótesis a validar

| # | Hipótesis | Cómo se mide | Criterio de éxito |
|---|---|---|---|
| **H1** | El pipeline agéntico produce insights que las gerencias consideran relevantes | Distribución de calificaciones 1-5 | ≥30% de insights con promedio ≥4 **[EST]** |
| **H2** | Las 7 gerencias califican de forma sostenida | Tasa de respuesta por gerencia por ciclo | ≥50% promedio en ciclo 3 **[EST]** |
| **H3** | Las fuentes públicas con API contienen señal accionable | % de insights que sobreviven al validador | ≥60% **[EST]** |
| **H4** | La cadena multiagente preserva la trazabilidad | % de insights con evidencia completa hasta fuente | 100% (bloqueante) |
| **H5** | El costo por ciclo es viable a escala nacional | Tokens y costo por ciclo, extrapolado a 1.103 municipios | Extrapolación documentada |

**Regla de decisión:** si H2 o H4 fallan, el problema no se resuelve con más ingeniería. H2 fallido indica un problema de diseño organizacional; H4 fallido indica que la arquitectura no es auditable y no puede ir a producción.

---

## 2. Alcance del MVP

### 2.1 Qué entra

| Dimensión | Alcance MVP | Alcance PRD completo |
|---|---|---|
| Municipios | **25-30** (capitales + donde Pactia ya tiene activos) | 1.103 |
| Fuentes | **3, todas con API** | Universo abierto |
| Agentes | **4** (Fuentes, Clasificador, Correlacionador, Sintetizador) | 5 (+ Orquestador, con 3 agentes de fuentes en paralelo) |
| Scoring | Reglas deterministas en código | Learning-to-rank + bandits |
| Priorización | **Top 3 fijo** | Top N por umbral de score |
| Ciclo | **Quincenal, disparado por cron** | Continuo (always-on) |
| Persistencia | Postgres | Microsoft Fabric / OneLake |
| Gerencias calificadoras | **7** (sin cambios) | 7 |
| Interfaz | **Aplicativo web propio** (calificación + seguimiento + informes) | Teams / Power Platform integrados al ecosistema Microsoft |

### 2.2 Qué NO entra

- Agente orquestador (su función de planificación es configuración determinista)
- POT, catastro, IGAC — fuentes sin API nacional, alto costo de normalización
- Fuentes primarias (conversaciones, audio, video)
- Umbral de fatiga — con ~6 alertas por ciclo no hay fatiga que suprimir
- Motor de scoring con ML y reentrenamiento
- Acción a demanda
- Base de conocimiento consultable sobre el universo de fuentes (el aplicativo web solo expone los ciclos del MVP, no un buscador general)
- Del aplicativo web quedan fuera: app móvil nativa, edición manual de insights, exportables a herramientas BI, gestión avanzada de usuarios y roles más allá de los 7 perfiles de gerencia + 1 administrador
- Microsoft Fabric, Power Automate, Teams Adaptive Cards
- Aprobación humana de infografía previa a distribución (**ver §7 — Riesgo aceptado**)

### 2.3 Fuentes del MVP

| Fuente | Acceso | Categoría | Qué aporta |
|---|---|---|---|
| **SECOP II** (vía datos.gov.co / SODA API) | API | Contratación pública | Obra pública y licitaciones por municipio — señal temprana de infraestructura |
| **Feed de noticias georreferenciado** (GDELT o equivalente) | API | Noticias | Eventos y anuncios de desarrollo territorial |
| **TerriData / DANE** (dataset descargado y cargado una vez) | Descarga inicial | Datos de desarrollo | Features de contexto municipal: población, economía, vivienda |

> Las tres fuentes se eligieron por un único criterio: **acceso programático sin scraping.** Toda la ingeniería de scraping se difiere a la Fase 0.

---

## 3. Arquitectura

```
   ┌─── CRON quincenal ───┐
   │                      │
   ↓                      │
┌─────────────────────────────────────────────┐
│  CONFIGURACIÓN DETERMINISTA (no agente)     │
│  · lista de municipios del ciclo            │
│  · ventana temporal (últimos 15 días)       │
│  · consultas base por fuente                │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  AGENTE 1 — FUENTES                         │
│  Herramientas:                              │
│   · consultar_secop(municipio, desde)       │
│   · buscar_noticias(municipio, desde)       │
│   · consultar_indicadores(municipio)        │
│  Output: señales_crudas[]                   │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  AGENTE 2 — CLASIFICADOR                    │
│  Descarta ruido · categoriza · DIVIPOLA     │
│  Meta: reducción ≥85%                       │
│  Output: insights[] con evidencia           │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  VALIDADOR DETERMINISTA  (código, no LLM)   │
│  Rechaza todo insight sin URL + fecha +     │
│  cita textual verificable                   │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  AGENTE 3 — CORRELACIONADOR                 │
│  Cruza señales del mismo municipio          │
│  Extrapola implicación inmobiliaria         │
│  ← lee calificaciones de ciclos previos     │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  SCORING POR REGLAS  (código, no LLM)       │
│  → top 3 municipios                         │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  AGENTE 4 — SINTETIZADOR                    │
│  Informe + 3 infografías                    │
│  Prohibido generar cifras propias           │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  APLICATIVO WEB  (única interfaz humana)    │
│  · Bandeja del ciclo → informe del top 3    │
│  · Calificación 1-5 en ≤2 clics             │
│  · Seguimiento de municipios priorizados    │
│  · Histórico de informes por ciclo          │
│  · Panel de métricas (admin)                │
│  Correo = notificación con enlace profundo  │
└──────────────────┬──────────────────────────┘
                   ↓
        7 gerencias → calificación 1-5
                   ↓
              Postgres ──┐
                         └──→ ciclo siguiente
```

### 3.1 Por qué el validador y el scoring NO son agentes

Ambos son código determinista, deliberadamente:

- **Validador:** si un LLM decidiera qué evidencia es suficiente, el experimento perdería su ancla de honestidad. Un agente elocuente parece funcionar aunque invente.
- **Scoring:** si fuera agéntico, no se podría auditar por qué un municipio subió en el ranking. Se perdería la explicabilidad (CA6.3 del PRD principal), que es requisito de producción.

### 3.2 Ausencia del orquestador

La función de planificación del orquestador (qué municipios revisar, qué consultas lanzar) se resuelve con **configuración determinista** en este MVP. Razón: con un solo agente de fuentes, el orquestador no tendría nada que despachar en paralelo ni que consolidar.

**Implicación para la Fase 0:** el contrato de estado entre agentes debe diseñarse de modo que insertar un orquestador después no requiera rediseñar los agentes existentes. El punto de inserción queda documentado en §4.1.

### 3.3 Por qué el aplicativo web reemplaza al formulario suelto

El MVP sustituye el par "correo + formulario" por un **aplicativo web único**, por tres razones:

- **La calificación y el contexto viven juntos.** Un formulario desacoplado obliga a la gerencia a saltar entre el informe y la encuesta. Con el informe y el botón de calificación en la misma pantalla, el requisito de ≤2 clics (CA-M7.1) es real y no nominal.
- **El seguimiento no cabe en un correo.** H1 y la métrica "municipios priorizados que generaron interés de estructuración" exigen registrar qué pasó después con cada municipio del top 3. Eso requiere un estado persistente y editable, no un envío.
- **El histórico es la memoria del experimento.** En el ciclo 3 las gerencias necesitan poder volver a los informes de los ciclos 1 y 2 para calificar con criterio comparable.

**Límite deliberado:** el aplicativo es **de solo lectura sobre el pipeline**. No permite editar insights, relanzar ciclos ni modificar scores. Escribe únicamente calificaciones, comentarios y estado de seguimiento. Así el aplicativo no puede contaminar la evidencia que el MVP está midiendo.

---

## 4. Especificación técnica

### 4.1 Contrato de estado entre agentes

El estado compartido es un único objeto que cada agente enriquece. Este contrato es el activo más importante del MVP: **es lo que permite escalar a la arquitectura completa sin reescribir.**

```
EstadoCiclo {
  id_ciclo · fecha_inicio · ventana_temporal
  municipios_objetivo[]        ← hoy: configuración
                                 mañana: output del ORQUESTADOR
  señales_crudas[]             ← Agente Fuentes
  insights[]                   ← Agente Clasificador
  insights_validados[]         ← Validador (código)
  insights_correlacionados[]   ← Agente Correlacionador
  ranking[]                    ← Scoring (código)
  informe · infografias[]      ← Agente Sintetizador
  calificaciones[]             ← 7 gerencias
  metricas_ciclo{}             ← observabilidad
}
```

> **Punto de inserción del orquestador (Fase 0):** el campo `municipios_objetivo[]` pasa de ser configuración estática a ser output del agente orquestador, sin cambios en los agentes aguas abajo.

### 4.2 Modelo de datos mínimo

```
señal_cruda    (id, id_fuente, fecha_captura, fecha_publicacion,
                contenido, url, municipio_inferido, hash_dedup)

insight        (id, id_señal[], municipio_divipola, categoria,
                resumen, implicacion_inmobiliaria,
                evidencia[] {url, fecha, cita_textual},
                estado_validacion, id_ciclo)

calificacion   (id, id_insight, id_gerencia, valor_1_5,
                comentario, fecha)

municipio      (divipola, nombre, departamento,
                features_scoring{}, score_ciclo, ranking_ciclo)

ciclo          (id, fecha, n_señales, n_insights, n_validados,
                n_rechazados, costo_tokens, duracion_seg)

traza_agente   (id, id_ciclo, agente, input_hash, output_hash,
                tokens, duracion_ms, timestamp)

usuario        (id, id_gerencia, nombre, correo, rol
                {gerencia | administrador}, activo)

seguimiento    (id, municipio_divipola, id_ciclo_origen,
                estado {priorizado | en_revision | en_estructuracion |
                descartado}, responsable, nota, fecha_cambio,
                id_usuario)                    ← escrito desde la app

informe        (id, id_ciclo, fecha_publicacion, ruta_html,
                infografias[], estado {publicado | archivado})
```

> `seguimiento` es una tabla de **historial**, no de estado único: cada cambio inserta una fila. El estado vigente de un municipio es su fila más reciente. Esto permite reconstruir la trayectoria completa de un municipio priorizado a lo largo de los 3 ciclos.

### 4.3 Stack

| Componente | Elección | Justificación |
|---|---|---|
| Orquestación de agentes | **LangGraph** | Con 4 nodos y estado compartido justifica su peso. Checkpointing permite reanudar ciclos fallidos |
| Observabilidad | **Langfuse** (desde el primer commit) | Sin trazas por agente no se puede responder cuál de los 4 falló. Es la pregunta central del MVP |
| Persistencia | **Postgres** | La trazabilidad se prueba con tablas, no con un lakehouse |
| Scheduler | **GitHub Actions** o Azure Function con cron | Cero infraestructura dedicada |
| Aplicativo web | **Una sola app** (framework de stack único, ej. Next.js o Django) sobre la misma Postgres del pipeline | Sin API intermedia ni segundo almacén. La app lee lo que los agentes escribieron; la trazabilidad es la misma tabla, no una copia |
| Autenticación | **Enlace mágico por correo** o SSO corporativo si está disponible | Con 8 usuarios, un login con contraseña añade fricción sin añadir seguridad relevante |
| Distribución | **Correo HTML de notificación** con enlace profundo al informe del ciclo en la app | El correo avisa; el contenido y la calificación viven en la app. El canal definitivo (Teams) se define en Fase 0 |
| Calificación | **Dentro de la app**, en la misma vista del insight | Requisito: ≤2 clics |
| Hosting | Servicio gestionado (Azure App Service, Vercel o equivalente) | Cero infraestructura dedicada; el MVP dura 8 semanas |

---

## 5. Capacidades y criterios de aceptación

### M1 — Ingesta por API (Agente Fuentes)

- **CA-M1.1** — El agente consulta las 3 fuentes para cada municipio del ciclo sin intervención manual.
- **CA-M1.2** — Toda señal cruda se persiste con URL de origen y fecha de publicación original.
- **CA-M1.3** — La deduplicación por hash evita reprocesar la misma señal entre ciclos.
- **CA-M1.4** — Si una fuente falla, el ciclo continúa con las demás y registra el fallo. Un ciclo nunca se aborta por una fuente caída.
- **CA-M1.5** — El agente registra en la traza qué consultas ejecutó y cuántos resultados obtuvo por fuente.

### M2 — Clasificación (Agente Clasificador)

- **CA-M2.1** — Reduce el volumen de señales crudas en **≥85%** por ciclo.
- **CA-M2.2** — Cada insight incluye: municipio DIVIPOLA, categoría, resumen, implicación inmobiliaria y evidencia enlazada.
- **CA-M2.3** — Sin restricción de idioma en el procesamiento (RN-17 del PRD principal).
- **CA-M2.4** — No restringe tipología de activo a priori (RN-08 del PRD principal).
- **CA-M2.5** — Registra en la traza qué descartó y por qué.

### M3 — Validación determinista (código)

- **CA-M3.1** — Rechaza todo insight cuya evidencia no incluya **URL accesible + fecha + cita textual** localizable en la fuente.
- **CA-M3.2** — El insight rechazado se persiste con motivo de rechazo, no se descarta silenciosamente.
- **CA-M3.3** — La tasa de rechazo por ciclo se reporta como métrica primaria (**es la tasa de alucinación medida**).
- **CA-M3.4** — Ningún insight rechazado avanza al correlacionador bajo ninguna circunstancia.

### M4 — Correlación (Agente Correlacionador)

- **CA-M4.1** — Cruza señales de categorías distintas sobre el mismo municipio y genera insight consolidado cuando hay convergencia.
- **CA-M4.2** — Extrapola explícitamente la implicación inmobiliaria de cada señal (ej. natalidad → tipología residencial).
- **CA-M4.3** — Lee las calificaciones de ciclos previos y ajusta su criterio de relevancia. **Este es el bucle de aprendizaje del MVP.**
- **CA-M4.4** — La consolidación preserva la trazabilidad de todas las señales de origen.

### M5 — Scoring y priorización (código)

- **CA-M5.1** — Produce ranking de los municipios del ciclo con score explicable.
- **CA-M5.2** — Combina features objetivas (TerriData/DANE) + calificaciones previas ponderadas por gerencia.
- **CA-M5.3** — Los pesos son configurables sin cambio de código.
- **CA-M5.4** — Selecciona **top 3 fijo**.
- **CA-M5.5** — Para cada municipio del top 3 se puede listar qué factores lo empujaron hacia arriba.

### M6 — Síntesis y distribución (Agente Sintetizador)

- **CA-M6.1** — Genera informe con el top 3, justificación y sugerencias de acción.
- **CA-M6.2** — Genera **una infografía por cada municipio del top 3**.
- **CA-M6.3** — **Ninguna cifra proviene de generación del LLM.** Todas se componen desde el almacén de datos (RN-12 del PRD principal).
- **CA-M6.4** — Cada dato muestra su fuente y fecha.
- **CA-M6.5** — El informe se marca visiblemente como **"MVP — contenido no validado por Analítica"**, tanto en la app como en el correo de notificación.
- **CA-M6.6** — Formato y canal idénticos para las 7 gerencias, sin personalización (RN-14, RN-16 del PRD principal).
- **CA-M6.7** — Al cerrar el ciclo, el informe se **publica en el aplicativo web** y queda disponible de forma permanente; el correo solo notifica con enlace profundo.

### M7 — Calificación (en el aplicativo web)

- **CA-M7.1** — Las 7 gerencias reciben el mismo informe y pueden calificar cada insight de 1-5 en **≤2 clics** desde la misma vista donde lo leen, sin cambiar de herramienta.
- **CA-M7.2** — Las calificaciones son independientes: ninguna gerencia ve la de otra antes de emitir la suya.
- **CA-M7.3** — La ausencia de calificación se registra como `sin_respuesta`, no como calificación baja.
- **CA-M7.4** — Comentario libre opcional.
- **CA-M7.5** — La tasa de respuesta por gerencia se reporta cada ciclo.
- **CA-M7.6** — La calificación se guarda al instante, sin botón de "enviar" final: una gerencia puede calificar 2 insights hoy y 4 mañana sin perder lo hecho.
- **CA-M7.7** — La calificación se cierra al publicarse el ciclo siguiente; los insights de ciclos cerrados quedan visibles pero no editables.

### M9 — Aplicativo web (informes, seguimiento y acceso)

**M9.a — Acceso y navegación**

- **CA-M9.1** — Cada usuario accede con identidad propia asociada a una de las 7 gerencias o al rol administrador. Ninguna cuenta compartida.
- **CA-M9.2** — El enlace profundo del correo lleva directamente al informe del ciclo, autenticando en el mismo paso. Un clic desde el correo hasta el contenido.
- **CA-M9.3** — La app expone tres vistas y solo tres: **Ciclo actual**, **Municipios priorizados** e **Histórico de informes**. El administrador ve además **Métricas**.

**M9.b — Informes de municipios priorizados**

- **CA-M9.4** — La vista de ciclo muestra el informe completo del top 3 con sus 3 infografías, los insights que lo sustentan y la evidencia enlazada de cada uno (URL, fecha, cita textual).
- **CA-M9.5** — Desde cualquier insight se puede navegar a su cadena de trazabilidad completa: `señal → insight → validación → correlación → score` (CA-M8.1 expuesto en interfaz, no solo en base de datos).
- **CA-M9.6** — La justificación del score de cada municipio del top 3 se muestra en la interfaz como lista de factores que lo empujaron hacia arriba (CA-M5.5 expuesto al usuario).
- **CA-M9.7** — Todo informe publicado permanece consultable en el histórico, con su fecha de publicación y el ciclo al que pertenece. Nada se sobrescribe entre ciclos.

**M9.c — Seguimiento de municipios priorizados**

- **CA-M9.8** — Todo municipio que entra al top 3 se crea automáticamente en el tablero de seguimiento con estado inicial `priorizado`. No requiere alta manual.
- **CA-M9.9** — Cualquier gerencia puede cambiar el estado de un municipio entre `priorizado`, `en_revision`, `en_estructuracion` y `descartado`, con nota obligatoria al pasar a `descartado` o `en_estructuracion`.
- **CA-M9.10** — Cada cambio de estado registra usuario, gerencia, fecha y nota, y se conserva como historial: la trayectoria completa del municipio es reconstruible.
- **CA-M9.11** — La ficha de municipio muestra todos los ciclos en que fue priorizado, sus insights acumulados y su calificación promedio, para distinguir un municipio de señal persistente de uno de señal puntual.
- **CA-M9.12** — El tablero permite filtrar por estado, ciclo y departamento, y ordenar por score o por fecha del último cambio.

**M9.d — Métricas (rol administrador)**

- **CA-M9.13** — Panel con las métricas de §6 actualizadas por ciclo: tasa de respuesta por gerencia, distribución de calificaciones, tasa de rechazo del validador y costo por ciclo por agente.
- **CA-M9.14** — La tasa de respuesta es visible por gerencia **solo para el administrador**; ninguna gerencia ve el avance de otra, para no contaminar H2 ni violar CA-M7.2.
- **CA-M9.15** — Exportación a CSV de calificaciones y seguimiento, para el análisis de cierre de la semana 8.

**M9.e — Restricciones**

- **CA-M9.16** — La app **no escribe sobre el pipeline**: no permite editar insights, alterar scores, relanzar ciclos ni cambiar el top 3. Sus únicas escrituras son calificación, comentario y seguimiento.
- **CA-M9.17** — Toda pantalla que muestre contenido generado lleva la marca **"MVP — contenido no validado por Analítica"**.
- **CA-M9.18** — La app es usable en navegador móvil para las vistas de lectura y calificación. No hay app nativa.

### M8 — Trazabilidad y observabilidad

- **CA-M8.1** — Cadena completa consultable: `señal → insight → validación → correlación → score → informe → calificación`.
- **CA-M8.2** — Traza por agente con input, output, tokens y duración (Langfuse).
- **CA-M8.3** — Costo por ciclo desglosado **por agente**.
- **CA-M8.4** — Un ciclo fallido se puede reanudar desde el último checkpoint sin reprocesar desde cero.

---

## 6. Métricas de salida

Al cierre de los 3 ciclos, el MVP entrega estos datos, que hoy son suposiciones en el PRD principal:

| Métrica | Alimenta |
|---|---|
| Distribución de calificaciones 1-5 por gerencia | Ponderación por rol — **pendiente 11 del PRD** |
| Curva de scores de los municipios evaluados | Valor del umbral de score — **pendiente 9 del PRD** |
| Tasa de respuesta por gerencia y su evolución | Viabilidad del diseño de calificación; calibración del umbral de fatiga |
| Grado de acuerdo/divergencia entre gerencias | Diseño del agregador multi-evaluador |
| Tasa de rechazo del validador | Tasa real de alucinación; ajuste de prompts |
| Costo por ciclo por agente | Extrapolación presupuestal a 1.103 municipios |
| Horas reales de intervención humana | Capacidad requerida de Analítica — **pendiente 1 del PRD** |
| Municipios priorizados que generaron interés de estructuración | Primera señal sobre conversión municipio → proyecto — **medida directamente con los estados del tablero de seguimiento (CA-M9.9)** |
| Uso del aplicativo: sesiones por gerencia, tiempo hasta la primera calificación tras la notificación, % de informes abiertos | Distingue "no le interesó" de "no se enteró" — insumo crítico para interpretar H2 |
| Municipios que cambian de estado vs. los que quedan en `priorizado` sin tocar | Señal sobre si el top 3 produce acción o solo lectura |

---

## 7. Riesgos y decisiones aceptadas

| Riesgo | Severidad | Tratamiento |
|---|---|---|
| **Sin revisión humana previa a distribución** (se elimina CA7.5 del PRD) | **Alto — aceptado** | Compensado por el validador determinista + marca "no validado" (CA-M6.5). **En producción CA7.5 debe volver.** Un dato mal interpretado lo ven 7 gerencias a la vez |
| Sin capacidad de desarrollo confirmada | **Alto — no resuelto** | El MVP corre solo, pero alguien debe construirlo. El pendiente 1 del PRD sigue abierto. **Decisión previa: contratar, asignar o usar proveedor** |
| **El aplicativo web añade alcance de construcción a un cronograma de 8 semanas con 1 desarrollador** | **Alto — mitigado** | Se acota con CA-M9.16 (solo lectura sobre el pipeline), 4 vistas, 8 usuarios y autenticación por enlace mágico. Si la semana 5 va con retraso, **el orden de recorte es: panel de métricas → filtros del tablero → histórico**, nunca la calificación ni el informe |
| El tablero de seguimiento se abandona tras el ciclo 1 | Medio | Es un dato, no un fallo: indica que el top 3 no dispara acción. Se mide con la métrica de cambios de estado en §6 |
| Las 3 fuentes pueden no contener señal suficiente | Medio | Es precisamente H3. Un resultado negativo es información válida, no un fracaso |
| Degradación de información entre agentes | Medio | Riesgo estructural del multiagente. Se mide con CA-M8.1 y trazas por agente |
| El orquestador ausente no se valida | Bajo — aceptado | El contrato de estado (§4.1) deja el punto de inserción listo. **No concluir de este MVP que la orquestación escala** |
| 25-30 municipios no representan la diversidad nacional | Bajo | Aceptado: el MVP valida el mecanismo, no la cobertura |

---

## 8. Plan de ejecución

| Semana | Actividad | Entregable |
|---|---|---|
| 1-2 | Conectores a SECOP/Socrata, feed de noticias, carga de TerriData. Modelo de datos en Postgres | Datos de 25-30 municipios consultables |
| 3-4 | Agentes Fuentes y Clasificador. Validador determinista. Langfuse operativo | Pipeline hasta insight validado |
| 5 | Agente Correlacionador + scoring por reglas. Esqueleto del aplicativo web: autenticación, vista de ciclo y calificación (M7, M9.a, M9.b) | Ranking top 3 funcionando + app con informe y calificación operativos |
| 6 | Agente Sintetizador + publicación del informe en la app + correo de notificación con enlace profundo. Tablero de seguimiento (M9.c) | **Ciclo 1 completo publicado y notificado a las 7 gerencias** |
| 7 | Ciclo 2 (con calificaciones del ciclo 1 realimentadas). Histórico de informes y panel de métricas (M9.d) | Ciclo 2 + primeras métricas + app completa |
| 8 | Ciclo 3 + consolidación de métricas + exportación CSV | **Informe de resultados y recomendación go/no-go** |

> **Regla de recorte:** si la semana 5 termina con retraso, se sacrifica funcionalidad de la app en el orden definido en §7, nunca la vista de informe ni la calificación — sin ellas no hay H1 ni H2 que medir.

---

## 9. Compuerta de decisión

Al cierre de la semana 8, la decisión sobre la Fase 0 se toma con estos criterios:

**GO** — H2 y H4 cumplidos, y al menos dos de H1/H3/H5 en rango aceptable. Se procede a Fase 0 con umbrales calibrados con datos reales.

**GO CONDICIONADO** — H4 cumplido pero H2 bajo. El problema es de adopción, no de tecnología. Se rediseña el mecanismo de calificación antes de escalar.

**NO-GO** — H4 incumplido (trazabilidad rota) o H1 y H3 ambos por debajo del criterio. La arquitectura no es auditable o las fuentes no contienen señal. En ambos casos, escalar amplificaría el problema.

---

## 10. Pendientes de decisión del MVP

| # | Pendiente | Bloquea | Responsable |
|---|---|---|---|
| 1 | **Quién construye el MVP** (interno, contratación o proveedor) | Todo el cronograma | Gerencia General |
| 2 | Lista definitiva de los 25-30 municipios del MVP | Semana 1 | Gerencia General + Estrategia de Portafolio |
| 3 | Canal de **notificación** del MVP (correo corporativo vs. otro) — el contenido y la calificación viven en el aplicativo web en cualquier caso | Semana 6 | Área de Analítica |
| 3b | Método de autenticación del aplicativo web (enlace mágico propio vs. SSO corporativo) y hosting aprobado por TI | Semana 5 | Área de Analítica + TI |
| 3c | Definición de los estados de seguimiento y quién es responsable de mantenerlos actualizados por municipio | Semana 6 | Gerencia General + Estrategia de Portafolio |
| 4 | Pesos iniciales del scoring por reglas | Semana 5 | Gerencia General |
| 5 | Confirmación de que las 7 gerencias se comprometen a calificar 3 ciclos | H2 completo | Gerencia General |

---

## Anexo — Trazabilidad con el PRD principal

Este MVP preserva sin cambios las reglas de negocio RN-03 (calificación independiente), RN-08 (sin restricción de tipología), RN-09 (granularidad municipio), RN-12 (ninguna cifra generada sin fuente), RN-14 (formato estandarizado), RN-16 (alerta idéntica), RN-17 (sin restricción de idioma) y RN-18 (municipio origina proyecto, no lo reemplaza).

Difiere deliberadamente en RN-01 (continuo → quincenal), RN-05 y RN-19 (top N por umbral → top 3 fijo), RN-02 (umbral de relevancia → sin umbral de fatiga) y en la ausencia de CA7.5 (revisión humana previa).
