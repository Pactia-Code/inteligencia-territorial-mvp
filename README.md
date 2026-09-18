# MVP Inteligencia Territorial — Pactia

Validación de capacidades agénticas sobre fuentes públicas colombianas.
Experimento de 8 semanas y 3 ciclos para decidir go/no-go sobre la Fase 0.

## Documentos

| Documento | Qué contiene |
|---|---|
| [PRD del MVP](docs/prd.md) | Hipótesis H1–H5, alcance, arquitectura, criterios de aceptación |
| [Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) | Decisiones D1–D4 sobre el snapshot, los ciclos y el scoring |
| [Addendum 02 — Stack](docs/addendum-02-stack.md) | Decisiones D5–D9 sobre tecnología, almacenamiento y entorno |

## Entorno

El proyecto corre sobre un entorno virtual **fuera del repositorio**, porque la
política corporativa de esta máquina impide ejecutar binarios desde `Downloads`.

```
%LOCALAPPDATA%\venvs\territorial\Scripts\python.exe
```

Ese es el intérprete a usar siempre. El comando `python` a secas resuelve al stub
de Microsoft Store y no sirve.

### Montar el entorno desde cero

```powershell
# 1. uv (gestor de paquetes y de versiones de Python)
#    Se instala descargando el zip de github.com/astral-sh/uv/releases
#    a %LOCALAPPDATA%\Programs\uv

# 2. Python 3.12 — sin pasar por el instalador MSI, que la política bloquea
uv python install 3.12

# 3. Entorno virtual. Se usa el modulo venv estandar, no `uv venv`:
#    uv crea un trampolin sin firmar que la política tambien bloquea.
$base = "$env:APPDATA\uv\python\cpython-3.12-windows-x86_64-none\python.exe"
& $base -m venv "$env:LOCALAPPDATA\venvs\territorial"

# 4. Dependencias
uv pip install --python "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe" -r pyproject.toml
```

### Configuración

```powershell
Copy-Item .env.example .env
```

Luego se rellenan los valores en `.env`. Los tres que importan:

| Variable | Qué es | Dónde se obtiene |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | La clave | Portal de Azure AI Foundry → recurso → *Keys and Endpoint* |
| `AZURE_OPENAI_ENDPOINT` | **URL completa**, con `https://` y sin barra final | Misma pantalla, campo *Endpoint* |
| `MODELO_*` | **Nombre del despliegue**, no del modelo | Columna *Deployment name* del portal |

Para comprobar que quedó bien:

```powershell
& $py scripts\verificar_llm.py
```

`.env` nunca se sube a git. `.env.example` sí, con valores de ejemplo.

**Ni la ingesta ni la capa determinista necesitan la clave** — solo los agentes.

## Uso

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"

& $py scripts\cargar_snapshot.py                              # M1 — ingesta
& $py scripts\correr_ciclo.py --ciclo 1 --municipio 05147     # M2 → M3 → M4
& $py scripts\calcular_scores.py --ciclo 1                    # M5 — top 3
& $py scripts\estimar_costo.py                                # costo por ciclo
```

`cargar_snapshot.py` carga los 18 municipios y las 20.030 señales, normaliza los
DIVIPOLA a 5 dígitos y reparte las señales en los 3 ciclos. Aplica las
migraciones de Alembic por su cuenta, así que sirve sobre una base vacía.

`correr_ciclo.py` **gasta tokens**: sin `--municipio` procesa los 18, en lotes de
50 señales por llamada. Prueba siempre con uno primero; `--seco` corre y
revierte. **No recalcula los scores** — eso es `calcular_scores.py`, que no
llama a ningún LLM y se puede repetir cuantas veces haga falta.

Scripts de calibración: `medir_prefiltro.py`, `probar_clasificador.py`,
`probar_correlacionador.py` y `comparar_prompts.py`, que mide dos versiones de
prompt sobre el mismo lote.

### Migraciones

```powershell
& $py -m alembic current                              # en qué revisión está
& $py -m alembic upgrade head                         # aplicar pendientes
& $py -m alembic revision --autogenerate -m "motivo"  # tras tocar modelos.py
& $py -m alembic check                                # ¿esquema y modelos concuerdan?
```

## Estructura

```
docs/                         PRD y addenda. El snapshot es el origen de verdad.
config/                       Datos de negocio editables sin tocar código
  tarifas.json                Tarifas del tenant, para estimar costo
  pesos.json                  Pesos del score (opcional; sin él rigen los de D4)
