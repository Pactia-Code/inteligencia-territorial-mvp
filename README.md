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

**`alembic check` después de cada `upgrade`, siempre.** El `Running upgrade` del
log no prueba que la migración terminara: ya ocurrió una que lo imprimió y falló
después, dejando la base en la revisión anterior. `check` compara el esquema
real contra los modelos y es lo único que lo detecta. Detalle en
[CLAUDE.md](CLAUDE.md) §6.1.

### A qué base apunta: `DATABASE_URL`

**Una sola variable decide la base.** No hay ninguna URL de entorno escrita en
el código; `DATABASE_URL` se lee del `.env` o del entorno, y se acepta el nombre
antiguo `URL_BASE_DATOS` con menos prioridad.

```powershell
# Local — SQLite, lo que corre el pipeline por defecto
$env:DATABASE_URL = "sqlite:///data/territorial.db"

# Neon — PostgreSQL gestionado. Pega la cadena tal cual la da el panel:
# el prefijo postgresql:// se reescribe solo a psycopg 3.
$env:DATABASE_URL = "postgresql://usuario:clave@ep-xxx.us-east-2.aws.neon.tech/territorial?sslmode=require"
```

**Neon publica dos hosts y solo uno sirve para migrar.** El que lleva `-pooler`
va por PgBouncer en modo transacción, que no conserva la sesión entre
sentencias: Alembic se rompería a media migración y la base quedaría en un
estado que depende de por dónde fuera. Usa el **directo**, el mismo host sin
`-pooler`. `aplicar_migraciones()` se niega a arrancar por el pooled en vez de
dejar que falle a mitad.

### Si conectar a Neon se cuelga: es IPv6

**Síntoma:** `alembic current` no da error, se queda colgado minutos. Pasó el
2026-09-21 y cuesta media tarde diagnosticarlo, así que queda escrito.

**Causa:** el DNS de Neon devuelve direcciones IPv6 **y** IPv4, y las IPv6
primero. En una red corporativa sin ruta IPv6, libpq las prueba en orden y cada
una agota el timeout por defecto del sistema antes de caer a IPv4. Medido en
esta máquina:

```
TCP 5432 por IPv6  ->  timeout           (no rutea)
TCP 5432 por IPv4  ->  conecta en 0,09s
psycopg sin connect_timeout  ->  cuelga varios minutos
psycopg con connect_timeout=20  ->  conecta en 61s  (3 intentos IPv6 + IPv4)
```

**Arreglo, y va puesto de forma permanente:** `connect_timeout` en la cadena.

```
DATABASE_URL=postgresql://...neon.tech/territorial?sslmode=require&connect_timeout=3
```

Baja el peaje a unos 9 segundos por conexión. **No es un apaño temporal**: es
configuración razonable para cualquier cliente en una red sin IPv6 y no molesta
donde sí la hay. Lo que **no** hay que dejar puesto es un `hostaddr=` con una IP
fija: funciona, pero Neon las rota.

Vercel sí tiene IPv6, así que esto no afecta a la app desplegada. Importa si el
pipeline corre desde esta red o desde un runner corporativo.

### Llevar la base a Neon

Los datos de desarrollo son SQLite, así que no hay `pg_dump` que restaurar: la
copia va por SQLAlchemy, fila a fila, que es además lo que exige la regla de que
todo acceso a datos pase por el ORM.

```powershell
$env:DATABASE_URL = "postgresql://...ep-xxx.us-east-2.aws.neon.tech/territorial?sslmode=require"

& $py -m alembic upgrade head        # crea el esquema desde cero
& $py -m alembic check               # y comprueba que no quedó deriva
& $py scripts\copiar_base.py          # copia local -> DATABASE_URL
& $py scriptserificar_copia.py      # y comprueba que la copia es fiel
```

`copiar_base.py` conserva los identificadores —renumerarlos rompería
`informe.id_corrida` y todo el linaje— y por eso reinicia las secuencias de
Postgres al terminar. También reetiqueta como UTC las fechas que SQLite devuelve
sin zona, para que no dependan de la zona del servidor. Se niega a escribir
sobre un destino que ya tenga filas salvo que se le pase `--vaciar`, y `--seco`
cuenta sin escribir.

