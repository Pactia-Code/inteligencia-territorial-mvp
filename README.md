# MVP Inteligencia Territorial — Pactia

Valida si una cadena multiagente puede extraer señal inmobiliaria accionable de
fuentes públicas colombianas. Es la **Fase -1** del PRD: un experimento de 8
semanas y 3 ciclos para decidir go/no-go sobre la Fase 0, **no un producto**.

El pipeline va de un snapshot de datos —SECOP II, feed de noticias, TerriData—
a un informe de los **10 municipios mejor puntuados** que **7 gerencias**
califican de 1 a 5.

## Estado — 2026-09-23

**Desplegado y en uso.** El despliegue terminó el 2026-09-23, 11 de 11 pasos
(ver [estado-despliegue.md](docs/estado-despliegue.md)).

| | |
|---|---|
| **Aplicación** | <https://inteligencia-territorial-mvp.vercel.app> — Vercel, rama de producción `main` |
| **Informe publicado** | **el 8**, ciclo 3, congelando scoring 24 y agentes 10 · 241 insights, 933 citas, 10 municipios |
| **Ronda de calificación** | En curso, **hasta el martes 2026-09-29** ([bitácora](docs/ronda-calificacion.md)) |
| **Base** | Neon PostgreSQL, base `territorial`, rama `main` · Alembic en `d5932c3bdc03` |
| **Usuarios** | 8 activos: 7 gerencias calificadoras y 1 administrador |
| **Pruebas** | 345, en verde |

> ### Tres reglas operativas en vigor
>
> **1. Congelamiento hasta el corte del martes 29.** No se republica el informe
> ni se cambia nada que altere lo que ven los calificadores: ni el payload, ni
> los textos, ni la selección pedida. Republicar cambiaría los insights pedidos
> y las calificaciones ya emitidas dejarían de ser comparables. **Solo se
> corrige un error que impida calificar**, y queda anotado en la bitácora.
>
> **2. No se corren ciclos nuevos** hasta cerrar el bloque **P4** del
> [plan](docs/plan-siguientes-pasos.md): una corrida interrumpida hoy queda
> marcada como completa y es publicable (H-037).
>
> **3. `correr_ciclo.py --seco` no es seco: escribe y gasta tokens** (H-038).
> No lo uses. El `--seco` de `publicar_informe.py` sí revierte, y ese es el que
> hay que usar antes de publicar.

## Qué está construido y qué no

**Construido y funcionando:**

| | |
|---|---|
| **Ingesta** (M1) | 18 municipios y 20.030 señales desde el snapshot, repartidas en 3 ciclos |
| **Clasificador** (M2) | Prompt v4, lotes de 50. Reduce el 95,2% de las señales |
| **Correlacionador** (M4) | Cruza señales de categorías distintas sobre un mismo municipio. **Corre con el prompt v1**, que es lo publicado; v2 es candidata y espera a F2.3 |
| **Validador** (M3) | 7 reglas **en código, nunca un LLM**. Su tasa de rechazo es la tasa de alucinación medida |
| **Scoring** (M5) | F1–F6, top 10 con desglose por fuente. **Código determinista: lo único reproducible del sistema** |
| **Composición y publicación** (M6) | El payload se compone desde el almacén y se publica congelando las dos corridas |
| **Aplicativo** (M9) | Vista de ciclo, identificación por correo y calificación, en producción |

**No construido, y conviene saberlo antes de buscarlo:**

- **El Sintetizador no existe.** `justificacion` y `sugerencias` viajan vacías y
  la pantalla pinta el hueco. **El informe se compone de forma determinista**:
  las cifras, los factores y las citas las pone el código, que es justamente lo
  que CA-M6.3 exige. Lo que falta es la prosa. Es el hueco grande del bloque
  **P3** del [plan](docs/plan-siguientes-pasos.md), y el único ítem **sin
  estimación**, porque la auditoría no lo planificó: no es un defecto, es
  trabajo pendiente.
- **Histórico, panel de métricas y trazabilidad en pantalla** — también P3.
- **El sistema no envía ningún correo.** No hay canal de notificación ni código
  que mande nada: **el enlace se comparte a mano**, fuera del sistema.
- **No hay autenticación.** Leer es abierto con el enlace; calificar pide el
  correo y lo valida contra la lista precargada.
