# Ronda de calificación — ciclo 3, informe 8

**Plazo: martes 2026-09-29.** Registro de las sesiones 1 a 1 y de cualquier
cambio hecho durante el congelamiento.

El avance en vivo no se anota aquí: se consulta, que es más fiable que una
tabla escrita a mano.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py scripts\avance_calificacion.py            # por persona y por gerencia
& $py scripts\avance_calificacion.py --csv
```

> **Condición acompañada.** Estas calificaciones se emiten con el dueño
> presente. **H2 del PRD mide calificación sostenida sin acompañamiento**, así
> que la tasa que salga de aquí se reporta como tasa en condición acompañada y
> no se compara con el criterio de éxito. Ver
> [plan-siguientes-pasos.md](plan-siguientes-pasos.md) y
> [decisiones-remediacion.md](decisiones-remediacion.md).

## Cómo se conduce la sesión

- **Cada persona teclea su propio correo y emite sus propias calificaciones.**
  `calificacion.id_usuario` registra quién tecleó; calificar por otro dejaría un
  registro falso.
- **Se explica la herramienta, no los insights.** Lo que H1 mide es si el
  insight le parece relevante a la gerencia, no si se entiende la pantalla.
- **No se comenta ante nadie la calificación de otro** (CA-M7.2). Basta con
  mencionar «fulano le puso 5» para que dejen de ser independientes.
- **Se piden 5 insights en cada uno de los 3 primeros municipios: 15 en total.**
  El resto del informe es opcional y se puede leer sin calificar.

## Sesiones

| Fecha | Persona | Gerencia | Tipo | Acompañada | Notas |
|---|---|---|---|---|---|
| 2026-09-23 | wsanchez@pactia.com | analitica | adicional | — (prueba de humo) | 6 calificaciones **reales**, emitidas al verificar el despliegue. Cuentan para el análisis |
| *por registrar* | sherrera@pactia.com | rotacion_portafolio | prd | *por registrar* | 2 de 15 al 2026-09-23 |
| | abejarano@pactia.com | general | prd | | |
| | rcuentas@pactia.com | juridica | prd | | |
| | lnavarro@pactia.com | producto_hoteles_oficinas | prd | | |
| | egomez@pactia.com | producto_logistica | prd | | |
| | jecheverri@pactia.com | administrativa | adicional | | |

Las 5 gerencias `prd` son el núcleo del experimento; `analitica` y
`administrativa` se reportan aparte (F0.1b).

## Congelamiento

Hasta el corte del martes **no se republica el informe** ni se cambia nada que
altere lo que ven los calificadores: ni el payload, ni los textos, ni la
selección pedida. Un informe republicado cambiaría los insights pedidos y las
calificaciones ya emitidas dejarían de ser comparables.

**Solo se corrige un error que impida calificar**, y se anota aquí.

| Fecha | Qué se cambió | Por qué impedía calificar | A quién afectó |
|---|---|---|---|
| — | *nada hasta ahora* | | |

## Corte

**Martes 29 al final del día**: exportación de `calificacion` a CSV **fuera del
repositorio**. Esa foto es la que se analiza.

**La app no cierra el ciclo sola**: nada en el código impide calificar después
del martes, así que el corte lo define la exportación y no el sistema. Si
alguien califica el miércoles, la calificación existirá en la base pero no
estará en la foto — y la diferencia hay que declararla al reportar.
