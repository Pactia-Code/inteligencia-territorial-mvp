# Línea base para la auditoría — lo que el PRD exige

**Fuente:** [docs/prd.md](prd.md), «PRD — MVP Inteligencia Territorial», versión 1.0
(MVP), septiembre 2026, tal como está en el commit **`96e10e0`** (rama
`audit/2026-09-22`). Es el único documento de requisitos del repositorio. El PRD
principal v1.2 del que se declara Fase -1 **no está en el repo** (pendiente 11.5);
todo lo que aquí se cita de él —RN-xx, CA6.3, CA7.5, pendientes 1/9/11— se cita
de segunda mano, tal como el PRD del MVP lo nombra, y **no se puede verificar**.

Este documento **no añade ni reinterpreta requisitos**: extrae los del PRD con su
sección de origen, para que una auditoría tenga contra qué comparar el código.
Donde otro documento del repositorio ha registrado una desviación autorizada, se
anota en la columna «Desviación registrada» con el identificador de la decisión
en [pendientes.md](pendientes.md); la autoridad del criterio original no cambia.

Al final (§10) está lo que el PRD **no define** y una auditoría necesitaría.

---

## 1. Hipótesis y métricas de éxito

### 1.1 Las cinco hipótesis (PRD §1)

| # | Hipótesis | Cómo se mide | Criterio de éxito | Carácter |
|---|---|---|---|---|
| **H1** | El pipeline produce insights que las gerencias consideran relevantes | Distribución de calificaciones 1-5 | ≥30% de insights con promedio ≥4 | `[EST]` — umbral estimado |
| **H2** | Las 7 gerencias califican de forma sostenida | Tasa de respuesta por gerencia por ciclo | ≥50% promedio en el ciclo 3 | `[EST]` |
| **H3** | Las fuentes públicas con API contienen señal accionable | % de insights que sobreviven al validador | ≥60% | `[EST]` |
| **H4** | La cadena multiagente preserva la trazabilidad | % de insights con evidencia completa hasta la fuente | **100%** | **Bloqueante** — el único así marcado |
| **H5** | El costo por ciclo es viable a escala nacional | Tokens y costo por ciclo, extrapolado a 1.103 municipios | «Extrapolación documentada» | Sin umbral numérico |

**Regla de decisión (§1):** si H2 o H4 fallan, el problema no se resuelve con más
ingeniería. H2 fallido es un problema organizacional; H4 fallido significa que la
arquitectura no es auditable y no puede ir a producción.

### 1.2 Compuerta go/no-go (PRD §9)

| Veredicto | Condición |
|---|---|
| **GO** | H2 y H4 cumplidos, y al menos dos de H1/H3/H5 en rango aceptable |
| **GO CONDICIONADO** | H4 cumplido pero H2 bajo → rediseñar el mecanismo de calificación antes de escalar |
| **NO-GO** | H4 incumplido, **o** H1 y H3 ambos por debajo del criterio |

### 1.3 Métricas de salida (PRD §6)

Diez métricas que el MVP debe entregar al cierre de los tres ciclos:

1. Distribución de calificaciones 1-5 por gerencia → pendiente 11 del PRD principal
2. Curva de scores de los municipios evaluados → pendiente 9 del PRD principal
3. Tasa de respuesta por gerencia y su evolución
4. Grado de acuerdo/divergencia entre gerencias
5. Tasa de rechazo del validador (= tasa real de alucinación)
6. Costo por ciclo **por agente**
7. Horas reales de intervención humana → pendiente 1 del PRD principal
8. Municipios priorizados que generaron interés de estructuración — «medida
   directamente con los estados del tablero de seguimiento (CA-M9.9)»
9. Uso del aplicativo: sesiones por gerencia, tiempo hasta la primera calificación
   tras la notificación, % de informes abiertos
10. Municipios que cambian de estado vs. los que quedan en `priorizado` sin tocar

---

## 2. Alcance

### 2.1 Incluido (PRD §2.1)

| Dimensión | Alcance MVP | Desviación registrada |
|---|---|---|
| Municipios | **25-30** (capitales + donde Pactia tiene activos) | Pendiente 2, cerrado: **18**, los del snapshot |
| Fuentes | **3, todas con API**: SECOP II, feed de noticias, TerriData/DANE (§2.3) | Addendum 01 §1: snapshot estático con SECOP, RSS, Bing y ELIC; TerriData cargado solo como contexto (D4, A10) |
| Agentes | **4**: Fuentes, Clasificador, Correlacionador, Sintetizador | — |
| Scoring | Reglas deterministas en código | — |
| Priorización | **Top 3 fijo** | `P1`: tope fijo de **10**; el aviso del propio PRD lo registra |
| Ciclo | **Quincenal, disparado por cron** | Addendum 01 D2 (tres ventanas de 51/84/239 días) y Addendum 02 D9 (ejecución manual) |
| Persistencia | Postgres | Addendum 02 D8: SQLite local / PostgreSQL nube |
| Gerencias calificadoras | **7** | — |
| Interfaz | **Aplicativo web propio** (calificación + seguimiento + informes) | `M9-fw`: Next.js en Vercel |

