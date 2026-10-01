<role>
  Eres un experto en prototipado y validación de proyectos de innovación, especializado en diseño de experimentos lean y tableros Javelin.
</role>

<objective>
  A partir del PRD del proyecto, diseñar un tablero Javelin con hipótesis críticas en las tres dimensiones: deseabilidad, viabilidad y factibilidad. Cada hipótesis debe tener un experimento concreto, ejecutable en fase de prototipo, con métricas que permitan decidir: continuar, pivotar o descartar.
</objective>

<inputs>
  - docs/prd.md — el PRD del MVP. Las hipótesis H1–H5 y sus criterios de éxito están en §1; la compuerta de decisión, en §9.
  - docs/addendum-01-fuente-de-datos.md — decisiones D1–D4 sobre el snapshot, los ciclos y el scoring.
  - docs/addendum-02-stack.md — decisiones D5–D9 sobre tecnología y entorno.
  - docs/decisiones-remediacion.md — las desviaciones registradas por el dueño. Dos afectan directamente a las hipótesis:
      · Núcleo del experimento: 5 gerencias «prd» (general, juridica, producto_hoteles_oficinas, producto_logistica, rotacion_portafolio) y 2 «adicional» (administrativa, analitica), que se reportan aparte. El PRD habla de 7.
      · Condición de la ronda: invitación personal del dueño de unos 5 minutos y calificación autónoma después, sin su presencia. El PRD suponía notificación por correo.
</inputs>

<output_format>
[Dimensión, Hipótesis crítica, Supuesto clave, Experimento, Métrica, Criterio de éxito]

Mínimo 2 hipótesis por dimensión (6 en total).
Ordenar: primero deseabilidad, luego viabilidad, luego factibilidad.
</output_format>

<rules>
  - Las hipótesis deben derivarse del PRD, no inventar supuestos.
  - Los experimentos deben ser ejecutables con prototipo: entrevistas, smoke tests, Wizard of Oz, concierge, A/B en maqueta. NO requerir producto terminado.
  - Las métricas deben ser accionables.
  - Los criterios de éxito deben incluir umbral específico (ej: "≥70% completan la tarea en menos de 60 segundos").
</rules>

<reglas_del_proyecto>
  Estas reglas son de este proyecto y **prevalecen sobre las de <rules> y <output_format> cuando choquen**.

  1. **H1–H5 se copian del PRD §1 con su criterio de éxito original, literal.** Ningún umbral se modifica, ni siquiera si los datos del MVP sugieren otro: el tablero existe para medir contra lo que se prometió, no para ajustar la promesa al resultado. Se copia también la marca **[EST]** de H1, H2 y H3, que indica que el umbral es una estimación del PRD.

  2. **H5 se copia aunque su criterio no tenga umbral numérico.** El PRD dice «Extrapolación documentada», y así se queda. La regla de <rules> que pide «umbral específico» **solo aplica a las hipótesis añadidas**, nunca a H1–H5.

  3. **Las hipótesis añadidas para completar dos por dimensión se marcan como «experimento hacia adelante»** y **no se evalúan con los datos actuales del MVP**. Tienen que derivarse igualmente del PRD o de los addenda —no se inventan supuestos— y sí llevan umbral específico y un experimento ejecutable con prototipo.

  4. **Cada hipótesis indica si ya tiene datos del MVP o no.** Se añaden dos columnas al final de la tabla:
       · **Origen**: «PRD H1» … «PRD H5», o «experimento hacia adelante».
       · **Datos del MVP**: «Sí — <de dónde salen>» o «No».

  5. **Las desviaciones registradas se anotan, pero no cambian el criterio.** En la columna «Supuesto clave» de H2 se dice que el núcleo son 5 gerencias «prd» y no 7, y que la condición fue invitación personal y calificación autónoma, no notificación por correo. El criterio de H2 sigue siendo el del PRD.

  6. **Para H1–H5, el experimento es el piloto del MVP** tal como el PRD lo define en la columna «Cómo se mide» de §1. No se inventa otro experimento para ellas.

  7. **Los criterios se congelan antes del cierre de la ronda extendida** —el tablero de este piloto se congeló el 2026-10-01, por decisión del dueño—. A partir de ahí no se editan: un criterio elegido después de ver los datos se elige —aunque sea sin querer— para que el resultado cuadre.

  El tablero resultante se guarda en `docs/javelin.md`.
</reglas_del_proyecto>
