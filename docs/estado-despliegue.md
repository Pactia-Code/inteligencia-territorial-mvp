# Estado del despliegue

**Actualizado:** 2026-09-22 · rama `remediacion/f0`, 24 commits por delante de
`main` · **sin push**

> **Para retomar mañana:** lee esto primero, después
> [decisiones-remediacion.md](decisiones-remediacion.md). Lo que hay que decidir
> antes de tocar nada está en «Pendiente del dueño».

## Progreso: 2 de 10 pasos

| | Paso | Estado |
|---|---|---|
| 1 | **Revisión de Vercel y compatibilidad de migraciones** | ✅ **Cerrado** |
| 2 | **Revisión de `remediacion/f0` frente a `main`** | ✅ **Cerrado** |
| 3 | `pg_dump` de la base principal, fuera del repositorio | ⬜ **Siguiente**, después de decidir el push |
| 4 | `alembic upgrade head` con la cadena **directa**, y confirmar con `current` y `check` | ⬜ |
| 5 | `cargar_usuarios.py --previsualizar` y luego `--confirmar` | ⬜ |
| 6 | `publicar_informe.py --seco` y luego la publicación real | ⬜ |
| 7 | Verificación posterior: lista congelada, `informe.origen`, traza 241/241, informe anterior archivado | ⬜ |
| 8 | `COOKIE_SECRET` en Vercel, push, PR y fusión | ⬜ |
| 9 | Comprobar el despliegue y **compartir la URL** | ⬜ |
| 10 | Abrir la ventana de calificación y seguirla | ⬜ |

**Antes del paso 3 hay una decisión abierta: hacer push o no.** No se ha hecho
porque puede disparar un despliegue de vista previa en Vercel.

> Los números 1, 2, 3 y 9 y la regla de que 3 a 8 van en una sesión los fijó el
> dueño. **Los pasos 4 a 8 y el 10 son la reconstrucción** de la secuencia de
> republicación que está en `decisiones-remediacion.md`: si el plan del dueño
> los ordena de otra forma, manda el suyo.

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

## Pendiente del dueño

Tres cosas que **solo se pueden confirmar en el panel de Vercel** y que el
repositorio no dice:

1. **Qué rama despliega a producción.** Por defecto sería `main`, pero no hay
   nada en el repositorio que lo confirme.
2. **Si el despliegue es automático al fusionar**, y si las ramas abiertas
   generan despliegues de vista previa. De esto depende que hacer push sea
   inocuo o no.
3. **A qué entornos aplica `DATABASE_URL`** —producción, vista previa,
   desarrollo— y si la de vista previa apunta a la base principal. **Si apunta
   ahí, un despliegue de vista previa serviría el informe real desde una rama
   sin fusionar.**

## Reglas vigentes

- **Migrar y republicar antes de fusionar.** El código viejo tolera el esquema
  nuevo; el nuevo no funciona sin él.
- **Nunca publicar desde `main` después de migrar.** Su `publicar()` no escribe
  `informe.origen`, que es NOT NULL, así que falla. Se opera desde
  `remediacion/f0`.
- **Los pasos 3 a 8 van en una misma sesión.** Entre migrar y fusionar el
  sistema queda a medias: base nueva y código viejo desplegado. Funciona, pero
  no es un estado donde convenga dormir.
- **No se comparte la URL hasta el paso 9.** Antes de eso el informe publicado
  puede no tener la lista congelada, y sin ella **nadie puede calificar** — es
  el comportamiento conservador de F0.4, no un fallo.
- **No se corren ciclos nuevos**, ni siquiera con `correr_ciclo.py --seco`: esa
  bandera revierte la base pero **gasta tokens igual**, porque llama al modelo.
  Y hasta F2.3 el prompt por defecto volvió a v1.
  *(Ojo: `publicar_informe.py --seco` es otra cosa y sí se usa, en el paso 6: no
  llama a ningún modelo, compone y revierte.)*

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Decisiones del dueño, riesgos aceptados e incidentes | [decisiones-remediacion.md](decisiones-remediacion.md) |
| Secuencia de republicación, paso a paso | [decisiones-remediacion.md](decisiones-remediacion.md), sección «Secuencia de republicación en la base principal» |
| Informe de auditoría | rama **`audit/2026-09-22`**, commit **`c6f660b`**. Describe `96e10e0` y **no se toca** |
| Descripción del PR | [pr-remediacion-f0.md](pr-remediacion-f0.md) |
| Branch de Neon `remediacion-f0` | **No es fuente de datos.** Tiene informes republicados, usuarios de prueba desactivados y **una calificación de prueba** (insight 1088, gerencia `general`) |
| Verificación del alcance con la app corriendo | `scripts/verificar_alcance_web.py` |
