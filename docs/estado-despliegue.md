# Estado del despliegue

**Actualizado:** 2026-09-23 · **despliegue terminado, 11 de 11** · se trabaja sobre `main`

> **El despliegue está terminado.** Este documento queda como registro de cómo
> se hizo y de lo que quedó abierto. Las decisiones y los riesgos aceptados están
> en [decisiones-remediacion.md](decisiones-remediacion.md).

## Progreso: 11 de 11 pasos — **despliegue terminado**

| | Paso | Estado |
|---|---|---|
| 1 | **Revisión de Vercel y compatibilidad de migraciones** | ✅ **Cerrado** |
| 2 | **Revisión de `remediacion/f0` frente a `main`** | ✅ **Cerrado** |
| 3 | **Push de la rama** a `origin` (sin PR) | ✅ **Cerrado**, en `49ce1e8` |
| 4 | **Respaldo** de la base principal, fuera del repositorio | ✅ **Cerrado**, pero **no con `pg_dump`**: es una exportación lógica |
| 5 | **Variables en Vercel** | ✅ **Cerrado**. Raíz `web` confirmada por el dueño en el panel |
| 6 | **Migraciones** sobre la base principal | ✅ **Cerrado**: `d5932c3bdc03`, `check` limpio |
| 7 | **Carga de usuarios** en la base principal | ✅ **Cerrado**: 8 altas, 2 desactivados |
| 8 | **Republicación y verificación** | ✅ **Cerrado**: informe 8 publicado, traza 241/241 |
| 9 | **Fusión del PR y conexión de Git** | ✅ **Cerrado**: producción sirve el merge `bfc1233` |
| 10 | **Prueba de humo** sobre el despliegue | ✅ **Cerrado**: 6 calificaciones reales emitidas |
| 11 | **Borrar el branch de Neon** `remediacion-f0` | ✅ **Cerrado** |

> **Los once pasos están acordados por el dueño**, con su numeración y su orden.
> No se reordenan sobre la marcha: si alguno cambia, se cambia aquí primero.
>
> **Cambio acordado el 2026-09-23:** el `pg_dump` pasa del 5 al **4** y las
> variables de Vercel del 4 al **5**. Motivo: la integración de Neon **la
> administra Vercel**, así que tocar sus variables es tocar algo gestionado desde
> fuera, y eso se hace **con respaldo hecho**, no antes de hacerlo.

## Hallazgos sobre Vercel y Neon (2026-09-22, confirmados el 23)

Vienen de una auditoría externa de solo lectura y se **confirmaron con los
conectores de Vercel y Neon**, sin cambiar nada y sin leer ninguna contraseña.
**Cambian el orden del despliegue**: no había nada que romper, pero sí bastante
que configurar antes de conectar Git.

- **El proyecto de Vercel `inteligencia-territorial-mvp` nunca ha desplegado y
  no tiene repositorio conectado.** El registro del proyecto trae
  `latestDeployment: null`, `live: false`, sin dominios y sin enlace a Git. **No
  hay producción activa**, así que el push del paso 3 no puede disparar nada.
- **La integración de Neon inyectó 18 variables** —`DATABASE_URL`,
  `DATABASE_URL_UNPOOLED`, `POSTGRES_*`, `PG*`, `NEON_*`, `VITE_NEON_AUTH_URL`—
  **todas con target `preview` y `production` a la vez y un único valor**. No hay
  preview branching. *(La auditoría contó 19; por la API se ven 18.)*
- **Esas variables apuntan a la base `neondb`, no a `territorial`.** No se
  pudieron leer sus valores —Vercel no expone los secretos de una integración
  por API— pero lo confirma el estado de Neon: en la rama `main` conviven
  **`neondb`** (creada con el proyecto, dueño `neondb_owner`) y **`territorial`**
  (creada 14 minutos después a mano, dueño `territorial_owner`), y **`neondb`
  solo tiene las 9 tablas de `neon_auth`, ninguna en `public`**. La integración
  provisionó además `NEON_AUTH_BASE_URL`, que es de ese mismo esquema.
- **Las tablas del experimento están en `territorial`**: 18 tablas en `public`,
  4 informes y Alembic en `b37b4fd6e183`. El `.env` local apunta ahí, con rol
  `territorial_owner` y host **directo**.
