# Arquitectura — MVP Inteligencia Territorial

**Documentos base:** [PRD del MVP](prd.md) · [Addendum 01 — Fuente de datos](addendum-01-fuente-de-datos.md) · [Addendum 02 — Stack](addendum-02-stack.md)
**Fecha:** 2026-09-11
**Alcance:** Diseño técnico del MVP. Todo lo aquí descrito se deriva del PRD y de los dos addenda. Lo que no tiene base en esos documentos está marcado como **[SIN BASE]** y recogido en §11.

---

## 0. Referencias citadas que no existen en el PRD

Seis referencias solicitadas para este documento no aparecen en [prd.md](prd.md). Se verificó por búsqueda sobre el texto completo. No se inventó requisito alguno para cubrirlas; cada una se trata en §11.

| Referencia pedida | Qué hay realmente en el PRD del MVP |
|---|---|
| §4.1, "9 entidades" | §4.1 es el *contrato de estado entre agentes*. Las 9 entidades están en **§4.2**. Se usa §4.2. |
| §8.1, "los cuatro agentes" | §8 es el *plan de ejecución*. Los 4 agentes están en **§3** y §2.1. Se usa §3. |
| RN-13 (frecuencia por fuente) | **No existe.** El PRD fija un único ciclo quincenal para las 3 fuentes (§2.1). |
| CA1.7 (deduplicación) | **No existe.** El equivalente es **CA-M1.3**. |
| CA1.6 (fuente degradada) | **No existe.** El equivalente es **CA-M1.4**. |
| CA2.6 (trazas) | **No existe.** Los equivalentes son **CA-M2.5** y **CA-M8.2**. |
| CA6.7 (versionado de modelo) | **No existe.** CA-M6.7 trata de la publicación del informe. El versionado se apoya en el Addendum 02 D7. |
| "las 10 capacidades" | El PRD define **9 módulos**: M1–M9. |
| "colaborador que aporta fuentes primarias (§3)" | **No existe.** §2.2 excluye explícitamente las fuentes primarias, y CA-M9.1 define **solo dos roles**. |

---

## 1. Stack

Versiones con marca ✅ están instaladas y verificadas; las marcadas ⬜ están declaradas en `pyproject.toml` pero aún no instaladas.

| Componente | Versión | Por qué |
|---|---|---|
| Python | 3.12.14 ✅ | Un solo lenguaje en todo el sistema (D5); 3.12 es la versión estable con soporte largo |
| uv | 0.12.13 ✅ | Único instalador que evita el MSI, bloqueado por política corporativa (`EnableUserControl=0`) |
| SQLAlchemy | 2.0.52 ✅ | Aísla el dialecto: la misma capa de datos sirve a SQLite local y PostgreSQL en nube (D8) |
| SQLite | 3.53.1 ✅ | Cero administración en local; el modelo de §4.2 es relacional plano (D8) |
| pydantic / pydantic-settings | 2.13.5 / 2.15.0 ✅ | Configuración validada en el arranque, no a mitad de un ciclo |
| polars | 1.44.2 ✅ | Particionado y Parquet sobre 19.640 registros sin cargar todo a memoria |
| alembic | ≥1.14 ⬜ | Regla 2 de D8: el esquema se gobierna por migraciones desde el principio |
| anthropic | ≥0.40 ⬜ | Cliente `AnthropicFoundry` contra el tenant de Pactia (D6) |
| langgraph | ≥0.2 ⬜ | Estado compartido entre los 4 agentes (§4.1) y checkpointing para CA-M8.4 |
| langgraph-checkpoint-sqlite | ≥2.0 ⬜ | Checkpointer que respalda CA-M8.4 en local; su gemelo Postgres en Fase 0 |
| langfuse | ≥2.55 ⬜ | Traza por agente con tokens y duración: CA-M8.2 y CA-M8.3 |
| httpx | ≥0.28 ⬜ | Cliente HTTP para la ingesta viva de Fase 0 |
| ~~Django~~ → **Next.js** | por fijar ⬜ | **Desviación del 2026-09-21**: la app web va en Next.js sobre Vercel, no Django. Ver la nota en Addendum 02 D5. El PRD §4.3 ya contemplaba Next.js. **Perder el admin de Django no es una pérdida**: CA-M9.13 son cuatro métricas concretas —cuatro consultas y una página—, y el admin servía para editar registros, que es lo que CA-M9.16 prohíbe |
| Playwright | por fijar ⬜ | HTML → PNG para infografías. **Verificar**: descarga binarios sin firmar y esta máquina los bloquea |
| azure-storage-blob / psycopg | ≥12.24 / ≥3.2 ⬜ | Extra `azure`, solo para Fase 0 |