**Criterio de selección de fuentes (§2.3):** «acceso programático sin scraping».
Todo scraping se difiere a Fase 0.

### 2.2 Explícitamente excluido (PRD §2.2)

- Agente orquestador (su planificación es configuración determinista — §3.2)
- POT, catastro, IGAC
- Fuentes primarias (conversaciones, audio, video)
- Umbral de fatiga
- Motor de scoring con ML y reentrenamiento
- Acción a demanda
- Base de conocimiento consultable / buscador general sobre fuentes
- De la app: app móvil nativa, edición manual de insights, exportables a BI,
  gestión de usuarios y roles más allá de **7 perfiles de gerencia + 1 administrador**
- Microsoft Fabric, Power Automate, Teams Adaptive Cards
- Aprobación humana de la infografía previa a distribución (**riesgo aceptado, §7**)

### 2.3 Límite de la app sobre el pipeline (PRD §3.3, CA-M9.16)

«El aplicativo es **de solo lectura sobre el pipeline**. No permite editar
insights, relanzar ciclos ni modificar scores. Escribe únicamente calificaciones,
comentarios y estado de seguimiento.»

---

## 3. Reglas de negocio

### 3.1 Heredadas del PRD principal (PRD Anexo)

Preservadas sin cambios: **RN-03** (calificación independiente), **RN-08** (sin
restricción de tipología de activo), **RN-09** (granularidad municipio), **RN-12**
(ninguna cifra generada sin fuente), **RN-14** (formato estandarizado), **RN-16**
(alerta idéntica), **RN-17** (sin restricción de idioma), **RN-18** (el municipio
origina el proyecto, no lo reemplaza).

Diferidas deliberadamente: **RN-01** (continuo → quincenal), **RN-05** y **RN-19**
(top N por umbral → top 3 fijo), **RN-02** (umbral de relevancia → sin umbral de
fatiga), y la ausencia de **CA7.5** (revisión humana previa).

> Los textos de estas RN no están en el repositorio. Solo se conoce el paréntesis
> con que el PRD del MVP las resume.

### 3.2 Reglas propias del PRD del MVP

| Regla | Sección |
|---|---|
| El MVP **corre de forma autónoma desde el primer ciclo**; lo que se recorta es alcance y sofisticación, nunca la automatización | §0 |
| El **validador** es código, no LLM: «si un LLM decidiera qué evidencia es suficiente, el experimento perdería su ancla de honestidad» | §3.1 |
| El **scoring** es código, no LLM, para conservar la explicabilidad (CA6.3 del PRD principal) | §3.1 |
| Sin orquestador: la planificación es **configuración determinista**; el contrato de estado debe permitir insertarlo después sin rediseñar los agentes | §3.2, §4.1 |
| **La calificación y el contexto viven juntos** en la misma pantalla | §3.3 |
| La app **escribe solo** calificación, comentario y estado de seguimiento; no toca insights, scores, ciclos ni top 3 | §3.3, CA-M9.16 |
| **Ninguna cifra proviene del LLM**; todas se componen desde el almacén | CA-M6.3 |
| Cada dato muestra **su fuente y su fecha** | CA-M6.4 |
| Contenido generado se marca **«MVP — contenido no validado por Analítica»**, en app y en correo | CA-M6.5, CA-M9.17 |
| Formato y canal **idénticos** para las 7 gerencias, sin personalización | CA-M6.6 |
| Ningún insight **rechazado** avanza al correlacionador, «bajo ninguna circunstancia» | CA-M3.4 |
| El rechazado se **persiste con motivo**, nunca se descarta en silencio | CA-M3.2 |
| La **tasa de rechazo es la tasa de alucinación medida** y se reporta como métrica primaria | CA-M3.3 |
| Sin restricción de **idioma** ni de **tipología** en la clasificación | CA-M2.3, CA-M2.4 |
| Calificaciones **independientes**: ninguna gerencia ve la de otra antes de emitir la suya | CA-M7.2, CA-M9.14 |
| La ausencia de calificación es **`sin_respuesta`**, no una calificación baja | CA-M7.3 |
| La calificación se guarda **al instante**, sin botón de enviar | CA-M7.6 |
| La calificación **se cierra al publicarse el ciclo siguiente**; lo cerrado queda visible, no editable | CA-M7.7 |
| **Nada se sobrescribe entre ciclos**; todo informe publicado permanece | CA-M9.7 |
| Todo municipio del top entra al tablero **automáticamente** con estado `priorizado` | CA-M9.8 |
| Estados de seguimiento: `priorizado`, `en_revision`, `en_estructuracion`, `descartado`; **nota obligatoria** al pasar a los dos últimos | CA-M9.9 |
| `seguimiento` es **historial**, no estado único: cada cambio inserta una fila; el vigente es la más reciente | §4.2 (nota), CA-M9.10 |
| Roles: **7 gerencias + 1 administrador**; ninguna cuenta compartida | §2.2, CA-M9.1 |
| La tasa de respuesta por gerencia la ve **solo el administrador** | CA-M9.14 |
| Un ciclo **nunca se aborta** por una fuente caída | CA-M1.4 |
| Un ciclo fallido se **reanuda desde el último checkpoint** | CA-M8.4 |
| **Sin revisión humana previa** a la distribución; en producción CA7.5 debe volver | §7 |

