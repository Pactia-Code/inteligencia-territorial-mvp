# Decisiones del dueño para la remediación F0

**Fecha:** 2026-09-22
**Referencia:** `docs/auditoria.md` (rama `audit/2026-09-22`, commit `c6f660b`),
sección 7 «Plan de remediación», fase F0 «Prerrequisitos de distribución», y
sección 9 «Preguntas abiertas». La auditoría describe el commit `96e10e0`; la
remediación parte de ese mismo commit en la rama `remediacion/f0`.

## Decisiones

- **Token de F0.3 (H-012): ADOPTADO.** Enlace personal por usuario con token
  aleatorio, entrega única por canal interno. El riesgo condicional R-A2 **no se
  activa**.
- **P-2:** congelar la lista de gerencias en el **payload del informe** (opción
  que asume el plan en F0.1).
- **P-4:** se **retira formalmente la infografía** del MVP; queda para Fase 0.
- **P-5:** **abierta**; no bloquea F0. Analítica aportará la tarifa real de
  `gpt-5.4-mini` para F0b.2.
- **P-6:** se **consultará a jurídica antes de cargar los 7 usuarios reales**.
  La carga de usuarios **no forma parte de F0** y no se hace sin confirmación
  expresa del dueño.
- **P-1:** **cerrada** (v1 publicado; corrección de `CLAUDE.md` en F0.5).

## Decisiones del 2026-09-22 sobre calificadores y secuencia (segunda tanda)

Registradas tras cerrar F0.1. Amplían, no sustituyen, las de arriba.

- **a) El conjunto de calificadores no se cierra a las 7 gerencias del PRD.**
  Podrá incluir **gerencias adicionales** —por ejemplo Analítica, que no es una
  de las 7—. **Es una desviación del PRD** (§1 «7 gerencias», CA-M9.1) y se
  registra como tal. Qué usuarios califican **se decide antes de la
  republicación definitiva de F0.6**, porque la lista se congela al publicar.
- **b) Cómo se reporta.** **H2 se reporta siempre sobre las 7 gerencias del
  PRD**; los calificadores adicionales, **por separado**. **H1 se reporta con y
  sin ellos.** De ahí la marca `prd` / `adicional` de F0.1b: sin ella, las dos
  cifras no se pueden separar después.
- **c) Usuarios del dueño: dos, distintos.** Uno con rol `administrador` y otro
  con rol `gerencia` de **Analítica (adicional)**, con **correos distintos**
  (variante con `+`). Motivo, que es el que hay que conservar: **el operador del
  pipeline también califica**, así que hay conflicto de interés en H1 y sus
  calificaciones tienen que poder separarse de las demás.
- **d) Semilla de usuarios.** La lista real vive en un **archivo ignorado por
  git** y `scripts/cargar_usuarios.py` la lee de ahí. **Los tokens nunca se
  escriben** en ese archivo, ni en la base en claro, ni en logs: se generan en
  la carga y **se muestran una sola vez**. La carga de usuarios reales **no
  forma parte de F0** y no se hace sin confirmación del dueño (depende de P-6).
- **e) F0.4 ampliada.** Las Server Actions de calificación y comentario solo
  aceptan a un usuario con rol `gerencia` **cuya `id_gerencia` esté en la lista
  congelada del payload**. Un administrador, o una gerencia dada de alta
  después de publicar, **recibe error y no escribe**.
- **f) F0.6 cambiada.** Se **prepara y verifica en un branch de Neon** con
  usuarios de prueba. La **republicación definitiva en la base principal ocurre
  después** de cargar los usuarios reales y **desactivar los de prueba**, y
  **la ejecuta el dueño** con el comando que se le deje preparado.

## Orden de ejecución acordado

F0.1 → **F0.1b** → F0.3 → F0.2 → F0.4 (ampliada por la decisión e) → F0.7 →
F0.8 → F0.5 → F0.6 (solo preparación y verificación en branch).

## Reglas de ejecución

1. Una subfase por commit, sin arreglos oportunistas de otras.
2. Tests añadidos o actualizados; `pytest`, `tsc --noEmit` y
   `generar_contrato_ts.py --check` en verde antes de cada commit.
3. La verificación de cierre exacta del informe se ejecuta y su salida se pega en
   el mensaje de commit.
4. Migraciones y pruebas solo sobre SQLite local o una copia; ninguna migración a
   Neon sin preguntar. F0.4 y F0.6 se verifican en un branch de Neon.
5. Antes de F0.6 sobre la base principal: `pg_dump` de Neon fuera del repositorio
   y confirmación del dueño para republicar (corridas 24/10; cierre: traza
   241/241 repetida).
6. Sin usuarios reales ni tokens reales: solo el mecanismo y un usuario de prueba.