---

## 2. Estructura de carpetas

Las tres capas del PRD §3 se separan físicamente. La frontera entre ellas es la que sostiene H4: **lo determinista nunca depende de un LLM, y lo agéntico nunca decide qué es evidencia suficiente** (§3.1).

```
src/territorial/
│
├── CAPA 1 — DETERMINISTA (código, nunca LLM)
│   ├── ingesta/            Carga, particionado por ciclo, deduplicación, estado de fuente
│   │   ├── snapshot.py     Lector del snapshot (MVP)
│   │   └── fuentes/        Conectores vivos (Fase 0): secop.py, rss.py, elic.py
│   ├── reglas/             Reglas de negocio explícitas y auditables
│   │   ├── validador.py    M3 — rechaza insight sin URL + fecha + cita (CA-M3.1)
│   │   ├── prefiltro.py    Diccionario de obra e infraestructura (pendiente A2)
│   │   └── cobertura.py    Días cubiertos y umbral sin_cobertura (D4)
│   └── scoring/            M5 — motor de scoring
│       ├── factores.py     F1–F6 del Addendum 01 D4
│       ├── pesos.py        Carga de pesos configurables (CA-M5.3)
│       └── ranking.py      Top 3 fijo (CA-M5.4) con desglose (CA-M5.5)
│
├── CAPA 2 — AGENTES (LLM)
│   ├── agentes/
│   │   ├── fuentes.py          Agente 1
│   │   ├── clasificador.py     Agente 2
│   │   ├── correlacionador.py  Agente 3
│   │   └── sintetizador.py     Agente 4
│   ├── prompts/            Versionados; se archivan en el almacén (D7)
│   └── grafo/
│       ├── estado.py       EstadoCiclo de §4.1
│       └── flujo.py        Grafo LangGraph y checkpointing (CA-M8.4)
│
├── CAPA 3 — SUPERFICIE
│   ├── web/                Django: ciclo actual, priorizados, histórico, métricas (CA-M9.3)
│   ├── informes/           Plantillas Jinja2 e infografías (CA-M6.2)
│   └── notificacion/       Correo con enlace profundo (CA-M6.7)
│
└── TRANSVERSAL
    ├── almacen/            Blob y SQL (D7)
    ├── observabilidad/     Langfuse, trazas, métricas de ciclo (M8)
    ├── utiles/             divipola.py y afines
    └── config.py

evaluacion/                 Set de evaluación  [SIN BASE — ver §11.7]
  casos/                    Insights con juicio humano de referencia
  correr_eval.py
scripts/                    Puntos de entrada por ciclo
alembic/                    Migraciones (regla 2 de D8)
```

---

## 3. Modelo de datos

Las **9 entidades de §4.2**, con DIVIPOLA como clave geográfica en todo el modelo. Implementadas en [`src/territorial/almacen/modelos.py`](../src/territorial/almacen/modelos.py).

**DIVIPOLA es `CHAR(5)`** y se normaliza en ingesta con relleno de ceros (D7). El snapshot trae Antioquia como `5` y Atlántico como `8`; el estándar DANE es `05` y `08`. Toda tabla con dimensión geográfica referencia `municipio.divipola` por clave foránea. Esto materializa RN-09 (granularidad municipio).

