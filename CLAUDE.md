# CLAUDE.md — MVP Inteligencia Territorial (Pactia)

Guía de trabajo para agentes sobre este repositorio.
**Actualizado:** 2026-09-17

---

## 1. Qué es este proyecto

Un **experimento acotado, no un producto.** Es la *Fase -1* del PRD de
Inteligencia Territorial v1.2 de Pactia: 8 semanas, 3 ciclos quincenales, para
decidir go/no-go sobre la Fase 0.

Comprueba si una cadena multiagente puede extraer señal inmobiliaria accionable
de fuentes públicas colombianas. El pipeline va de un snapshot de datos
(SECOP II, feed de noticias, Bing, TerriData) a un informe del top 3 de
municipios que 7 gerencias califican de 1 a 5 durante 3 ciclos.

| Dato | Valor |
|---|---|
| Municipios | **18** — los que trae el snapshot, no los 25-30 que preveía el PRD §2.1 |
| Señales | 20.030, repartidas en 3 ciclos por la fecha de cada registro (D2) |
| LLM | Azure OpenAI, superficie v1 de Foundry, **Responses API** (no `chat.completions`) |
| Base | SQLAlchemy sobre SQLite en local, PostgreSQL en nube (D8) |

Las hipótesis que valida son H1–H5 ([PRD §1](docs/prd.md)). **H4 — trazabilidad
al 100% — es bloqueante**: si falla, la arquitectura no es auditable y no puede
ir a producción. No se resuelve con más ingeniería.

Documentos de referencia, en orden de autoridad: [PRD](docs/prd.md) ·
[Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) ·
[Addendum 02 — Stack](docs/addendum-02-stack.md) ·
[Arquitectura](docs/architecture.md) · [Pendientes](docs/pendientes.md)

> El PRD principal v1.2 **no está en el repositorio** (pendiente 11.5). Varias
> referencias citadas en otros documentos vienen de ahí y no se pueden
> verificar. No inventes requisitos para cubrirlas.

---

## 2. Reglas de obligado cumplimiento

### 2.1 Datos — consecuencia de D8 (SQLite local / PostgreSQL nube)

1. **Todo acceso a datos pasa por SQLAlchemy.** Nunca SQL crudo de un motor.
2. **El esquema se gobierna con Alembic** desde la primera migración.
3. **Las columnas JSON usan el tipo `JSON` portátil.** Nunca operadores JSONB de
   PostgreSQL (`->>`, `@>`, `jsonb_path_query`): no existen en SQLite y rompen
   el entorno local.

### 2.2 Bloqueante — CA-M6.3

**Ninguna cifra de un informe o infografía puede provenir del LLM.** Todas se
componen desde el almacén de datos. El LLM redacta; los números los pone el
código. Esta regla no admite excepción ni atajo.

### 2.3 Corolarios que sostienen H4

- El validador (M3) es **código, nunca LLM**. Si un modelo decidiera qué
  evidencia es suficiente, el experimento perdería su ancla: un agente elocuente
  parece funcionar aunque invente. **Su tasa de rechazo es la tasa de
  alucinación medida** (CA-M3.3).
- **Bing nunca es evidencia** (Addendum 01, D1). Es contexto cualitativo: llega
  sin fecha y sin URL. El validador lo rechaza por la regla R2.
- Los prompts van **versionados** y se archivan en el almacén (D7). El linaje se
  registra; no se edita un prompt en sitio.

---

## 3. Separación de capas

La frontera entre capas es lo que sostiene H4:
**lo determinista nunca depende de un LLM, y lo agéntico nunca decide qué es
evidencia suficiente** (PRD §3.1).