- **Vercel Authentication está activa** en Standard Protection
  (`ssoProtection`, `all_except_custom_domains`). Habrá que decidir si se deja:
  con ella puesta, el enlace solo lo abre quien tenga acceso al equipo de
  Vercel, y el informe se comparte con siete gerencias.

**La consecuencia práctica:** si se conectara Git ahora, el primer despliegue
tomaría la `DATABASE_URL` de la integración, apuntaría a `neondb` y la app no
encontraría ni una tabla. Por eso el paso 4 va antes que el 9.

### Lo que hay que resolver en el paso 4

- **Conflicto de clave con la integración.** Ya existe una `DATABASE_URL` de la
  integración con target `preview` y `production`. No puede haber dos con la
  misma clave y el mismo target: hay que **quitar o desvincular** la de la
  integración antes de poner la buena, o el valor correcto no llegará.
- **La cadena que va es la del `-pooler`**, con la base `territorial`. Es el
  mismo host de `main` que usa el `.env` local con `-pooler` añadido al nombre
  del endpoint. Alembic seguirá yendo por la **directa**, desde local.
- **`COOKIE_SECRET`**, que hoy no está. Sin él la app no identifica a nadie.
- **Raíz de despliegue `web`**, que no se deduce del repositorio.
- **Solo `Production`.** Sin preview branching, dejar las variables también en
  `preview` significa que cualquier rama desplegada escribiría en la base real.

### El respaldo del paso 4 es una exportación lógica, no un `pg_dump`

**`pg_dump` no se puede ejecutar en esta máquina.** Acceso denegado por la
política corporativa, probado en `C:\herramientas`, en
`%LOCALAPPDATA%\Programs` y también como administrador. No hay `psql` ni Docker.
Se hizo un **plan B acordado**: exportación lógica con Python y psycopg, con la
conexión puesta en **solo lectura a nivel de servidor**.

