# Estado del despliegue

**Actualizado:** 2026-09-23 · rama `remediacion/f0` **publicada en `origin`**

> **Para retomar:** lee esto primero, después
> [decisiones-remediacion.md](decisiones-remediacion.md).

## Progreso: 3 de 11 pasos

| | Paso | Estado |
|---|---|---|
| 1 | **Revisión de Vercel y compatibilidad de migraciones** | ✅ **Cerrado** |
| 2 | **Revisión de `remediacion/f0` frente a `main`** | ✅ **Cerrado** |
| 3 | **Push de la rama** a `origin` (sin PR) | ✅ **Cerrado**, en `49ce1e8` |
| 4 | `pg_dump` de la base principal, fuera del repositorio | 🔴 **Bloqueado**: `pg_dump` no está instalado |
| 5 | **Variables en Vercel**: solo *Production*, base `territorial` con **pooler**, `COOKIE_SECRET`, raíz `web` | ⬜ |
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

### El paso 4 está bloqueado: falta `pg_dump`

**No hay cliente de PostgreSQL en esta máquina.** Ni `pg_dump`, ni `pg_restore`,
ni `psql`, ni en el `PATH` ni en las rutas habituales de instalación. Tampoco hay
Docker. El respaldo **no se ha hecho**.

**La versión tiene que ser 18 o posterior**, porque el servidor es PostgreSQL 18
y `pg_dump` se niega a volcar una base de versión mayor que la suya. Una 17 no
sirve.

Dos formas de instalarlo en Windows, y la segunda encaja mejor con la política
de esta máquina:

1. **Instalador de EDB** —el oficial, en `postgresql.org/download/windows`—
   eligiendo **solo «Command Line Tools»**, sin el servidor. Pide permisos de
   administrador.
2. **Binarios en zip**, de la misma página, sección *«Binaries»*: se
   descomprimen donde sea y se usa `bin\pg_dump.exe` sin instalar nada. **Es la
   vía que respeta la política corporativa**, que impide ejecutar binarios desde
   `Downloads`: hay que descomprimir fuera de esa carpeta, por ejemplo en
   `C:\herramientas\pgsql`, igual que se hizo con el intérprete de Python.

`winget` está disponible (v1.29.380) pero **su origen no responde desde esta
red**, así que no se pudo confirmar el identificador del paquete. Si la red lo
permite, `winget search PostgreSQL` lo resuelve.

Después de instalar, comprobar que la versión es la correcta:

```powershell
$env:Path += ";C:\herramientas\pgsql\bin"
pg_dump --version      # tiene que decir 18.x o superior
```

**Alternativa que no necesita pg_dump, por si se prefiere:** Neon puede crear un
**snapshot** de la rama `main`, que es un respaldo del lado del servidor y se
restaura desde el panel. No sustituye a un `.dump` portable —vive dentro de
Neon— pero sirve como red de seguridad inmediata. Es una escritura en Neon, así
que requiere decidirlo.

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