`verificar_copia.py` hace tres comprobaciones y devuelve código distinto de cero
si alguna falla. La tercera es la que vale: **las corridas de scoring 3 y 4 son
idénticas municipio por municipio** pese a llevar etiquetas distintas, así que
si siguen siéndolo en el destino, los `float`, los enteros y el JSON cruzaron
sin deformarse. Contar filas no lo detectaría.

## El aplicativo web (M9)

Vive en [`web/`](web/) — Next.js sobre Vercel, leyendo Neon. No es Django: D5 del
Addendum 02 lo eligió antes de que el hosting fuera Vercel, y la desviación está
anotada allí.

```powershell
cd web
npm install
$env:DATABASE_URL = "postgresql://...neon.tech/territorial?sslmode=require"
npm run dev          # http://localhost:3000
npm run typecheck    # tsc --noEmit
npm run build
```

### La raíz de despliegue en Vercel es `web/`

**Esto no se puede deducir mirando el repositorio.** Vive solo en el panel de
Vercel, en *Settings → General → Root Directory*, y hay que ponerlo a mano:

```
Root Directory:  web
```

Sin eso, Vercel compila desde la raíz, no encuentra `package.json` y falla con
un error que no menciona la causa. El repositorio es un monorepo a medias —
Python en la raíz, la app en `web/`— porque D5 pedía un solo repositorio.

### Y la cadena de Neon en Vercel es la del **pooler**

Al revés que la de este README para el pipeline. Las funciones serverless abren
muchas conexiones cortas, así que la app va por el endpoint con `-pooler`;
Alembic va por el directo, porque por el pooled no se puede migrar. Son dos
cadenas para dos usos opuestos, y confundirlas falla en sitios distintos: la app
agotaría conexiones, y la migración se rompería a la mitad.

El `&connect_timeout=3` que lleva la cadena local **no hace falta en Vercel**:
allí sí hay ruta IPv6. No molesta si se queda.

### Lo que la app puede escribir

Solo `calificacion` y `seguimiento` (CA-M9.16). **No migra nada** — Alembic es la
única autoridad del esquema— y la forma de esas dos escrituras se verifica
contra `modelos.py`:

```powershell
& $py scripts\generar_contrato_ts.py          # regenera web/lib/contrato.generado.ts
& $py scripts\generar_contrato_ts.py --check  # falla si quedó desactualizado
```

`tests/test_contrato.py` corre ese `--check` dentro del suite, así que tocar
`modelos.py` sin regenerar rompe las pruebas de Python. Es lo que impide que la
app escriba contra una columna que ya no existe.

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

Verificado sobre el código el 2026-09-18. Las 139 pruebas de `tests/` pasan.
El detalle por criterio de aceptación está en [CLAUDE.md](CLAUDE.md) §4.

| Módulo | Estado |
|---|---|
| Ingesta del snapshot (M1) | ✅ Funcionando |
| Clasificador (M2) | 🟡 Funciona, persiste, trocea y registra descartes (CA-M2.5) — sigue **variando entre corridas** (A6) |
| Validador determinista (M3) | ✅ Funcionando — R1 a R7 |
| Correlacionador (M4) | 🟡 Funciona — CA-M4.3 sin poder probarse: no hay calificaciones |
| Scoring por reglas (M5) | 🟡 Funciona sobre **5 de 6 factores** — F6 nunca se activa sin calificaciones |
| Sintetizador (M6) | ⬜ Sin código |
| Calificación y aplicativo web (M7, M9) | ⬜ Sin código |
| Trazabilidad (M8) | 🟡 Parcial — linaje de dataset, de prompts (D7) y trazas por agente; falta Langfuse y CA-M8.4 |
| Esquema con Alembic | ✅ 2 migraciones, sin deriva |

**M7 es el cuello de botella oculto.** Sin él no hay calificaciones, y sin
calificaciones ni F6 del scoring ni el bucle de aprendizaje del Correlacionador
(CA-M4.3) pueden ejercitarse nunca.