- **La infografía se retiró** formalmente del MVP (F0.8). No es deuda.
- **No es Django.** D5 lo eligió antes de que el hosting fuera Vercel y nunca se
  instaló; la desviación está registrada en el Addendum 02.

## Arquitectura

```
 snapshot ──► pipeline Python ──►  Neon (PostgreSQL)  ◄── app Next.js ──► Vercel
              determinista y agentes   base «territorial»       web/
```

**Una sola base y ninguna API intermedia**, que es lo que pide el PRD §4.3. La
app **lee Neon directamente**: la regla de que todo acceso pase por SQLAlchemy
protege las escrituras y el esquema, y una app que solo lee no puede corromper
nada. Sus tres escrituras —calificación, comentario y seguimiento— se verifican
contra `modelos.py` mediante un contrato generado, y **la app no migra nunca**.

La frontera entre capas es lo que sostiene H4: **lo determinista nunca depende
de un LLM, y lo agéntico nunca decide qué es evidencia suficiente.**

```
src/territorial/
  reglas/      validador · prefiltro · cobertura · contexto     CAPA DETERMINISTA
  scoring/     factores · pesos · ranking · persistencia        nunca un LLM
  agentes/     clasificador · correlacionador · prompts/        CAPA LLM
  informes/    composicion · publicacion · seleccion            CAPA SUPERFICIE
  almacen/     modelos · sesion · blob                          TRANSVERSAL
web/           La app: Next.js, Server Actions, sin API intermedia
alembic/       Migraciones. Única autoridad del esquema.
config/        usuarios.csv · gerencias.json · pesos.json · tarifas.json
```

## Configuración local

El intérprete vive **fuera del repositorio**, porque la política corporativa
impide ejecutar binarios desde `Downloads`. El comando `python` a secas resuelve
al stub de Microsoft Store y no sirve.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
```

Para montar el entorno desde cero, ver [CLAUDE.md](CLAUDE.md) §6.

```powershell
Copy-Item .env.example .env      # y se rellenan los valores
```

**Las variables, por nombre. Los valores no están en el repositorio y no deben
estarlo:**

| Variable | Qué es | Quién la necesita |
|---|---|---|
| `DATABASE_URL` | La base contra la que corre todo | Todo |
| `AZURE_OPENAI_API_KEY` | La clave del tenant | Solo los agentes |
| `AZURE_OPENAI_ENDPOINT` | URL completa, con `https://` y sin barra final | Solo los agentes |
| `MODELO_CLASIFICADOR`, `MODELO_CORRELACIONADOR`, `MODELO_SINTETIZADOR` | **Nombre del despliegue**, no del modelo | Solo los agentes |
| `COOKIE_SECRET` | Firma la cookie de identificación (HMAC-SHA256) | Solo la app |

**Ni la ingesta ni la capa determinista necesitan la clave** — solo los agentes.
`.env` nunca se sube a git; `.env.example` sí, con los nombres y sin valores.

**Sin `COOKIE_SECRET` la app falla cerrado a propósito**: no emite identidad, la
pantalla explica por qué y leer el informe sigue funcionando. Es decir, **si
falta en Vercel nadie puede calificar** aunque todo lo demás esté bien. Se
genera una sola vez con `secrets.token_urlsafe(48)`. Cambiarlo invalida las
cookies emitidas —hay que volver a teclear el correo— pero **no pierde ninguna
calificación**.

### A qué base apunta

Una sola variable decide contra qué base corre todo, y **no hay ninguna URL
escrita en el código**. Se acepta el nombre antiguo `URL_BASE_DATOS` con menos
prioridad, así que **si borras `DATABASE_URL` vuelve a SQLite sin avisar**.

```powershell
$env:DATABASE_URL = "sqlite:///data/territorial.db"
$env:DATABASE_URL = "postgresql://...neon.tech/territorial?sslmode=require&connect_timeout=3"
```

Tres cosas que cuesta descubrir solas:

- **Neon publica dos hosts y son para usos opuestos.** El `-pooler` va por
  PgBouncer en modo transacción y **por ahí no se puede migrar**: Alembic se
  rompería a media migración. `exigir_directa()` se niega a arrancar por el
  pooled, y lo comprueban los dos caminos a Alembic. **La app sí usa el
  pooler**, porque las funciones serverless abren muchas conexiones cortas.