```
src/territorial/
│
├── CAPA 1 — DETERMINISTA (código, nunca LLM)
│   ├── ingesta/     Carga, particionado por ciclo, deduplicación
│   ├── reglas/      validador.py · prefiltro.py · cobertura.py · normalizacion.py
│   └── scoring/     M5 — F1–F6, pesos, ranking del top 3   [aún sin código]
│
├── CAPA 2 — AGENTES (LLM)
│   ├── agentes/     fuentes · clasificador · correlacionador · sintetizador
│   ├── agentes/prompts/   Versionados (D7)
│   └── grafo/       EstadoCiclo y flujo LangGraph            [aún sin código]
│
├── CAPA 3 — SUPERFICIE
│   ├── web/         Django                                   [aún sin código]
│   ├── informes/    Jinja2 e infografías                     [aún sin código]
│   └── notificacion/  Correo con enlace profundo             [aún sin código]
│
└── TRANSVERSAL
    ├── almacen/     blob.py · modelos.py · sesion.py
    ├── observabilidad/  Langfuse, trazas de ciclo            [aún sin código]
    ├── utiles/      divipola.py
    └── config.py
```

Al añadir código, respeta la capa. Una regla de negocio no vive en un prompt, y
una llamada a LLM no vive en `reglas/`.

---

## 4. Estado real por módulo

Diagnóstico verificado sobre el árbol de trabajo el 2026-09-17. Las 35 pruebas
de [tests/test_reglas.py](tests/test_reglas.py) pasan.

| Módulo | Estado | Detalle |
|---|---|---|
| **M1** Ingesta por API (Agente Fuentes) | ✅ Funciona | Carga los 18 municipios y las 20.030 señales; `data/territorial.db` poblada. Conectores vivos diferidos a Fase 0 |
| **Prefiltro** (apoya M2 y M5) | 🟡 Implementado, sin validar | Reduce 61,2%. El diccionario de obra produce entre 13% y 90% según el municipio — rango demasiado ancho para confiar en él (**pendiente A2**) |
| **M2** Clasificación | 🟡 Funciona, no alcanza el criterio | Salida estructurada con `responses.parse` y esquema pydantic; prompt en **v4**. Reducción medida 43,5%–49,0%, pero **CA-M2.1 exige 85% combinado**, lo que obliga a descartar otro 61,4% de lo que recibe (**pendiente B2**) |
| **M3** Validación determinista | ✅ Funciona | 7 reglas R1–R7. Tasa de rechazo 0,0% tras corregir el falso positivo de puntuación de SECOP. **Muestra pequeña: insuficiente para concluir sobre H4** |
| **M4** Correlación | ⬜ Sin código | — |
| **M5** Scoring y priorización | ⬜ Sin código | Diseño cerrado en Addendum 01 **D4** (seis factores). Los **pesos definitivos** los decide Gerencia General (**pendiente A1/4**) |
| **M6** Síntesis y distribución | ⬜ Sin código | Canal de notificación sin decidir (**pendiente 11.4/3**); §2.2 excluye Teams |
| **M7** Calificación | ⬜ Sin código | Depende del aplicativo web |
| **M8** Trazabilidad y observabilidad | 🟡 Parcial | Linaje de dataset listo en `almacen/`. Langfuse 4.15.4 y langgraph 1.2.11 están **instalados pero sin cablear**: no hay `grafo/` ni trazas por agente |
| **M9** Aplicativo web | ⬜ Sin código | Django **no está instalado** ni tiene versión fijada. Playwright está por verificar: descarga binarios sin firmar que la política de esta máquina bloquea |

### Pendientes que frenan el avance

- **B2** — el Clasificador no alcanza CA-M2.1. No es un ajuste fino.
- **A4** — tras cuatro versiones del prompt, el Clasificador sigue partiendo un
  mismo frente de obra en varios insights (cuatro de pavimentación en Carepa).
  Infla el conteo y degrada el informe.
- **A3** — atribución geográfica (R8). El 0,5% de las señales SECOP nombran un
  municipio distinto al que están archivadas, y entran municipios fuera del MVP
  (caso Frontino). Resolverlo exige un nomenclátor DIVIPOLA de los 1.103
  municipios, que el snapshot no trae.
