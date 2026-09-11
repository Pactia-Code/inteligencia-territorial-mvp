# Addendum 02 — Stack tecnológico

**Documento base:** [PRD — MVP Inteligencia Territorial v1.0](prd.md) · [Addendum 01 — Fuente de datos](addendum-01-fuente-de-datos.md)
**Fecha:** 2026-09-11
**Estado:** Decisiones tomadas
**Alcance:** Sustituye la §4.3 (Stack) del PRD del MVP.

---

## D5 — Opción A: monolito Python autocontenido

Un solo lenguaje, un solo repositorio, un solo despliegue.

| Capa | Elección | Reemplaza a (PRD §4.3) |
|---|---|---|
| Orquestación | LangGraph + checkpointer | LangGraph — sin cambio |
| LLM | `AnthropicFoundry` (SDK `anthropic`) contra el tenant de Pactia | No especificado en el PRD |
| Observabilidad | Langfuse Cloud, instrumentado por nodo | Langfuse — sin cambio |
| Semi-estructurado | Azure Blob Storage (local: sistema de archivos) | No previsto |
| Estructurado | SQLite en local → Azure PostgreSQL en nube | Postgres — ver D8 |
| Ingesta | `httpx` · `polars` · Playwright (Fase 0) | Conectores SODA |
| Scheduler | Ejecución manual en local → GitHub Actions → Container Apps Job | GitHub Actions / Azure Function |
| App web | Django + HTMX sobre la misma base | Next.js o Django — se elige Django |
| Infografías | Jinja2 → HTML poblado desde SQL → Playwright → PNG | No especificado |

**Por qué se descartaron las otras dos opciones evaluadas:** el stack nativo Microsoft (Fabric + Power Automate + Power BI) exige licencias, capacidad Fabric y permisos de tenant — dependencias de TI que el PRD ya arrastra como pendiente 3b y como riesgo alto no resuelto en §7. Managed Agents de Anthropic habría sido más rápido, pero cede las trazas a una plataforma en beta justo en el eje que el experimento mide (H4, bloqueante).

---

## D6 — El LLM se consume vía Microsoft Foundry

Los modelos se despliegan en el tenant de Pactia en Azure AI Foundry. El cliente es
`AnthropicFoundry(api_key=..., resource=...)` del SDK oficial `anthropic`.

### Modelos propuestos

| Agente | Modelo | Razón |
|---|---|---|
| Clasificador | `claude-haiku-4-5` | Clasificación masiva de ~19.640 registros; el trabajo es de criba, no de razonamiento |
| Correlacionador | `claude-opus-5` | Cruza señales y extrapola implicación inmobiliaria. Es donde se juega H1 |
| Sintetizador | `claude-opus-5` | Redacta el informe del top 3 bajo la restricción de CA-M6.3 |

El Agente Fuentes no usa LLM en el MVP: lee del snapshot (ver Addendum 01, D2).

### Lo que Foundry no soporta — verificado

| Capacidad | Foundry | Consecuencia |
|---|---|---|
| **Message Batches** | ❌ No | Se pierde el descuento del 50% en la clasificación masiva |
| Prompt caching (5m, 1h) | ✅ GA | **Pasa a ser la palanca principal de costo** |
| Messages, streaming, tool use | ✅ GA | Sin impacto |
| Structured outputs / strict tools | ⚠️ Beta | Usable; es beta en esta plataforma |
| Adaptive thinking / effort | ⚠️ Beta | Idem |
| Token counting | ⚠️ Beta | Afecta cómo se instrumenta H5 |
| Models API | ❌ No | El catálogo se fija por configuración, no se descubre en runtime |

**Impacto real.** Para el MVP es despreciable: 19.640 registros procesados una sola vez cuestan
del orden de $10–30 en total, con o sin batch. Para Fase 0 sí pesa, porque a escala nacional la
clasificación no baja a la mitad.

**Mitigación — orden del prompt.** Como el caching sí está disponible, el prompt del Clasificador
debe ordenarse con lo estable primero (instrucciones, taxonomía de categorías, ejemplos) y lo
volátil al final (el registro a clasificar). El caching es por coincidencia de prefijo: cualquier
byte que cambie antes del punto de corte invalida todo lo que sigue. Se verifica midiendo
`usage.cache_read_input_tokens`; si sale cero de forma repetida, algo está invalidando el prefijo.

---

## D7 — Reparto entre Blob y SQL

**Regla:** SQL guarda lo que se consulta, se une o se califica. Blob guarda lo que es grande,
inmutable o binario. **SQL almacena la URI del blob, nunca el contenido.**

