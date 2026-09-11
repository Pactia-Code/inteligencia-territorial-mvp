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
& $py scripts\cargar_snapshot.py
```

Carga los 18 municipios y las 20.030 señales del snapshot, normaliza los códigos
DIVIPOLA a 5 dígitos y reparte las señales en los 3 ciclos.

## Estructura

```
docs/                         PRD y addenda. El snapshot es el origen de verdad.
src/territorial/
  config.py                   Configuración leída de .env
  almacen/
    blob.py                   Objetos semi-estructurados: local o Azure Blob
    modelos.py                Esquema SQL (PRD §4.2 + linaje)
    sesion.py                 Motor y sesiones de SQLAlchemy
  ingesta/snapshot.py         Carga del snapshot y partición en ciclos
  utiles/divipola.py          Normalización de códigos DIVIPOLA
scripts/cargar_snapshot.py    Punto de entrada de la ingesta
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

| Módulo | Estado |
|---|---|
| Ingesta del snapshot (M1) | ✅ Funcionando |
| Clasificador (M2) | Pendiente |
| Validador determinista (M3) | Pendiente |
| Correlacionador (M4) | Pendiente |
| Scoring por reglas (M5) | Pendiente — diseño en Addendum 01 D4 |
| Sintetizador (M6) | Pendiente |
| Calificación y aplicativo web (M7, M9) | Pendiente |
| Trazabilidad (M8) | Parcial — linaje de dataset listo |