### 3.1 `municipio`

| Campo | Tipo | Restricción |
|---|---|---|
| `divipola` | CHAR(5) | **PK**, `CHECK length = 5` |
| `nombre` | VARCHAR(120) | NOT NULL |
| `departamento` | VARCHAR(80) | NOT NULL |
| `corredores` | JSON | Lista; concepto que aporta el snapshot |
| `elic` | JSON | Contexto ELIC, constante en los 3 ciclos (D2, R3) |

### 3.2 `ciclo`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `fecha_desde`, `fecha_hasta` | DATE | Ventana del ciclo (D2) |
| `id_dataset` | INTEGER | **FK** → `dataset_version.id` — ancla el linaje |
| `n_senales`, `n_insights`, `n_validados`, `n_rechazados` | INTEGER | Métricas de §6 |
| `costo_tokens` | FLOAT | CA-M8.3 |
| `duracion_seg` | FLOAT | |

### 3.3 `senal_cruda`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `id_ciclo` | INTEGER | **FK** → `ciclo.id`, indexado |
| `divipola` | CHAR(5) | **FK** → `municipio.divipola`, indexado |
| `fuente` | VARCHAR(20) | `SECOP II` \| `RSS` \| `ELIC` \| `Bing` |
| `id_externo` | VARCHAR(120) | Identificador en origen |
| `fecha_publicacion` | DATE | Indexado; nulo en ELIC y Bing (D2) |
| `contenido` | TEXT | NOT NULL |
| `url` | TEXT | Nulo solo en Bing (D1) |
| `hash_dedup` | CHAR(64) | Indexado — CA-M1.3 |
| `uri_blob` | TEXT | Puntero al almacén de objetos (D7) |
| `datos` | JSON | Registro original, con la PII conservada (D3) |
| | | `UNIQUE (id_ciclo, hash_dedup)` |

### 3.4 `insight`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `id_ciclo` | INTEGER | **FK** → `ciclo.id` |
| `divipola` | CHAR(5) | **FK** → `municipio.divipola` |
| `categoria` | VARCHAR(60) | CA-M2.2 |
| `resumen` | TEXT | CA-M2.2 |
| `implicacion_inmobiliaria` | TEXT | CA-M2.2, CA-M4.2 |
| `evidencia` | JSON | `[{url, fecha, cita_textual, fuente}]` — CA-M3.1 exige los tres primeros |
| `ids_senal` | JSON | Trazabilidad hacia atrás (CA-M4.4) |
| `estado_validacion` | VARCHAR(20) | `CHECK IN (pendiente, validado, rechazado)` |
| `motivo_rechazo` | TEXT | CA-M3.2: el rechazado se persiste, no se descarta |
| `contexto_no_verificado` | BOOLEAN | Marca el uso de contexto Bing (D1) |

### 3.5 `calificacion`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `id_insight` | INTEGER | **FK** → `insight.id` |
| `id_gerencia` | VARCHAR(60) | Indexado |
| `valor` | INTEGER | `CHECK BETWEEN 1 AND 5` |
| `comentario` | TEXT | Opcional (CA-M7.4) |
| | | `UNIQUE (id_insight, id_gerencia)` — CA-M7.2 |

La ausencia de fila **es** `sin_respuesta` (CA-M7.3). No se escribe ningún valor centinela.

### 3.6 `usuario`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `id_gerencia` | VARCHAR(60) | Indexado |
| `nombre` | VARCHAR(120) | |
| `correo` | VARCHAR(160) | **UNIQUE** — CA-M9.1, sin cuentas compartidas |
| `rol` | VARCHAR(20) | `CHECK IN (gerencia, administrador)` |
| `activo` | BOOLEAN | |

### 3.7 `seguimiento`