`C:\dev
espaldos	erritorial-antes-de-despliegue-2026-09-23\`, 39 MB:

- `tablas/` — las **18 tablas** en CSV con encabezado, una por archivo, sacadas
  con `COPY ... TO STDOUT (FORMAT CSV, HEADER)`. **29.976 filas**, incluida
  `alembic_version`.
- `esquema.json` — columnas, tipos, nulabilidad, claves y restricciones desde
  `information_schema`.
- `manifiesto.json` — por tabla: filas en la base, filas exportadas y sha256.
  **Las 18 cuadran.**
- `README.md` — cómo restaurar.

**Qué NO trae, y por qué importa saberlo antes de necesitarlo.** No lleva
secuencias, permisos, índices ni orden de creación. El esquema lo reconstruye
**Alembic**, que es la única autoridad del esquema (regla 2 de D8), así que eso
no se echa en falta. Lo que sí hay que hacer a mano es **reponer las secuencias**
tras cargar los datos: `COPY` no las adelanta, son **14 columnas**, y sin eso la
base queda rota de una forma que no se ve hasta el primer `INSERT`. El README
trae el bloque que las repone todas.

**Restaurar es: crear la base, `alembic upgrade b37b4fd6e183`** —esa revisión,
no `head`, que traería columnas que estos datos no tienen— **y cargar los CSV en
orden de dependencias**, que no es el alfabético. El orden está en el manifiesto
y en el README.

## Paso 5 — la configuración de Vercel, como quedó

### Parte A, hecha por el dueño en el panel

- **La conexión del store de Neon con el proyecto quedó solo en
  `Development`.** Era el problema de fondo: esas 18 variables apuntaban a la
  base `neondb` y estaban en `preview` y `production` a la vez.
- **Vercel Authentication se mantiene** en Standard Protection **hasta el final
  del paso 10**. El dueño la desactivará justo antes de compartir la URL.
- **El plan Hobby no ofrece «Only Preview Deployments»**, así que la protección
  no se puede acotar a vista previa. **El aislamiento de datos lo dan las
  variables, que están solo en `Production`**, no la protección.

### Parte B, hecha por el conector

Comprobado por lectura, y **sin valores**:

| Variable | Target | Tipo |
|---|---|---|
| `DATABASE_URL` (nueva) | **production** | sensitive |
| `COOKIE_SECRET` (nueva) | **production** | sensitive |
| las 18 de la integración de Neon | **development** | encrypted |

- **`DATABASE_URL`** apunta a la base **`territorial`** de la rama `main`, con
  rol `territorial_owner` y **host con `-pooler`**, que es el que corresponde a
  las funciones serverless. `hiddenProductionEnvCount` es 0.
- **`COOKIE_SECRET`** se generó con `secrets.token_urlsafe(48)` y **no se guardó
  en ningún archivo**: existe solo en Vercel.
- **No hubo conflicto de clave**, al contrario de lo previsto: la `DATABASE_URL`
  de la integración quedó en `development` y la nueva en `production`, así que
  conviven. Eso sí, **en desarrollo local la de la integración sigue apuntando a
  `neondb`**; el pipeline y la app local usan el `.env`, no esa.
- **Framework: `nextjs`**, confirmado por lectura.

**Raíz de despliegue `web`: confirmada por el dueño en el panel.** El conector
no devuelve `rootDirectory` al leer el proyecto, así que la comprobación tuvo
que ser visual.

## Paso 6 — migraciones sobre la base principal

Aplicadas el 2026-09-23 desde `remediacion/f0`, con la cadena **directa** de la
base `territorial` de la rama `main`.

    b37b4fd6e183 -> 63531e6d5a5f  cargo del usuario
    63531e6d5a5f -> dd0101cc28ae  identidad: autor de la calificacion y registro
    dd0101cc28ae -> d5932c3bdc03  origen del informe: commit e invocacion

`alembic current` dice **`d5932c3bdc03 (head)`** y `alembic check` responde «No
new upgrade operations detected», que es la comprobación que vale: el `upgrade`
puede mentir y el `check` no.

**Lo que la migración creó, verificado por lectura:** `usuario.cargo`
(anulable), `calificacion.id_usuario` (entero anulable), `informe.origen` (JSON
no nulo) y la tabla `identificacion` con sus cinco columnas.

**Lo que la migración NO movió**, que es lo que había que demostrar: las **18
tablas conservan exactamente las filas del manifiesto** del respaldo lógico
—29.976 en total— e `identificacion` nace con **0 filas**. La base pasa a 19
tablas.

`informe.origen` quedó relleno en los **4 informes**, con `{}`: los cuatro son
anteriores a F0.6 y no tienen origen que declarar. Es un hecho registrado, no un
hueco; la migración lo rellena así a propósito para poder cerrar la columna como
NOT NULL.

**Un tropiezo, y no fue de la base.** El primer intento de `upgrade` falló al
conectar con `bad value for connect_timeout: "('3', '5')"`: el `.env` ya trae
`connect_timeout=3` y la invocación le añadió otro. **No llegó a ejecutarse
ningún DDL** —falló antes de abrir la conexión— y se comprobó que la revisión
seguía en `b37b4fd6e183` antes de repetir.

## Paso 7 — usuarios cargados en la base principal

Previsualización y carga el 2026-09-23, desde `remediacion/f0`, con
`config/usuarios.csv` y `config/gerencias.json` versionados.

**La previsualización coincidió exactamente con lo autorizado** —8 altas con sus
`id_gerencia`, 2 desactivaciones, 0 cambios y ningún error de validación— así
que se confirmó. Resultado: `8 altas · 0 cambios · 0 reactivados · 2
desactivados · 0 sin cambios`.

| | |
|---|---|
| Activos, rol `gerencia` | `abejarano` (general), `rcuentas` (juridica), `sherrera` (rotacion_portafolio), `egomez` (producto_logistica), `lnavarro` (producto_hoteles_oficinas), `jecheverri` (administrativa), `wsanchez` (analitica) |
| Activo, rol `administrador` | `wsanchez+admin` (analitica) |
| Inactivos, **no borrados** | `prueba@territorial.local`, `admin@territorial.local` |

Verificado por lectura: **10 filas, 8 activas y 2 inactivas**; **cada una de las
5 gerencias `prd` tiene un calificador activo**; y **ningún administrador figura
con rol `gerencia`**, incluidos los dos usuarios del dueño, que son filas
separadas con correos distintos (decisión c: el operador del pipeline también
califica y sus notas tienen que poder aislarse en H1).

**La guarda pasa.** `publicar_informe.py --seco` imprime «gerencias «prd» con
calificador activo» con las cinco y compone el payload con **5 `prd` + 2
`adicional`**. Se revirtió: la base sigue con 4 informes, el 5 publicado y 0
calificaciones. **No se publicó nada.**

## Paso 8 — informe republicado en la base principal

Publicado el 2026-09-23 desde `remediacion/f0`, con el árbol limpio y la rama
exactamente en `7bfcc23`, igual que `origin`.

**Informe 8, publicado**, con las corridas **24/10**. Los informes 2, 3, 4 y
**5 quedan archivados, no borrados**: un solo publicado por ciclo, que es lo que
garantiza el índice único parcial.

`informe.origen` registra **`7bfcc23`, el HEAD del momento**, y la invocación
completa. De ahí la regla sobre el merge commit.

**Lista congelada:** 5 `prd` —`general`, `juridica`,
`producto_hoteles_oficinas`, `producto_logistica`, `rotacion_portafolio`— y 2
`adicional` —`administrativa`, `analitica`—, con los códigos de
`config/gerencias.json`.

**`composicion_pedida` en los 3 municipios calificables:** Ibagué y Funza con
3 correlacionados, 1 de contratación y 1 de prensa; **Armenia con 1, 1 y 3 para
completar**, que es la regla de relleno funcionando.

**Traza sobre el informe 8: 241/241 insights, 933/933 citas y 10/10 scores.**
Las mismas cifras que midió la auditoría sobre el informe 5 y que se repitieron
en el branch.

**Y el payload es idéntico, campo por campo, al que se publicó en el branch en
F0.6.** Ni una diferencia, tampoco en `origen` ni en fechas, que viven fuera del
payload. Es la prueba de que la composición no depende de la base contra la que
corre.

**0 calificaciones y 0 seguimientos**: la ventana no se ha abierto.

## Paso 9 — fusionado y desplegado

**En git.** `origin/main` está en **`bfc1233`**, un **merge commit** de verdad
—dos padres, `96e10e0` y `ace3124`— y `git merge-base --is-ancestor` confirma
que **`7bfcc23` es alcanzable desde `main`**. Es lo que la regla protegía: el
commit que `informe.origen` graba sigue en la historia, así que el informe
publicado se puede reconstruir con `git checkout 7bfcc23`.

**En Vercel.** El despliegue de producción **actual** es
`dpl_HCbBxJdRc41WXiQTJ2GpcajNKK7A`: sale de **`main`** con el commit del merge
**`bfc1233`**, está **READY**, tipo `LAMBDAS`, framework **`nextjs`**, y es el
que **tiene asignados los alias de producción**, incluido
`inteligencia-territorial-mvp.vercel.app`. El proyecto lo reporta como
`latestDeployment`.

**El despliegue anterior, el que salió de `remediacion/f0` (`ace3124`), ya no
sirve producción.** Sigue existiendo como candidato a rollback, y conviene
saberlo: revertir a él serviría el mismo código —es el contenido que se
fusionó— pero desde una rama, no desde `main`.

**La raíz `web` no se puede leer por la API**, ni en el proyecto ni en el
despliegue. Lo que sí es evidencia: el build **encontró el `package.json` y
produjo funciones**, cosa que no habría pasado compilando desde la raíz del
repositorio, que es Python. Más la confirmación visual del dueño en el paso 5.

**La vista previa de `remediacion/f0` no tiene ninguna variable de entorno**,
`DATABASE_URL` incluida: la consulta filtrada por esa rama devuelve una lista
vacía. El aislamiento de datos funciona como se diseñó.

**Los errores de runtime no se pudieron consultar:** el conector responde
**403 Forbidden**, que es lo esperable en el plan Hobby, donde la observabilidad
no está disponible. Queda pendiente mirarlos en el panel si la prueba de humo
del paso 10 diera algún problema.

## Paso 10 — prueba de humo, y las primeras calificaciones del experimento

> **⚠ Para quien analice H1 y H2: las 6 primeras calificaciones de la base se
> emitieron durante la prueba de humo del despliegue, el 2026-09-23, y SON
> REALES.** No son de prueba y **no deben descartarse sin decidirlo**: las emitió
> una persona leyendo los insights, con su identidad, y están en las tablas
> igual que cualquier otra.
>
> Las seis son de **`analitica`, que es una gerencia `adicional`, no del núcleo
> `prd`**. Por la decisión de reporte del dueño, **H2 se computa sobre las
> gerencias `prd`**, así que estas seis **no entran en esa tasa**; y **H1 se
> reporta con y sin las adicionales**, así que sí aparecen, en la mitad «con».
>
> Y llevan el conflicto de interés ya registrado: las emitió **el operador del
> pipeline**, que es justo la razón por la que sus dos usuarios son filas
> separadas y `calificacion.id_usuario` existe. Se pueden aislar con
> `id_usuario = 10`.

| Insight | Valor | Municipio | Comentario |
|---|---|---|---|
| #1054 | 5 | Armenia | — |
| #1088 | 3 | Ibagué | «Es importante que hable de vivienda pero sobre todo está enf…» |
| #1090 | 4 | Ibagué | «Noticia de interés sobre activación de vivienda» |
| #1092 | 5 | Ibagué | — |
| #1093 | 5 | Ibagué | — |
| #1094 | 5 | Ibagué | — |

Verificado por lectura sobre la base principal:

- **`calificacion`: exactamente 6 filas**, con esos insights y valores, todas
  con `id_gerencia = analitica` e `id_usuario = 10` (`wsanchez@pactia.com`), y
  con fecha entre las 19:50 y las 19:57 UTC.
- **Los 6 están entre los 15 insights pedidos** del informe 8 —5 en cada uno de
  los 3 municipios calificables—, así que la regla «se califica solo lo pedido»
  se cumplió en producción, no solo en las pruebas.
- **`identificacion`: 4 filas**, dos de `wsanchez@pactia.com` y dos de
  `wsanchez+admin@pactia.com`, **todas con user agent e IP** (`190.90.208.25`).
  **El correo inventado que se probó no dejó ninguna fila**: las 4 pertenecen a
  usuarios registrados, que es lo que F0.3 tenía que garantizar.
- **`seguimiento`: 0 filas.**
- **Ninguna otra tabla se movió.** Las 19 conservan los conteos del paso 8:
  `usuario` 10, `informe` 5, y las 16 del pipeline exactamente como en el
  respaldo.

### Cómo terminó el paso 10

El dueño **apagó la protección de Vercel** —Vercel Authentication, que estuvo en
Standard Protection desde el principio justo para esto— y **verificó el acceso
en una ventana de incógnito**, sin sesión de Vercel. Es la comprobación que
importaba: el enlace que van a recibir las gerencias abre sin pedir cuenta.

## Paso 11 — branch de Neon borrado, y fin del despliegue

Con confirmación explícita del dueño se borró el branch **`remediacion-f0`**
(`br-weathered-hall-aw6tiknb`), después de comprobar por lectura que **no era ni
el primario ni el de por defecto**. Con él se van los informes republicados, los
usuarios de prueba y la calificación de prueba del insight 1088, que nunca
fueron fuente de datos.

**El proyecto queda con un solo branch, `main`** (`br-soft-feather-aw72a98p`),
primario y por defecto. Estado de la base `territorial` justo después:

| | |
|---|---|
| Alembic | `d5932c3bdc03` |
| Usuarios | 8 activos de 10 (2 de prueba, inactivos) |
| Informe publicado | **8**, con 4 archivados |
| Calificaciones | **6** (las de la prueba de humo, reales) |
| Identificaciones | 5 |
| Seguimientos | 0 |

Se quitó `DATABASE_URL_NEON_BRANCH` del `.env` y de su copia en
`C:\dev\respaldos\`, sin tocar ninguna otra línea: 66 a 65 líneas en los dos
archivos, que siguen siendo idénticos entre sí.

## Lo que queda abierto

El despliegue terminó; **el experimento no**.

- **F0b entera**, que bloquea la decisión go/no-go: `informe_resultados.md`
  tiene dos afirmaciones falsas sobre la hipótesis bloqueante y una cifra sin
  productor.
- **F2.3**: validar el Correlacionador v2 con linaje persistido. Hasta entonces
  el valor por defecto es **v1**, y una prueba impide cambiarlo en silencio.
- **El resto del plan de remediación**, F1 a F6.
- **Las 6 primeras calificaciones son reales y de una gerencia adicional.** Ver
  el aviso del paso 10 antes de calcular H1 o H2.

## Reglas vigentes

- **El PR se fusiona con MERGE COMMIT, nunca con squash.** `informe.origen`
  del informe publicado graba el commit `7bfcc23`, y un squash lo reescribiría:
  el informe apuntaría a un commit que no existe en `main` y se perdería
  justamente lo que F0.6 vino a dar, poder reconstruirlo con
  `git checkout <commit>`.
- **No conectar Git en Vercel hasta cerrar el paso 4.** Conectarlo antes
  dispara un despliegue con la configuración equivocada.
- **Un error que falla ANTES de conectar a la base se puede reintentar una vez**,
  tras comprobar que el estado no cambió. **Cualquier error que ya tocó la base:
  detenerse.** La distinción no es teórica: el primer `upgrade` del paso 6 falló
  en la validación de la cadena de conexión, sin abrir sesión ni ejecutar DDL, y
  reintentarlo era seguro; un `upgrade` que falla a mitad, no.
- **Migrar y republicar antes de fusionar.** El código viejo tolera el esquema
  nuevo; el nuevo no funciona sin él.
- **Nunca publicar desde `main` después de migrar.** Su `publicar()` no escribe
  `informe.origen`, que es NOT NULL, así que falla. Se opera desde
  `remediacion/f0`.
- **Los pasos 6 a 8 van en una misma sesión.** Entre migrar y republicar el
  sistema queda a medias; no es un estado donde convenga dormir.
- **No se comparte la URL hasta pasar la prueba de humo del paso 10.** Antes de
  eso el informe publicado puede no tener la lista congelada, y sin ella **nadie
  puede calificar** — es el comportamiento conservador de F0.4, no un fallo.
- **No se corren ciclos nuevos**, ni siquiera con `correr_ciclo.py --seco`: esa
  bandera revierte la base pero **gasta tokens igual**, porque llama al modelo.
  Y hasta F2.3 el prompt por defecto volvió a v1.
  *(Ojo: `publicar_informe.py --seco` es otra cosa y sí se usa, en el paso 8: no
  llama a ningún modelo, compone y revierte.)*

### Lo que cerró el paso 1

- **La conexión con Vercel vive solo en el panel.** No hay `vercel.json`, ni
  `.vercel/`, ni workflows de CI. La raíz de despliegue es `web/` y se configura
  a mano.
- **Las tres migraciones son aditivas** y el código viejo tolera el esquema
  nuevo. La única trampa: `informe.origen` es NOT NULL y el `publicar()` de
  `main` no lo escribe.
- **La app lee `DATABASE_URL` con el driver HTTP de Neon**, así que
  `connect_timeout` ahí no hace nada. En producción va la cadena del **pooler**;
  Alembic, por la **directa**.

### Lo que cerró el paso 2

24 commits, 54 archivos, 3.828 líneas añadidas. Sin `.env`, sin secretos, sin
cadenas de conexión ni temporales. `pytest` 333 passed, `tsc` limpio,
`next build` compila y el contrato de TypeScript al día. La descripción del PR
está en [pr-remediacion-f0.md](pr-remediacion-f0.md).

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Decisiones del dueño, riesgos aceptados e incidentes | [decisiones-remediacion.md](decisiones-remediacion.md) |
| Secuencia de republicación, paso a paso | [decisiones-remediacion.md](decisiones-remediacion.md), sección «Secuencia de republicación en la base principal» |
| Informe de auditoría | rama **`audit/2026-09-22`**, commit **`c6f660b`**. Describe `96e10e0` y **no se toca** |
| Descripción del PR | [pr-remediacion-f0.md](pr-remediacion-f0.md) |
| Branch de Neon `remediacion-f0` | **No es fuente de datos.** Tiene informes republicados, usuarios de prueba desactivados y **una calificación de prueba** (insight 1088, gerencia `general`) |
| Verificación del alcance con la app corriendo | `scripts/verificar_alcance_web.py` |

---

## Fase 2 del 2026-09-24 — correcciones P0.5, en `fix/p0-5-correcciones`

Excepción al congelamiento autorizada por el dueño (ver
[decisiones-remediacion.md](decisiones-remediacion.md)). **Nada de esto toca el
informe, los insights pedidos ni las reglas de alcance.** Tres commits, sin
fusionar ni empujar: el dueño revisa, empuja y fusiona con merge commit.

### Lo que se corrigió

| Commit | Qué |
|---|---|
| `1ce5ff0` | **`/priorizados` y «cambiar estado» eran el mismo fallo.** Un componente de cliente importaba una constante de un módulo que toca la base, así que el driver de Neon y el `throw` de `db.ts` viajaban al navegador. Las constantes pasan a `web/lib/estados.ts` |
| `8016522` | **Guarda de empaquetado**: `web/scripts/verificar_bundle.mjs`, encadenada a `npm run build`, más 10 pruebas |
| `e4f861a` | **«Próximamente»** en `/historico` y `/metricas` en vez del 404. `/metricas` sigue siendo solo de administrador |

**Medido:** `/priorizados` baja de **43,8 kB a 1,65 kB** de JavaScript de
cliente.

> ### Lo que este episodio deja como regla
>
> **Tres comprobaciones en verde no vieron una página caída.** `tsc --noEmit`
> pasaba, `next build` pasaba y `curl` devolvía **200 con el HTML correcto**,
> porque el servidor renderizaba bien y **curl no ejecuta JavaScript**. El fallo
> solo existía en un navegador de verdad.
>
> De ahí la guarda sobre `.next/static`: mira el **resultado** del build en vez
> de fiarse del código fuente. Y de ahí que la verificación final la haga una
> persona con un navegador, no un `curl` más.

### Verificación, sobre un branch de Neon desechable

Se creó **`fix-p0-5`** (`br-small-dust-awr8lrmc`), copia de `main` al momento:
1 informe publicado, 0 en `seguimiento`, 23 calificaciones, Alembic en
`d5932c3bdc03`. No hizo falta migrar. **Se borró al terminar.**

Comprobado con la app corriendo contra ese branch:

| Qué | Resultado |
|---|---|
| `/priorizados` | Carga la tabla. Ya no sale la pantalla de error |
| «cambiar estado» a `descartado` **sin nota** | Rechazado, y **no escribió ninguna fila** |
| `en_revision` sin nota · `descartado` con nota | Registrados, con `id_usuario` y `fecha_cambio`. **El historial apila**, no sobrescribe (CA-M9.10) |
| `/historico` | 200 y «Próximamente» para cualquiera |
| `/metricas` | **404** a anónimo y a gerencia, **200** a administrador (CA-M9.14) |
| Etiqueta «MVP» | En las tres pantallas, puesta por el layout (CA-M9.17) |

**La base principal no se tocó**: `seguimiento` siguió en 0 y `calificacion` en
23 durante toda la fase, comprobado por lectura al terminar.

Verde: **355 pruebas** de Python, `tsc --noEmit`, `next build` y la guarda
nueva. Confirmación en navegador del dueño el 2026-09-24.

### Un tropiezo que conviene no repetir

Reescribir un `.tsx` con `Set-Content -Encoding utf8` de PowerShell **le metió
un BOM y dobló la codificación de todas las tildes** («revisión» → «revisiÃ³n»).
No lo detectó ninguna prueba; lo detectó el `git diff`, que salió lleno de
líneas que nadie había tocado. El archivo se restauró desde `main` y se
reaplicó el cambio con `sed`. **Para editar archivos con acentos, no uses
`Set-Content`.** Es el mismo tipo de trampa que el escape de rutas de Windows.

---

## Fase 3 del 2026-09-24 — entrada por correo, en `feat/login-correo`

Tres commits, sin fusionar ni empujar. Ver
[decisiones-remediacion.md](decisiones-remediacion.md) para el porqué de cada
decisión; aquí está qué se verificó y cómo.

| Commit | Qué |
|---|---|
| `173a152` | `exigirIdentidad`, `entrar`, `salir` y el saneo del destino (`web/lib/destino.ts`) |
| `74e44c5` | Pantalla `/entrar` y barra con logo en negativo y «Salir» |
| `b0881b3` | Las cinco rutas exigen identidad, se retira el formulario de la vista de ciclo y se añade la guarda |

**Por qué no hay middleware.** Verificar la firma necesita `node:crypto` y el
runtime edge no lo tiene; duplicarla con Web Crypto habría creado **una segunda
fuente de verdad de algo que decide quién es quién**. La puerta la llama cada
página, y una guarda recorre `web/app/**/page.tsx` para que no se olvide.

### Verificación, sobre el branch de Neon `login-correo`

Creado desde `main` (`br-soft-bonus-aw5ya5ss`) y **borrado al terminar**.

| Caso | Resultado |
|---|---|
| Sin cookie, las seis rutas | 307 a `/entrar` conservando el destino, incluido `/ciclo/3?m=73001` |
| Correo no registrado | No entra, **no emite cookie y no deja fila** en `identificacion` |
| Correo registrado | Entra, **deja fila con `user_agent`** y vuelve al destino pedido |
| Cookie ya emitida | Sigue valiendo: no pasa por `/entrar` |
| Cookie con firma inventada | No vale: 307 a `/entrar` |
| Destino hostil (`//evil.com`, `https://evil.com`) | Neutralizado a `/` |
| «Salir» | Borra la cookie y lleva a `/entrar` |
| `/metricas` | 404 para gerencia, 200 para administrador (CA-M9.14) |
| Pantalla de calificación | `Panel.tsx` y `Calificar.tsx` **intactos**; 25 controles de calificación en su sitio |