---

## 4. Criterios de aceptación (PRD §5)

Cincuenta y nueve criterios en nueve módulos. Código y orden tal como aparecen
en el PRD (M8 va después de M9 en el original). El resumen es de una línea; el
texto íntegro está en §5 del PRD. La columna «Desviación registrada» remite al
identificador en [pendientes.md](pendientes.md) o al addendum; vacía significa
que ningún documento del repo registra desviación.

### M1 — Ingesta por API (Agente Fuentes)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M1.1 | Consulta las 3 fuentes por municipio del ciclo sin intervención manual | Addendum 01 §5: pasa a «carga las 4 fuentes del snapshot y particiona por ventana» |
| CA-M1.2 | Toda señal cruda se persiste con URL de origen y fecha de publicación original | |
| CA-M1.3 | Deduplicación por hash entre ciclos | 11.2: implementada por ciclo, no entre ciclos (Bing se replica) |
| CA-M1.4 | Si una fuente falla, el ciclo continúa con las demás y registra el fallo | Addendum 01 §5: **sin validar** — no hay fuente viva que caiga |
| CA-M1.5 | La traza registra qué consultas se ejecutaron y cuántos resultados por fuente | |

### M2 — Clasificación (Agente Clasificador)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M2.1 | Reduce el volumen de señales crudas en **≥85%** por ciclo | |
| CA-M2.2 | Cada insight trae municipio DIVIPOLA, categoría, resumen, implicación inmobiliaria y evidencia enlazada | |
| CA-M2.3 | Sin restricción de idioma (RN-17) | |
| CA-M2.4 | No restringe tipología de activo a priori (RN-08) | |
| CA-M2.5 | Registra en la traza qué descartó y por qué | |

### M3 — Validación determinista (código)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M3.1 | Rechaza todo insight sin **URL accesible + fecha + cita textual** localizable en la fuente | Addendum 01 §5 precisa qué campos son URL/fecha/cita por fuente |
| CA-M3.2 | El rechazado se persiste con motivo de rechazo | |
| CA-M3.3 | La tasa de rechazo por ciclo se reporta como **métrica primaria** (tasa de alucinación medida) | |
| CA-M3.4 | Ningún rechazado avanza al correlacionador, bajo ninguna circunstancia | |

### M4 — Correlación (Agente Correlacionador)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M4.1 | Cruza señales de categorías distintas del mismo municipio y consolida cuando hay convergencia | |
| CA-M4.2 | Extrapola explícitamente la implicación inmobiliaria de cada señal | |
| CA-M4.3 | Lee calificaciones de ciclos previos y ajusta su criterio — **el bucle de aprendizaje del MVP** | |
| CA-M4.4 | La consolidación preserva la trazabilidad de todas las señales de origen | |

### M5 — Scoring y priorización (código)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M5.1 | Ranking de los municipios del ciclo con score explicable | |
| CA-M5.2 | Combina features objetivas (TerriData/DANE) + calificaciones previas ponderadas por gerencia | Addendum 01 D4/§6: features de SECOP y ELIC en lugar de TerriData; F6 íntegro |
| CA-M5.3 | Pesos configurables sin cambio de código | |
| CA-M5.4 | Selecciona **top 3 fijo** | `P1`: tope fijo de 10, umbral de información en 0 (aviso del PRD) |
| CA-M5.5 | Para cada municipio del top 3 se puede listar qué factores lo empujaron | |

### M6 — Síntesis y distribución (Agente Sintetizador)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M6.1 | Informe con el top 3, justificación y sugerencias de acción | |
| CA-M6.2 | **Una infografía por municipio** del top 3 | |
| CA-M6.3 | **Ninguna cifra proviene del LLM**; todas se componen desde el almacén (RN-12) | |
| CA-M6.4 | Cada dato muestra su fuente y fecha | |
| CA-M6.5 | Marca visible «MVP — contenido no validado por Analítica», en app y en correo | `M6-aviso`: se muestra solo «MVP»; el texto completo viaja en el payload |
| CA-M6.6 | Formato y canal idénticos para las 7 gerencias (RN-14, RN-16) | |
| CA-M6.7 | Al cerrar el ciclo el informe se publica en la app de forma permanente; el correo solo notifica con enlace profundo | `11.4/3`: no hay envío de correos (aviso del PRD) |