- **B4** — **H5 quedó sin base** tras el cambio de proveedor a Azure OpenAI. Hay
  que rehacer la estimación de costo contando los **tokens de razonamiento**,
  que no aparecen en el texto pero sí en la factura.

---

## 5. Problemas abiertos en el repositorio

1. **La tabla «Estado» del [README.md](README.md) está desactualizada.** Declara
   M2 y M3 como pendientes, cuando ambos están en el repo desde los commits
   `440fe58` y `6f0b098`. La tabla de §4 de este archivo es la fuente correcta
   mientras el README no se corrija.

*Cerrado 2026-09-17:* Alembic estaba instalado pero sin inicializar. Ya existe
`alembic/` con la migración de línea base `949a8ff9e15d`, la ingesta migra en
vez de llamar a `create_all` y la base de desarrollo quedó estampada en `head`.
Ver §6.1.

---

## 6. Entorno

El intérprete vive **fuera del repositorio**, porque la política corporativa
impide ejecutar binarios desde `Downloads`. `python` a secas resuelve al stub de
Microsoft Store y no sirve.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py scripts\cargar_snapshot.py     # ingesta
& $py scripts\verificar_llm.py       # comprueba la conexión al tenant
& $py -m pytest -q                   # pruebas
```

Scripts de calibración: `medir_prefiltro.py`, `probar_clasificador.py`
(prefiltro → Clasificador → Validador en miniatura) y `comparar_prompts.py`,
que mide dos versiones de prompt sobre el mismo lote.

### 6.1 Migraciones (regla 2 de D8)

```powershell
& $py -m alembic current                              # en qué revisión está
& $py -m alembic upgrade head                         # aplicar pendientes
& $py -m alembic revision --autogenerate -m "motivo"  # tras tocar modelos.py
& $py -m alembic check                                # ¿el esquema y los modelos concuerdan?
```

Cuatro cosas que ahorran un rato:

- **`aplicar_migraciones()` en `almacen/sesion.py` es el camino desde código.**
  La ingesta lo llama; ya no existe `crear_esquema`. `create_all` quedó
  prohibido porque crea lo que falta y calla ante lo que cambió.
- **La URL no está en `alembic.ini`.** Sale de `Config.url_base_datos` vía
  `env.py`. No la escribas en el `.ini` o local y nube se separarán sin aviso.
- **`render_as_batch=True` está activo**, y es obligatorio: SQLite no sabe
  eliminar una columna ni cambiarle el tipo con un `ALTER TABLE` normal.
- **`--autogenerate` compara contra la base a la que apuntes.** Si esa base ya
  tiene las tablas, la migración sale vacía. Genera contra una base limpia:
  `URL_BASE_DATOS="sqlite:///$env:TEMP\vacia.db"`.

Corre `alembic check` antes de abrir una PR que toque `modelos.py`: falla si el
modelo y las migraciones se desincronizaron.

**Ni la ingesta ni la capa determinista necesitan la clave** — solo los agentes.
`.env` nunca se sube a git; `.env.example` sí.

### Notas del tenant, verificadas por llamada real

- Cliente `OpenAI` con `base_url`, **no** `AzureOpenAI`. `api_version` no aplica
  en esta superficie.
- Despliegues asignados: clasificador `gpt-5.4-mini`, correlacionador `gpt-5`,
  sintetizador `gpt-5`. El criterio salió de una medición de tokens, no de una
  preferencia.
- Un `max_output_tokens` bajo **corta a los modelos de razonamiento antes de que
  emitan texto, y la llamada vuelve vacía sin error.** El techo queda en 4096.

---

## 7. Al cambiar el prompt de un agente

No lo afines a ojo. Crea una versión nueva en `agentes/prompts/`, córrela contra
la anterior sobre el mismo lote con `comparar_prompts.py` y reporta las métricas
(reducción, tasa de rechazo, señales sin contabilizar, insights duplicados,
tokens). Las versiones que resultan peores **se conservan como registro**: v3
está en el repo porque documenta una hipótesis que resultó incorrecta.