Tabla de **historial**: cada cambio inserta una fila. El estado vigente de un municipio es su fila más reciente (§4.2, CA-M9.10).

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `divipola` | CHAR(5) | **FK** → `municipio.divipola` |
| `id_ciclo_origen` | INTEGER | **FK** → `ciclo.id` |
| `estado` | VARCHAR(30) | `CHECK IN (priorizado, en_revision, en_estructuracion, descartado)` |
| `nota` | TEXT | Obligatoria al pasar a `descartado` o `en_estructuracion` (CA-M9.9) — se valida en la capa web |
| `id_usuario` | INTEGER | **FK** → `usuario.id` |
| `fecha_cambio` | TIMESTAMP | |

### 3.8 `informe`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `id_ciclo` | INTEGER | **FK** → `ciclo.id` |
| `uri_html` | TEXT | Puntero al almacén (D7) |
| `infografias` | JSON | `[{divipola, uri}]` — CA-M6.2 |
| `estado` | VARCHAR(20) | `publicado` \| `archivado` |
| `fecha_publicacion` | TIMESTAMP | CA-M9.7: nada se sobrescribe entre ciclos |

### 3.9 `traza_agente`

| Campo | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | **PK** |
| `id_ciclo` | INTEGER | **FK** → `ciclo.id` |
| `agente` | VARCHAR(40) | Indexado |
| `modelo` | VARCHAR(80) | Qué modelo corrió |
| `id_prompt` | INTEGER | **FK** → `prompt_version.id` |
| `id_dataset` | INTEGER | **FK** → `dataset_version.id` |
| `hash_input`, `hash_output` | CHAR(64) | |
| `tokens_entrada`, `tokens_salida`, `tokens_cache_lectura` | INTEGER | CA-M8.2, CA-M8.3 |
| `duracion_ms` | INTEGER | |
| `id_traza_langfuse` | VARCHAR(80) | Puente hacia la traza completa |

### 3.10 Tablas añadidas sobre §4.2

No están en el PRD; las exige el linaje del Addendum 02 D7 y el scoring de D4.

| Tabla | Para qué |
|---|---|
| `dataset_version` | Snapshot inmutable + SHA-256 + URI. Ancla del linaje |
| `prompt_version` | Prompt por agente y versión, archivado en el almacén |
| `score_municipio` | Score y ranking por ciclo, con `factores` JSON que materializa CA-M5.5, más `dias_cubiertos` y `sin_cobertura` de D4 |

---

## 4. Diseño de la ingesta

### 4.1 Programación por fuente

**[SIN BASE] RN-13 no existe en el PRD del MVP.** Lo que el PRD sí fija (§2.1) es **un único ciclo quincenal para las tres fuentes**, disparado por cron. Y el Addendum 02 D9 lo reduce más: durante el MVP los 3 ciclos se ejecutan **a mano** sobre el snapshot, porque un cron sobre datos estáticos no valida nada.

El diseño que sí se deriva:

| Fuente | Cadencia en el MVP | Cadencia prevista en Fase 0 |
|---|---|---|
| SECOP II | Partición del snapshot por `fecha` | Por definir |
| RSS | Partición del snapshot por `fecha` | Por definir |
| ELIC | Carga única; constante en los 3 ciclos (D2) | Publicación DANE, no controlada por nosotros |
| Bing | Carga única; constante y solo como contexto (D1) | Por definir |

El disparador se escribe como una función de entrada intercambiable: da igual si la invoca una persona, un cron o un job. Sustituir uno por otro no toca el pipeline.

### 4.2 Deduplicación — CA-M1.3

`hash_dedup = SHA-256(fuente | divipola | id_estable)`, donde el identificador estable es `id` en SECOP y `link` en RSS.

