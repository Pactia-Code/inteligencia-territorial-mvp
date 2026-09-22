# MVP Inteligencia Territorial — Pactia

Validación de capacidades agénticas sobre fuentes públicas colombianas.
Experimento de 8 semanas y 3 ciclos para decidir go/no-go sobre la Fase 0.

## Estado — 2026-09-22

**El pipeline funciona de punta a punta y produce un informe. Lo que falta es la
mitad que mira a las personas**, y es donde se miden las dos hipótesis que
deciden el go/no-go.

| Módulo | Estado | |
|---|---|---|
| **M1** Ingesta | ✅ | 18 municipios, 20.030 señales |
| **M2** Clasificación | ✅ | Prompt v4. Reduce 95,2%. **No reproducible**: 19,5% de las señales cambian de destino entre pasadas |
| **M3** Validación | ✅ | 7 reglas, código puro. Nunca un LLM |
| **M4** Correlación | ✅ | Prompt v2, con contexto estructural. **No reproducible**: 14,1% de convergencias se repiten |
| **M5** Scoring | ✅ | F1–F6, top 10, desglose por fuente. **Código determinista: lo único reproducible del sistema** |
| **M6** Síntesis | 🟡 | Composición y publicación hechas. **Falta el Sintetizador** (la prosa) |
| **M7** Calificación | ⬜ | En construcción |
| **M8** Trazabilidad | 🟡 | Linaje y trazas por agente sí. Langfuse y checkpointing **instalados sin cablear** |
| **M9** Aplicativo web | 🟡 | Vista de ciclo hecha. Faltan calificación, priorizados, histórico y métricas |

### La app

Vive en [`web/`](web/) — Next.js sobre Vercel. De las tres vistas de CA-M9.3
más el panel:

| Vista | Ruta | Estado |
|---|---|---|
| Ciclo actual | `/ciclo/[id]` | ✅ Lista de 10 municipios, score y línea de fuentes |
| Municipios priorizados | `/priorizados` | ⬜ |
| Histórico | `/historico` | ⬜ |
| Métricas (solo administrador) | `/metricas` | ⬜ |

La **calificación** es lo siguiente, y va dentro de la vista de ciclo.

### Qué hay en la base

Las mismas filas en la SQLite local y en Neon.

| | |
|---|---|
| Señales · insights · descartes | 20.030 · 1.213 · 5.731 |
| Corridas de agentes · de scoring | 12 · 24 |
| Ciclos publicables | **1 y 3**. El **ciclo 2 nunca se corrió entero**: su única corrida de agentes tiene 1 de 18 municipios, así que `publicar()` lo rechaza |
| Informes publicados | **1** — ciclo 3, congelando scoring 24 y agentes 10 |
| Calificaciones · usuarios | **0 · 0** — por eso H1 y H2 no tienen ningún dato |
| Nomenclátor · contexto municipal | 1.135 entidades · 1.102 municipios |

### Qué se puede correr hoy

| Qué | Comando | Contra qué base |
|---|---|---|
| Pipeline de un ciclo | `$py scripts\correr_ciclo.py --ciclo 3 --municipio 05147` | `DATABASE_URL` |
| Scoring | `$py scripts\calcular_scores.py --ciclo 3` | `DATABASE_URL` |
| Migraciones | `$py -m alembic upgrade head` · `check` | `DATABASE_URL`, **host directo** |
| Copiar local → nube | `$py scripts\copiar_base.py` | de SQLite a `DATABASE_URL` |
| Pruebas | `$py -m pytest -q` | ninguna: aisladas |
| La app | `cd web` · `npm run dev` | `DATABASE_URL`, **host pooled** |

> ### Dos configuraciones que no se deducen mirando el repositorio
>
> **1. La raíz de despliegue en Vercel es `web/`.** Vive solo en el panel, en
> *Settings → General → Root Directory*. Sin eso Vercel compila desde la raíz,
> no encuentra `package.json` y falla con un error que no menciona la causa.
>
> **2. La cadena de Neon de la app es la del `-pooler`; la del pipeline es la
> directa.** Las funciones serverless abren muchas conexiones cortas, así que la
> app va por el pooler; Alembic va por el directo porque **por el pooled no se
> puede migrar**. Confundirlas falla en sitios distintos: la app agotaría
> conexiones y la migración se rompería a la mitad.
>
> Las dos están explicadas más abajo, en [El aplicativo web](#el-aplicativo-web-m9).

## Documentos

| Documento | Qué contiene |
|---|---|
| [PRD del MVP](docs/prd.md) | Hipótesis H1–H5, alcance, arquitectura, criterios de aceptación |
| [Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) | Decisiones D1–D4 sobre el snapshot, los ciclos y el scoring |
| [Addendum 02 — Stack](docs/addendum-02-stack.md) | Decisiones D5–D9 sobre tecnología, almacenamiento y entorno |
| [Design System](docs/design-system.md) | **Autoridad de color y tipografía.** Navy `#0F4761` y Aptos, de la plantilla corporativa |
| [Pendientes](docs/pendientes.md) | Registro único de lo que falta decidir, y de lo decidido |
| [Informe de resultados](docs/informe_resultados.md) | Lo medido por hipótesis, para la compuerta de la semana 8 |

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
& $py scripts\calcular_scores.py --ciclo 1                    # M5 — top 10
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

> **El sistema no envía ningún correo.** No hay canal de notificación en el MVP
> (pendiente 11.4/3) ni código que mande nada: **el enlace se comparte a mano**,
> por fuera del sistema. Si buscas el servicio de envío, no existe.
>
> Lo que sí hay es **identificación por correo**, que es otra cosa. El flujo:
>
> 1. El enlace se comparte fuera del sistema.
> 2. Cualquiera que lo tenga **lee sin identificarse**.
> 3. Al intentar **calificar** se pide el correo.
> 4. Se valida contra `usuario`. Si está, califica con su gerencia.
> 5. Si no está, **solo visualiza**, con el mensaje «este correo no está en la
>    lista» y a quién escribir — nunca un error genérico.

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

## Qué falta, y por qué ese orden

**El estado por módulo está arriba.** Lo que queda, en orden de lo que bloquea:

1. **M7 y M9 — calificación y aplicativo.** Es el único pendiente que bloquea el
   go/no-go. **H1 y H2 no tienen un solo dato** y ambas se miden ahí; H2 es
   condición necesaria para el GO según la regla de decisión del PRD §11. No
   tiene decisiones abiertas: solo código.
2. **M6 — el Sintetizador.** La composición ya está; falta la prosa. Su costo es
   además la cifra que falta para cerrar H5.
3. **Las hojas de revisión del equipo.** Llegan cuando lleguen y destraban A2,
   A4 y el criterio de frontera del Clasificador.

**Lo que no bloquea**: Langfuse y el checkpointing de CA-M8.4 son deuda, no
cuello — el pipeline ya se reanuda porque confirma municipio a municipio y las
trazas por agente existen sin Langfuse.

Si la semana 8 llega con un pipeline impecable y cero calificaciones, la
compuerta es NO-GO por falta de datos, no por el sistema.
