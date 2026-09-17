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
| LLM | `OpenAI` (SDK `openai`) contra la superficie v1 del tenant de Pactia | No especificado en el PRD |
| Observabilidad | Langfuse Cloud, instrumentado por nodo | Langfuse — sin cambio |
| Semi-estructurado | Azure Blob Storage (local: sistema de archivos) | No previsto |
| Estructurado | SQLite en local → Azure PostgreSQL en nube | Postgres — ver D8 |
| Ingesta | `httpx` · `polars` · Playwright (Fase 0) | Conectores SODA |
| Scheduler | Ejecución manual en local → GitHub Actions → Container Apps Job | GitHub Actions / Azure Function |
| App web | Django + HTMX sobre la misma base | Next.js o Django — se elige Django |
| Infografías | Jinja2 → HTML poblado desde SQL → Playwright → PNG | No especificado |

**Por qué se descartaron las otras dos opciones evaluadas:** el stack nativo Microsoft (Fabric + Power Automate + Power BI) exige licencias, capacidad Fabric y permisos de tenant — dependencias de TI que el PRD ya arrastra como pendiente 3b y como riesgo alto no resuelto en §7. Managed Agents de Anthropic habría sido más rápido, pero cede las trazas a una plataforma en beta justo en el eje que el experimento mide (H4, bloqueante).

---

## D6 — El LLM se consume vía Azure OpenAI

> **Revisado el 2026-09-11.** La versión anterior de D6 usaba Claude vía
> `AnthropicFoundry`. Por decisión del equipo se cambia a **modelos OpenAI** desplegados en el
> tenant de Pactia. El registro de lo que el cambio invalida está en §D6.4.

Cliente: **`OpenAI(api_key=..., base_url=...)`** del SDK oficial `openai`, apuntando a la
superficie **v1** de Foundry, que es compatible con la API de OpenAI. Construido en un único
punto ([`agentes/cliente.py`](../src/territorial/agentes/cliente.py)).

No se usa `AzureOpenAI`: esa clase sirve a la superficie clásica de Azure OpenAI, que tiene otra
forma de URL y exige `api_version`. Las llamadas van por la **Responses API**
(`client.responses.create`), no por chat.completions.

**Endpoint verificado:** `https://contratosai.services.ai.azure.com/openai/v1`
Termina en `/openai/v1` y **no** lleva `/responses` — eso lo añade el SDK. `normalizar_base_url()`
lo corrige si viene pegado, porque es el error más fácil al copiar del portal.

### D6.1 — Despliegues por agente

Verificado por llamada real contra el tenant el 2026-09-11.

| Agente | Despliegue | Razón |
|---|---|---|
| Clasificador | `gpt-5.4-mini` | Criba de 7.628 registros. **No es de razonamiento**: gastó 5 tokens de salida donde `gpt-5` gastó 117 para la misma respuesta trivial. A ese volumen la diferencia manda |
| Correlacionador | `gpt-5` | Cruza señales y extrapola implicación inmobiliaria. Es donde se juega H1, y aquí los tokens de razonamiento son la función, no el desperdicio |
| Sintetizador | `gpt-5` | Redacta el informe del top 3 bajo la restricción de CA-M6.3 |

El Agente Fuentes no usa LLM en el MVP: lee del snapshot (Addendum 01, D2).

**Disponibles sin asignar:** `gpt-5-mini` es la vía de escalada si `gpt-5.4-mini` no alcanza
CA-M2.1 (pendiente B2); `gpt-5.4-nano` es la de abaratamiento si el costo aprieta.

**Son nombres de despliegue, no nombres de modelo.** En Azure cada despliegue lleva el nombre que
se le puso al crearlo, que puede no coincidir con el del modelo. Es la causa más común de fallo
en la primera llamada.

### D6.2 — Modelos de razonamiento y techo de salida

`gpt-5` y `gpt-5-mini` consumen tokens de pensamiento **antes** de emitir texto. Medido: para
responder "ok", `gpt-5` gastó entre 64 y 173 tokens de salida, y `gpt-5-mini` 97; `gpt-5.4-mini`
y `gpt-5.4-nano` gastaron 5.

**Consecuencia práctica:** un `max_output_tokens` bajo corta al modelo antes de que llegue a
escribir nada, y la llamada devuelve vacío sin error. Por eso `max_tokens_salida` está en 4096
por defecto, no en el valor ajustado que bastaría para la respuesta visible.

**Consecuencia de costo:** la extrapolación de H5 debe contar los tokens de razonamiento, que no
aparecen en el texto pero sí en la factura. Es parte del pendiente B4.

### D6.3 — Diferencias frente al cliente anterior

| | Claude vía Foundry | Foundry v1, superficie OpenAI |
|---|---|---|
| Clase | `AnthropicFoundry` | `OpenAI` con `base_url` |
| Identificación | `resource="pactia-ia"` | `base_url=".../openai/v1"` (**URL completa**) |
| Versión de API | No aplica | No aplica en la superficie v1 |
| Llamada | `client.messages.create(...)` | `client.responses.create(...)` |
| Entrada | `messages=[...]` | `input=...` |
| Límite de salida | `max_tokens` | `max_output_tokens` |

### D6.4 — Lo que queda invalidado por el cambio

La tabla de capacidades que documentaba la versión anterior de D6 era específica de **Claude en
Foundry** y **no aplica a Azure OpenAI**. En concreto:

- **El hallazgo "Foundry no tiene Batch API" ya no vale como está escrito.** Era una limitación
  de Claude en Foundry. Azure OpenAI ofrece despliegues de tipo *batch* con tarifa reducida.
  **Sin verificar** contra el tenant de Pactia.
- **La estrategia de prompt caching cambia.** El caching de Claude es explícito y se mide con
  `usage.cache_read_input_tokens`; el de Azure OpenAI funciona con otro mecanismo y otras
  métricas de uso.
- **La estimación de costo de §D6 anterior queda sin base.** Estaba calculada con tarifas de
  Claude. Hay que rehacerla con las de los despliegues que efectivamente se creen.

**Queda como pendiente B4** (ver §Pendientes): verificar disponibilidad de batch, mecanismo de
caching y tarifas reales en el tenant, y rehacer la extrapolación de costo que alimenta **H5**.

### D6.5 — Lo que no cambia

La arquitectura es indiferente al proveedor, y eso es deliberado:

- El validador determinista (M3) y el motor de scoring (M5) **no usan LLM** (PRD §3.1). La pieza
  que mide la alucinación es la misma con cualquier modelo.
- `traza_agente.modelo` ya registra qué modelo corrió cada paso, así que el linaje sigue siendo
  reproducible tras el cambio.
- El cliente se construye en un solo archivo. Cambiar de proveedor otra vez tocaría ese archivo
  y el `.env`, no los agentes.

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
- **D6** · LLM vía Azure OpenAI (superficie v1) en el tenant de Pactia. Revisado 2026-09-11. Batch **sí** está disponible, al 50% (ver §96); el caching está disponible pero medido no se activa.
- **D7** · Blob para lo semi-estructurado e inmutable, SQL para lo consultable. SQL guarda la URI.
- **D8** · Local: carpeta + SQLite. Nube: Blob + Postgres. Misma interfaz, distinta configuración.
- **D9** · Los 3 ciclos se ejecutan a mano. El scheduler se difiere a Fase 0.