```
Blob / carpeta local                     Base SQL
├── raw/                                 ├── municipio        (divipola CHAR(5) PK)
│   ├── snapshot_v3.json   (inmutable)   ├── senal_cruda      → uri_blob
│   └── ciclo=N/fuente=*/*.parquet       ├── insight + evidencia[]
├── informes/ciclo=N/informe.html        ├── calificacion
├── infografias/ciclo=N/{divipola}.png   ├── seguimiento      (historial)
└── prompts/v{n}/*.md                    ├── traza_agente
                                         ├── dataset_version / prompt_version
                                         └── checkpoints de LangGraph
```

**Linaje de modelo y dataset.** `dataset_version` apunta a una ruta de Blob inmutable con su
hash; `prompt_version` a `prompts/v{n}/`; `traza_agente` amarra cada corrida a ambos más el
identificador de modelo usado. El linaje queda consultable en SQL y el artefacto versionado en
Blob.

**Normalización DIVIPOLA — obligatoria en ingesta.** El snapshot trae los códigos sin ceros a la
izquierda: Antioquia aparece como `5-045` y Atlántico como `8-573`, cuando el estándar DANE es
`05045` y `08573`. Se normaliza a `CHAR(5)` con relleno de ceros al cargar. Sin esto, cualquier
unión futura con TerriData o fuentes oficiales falla en silencio.

---

## D8 — Desarrollo y ejecución en local

Toda la ingesta y el desarrollo del MVP corren en la máquina local. Nada se despliega en nube
durante el experimento.

| | Local (ahora) | Azure (Fase 0) |
|---|---|---|
| Semi-estructurado | Carpeta `data/blob/` | Azure Blob Storage |
| Estructurado | SQLite (`data/territorial.db`) | Azure PostgreSQL Flexible Server |
| Checkpointer | `langgraph-checkpoint-sqlite` | `langgraph-checkpoint-postgres` |
| Ejecución | Comando manual por ciclo | Container Apps Job con cron |

Ambos lados quedan detrás de la misma interfaz: el código no sabe si escribe en disco o en Blob,
ni si habla con SQLite o con Postgres. Migrar es cambiar configuración, no código.

**Por qué SQLite y no PostgreSQL en local.** La máquina no tiene Docker ni PostgreSQL instalados,
y el PRD asigna la construcción a una sola persona. Instalar y administrar un motor de base de
datos es fricción que no compra nada durante el MVP: el modelo de datos de §4.2 es relacional
plano con algunas columnas JSON, que SQLite cubre sin esfuerzo.

**Riesgo aceptado — deriva de dialecto.** SQLite y PostgreSQL no son idénticos. Se contiene con
tres reglas de obligado cumplimiento:

1. Todo acceso a datos pasa por **SQLAlchemy**; nunca SQL crudo específico de un motor.
2. El esquema se gestiona con **Alembic** desde la primera migración.
3. Las columnas JSON usan el tipo `JSON` de SQLAlchemy, **nunca operadores JSONB de Postgres**
   (`->>`, `@>`, `jsonb_path_query`).

Si alguna consulta llegara a necesitar JSONB, se instala PostgreSQL en local antes que romper
la regla.

---

## D9 — Modelo de ejecución del MVP

Los tres ciclos se corren a mano, uno por uno, contra el snapshot particionado según Addendum 01
D2. No hay cron durante el MVP: un cron que dispara sobre datos estáticos no valida nada que no
valide una ejecución manual, y CA-M1.4 (tolerancia a fuente caída) ya quedó sin validar por R5.

**Implicación:** el scheduler se difiere a Fase 0 junto con la ingesta viva. El código se escribe
de modo que el disparador sea intercambiable — una función de entrada que da igual quién la
invoque.

---

## Pendientes que abre este addendum

| # | Pendiente | Bloquea |
|---|---|---|
| B1 | Confirmar el identificador exacto del modelo desplegado en Foundry y el nombre del recurso | Primera llamada al LLM |
| B2 | Validar que `claude-haiku-4-5` alcanza la reducción ≥85% de CA-M2.1; si no, escalar el Clasificador a `claude-sonnet-5` | Calibración de M2 |
| B3 | Instalar Python 3.12 en la máquina de desarrollo | Todo |

---

## Anexo — Decisiones en una línea

- **D5** · Monolito Python: LangGraph + Langfuse + Django, un repo, un lenguaje.
- **D6** · LLM vía `AnthropicFoundry` en el tenant de Pactia. Sin Batch API; el caching compensa.
- **D7** · Blob para lo semi-estructurado e inmutable, SQL para lo consultable. SQL guarda la URI.
- **D8** · Local: carpeta + SQLite. Nube: Blob + Postgres. Misma interfaz, distinta configuración.
- **D9** · Los 3 ciclos se ejecutan a mano. El scheduler se difiere a Fase 0.
