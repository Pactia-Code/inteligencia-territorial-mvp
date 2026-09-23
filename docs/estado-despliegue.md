# Estado del despliegue

**Actualizado:** 2026-09-23 · rama `remediacion/f0` **publicada en `origin`**

> **Para retomar:** lee esto primero, después
> [decisiones-remediacion.md](decisiones-remediacion.md).

## Progreso: 4 de 11 pasos

| | Paso | Estado |
|---|---|---|
| 1 | **Revisión de Vercel y compatibilidad de migraciones** | ✅ **Cerrado** |
| 2 | **Revisión de `remediacion/f0` frente a `main`** | ✅ **Cerrado** |
| 3 | **Push de la rama** a `origin` (sin PR) | ✅ **Cerrado**, en `49ce1e8` |
| 4 | **Respaldo** de la base principal, fuera del repositorio | ✅ **Cerrado**, pero **no con `pg_dump`**: es una exportación lógica |
| 5 | **Siguiente** · Variables en Vercel: solo *Production*, base `territorial` con **pooler**, `COOKIE_SECRET`, raíz `web` | ⬜ |
| 6 | **Migraciones**: `alembic upgrade head` con la cadena **directa**, y confirmar con `current` y `check` | ⬜ |
| 7 | **Carga de usuarios**: `cargar_usuarios.py --previsualizar` y luego `--confirmar` | ⬜ |
| 8 | **Republicación y verificación**: `publicar_informe.py --seco`, luego real, y la traza **241/241** | ⬜ |
| 9 | **Fusión del PR y conexión de Git** en Vercel | ⬜ |
| 10 | **Prueba de humo** sobre el despliegue | ⬜ |
| 11 | **Borrar el branch de Neon** `remediacion-f0` | ⬜ |

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

`C:\devespaldos	erritorial-antes-de-despliegue-2026-09-23\`, 39 MB:

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

## Reglas vigentes

- **No conectar Git en Vercel hasta cerrar el paso 4.** Conectarlo antes
  dispara un despliegue con la configuración equivocada.
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