**La base principal no se tocó**: 12 identificaciones, 23 calificaciones y 0 en
`seguimiento` antes y después.

Verde: **368 pruebas**, `tsc --noEmit`, `next build` y la guarda del bundle.
Confirmación del dueño en el navegador.

> ### Dónde aterriza cada quien, que es lo que se preguntó
>
> | Cómo entra | A dónde va |
> |---|---|
> | Enlace a secas | `/` → **`/ciclo/3`**, el informe |
> | Enlace profundo | A esa misma página |
>
> **Los gerentes de la ronda reciben el enlace pelado, así que caen en el
> informe.** El destino solo se usa cuando se pidió una página concreta, que es
> lo que hace que un enlace compartido siga llevando a donde apuntaba.

### Otro tropiezo de la máquina, van tres

Git Bash convirtió `/priorizados` en `C:/Users/.../Git/priorizados` **dentro del
argumento de `curl`**, antes de que la petición saliera. Pareció que la
aplicación perdía el destino; lo que pasaba es que recibía una ruta de Windows
y la rechazaba, que es lo correcto. Se confirmó con un build instrumentado, ya
retirado. **Para mandar rutas por `curl` desde Git Bash: `MSYS_NO_PATHCONV=1`.**

Junto al BOM de `Set-Content` y al escape de rutas en documentos, son tres
formas distintas de que esta máquina altere un texto en silencio.