- **Si conectar se cuelga sin error, es IPv6.** El DNS de Neon devuelve IPv6
  primero y esta red no la rutea, así que libpq agota el timeout del sistema
  antes de caer a IPv4. Por eso la cadena lleva **`&connect_timeout=3`**, y va
  permanente. En Vercel no hace falta y además no hace nada: la app usa el
  driver HTTP de Neon, que no mira ese parámetro.
- **`alembic check` después de cada `upgrade`, siempre.** El `Running upgrade`
  del log no prueba que la migración terminara: ya ocurrió una que lo imprimió y
  falló después, dejando la base en la revisión anterior. `check` compara el
  esquema real contra los modelos y fue lo único que lo detectó.

## Scripts, y cuándo usar cada uno

```powershell
& $py -m pytest -q                 # 345 pruebas; aisladas, no tocan ninguna base
& $py -m alembic upgrade head
& $py -m alembic check             # y esto es lo que de verdad lo verifica
```

| Script | Para qué | Cuidado |
|---|---|---|
| `cargar_snapshot.py` | M1 — carga los 18 municipios y las 20.030 señales | Aplica las migraciones por su cuenta; sirve sobre una base vacía |
| `correr_ciclo.py` | M2 → M3 → M4 de un ciclo | **Gasta tokens.** Sin `--municipio` procesa los 18: prueba siempre con uno. **`--seco` no es seco** (H-038). Congelado hasta cerrar P4 |
| `calcular_scores.py` | M5 — scores y top 10 | No llama a ningún LLM; se puede repetir cuantas veces haga falta |
| `publicar_informe.py` | **El único punto de entrada para publicar** | Empieza siempre por `--seco`, que corre y revierte. Archiva el anterior y congela las dos corridas en la misma transacción |
| `cargar_usuarios.py` | Sincroniza `usuario` desde `config/usuarios.csv` | **`--previsualizar` primero, siempre.** Solo escribe con `--confirmar`. Desactiva, no borra |
| `avance_calificacion.py` | Cuánto lleva calificado cada persona en la ronda | **Solo lectura.** Es lo que se mira durante la ronda |
| `estimar_costo.py` | Costo por ciclo, para H5 | No cuenta el Sintetizador, que no existe |
| `generar_contrato_ts.py` | Regenera `web/lib/contrato.generado.ts` desde `modelos.py` | Tras tocar `calificacion` o `seguimiento`. `--check` falla si quedó desactualizado, y el suite lo corre |

Calibración: `medir_prefiltro.py`, `probar_clasificador.py`,
`comparar_prompts.py` y `comparar_correlacionador.py`.

## Usuarios y gerencias

Se versionan en git, que es lo que hace auditable el denominador de H2:

| Archivo | Qué es |
|---|---|
| [`config/gerencias.json`](config/gerencias.json) | El catálogo, y **la marca `prd` o `adicional`** de cada gerencia |
| [`config/usuarios.csv`](config/usuarios.csv) | Quién califica, con su correo, su gerencia y su rol |

**El núcleo del experimento son 5 gerencias `prd`** —`general`, `juridica`,
`producto_hoteles_oficinas`, `producto_logistica` y `rotacion_portafolio`— y hay
**2 `adicional`**: `administrativa` y `analitica`. **H2 se reporta sobre las
`prd`**; las adicionales van por separado, y H1 se reporta con y sin ellas.

**Los usuarios se precargan: quien no esté en la lista no califica**, así que la
app nunca escribe `usuario` y el denominador se conoce antes de medir. La lista
de gerencias autorizadas queda **congelada en el payload** al publicar, de modo
que la tasa se computa contra ella y no contra el estado de `usuario` de hoy.

## Despliegue

| | |
|---|---|
| **Rama de producción** | `main`. Cada push despliega |
| **Root Directory** | `web` — vive **solo en el panel de Vercel**, no se deduce del repositorio. Sin eso Vercel compila desde la raíz, no encuentra `package.json` y falla con un error que no menciona la causa |
| **Variables de base y `COOKIE_SECRET`** | **Solo en Production.** Dejarlas en Preview expondría la base real a cualquier rama |
| **Integración de Neon** | Sus variables quedan **solo en Development**, para que no compitan con las de Production |
| **Fusión de un PR** | **Siempre con merge commit, nunca squash**, para que el linaje del commit publicado siga siendo cierto |