alembic/                      Migraciones. El esquema se gobierna desde aquí.
src/territorial/
  config.py                   Configuración leída de .env
  ciclo.py                    Orquesta prefiltro → M2 → M3 → M4 por municipio
  almacen/
    blob.py                   Objetos semi-estructurados: local o Azure Blob
    modelos.py                Esquema SQL (PRD §4.2 + linaje)
    sesion.py                 Motor, sesiones y aplicar_migraciones()
  ingesta/snapshot.py         Carga del snapshot y partición en ciclos
  reglas/                     CAPA DETERMINISTA — nunca LLM
    validador.py              M3 — R1 a R7 sobre la evidencia
    prefiltro.py              Diccionario de obra e infraestructura
    cobertura.py              Días cubiertos y redistribución de pesos
    normalizacion.py          Comparación de citas contra la fuente
  scoring/                    M5 — determinista
    factores.py               F1–F6 y normalización por cohorte
    pesos.py                  Pesos configurables (CA-M5.3)
    ranking.py                Score, top 3 y desglose (CA-M5.5)
    agregacion.py             Único módulo de M5 que conoce el ORM
    persistencia.py           Escritura idempotente en score_municipio
  agentes/                    CAPA LLM
    clasificador.py           M2
    correlacionador.py        M4
    cliente.py                Cliente único contra el tenant
    persistencia.py           Insights, consolidados y trazas
    prompts/                  Versionados (D7)
  utiles/divipola.py          Normalización de códigos DIVIPOLA
scripts/                      Puntos de entrada
data/                         Generado localmente. No se versiona.
```

## Reglas del proyecto

Tres reglas de obligado cumplimiento, por la decisión D8 de usar SQLite en local
y PostgreSQL en nube:

1. Todo acceso a datos pasa por **SQLAlchemy**. Nunca SQL crudo de un motor.
2. El esquema se gobierna con **Alembic** desde la primera migración.
3. Las columnas JSON usan el tipo `JSON` portátil, **nunca operadores JSONB**
   de PostgreSQL (`->>`, `@>`, `jsonb_path_query`).

Y una del PRD, que es bloqueante: **ninguna cifra de un informe o infografía
puede provenir del LLM** (CA-M6.3). Todas se componen desde el almacén de datos.

## Estado

Verificado sobre el código el 2026-09-18. Las 106 pruebas de `tests/` pasan.
El detalle por criterio de aceptación está en [CLAUDE.md](CLAUDE.md) §4.

| Módulo | Estado |
|---|---|
| Ingesta del snapshot (M1) | ✅ Funcionando |
| Clasificador (M2) | 🟡 Funciona, persiste y trocea — **CA-M2.5 sin cumplir**: los descartes no se guardan |
| Validador determinista (M3) | ✅ Funcionando — R1 a R7 |
| Correlacionador (M4) | 🟡 Funciona — CA-M4.3 sin poder probarse: no hay calificaciones |
| Scoring por reglas (M5) | 🟡 Funciona sobre **5 de 6 factores** — F6 nunca se activa sin calificaciones |
| Sintetizador (M6) | ⬜ Sin código |
| Calificación y aplicativo web (M7, M9) | ⬜ Sin código |
| Trazabilidad (M8) | 🟡 Parcial — linaje de dataset y trazas por agente; falta el linaje de prompts y Langfuse |
| Esquema con Alembic | ✅ 2 migraciones, sin deriva |

**M7 es el cuello de botella oculto.** Sin él no hay calificaciones, y sin
calificaciones ni F6 del scoring ni el bucle de aprendizaje del Correlacionador
(CA-M4.3) pueden ejercitarse nunca.