### Verificación en producción de la pantalla de entrada (2026-09-24)

**La hizo el dueño en navegador, tras fusionar el PR #3.** Importa distinguirla
de lo anterior: la verificación de la fase 3 fue **local y contra un branch
desechable**, así que hasta aquí nadie había comprobado la entrada sobre la base
y el despliegue reales.

| Caso | Resultado |
|---|---|
| Ventana de incógnito | Lleva a `/entrar` |
| Correo inventado | No entra |
| `wsanchez@pactia.com` | Entra y **ve sus 6 calificaciones**, que es lo que prueba que la identidad resuelve contra los datos reales y no solo contra la cookie |
| Navegador con cookie previa | Entra **sin pedir el correo** |
| «Salir» | Devuelve a `/entrar` |

Producción sirve el merge `45ec4d2` (`dpl_9HvwU1UdWSDruWTmfhE24UwANz3t`, READY).

**Con esto P0.5 queda cerrado entero**: las tres correcciones fusionadas,
desplegadas y verificadas. El desglose está en
[plan-siguientes-pasos.md](plan-siguientes-pasos.md) y la bitácora del
congelamiento en [ronda-calificacion.md](ronda-calificacion.md).

> **Lo que esto NO cierra.** La entrada no autentica: quien conozca un correo
> registrado entra por esa persona. **R-A2 y H-012 siguen abiertos**, y al
> publicar H1 y H2 hay que decirlo. Que ahora haya una pantalla de entrada lo
> hace más fácil de olvidar, no menos cierto.