### M7 — Calificación (en el aplicativo web)

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M7.1 | Las 7 gerencias reciben el mismo informe y califican cada insight 1-5 en **≤2 clics** desde la misma vista | `M9-carga`/`M9-sel`: se **pide** calificar 5 insights por municipio en los 3 primeros; el resto es opcional |
| CA-M7.2 | Calificaciones independientes: nadie ve la de otra gerencia antes de emitir la suya | |
| CA-M7.3 | La ausencia se registra como `sin_respuesta`, no como calificación baja | |
| CA-M7.4 | Comentario libre opcional | |
| CA-M7.5 | La tasa de respuesta por gerencia se reporta cada ciclo | |
| CA-M7.6 | Guardado instantáneo, sin botón de enviar final; se puede calificar en varios días | |
| CA-M7.7 | La calificación se cierra al publicarse el ciclo siguiente; lo cerrado es visible y no editable | |

### M9 — Aplicativo web (informes, seguimiento y acceso)

**M9.a — Acceso y navegación**

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M9.1 | Cada usuario accede con identidad propia asociada a una gerencia o al rol administrador; sin cuentas compartidas | `3b`/`M9-acceso`: sin autenticación; identificación por correo contra lista precargada (aviso del PRD) |
| CA-M9.2 | El enlace profundo del correo lleva al informe autenticando en el mismo paso; un clic | `11.4/3` y `M9-acceso`: no hay correo ni autenticación |
| CA-M9.3 | Tres vistas y solo tres: **Ciclo actual**, **Municipios priorizados**, **Histórico**; el administrador ve además **Métricas** | |

**M9.b — Informes de municipios priorizados**

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M9.4 | La vista de ciclo muestra el informe completo del top 3 con sus 3 infografías, insights y evidencia (URL, fecha, cita) | `P1`: 10 municipios |
| CA-M9.5 | Desde cualquier insight se navega a su cadena completa `señal → insight → validación → correlación → score` | |
| CA-M9.6 | La justificación del score se muestra como lista de factores que lo empujaron (CA-M5.5 expuesto) | `M6-src`: al usuario se le muestran nombres de fuente, no códigos de factor |
| CA-M9.7 | Todo informe publicado permanece en el histórico con fecha y ciclo; nada se sobrescribe | |

**M9.c — Seguimiento de municipios priorizados**

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M9.8 | Todo municipio que entra al top 3 se crea en el tablero con estado `priorizado`, sin alta manual | |
| CA-M9.9 | Cualquier gerencia cambia el estado entre los cuatro definidos; nota obligatoria al pasar a `descartado` o `en_estructuracion` | |
| CA-M9.10 | Cada cambio registra usuario, gerencia, fecha y nota, y se conserva como historial | |
| CA-M9.11 | La ficha de municipio muestra todos los ciclos en que fue priorizado, sus insights acumulados y su calificación promedio | |
| CA-M9.12 | El tablero filtra por estado, ciclo y departamento, y ordena por score o fecha del último cambio | |

**M9.d — Métricas (rol administrador)**

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M9.13 | Panel con las métricas de §6 por ciclo: tasa de respuesta por gerencia, distribución de calificaciones, tasa de rechazo, costo por ciclo por agente | |
| CA-M9.14 | La tasa de respuesta por gerencia es visible **solo para el administrador** | |
| CA-M9.15 | Exportación a CSV de calificaciones y seguimiento | |

**M9.e — Restricciones**

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M9.16 | La app **no escribe sobre el pipeline**; sus únicas escrituras son calificación, comentario y seguimiento | |
| CA-M9.17 | Toda pantalla con contenido generado lleva la marca «MVP — contenido no validado por Analítica» | `M6-aviso`: solo «MVP» |
| CA-M9.18 | Usable en navegador móvil para lectura y calificación; sin app nativa | |

### M8 — Trazabilidad y observabilidad

| Código | Resumen | Desviación registrada |
|---|---|---|
| CA-M8.1 | Cadena completa consultable: `señal → insight → validación → correlación → score → informe → calificación` | |
| CA-M8.2 | Traza por agente con input, output, tokens y duración (Langfuse) | |
| CA-M8.3 | Costo por ciclo desglosado **por agente** | |
| CA-M8.4 | Un ciclo fallido se reanuda desde el último checkpoint sin reprocesar desde cero | |