**Una discrepancia que conviene conocer.** CA-M1.3 dice que la deduplicación *"evita reprocesar la misma señal **entre ciclos**"*, pero la restricción implementada es `UNIQUE (id_ciclo, hash_dedup)`, que es *por ciclo*. La diferencia no muerde en el MVP por dos razones: SECOP y RSS asignan cada señal a exactamente un ciclo según su fecha, así que no pueden repetirse entre ciclos; y Bing **se replica a propósito** en los 3 ciclos, porque es contexto constante (D2) — una unicidad global lo impediría.

Si en Fase 0 la ingesta pasa a ser continua y una misma señal puede reaparecer en ventanas distintas, la restricción debe endurecerse a global y Bing necesitará tratamiento aparte.

### 4.3 Fuente degradada — CA-M1.4

CA-M1.4 exige que un ciclo **nunca se aborte** por una fuente caída: continúa con las demás y registra el fallo.

Diseño: cada fuente reporta un `EstadoFuente` por ciclo con `nombre`, `estado` (`ok` \| `degradada` \| `caida`), `n_registros`, `motivo` y `detectado_en`. El grafo continúa siempre; el estado se persiste en `ciclo.metricas` y se refleja en el informe.

Se marca **degradada**, no caída, cuando la fuente responde pero con cobertura parcial. El caso real está documentado: **R7**, el truncamiento de SECOP en los seis municipios de mayor volumen. Por eso la cobertura se calcula por municipio y por ciclo, y por debajo del 30% los factores SECOP se marcan `sin_cobertura` en vez de puntuarse cero (D4).

**Limitación declarada:** con el snapshot no hay fuente que se caiga, así que **CA-M1.4 queda sin validar** en el MVP (Addendum 01, R5). El mecanismo se construye para Fase 0; el experimento no prueba que funcione.

---

## 5. Diseño multiagente

Los **cuatro agentes de §3** del PRD, sobre el `EstadoCiclo` compartido de §4.1. Entre ellos hay dos piezas deterministas que no son agentes, deliberadamente (§3.1).

| # | Agente | Recibe | Entrega | Restricción propia |
|---|---|---|---|---|
| 1 | **Fuentes** | `municipios_objetivo[]`, ventana del ciclo | `señales_crudas[]` | En el MVP no usa LLM: lee del snapshot |
| — | *Validador* (código) | `insights[]` | `insights_validados[]` + rechazados con motivo | CA-M3.1; ningún rechazado avanza (CA-M3.4) |
| 2 | **Clasificador** | `señales_crudas[]` | `insights[]` con evidencia | Reducción ≥85% (CA-M2.1); registra qué descartó y por qué (CA-M2.5) |
| 3 | **Correlacionador** | `insights_validados[]` + calificaciones de ciclos previos | `insights_correlacionados[]` | Lee Bing solo como contexto (D1); preserva trazabilidad de origen (CA-M4.4) |
| — | *Scoring* (código) | `insights_correlacionados[]`, features | `ranking[]` top 3 | CA-M5.5: desglose por factor |
| 4 | **Sintetizador** | `ranking[]` + evidencia | `informe`, `infografias[]` | **Prohibido generar cifras** (CA-M6.3) |

El orden real de ejecución es: Fuentes → Clasificador → **Validador** → Correlacionador → **Scoring** → Sintetizador (§3).

### 5.1 Dónde se escriben las trazas

**[SIN BASE] CA2.6 no existe.** Los criterios reales son **CA-M8.2** (traza por agente con input, output, tokens y duración, en Langfuse) y **CA-M2.5** (el Clasificador registra qué descartó y por qué).

Las trazas se escriben en **dos lugares, con propósitos distintos**:

| Destino | Qué guarda | Para qué |
|---|---|---|
| **Langfuse** | Traza completa por nodo: prompt, respuesta, tokens, latencia | Depurar *cuál de los cuatro agentes falló* — la pregunta central del MVP (§4.3) |
| **`traza_agente`** (SQL) | Resumen por corrida + `id_prompt` + `id_dataset` + `modelo` + `id_traza_langfuse` | Auditoría y linaje reproducible; sobrevive aunque Langfuse no esté |