Las migraciones **no** las aplica el despliegue: van a mano, por el host directo
y antes de publicar. La secuencia completa está en
[decisiones-remediacion.md](docs/decisiones-remediacion.md).

## Riesgos aceptados

Decididos por el dueño y registrados en
[decisiones-remediacion.md](docs/decisiones-remediacion.md):

- **R-A1** — la credencial de la base estuvo expuesta; se acepta el riesgo
  residual en vez de rotarla durante la ventana del experimento.
- **R-A2** — **la identidad es declarativa**: un correo tecleado contra la lista
  precargada, y H-012 queda abierto. La cookie firmada impide falsificarla desde
  el navegador, pero no impide teclear el correo de otro, y **eso hay que
  decirlo al publicar H1 y H2**.
- **P-6** — no se consulta a jurídica antes de cargar los usuarios, pese a que la
  base contiene datos personales provenientes de SECOP.

## Reglas del proyecto

Tres, por la decisión D8 de usar SQLite en local y PostgreSQL en nube:

1. Todo acceso a datos pasa por **SQLAlchemy**. Nunca SQL crudo de un motor.
   *Alcance*: protege **escrituras y esquema, no lecturas** — por eso la app
   puede leer Neon directamente.
2. El esquema se gobierna con **Alembic** desde la primera migración. La app no
   genera migraciones nunca, ni para sus propias tablas.
3. Las columnas JSON usan el tipo `JSON` portátil, **nunca operadores JSONB** de
   PostgreSQL (`->>`, `@>`, `jsonb_path_query`): no existen en SQLite.

Y una del PRD, que es bloqueante: **ninguna cifra de un informe puede provenir
del LLM** (CA-M6.3). El LLM redacta; los números los pone el código.

## Documentos

| Documento | Qué contiene |
|---|---|
| [**Plan de siguientes pasos**](docs/plan-siguientes-pasos.md) | **Qué viene y en qué orden**, con el esfuerzo de cada bloque |
| [Ronda de calificación](docs/ronda-calificacion.md) | Bitácora de la ronda en curso y el corte del martes 29 |
| [Estado del despliegue](docs/estado-despliegue.md) | Los 11 pasos, qué quedó abierto y las reglas que salieron de ahí |
| [Decisiones de remediación](docs/decisiones-remediacion.md) | Lo que decidió el dueño, los riesgos aceptados y los incidentes |
| **Auditoría** | Rama `audit/2026-09-22` — 51 hallazgos, matriz de conformidad de los 59 CA y plan de remediación. **No está en `main`**: `git show audit/2026-09-22:docs/auditoria.md` |
| [PRD del MVP](docs/prd.md) | Hipótesis H1–H5, alcance y criterios de aceptación |
| [Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) · [02 — Stack](docs/addendum-02-stack.md) | Decisiones D1–D9 |
| [Design System](docs/design-system.md) | **Autoridad de color y tipografía.** Navy `#0F4761` y Aptos |
| [Informe de resultados](docs/informe_resultados.md) | Lo medido por hipótesis, para la compuerta de la semana 8 |
| [Pendientes](docs/pendientes.md) | Registro de lo que falta decidir, y de lo decidido |
| [CLAUDE.md](CLAUDE.md) | Guía de trabajo en el repositorio: entorno, trampas y reglas |

## Lo que decide el go/no-go

**H1 y H2 se miden con las calificaciones de esta ronda, y hasta el 2026-09-23
no había ninguna.** Por eso la ronda es la prioridad y todo lo demás espera al
corte del martes.

**H4 —trazabilidad al 100%— es bloqueante**: si falla, la arquitectura no es
auditable y no puede ir a producción. No se resuelve con más ingeniería.

Y la afirmación que ordena todo lo demás: **el scoring es código determinista y
es lo único reproducible del sistema.** Todo lo que pasa por un modelo varía
entre el 19% y el 26% entre pasadas idénticas. **Cualquier cosa que deba ser
reproducible tiene que estar en código.**