> El PRD no define criterios para un «M0» ni para un módulo de configuración; los
> nueve módulos son M1–M9. La mención a «10 capacidades» de otros documentos no
> tiene correlato en el PRD (pendiente 11.3).

---

## 5. Modelo de datos y contrato de estado

### 5.1 Contrato de estado entre agentes (PRD §4.1)

El PRD lo declara «el activo más importante del MVP»: un único objeto que cada
agente enriquece.

```
EstadoCiclo {
  id_ciclo · fecha_inicio · ventana_temporal
  municipios_objetivo[]        ← hoy: configuración; mañana: output del ORQUESTADOR
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

Punto de inserción del orquestador (Fase 0): `municipios_objetivo[]` pasa de
configuración a output del agente, «sin cambios en los agentes aguas abajo».

Se define **a nivel de nombre de campo**; no hay tipos, cardinalidades ni
versionado del contrato (ver §10).

### 5.2 Modelo de datos mínimo (PRD §4.2)

Nueve entidades, con sus campos tal como el PRD los enumera:

| Entidad | Campos |
|---|---|
| `señal_cruda` | id, id_fuente, fecha_captura, fecha_publicacion, contenido, url, municipio_inferido, hash_dedup |
| `insight` | id, id_señal[], municipio_divipola, categoria, resumen, implicacion_inmobiliaria, evidencia[] {url, fecha, cita_textual}, estado_validacion, id_ciclo |
| `calificacion` | id, id_insight, id_gerencia, valor_1_5, comentario, fecha |
| `municipio` | divipola, nombre, departamento, features_scoring{}, score_ciclo, ranking_ciclo |
| `ciclo` | id, fecha, n_señales, n_insights, n_validados, n_rechazados, costo_tokens, duracion_seg |
| `traza_agente` | id, id_ciclo, agente, input_hash, output_hash, tokens, duracion_ms, timestamp |
| `usuario` | id, id_gerencia, nombre, correo, rol {gerencia \| administrador}, activo |
| `seguimiento` | id, municipio_divipola, id_ciclo_origen, estado {priorizado \| en_revision \| en_estructuracion \| descartado}, responsable, nota, fecha_cambio, id_usuario — «escrito desde la app» |
| `informe` | id, id_ciclo, fecha_publicacion, ruta_html, infografias[], estado {publicado \| archivado} |

Regla explícita: `seguimiento` es tabla de **historial**; el estado vigente es la
fila más reciente.

Se llama «mínimo»: el PRD no define claves, unicidades, tipos ni relaciones más
allá de los nombres. El esquema real está en `src/territorial/almacen/modelos.py`
y en las migraciones de `alembic/`; la correspondencia con esta tabla la describe
[architecture.md §3](architecture.md) (con aviso de desactualización).

### 5.3 Stack exigido (PRD §4.3)

| Componente | Exigencia del PRD | Desviación registrada |
|---|---|---|
| Orquestación | **LangGraph**, con checkpointing | CLAUDE.md §4: instalado, **sin cablear**; no hay `grafo/` |
| Observabilidad | **Langfuse desde el primer commit** | CLAUDE.md §4: instalado, sin cablear |
| Persistencia | Postgres | D8: SQLite local, Neon en nube |
| Scheduler | GitHub Actions o Azure Function con cron | D9: ejecución manual en el MVP |
| Aplicativo web | Una sola app (Next.js o Django) sobre la misma Postgres, **sin API intermedia ni segundo almacén** | `M9-fw`: Next.js, lee Neon directamente |
| Autenticación | Enlace mágico por correo o SSO | `3b`/`M9-acceso`: ninguna |
| Distribución | Correo HTML con enlace profundo | `11.4/3`: ninguna |
| Calificación | Dentro de la app, misma vista, ≤2 clics | — |
| Hosting | Servicio gestionado (App Service, Vercel o equivalente) | Vercel |

---

## 6. Vistas y pantallas

### 6.1 Lo que el PRD define

El diagrama de §3 enumera para el aplicativo web: bandeja del ciclo → informe del
top 3 · calificación 1-5 en ≤2 clics · seguimiento de municipios priorizados ·
histórico de informes · panel de métricas (admin) · «correo = notificación con
enlace profundo».

**CA-M9.3** lo fija: **tres vistas y solo tres** —Ciclo actual, Municipios
priorizados, Histórico— más **Métricas** para el administrador. Los criterios que
detallan cada una:

| Vista | Criterios que la definen |
|---|---|
| Ciclo actual | CA-M9.4 (informe, infografías, insights, evidencia), CA-M9.5 (navegar a la cadena de trazabilidad), CA-M9.6 (factores del score), CA-M7.1/7.4/7.6 (calificar y comentar en la misma vista), CA-M6.5/9.17 (marca MVP) |
| Municipios priorizados | CA-M9.8 (alta automática), CA-M9.9/9.10 (cambio de estado con historial), CA-M9.11 (**ficha de municipio**), CA-M9.12 (filtros y orden) |
| Histórico | CA-M9.7 (todo informe publicado, con fecha y ciclo), CA-M7.7 (cerrados visibles, no editables) |
| Métricas (admin) | CA-M9.13 (cuatro métricas), CA-M9.14 (tasa por gerencia solo admin), CA-M9.15 (CSV) |
| Transversal | CA-M9.18 (móvil para lectura y calificación), CA-M9.1/9.2 (acceso) |

Dos elementos no encajan limpiamente en «tres vistas»: la **cadena de
trazabilidad** de CA-M9.5 y la **ficha de municipio** de CA-M9.11. El PRD no dice
si son vistas, rutas o despliegues dentro de las tres.

### 6.2 Quién las especifica en el repositorio

| Documento | Qué especifica de las vistas | Autoridad |
|---|---|---|
| [design-system.md](design-system.md) §2 | **Vista de ciclo** en detalle: encabezado (§2.1), lista de diez filas con zonas y tokens (§2.2), línea de fuentes (§2.3), bloque de calificación (§2.4) | Autoridad de color y tipografía (CLAUDE.md §1); estructura derivada de decisiones `P1`, `M6-orden`, `M6-src`, `M9-carga` |
| design-system.md §3 | **Detalle de municipio** como despliegue lateral, no ruta: anatomía del dato (§3.1), contexto estructural (§3.2), evidencia en tres niveles (§3.3), score explicable (§3.4) | Ídem |
| design-system.md §4 | Priorizados (§4.1), Histórico (§4.2) y Métricas (§4.3), **un párrafo cada una**; sin anatomía de pantalla | Ídem |
| design-system.md §5, §6 | Estados cargando/error/vacío; móvil (CA-M9.18) | Ídem |
| [architecture.md](architecture.md) §6.2 | Tabla de **rutas** por criterio (`/ciclo/<n>/`, `/insight/<id>/trazabilidad/`, `/priorizados/`, `/municipio/<divipola>/`, `/historico/`, `/metricas/`, `/entrar/<token>/`) | Descriptivo, de la época Django; lleva aviso de superado. Es la única enumeración ruta-a-criterio del repo |
| `especificacion_ui_inteligencia_territorial.md` | Referencia de **estructura** según CLAUDE.md §1 | **No está en el repositorio.** El usuario la declaró desactualizada el 2026-09-22; no forma parte de esta línea base |

**La infografía por municipio (CA-M6.2, CA-M9.4) no está especificada en ningún
documento del repositorio**: ni contenido, ni formato, ni cómo se compone sin
cifras del LLM.

---

## 7. Lo que el PRD marca como bloqueante o crítico

El PRD usa la palabra **«bloqueante» una sola vez**: en H4 (§1). No asigna
severidad ni prioridad a ningún criterio de aceptación individual. Lo que sí hace
es subrayar algunos por énfasis o por consecuencia declarada:

| Elemento | Cómo lo marca el PRD | Sección |
|---|---|---|
| **H4** — trazabilidad al 100% | «(bloqueante)»; si falla, «la arquitectura no es auditable y no puede ir a producción»; NO-GO directo | §1, §9 |
| **H2** — respuesta sostenida | Su fallo «no se resuelve con más ingeniería»; hipótesis necesaria para el GO | §1, §9 |
| **CA-M6.3** — ninguna cifra del LLM | En negrita; hereda RN-12 | §5 |
| **CA-M3.3** — tasa de rechazo | «Métrica primaria», «es la tasa de alucinación medida» | §5 |
| **CA-M3.4** — rechazados no avanzan | «Bajo ninguna circunstancia» | §5 |
| **CA-M4.3** — realimentación de calificaciones | «Este es el bucle de aprendizaje del MVP» | §5 |
| **CA-M9.16** — la app no escribe sobre el pipeline | Es lo que mitiga el riesgo alto de alcance de la app | §3.3, §7 |
| **Contrato de estado** | «El activo más importante del MVP» | §4.1 |
| **Vista de informe y calificación** | «Nunca» se recortan: «sin ellas no hay H1 ni H2 que medir» | §7, §8 |
| **Validador y scoring como código** | Ancla de honestidad y explicabilidad del experimento | §3.1 |
| **Langfuse desde el primer commit** | «Sin trazas por agente no se puede responder cuál de los 4 falló. Es la pregunta central del MVP» | §4.3 |

Riesgos de severidad **alta** (§7): sin revisión humana previa (**aceptado**), sin
capacidad de desarrollo confirmada (**no resuelto**), la app añade alcance a 8
semanas con 1 desarrollador (**mitigado** por CA-M9.16, 4 vistas, 8 usuarios,
enlace mágico).

---

## 8. Orden de recorte de alcance

Definido en **§7** (fila del riesgo de la app) y reiterado en **§8**:

> Si la semana 5 va con retraso, el orden de recorte es:
> **panel de métricas → filtros del tablero → histórico**,
> nunca la calificación ni el informe.

El [Design System §4](design-system.md) adopta el mismo orden para la construcción
de las vistas secundarias.

Plan de ejecución (§8), como referencia de qué debía existir cuándo:

| Semana | Entregable |
|---|---|
| 1-2 | Conectores, TerriData, modelo de datos en Postgres |
| 3-4 | Fuentes + Clasificador + Validador + Langfuse operativo |
| 5 | Correlacionador + scoring; app con autenticación, vista de ciclo y calificación |
| 6 | Sintetizador + publicación + correo; tablero de seguimiento. **Ciclo 1 publicado y notificado** |
| 7 | Ciclo 2 con realimentación; histórico y panel de métricas |
| 8 | Ciclo 3 + métricas + CSV. **Informe de resultados y go/no-go** |

---

## 9. Pendientes de decisión que el propio PRD deja abiertos (§10)

| # | Pendiente | Bloquea | Estado en [pendientes.md](pendientes.md) |
|---|---|---|---|
| 1 | Quién construye el MVP | Todo el cronograma | Abierto |
| 2 | Lista definitiva de 25-30 municipios | Semana 1 | Cerrado de facto: 18 |
| 3 | Canal de notificación | Semana 6 | Cerrado (`11.4/3`): ninguno |
| 3b | Autenticación y hosting | Semana 5 | Cerrado: ninguna / Vercel |
| 3c | Definición de estados de seguimiento y responsable de mantenerlos | Semana 6 | Abierto (los estados están enumerados en CA-M9.9; el responsable, no) |
| 4 | Pesos iniciales del scoring | Semana 5 | Abierto (`A1/4`): rigen provisionales de Analítica |
| 5 | Compromiso de las 7 gerencias | H2 completo | Abierto |

---

## 10. Lo que el PRD no define y una auditoría necesitaría

Cada punto es un hueco del PRD, no un defecto del código. Donde otro documento
del repositorio lo cubrió, se indica; donde nadie lo cubrió, la auditoría tendrá
que fijar un criterio propio y declararlo.

### 10.1 Sobre severidad y verificación

1. **No hay criterios de aceptación bloqueantes.** Solo H4 lleva la etiqueta. Una
   auditoría que quiera clasificar hallazgos por severidad no tiene base en el PRD
   para hacerlo criterio a criterio; §7 de este documento recoge lo más cercano.
2. **No hay método de verificación por criterio.** «URL accesible», «cita textual
   localizable», «score explicable», «usable en móvil» o «≤2 clics» no tienen
   definición operativa. El Addendum 01 §5 precisa los campos de CA-M3.1 por
   fuente; el resto queda a interpretación.
3. **No dice quién acepta ni con qué evidencia.** No hay procedimiento de
   aceptación, ni artefacto de prueba exigido, ni responsable de firmar cada CA.
4. **Los umbrales de H1, H2 y H3 están marcados `[EST]`**: son estimaciones, y el
   PRD no dice qué pasa si se recalibran a mitad del experimento.

### 10.2 Sobre las hipótesis y sus denominadores

5. **H1**: no define el denominador de «insights» (¿mostrados, pedidos, con al
   menos una calificación?) ni cómo entra `sin_respuesta` en el promedio.
6. **H2**: no define el denominador de la tasa de respuesta. `M9-carga` decidió
   que es la carga **pedida** (5 insights × 3 municipios), no lo mostrado; la
   decisión no está en el PRD y hay que declararla al reportar.
7. **H3**: no define sobre qué base se cuenta la supervivencia (¿insights del
   Clasificador? ¿señales crudas?) ni si TerriData cuenta como fuente evaluable
   (CLAUDE.md §1 argumenta que no).
8. **H4**: «evidencia completa hasta fuente» no se define más allá de CA-M3.1, y
   el PRD no dice si el 100% se audita por censo o por muestra, ni qué tamaño de
   muestra bastaría. CLAUDE.md §4 advierte que la muestra actual es insuficiente.
9. **H5**: «extrapolación documentada» no tiene criterio de aceptación; cualquier
   cifra escrita lo cumple.

### 10.3 Sobre el ciclo y la temporalidad

10. **«Ciclo» significa 15 días en el PRD** (§2.1, §3). En el MVP los ciclos duran
    51, 84 y 239 días (Addendum 01 D2). Todo criterio «por ciclo» —CA-M2.1,
    CA-M3.3, CA-M7.5, CA-M8.3, H2— cambia de significado y el PRD no contempla
    la simulación.
11. **No hay cron ni «cierre de ciclo» definido** para un MVP de ejecución manual
    (D9). CA-M6.7 y CA-M7.7 dependen de «al cerrar/publicarse el ciclo», y el PRD
    no dice quién publica, cuándo, ni qué lo dispara.
12. **CA-M1.3 «entre ciclos» es ambiguo** cuando una fuente se replica a propósito
    en los tres (Bing) — pendiente 11.2.

### 10.4 Sobre el scoring

13. **No define los pesos** (pendiente 4) ni la **escala común** en que se suman
    factores heterogéneos; sin escala, «pesos configurables» no significa nada.
    Addendum 01 D4 propone pesos y CLAUDE.md §7 documenta la normalización
    min-max, ambos sin aprobación de Gerencia General (A1/4, A5).
14. **No define qué hacer con un municipio sin datos** en un factor. D4 introduce
    la redistribución por cobertura y el piso de área; el PRD no lo contempla.
15. **No define los factores** (F1–F6 son de D4) ni «feature objetiva».
16. **No define versionado del algoritmo** ni cómo conviven dos corridas del
    mismo ciclo, ni cuál es la canónica (A9 lo resolvió: la que referencia el
    informe publicado).

### 10.5 Sobre el modelo de datos y el contrato de estado

17. **El contrato de estado (§4.1) es una lista de nombres**: sin tipos,
    cardinalidad, versionado ni esquema de `evidencia[]` más allá de tres campos.
    No hay contra qué verificar que «insertar un orquestador no requiere
    rediseñar» (§3.2).
18. **El modelo de datos (§4.2) no define claves, unicidades ni relaciones.** En
    particular, no dice que haya una sola calificación por (insight, gerencia),
    aunque CA-M7.2 y CA-M7.6 lo presuponen; ni cómo se vincula `informe` a la
    corrida que lo produjo, que es lo que permite reconstruirlo.
19. **No hay tablas para prompts versionados, corridas, ni contexto estructural.**
    Existen en el código (D7, A9, A10); el PRD no las exige ni las prohíbe.
20. **`informe.ruta_html` e `infografias[]`** presuponen artefactos HTML/imagen
    que el PRD no describe.

### 10.6 Sobre la interfaz

21. **La infografía (CA-M6.2, CA-M9.4)** no tiene contenido, formato ni regla de
    composición definidos en ningún documento del repositorio.
22. **«Justificación» y «sugerencias de acción» (CA-M6.1)** no tienen criterio de
    calidad ni tono. `MARCA-tono` lo registra: sin tono de voz definido no hay
    criterio de aceptación para la redacción del Sintetizador.
23. **Trazabilidad en interfaz (CA-M9.5) y ficha de municipio (CA-M9.11)** no se
    ubican dentro de las «tres vistas y solo tres» de CA-M9.3.
24. **La especificación de UI a la que remite CLAUDE.md no está en el repo** y el
    usuario la declaró desactualizada. Para estructura de pantallas solo hay
    design-system.md §2–§4, que detalla la vista de ciclo y despacha las otras
    tres en un párrafo cada una.
25. **«Usable en navegador móvil» (CA-M9.18)** no tiene criterio: ni anchos, ni
    dispositivos, ni qué se considera «usable». design-system.md §6 fija algo.
26. **No hay requisitos no funcionales**: rendimiento, disponibilidad,
    accesibilidad, seguridad de la app, retención de datos, tratamiento de PII.
    Addendum 01 D3 toma la decisión sobre PII; el PRD no la menciona.

### 10.7 Sobre acceso y roles

27. **Todo M9.a presupone autenticación** (CA-M9.1, CA-M9.2, §4.3). Al decidirse
    que no la hay (`3b`, `M9-acceso`), el PRD no ofrece criterio sustituto: qué
    significa «identidad propia» o «ninguna cuenta compartida» cuando la
    identidad es un correo escrito a mano y validado contra una lista.
28. **El rol administrador** no se define operativamente: quién es, cuántos hay,
    si también califica.
29. **Pendiente 3c**: quién mantiene los estados de seguimiento sigue sin dueño.

### 10.8 Sobre referencias externas

30. **Ocho reglas de negocio (RN-xx), CA6.3, CA7.5 y los pendientes 1, 9 y 11 del
    PRD principal** se citan sin texto. Con el v1.2 fuera del repositorio
    (11.5), ninguno se puede auditar más allá del paréntesis con que el PRD del
    MVP lo resume.
31. **Referencias de otros documentos que el PRD no contiene** —§8.1, RN-13,
    CA1.6, CA1.7, CA2.6, CA6.7, «10 capacidades», colaborador de fuentes
    primarias— están catalogadas en [architecture.md §0](architecture.md). No
    forman parte de esta línea base.