La cadena de CA-M8.1 (`señal → insight → validación → correlación → score → informe → calificación`) es reconstruible **solo con SQL**, sin depender de Langfuse. Esa es la condición para que H4 sea verificable.

### 5.2 Ausencia del orquestador

No hay orquestador (§3.2). `municipios_objetivo[]` es configuración estática. El punto de inserción para Fase 0 queda en ese campo: pasa a ser salida del orquestador sin tocar los agentes aguas abajo.

---

## 6. Jobs y endpoints

El PRD define **9 módulos (M1–M9)**, no 10.

### 6.1 Jobs del pipeline

| Job | Módulos | Entrada → salida |
|---|---|---|
| `cargar_snapshot` | M1 | JSON → `municipio`, `senal_cruda`, `ciclo`, `dataset_version` ✅ implementado |
| `correr_ciclo --ciclo N` | M2–M6 | Señales del ciclo → informe publicado |
| `publicar_informe --ciclo N` | M6 | Informe e infografías → almacén + `informe` + correo |
| `exportar_metricas --ciclo N` | M8 | → CSV de §6 del PRD (CA-M9.15) |

`correr_ciclo` es reanudable desde el último checkpoint (CA-M8.4).

### 6.2 Vistas web

CA-M9.3 fija **tres vistas, y solo tres**, más Métricas para el administrador.

| Ruta | Módulo | Criterio |
|---|---|---|
| `GET /ciclo/<n>/` | M9.b | Informe del top 3 con infografías y evidencia (CA-M9.4) |
| `GET /insight/<id>/trazabilidad/` | M9.b | Cadena completa en interfaz (CA-M9.5) |
| `POST /insight/<id>/calificar/` | M7 | Guardado inmediato, sin botón de envío (CA-M7.6) |
| `GET /priorizados/` | M9.c | Tablero con filtros por estado, ciclo y departamento (CA-M9.12) |
| `POST /municipio/<divipola>/estado/` | M9.c | Cambio de estado con nota obligatoria (CA-M9.9) |
| `GET /municipio/<divipola>/` | M9.c | Ficha: ciclos priorizados, insights acumulados, promedio (CA-M9.11) |
| `GET /historico/` | M9.b | Informes de ciclos anteriores (CA-M9.7) |
| `GET /metricas/` | M9.d | Solo administrador (CA-M9.13, CA-M9.14) |
| `GET /entrar/<token>/` | M9.a | Enlace mágico: autentica y redirige en un paso (CA-M9.2) |

---

## 7. Notificación y calificación embebida

**El canal es correo, y el contenido vive en el aplicativo web.** El PRD es explícito: §2.2 deja **fuera de alcance** Teams Adaptive Cards, Power Automate y Microsoft Fabric; §3.3 sustituye el par "correo + formulario" por un aplicativo web único.

| Pieza | Diseño | Criterio |
|---|---|---|
| Disparo | Al cerrar el ciclo, `publicar_informe` envía correo HTML a las 7 gerencias | CA-M6.7 |
| Contenido del correo | Resumen del top 3 y un botón. **No lleva la calificación dentro** | CA-M6.7: el correo solo notifica |
| Enlace | Enlace profundo con token que autentica y aterriza en el informe | CA-M9.2: un clic del correo al contenido |
| Calificación | Botones 1–5 junto a cada insight, en la misma vista donde se lee | CA-M7.1: ≤2 clics sin cambiar de herramienta |
| Guardado | Inmediato por insight, sin envío final | CA-M7.6 |
| Aislamiento | Ninguna gerencia ve la calificación de otra | CA-M7.2, CA-M9.14 |
| Cierre | Al publicarse el ciclo siguiente; lo anterior queda visible pero no editable | CA-M7.7 |
| Marca | "MVP — contenido no validado por Analítica" en correo y en toda pantalla | CA-M6.5, CA-M9.17 |

Los dos clics son: **botón del correo → informe autenticado**, y **clic en la estrella** del insight. El formato es idéntico para las 7 gerencias, sin personalización (CA-M6.6, RN-14, RN-16).

---

## 8. Autenticación y roles

CA-M9.1 define **exactamente dos roles** y ninguna cuenta compartida.

| Rol | Quiénes | Puede |
|---|---|---|
| `gerencia` | Las **7 gerencias** calificadoras | Leer informes, calificar, comentar, cambiar estado de seguimiento |
| `administrador` | **Área de Analítica** | Todo lo anterior + panel de métricas (CA-M9.13) y exportación CSV (CA-M9.15) |

Total: **8 usuarios** (§2.1). Autenticación por **enlace mágico por correo** o SSO corporativo si está disponible (§4.3): con 8 usuarios, una contraseña añade fricción sin añadir seguridad relevante. El método definitivo es el pendiente 3b del PRD.

Ninguna escritura de la app toca el pipeline: solo calificación, comentario y seguimiento (CA-M9.16).

**[SIN BASE] El "colaborador que aporta fuentes primarias" no existe en el PRD del MVP.** §2.2 excluye explícitamente las fuentes primarias (conversaciones, audio, video), y CA-M9.1 limita el acceso a las 7 gerencias más el administrador. Añadir ese rol exigiría un canal de aporte, moderación y trazabilidad de contenido no verificable — alcance que el PRD no contempla. Ver §11.6.

---

## 9. Versionado del modelo de scoring

**[SIN BASE] CA6.7 no existe en el PRD del MVP.** El diseño se apoya en lo que sí hay: el linaje de dataset y prompt del Addendum 02 **D7**, los factores del Addendum 01 **D4**, y **CA-M5.3** (pesos configurables sin cambio de código).

El score es determinista: **mismos pesos + mismo dataset ⇒ mismo ranking**. Eso permite versionarlo sin reentrenar nada.

Se añade una tabla `scoring_version`:

| Campo | Tipo | Para qué |
|---|---|---|
| `id` | INTEGER | **PK** |
| `version` | VARCHAR(20) | **UNIQUE** |
| `pesos` | JSON | Los pesos de F1–F6 usados |
| `uri_blob` | TEXT | Configuración archivada, inmutable |
| `hash_sha256` | CHAR(64) | Huella de la configuración |
| `id_dataset` | INTEGER | **FK** → `dataset_version.id` — el dataset contra el que se calibró |

Y `score_municipio` gana `id_scoring` → `scoring_version.id`.

Con eso, cada score guarda: qué pesos lo produjeron, contra qué dataset, y el desglose por factor. Reproducir el ranking de un ciclo pasado es releer la versión y volver a correr. Eso sostiene la explicabilidad que §3.1 exige para producción.

---

## 10. Decisiones técnicas y su alternativa descartada

| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| 1 | Monolito Python (D5) | Stack nativo Microsoft: Fabric, Power Automate, Power BI | Exige licencias, capacidad Fabric y permisos de tenant — dependencias de TI que el PRD ya arrastra como pendiente 3b y riesgo alto de §7 |
| 2 | Monolito Python (D5) | Managed Agents de Anthropic | Más rápido, pero cede las trazas a una plataforma en beta justo en el eje que el experimento mide (H4, bloqueante) |
| 3 | Validador y scoring en código (§3.1) | Hacerlos agentes | Un LLM decidiendo qué evidencia basta destruye el ancla de honestidad; un scoring agéntico no es auditable |
| 4 | Bing solo como contexto (D1) | Dejarlo originar insights | La tasa de rechazo pasaría a medir la alucinación de Bing en vez de la del pipeline, invalidando H4 como señal |
| 5 | Terciles por volumen SECOP (D2) | Tercios de tiempo iguales | Dejaría ciclos de 11.961 / 5.118 / 2.557 registros — razón 5:1 que vuelve insignificante la extrapolación de costo de H5 |
| 6 | Factores de composición y tasa (D4) | Volumen absoluto de SECOP | El volumen absoluto mide tamaño de ciudad: rankearía las mismas capitales los 3 ciclos |
| 7 | Normalizar por cobertura real (D4, R7) | Puntuar cero al municipio sin datos | Cinco capitales habrían salido con score ~0 por truncamiento de la extracción, y el informe lo habría presentado como falta de actividad |
| 8 | SQLite en local (D8) | PostgreSQL en local | No hay Docker ni Postgres en la máquina; el modelo de §4.2 es relacional plano. Precio: deriva de dialecto, contenida por las 3 reglas de D8 |
| 9 | Blob + SQL separados (D7) | Todo en la base de datos | El snapshot son 20 MB y las infografías son binarios; SQL guarda la URI, no el contenido |
| 10 | Prompt caching como palanca de costo (D6) | Batch API al 50% | **Corregido 2026-09-17.** El «Foundry no ofrece Batch API» era de la etapa Claude. Azure OpenAI sí ofrece batch al 50%, y sobre el piloto baja la quincena de $1,51 a $0,75. El caching está disponible pero **medido no se activa**: `cached_tokens` marca 0 en todas las llamadas |
| 11 | Entorno virtual fuera del repo | `.venv` dentro del proyecto | La política corporativa bloquea ejecutar binarios desde `Downloads` |
| 12 | `venv` estándar, no `uv venv` | Trampolín de uv | El trampolín va sin firmar y la política lo bloquea; `venv` copia el ejecutable real firmado |

---

## 11. Lo que no se pudo decidir con el PRD

Siete puntos. Ninguno se resolvió inventando requisitos.

**11.1 — Frecuencia de ingesta por fuente (RN-13).** No existe en el PRD del MVP, que fija un ciclo quincenal único para las tres fuentes. **¿Quieres cadencias distintas por fuente en Fase 0? ¿Cuáles?**

**11.2 — Alcance de la deduplicación (CA-M1.3).** El criterio dice "entre ciclos" pero la restricción implementada es por ciclo, porque Bing se replica a propósito. **¿Endurezco a unicidad global y trato Bing aparte, o lo dejo así hasta Fase 0?**

**11.3 — Las "10 capacidades".** El PRD define 9 módulos, M1 a M9. **¿Cuál es la décima, o me quedo con las nueve?**

**11.4 — Canal de notificación.** Pediste "el canal de trabajo de la organización" con calificación embebida, pero §2.2 excluye Teams y §3.3 sustituye el formulario por un aplicativo web. Diseñé correo + enlace profundo. **¿Confirmas, o quieres Teams y asumimos que contradice el alcance del PRD del MVP?**

**11.5 — Versión del PRD.** Varias referencias (§8.1, RN-13, CA1.6, CA1.7, CA2.6, CA6.7) parecen del **PRD principal v1.2**, que no está en el repositorio. **¿Lo agregas a `docs/`?** Con él podría cerrar 11.1, 11.4 y 11.6 sin suposiciones.

**11.6 — El colaborador de fuentes primarias.** No existe en el PRD del MVP, y §2.2 excluye las fuentes primarias. Un tercer rol necesitaría canal de aporte, moderación y trazabilidad de contenido no verificable. **¿Lo añado como alcance nuevo, o queda para Fase 0?**

**11.7 — Set de evaluación.** Reservé la carpeta `evaluacion/`, pero el PRD no define qué se evalúa ni contra qué referencia. Lo más cercano es la calificación 1–5 de las gerencias, que es juicio humano en producción, no un set fijo. **¿Contra qué quieres evaluar: un conjunto de insights con juicio de referencia, la precisión del prefiltro de obra, o el cumplimiento del validador?**
