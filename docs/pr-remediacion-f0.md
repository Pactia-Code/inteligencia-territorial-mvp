# Remediación F0: prerrequisitos de distribución

Cierra la fase **F0** del plan de remediación de la auditoría, más cuatro
subfases de interfaz que bloqueaban la lectura del informe. 24 commits desde
`96e10e0`.

> **⚠ No fusionar sin haber migrado y republicado antes.** El orden está al
> final y no es una recomendación: el código nuevo no funciona sin el esquema
> nuevo.

## Qué cierra

| Hallazgo | Subfase | Qué era |
|---|---|---|
| **H-005** 🔒 | F0.1 · F0.1b | El denominador de H2 no estaba congelado. El payload publica ahora la lista de gerencias autorizadas, cada una marcada `prd` o `adicional` |
| **H-009** 🔒 | F0.2 | La comprobación de cifras existía pero solo corría en calibración. Es la regla **R8** del validador y rechaza con motivo |
| **H-012** 🔒 | F0.3 | Cookie de identidad forjable. Va firmada (HMAC), solo se emite para correos registrados y activos, y cada identificación deja rastro. **El riesgo de fondo queda aceptado, no cerrado**: ver R-A2 |
| **H-013** 🔒 | F0.4 | Las acciones de escritura no verificaban alcance. Ahora se resuelve contra la base: insight de informe publicado, ciclo editable, rol `gerencia`, gerencia en la lista congelada y **solo lo pedido** |
| **H-045** 🔒 | F0.7 | Un fallo al guardar no se veía. La acción devuelve resultado, el mensaje sale en la fila y la selección no se pierde |
| **H-020** 🔒 | F0.8 | La infografía no estaba ni hecha ni retirada. **Retirada formalmente** del MVP (P-4) |
| **H-040** | F0.6 | El informe no se podía regenerar. `ORDER BY` determinista, `informe.origen` con commit e invocación, y `scripts/publicar_informe.py` como único punto de entrada |
| **H-023** | F0.5 | Cuatro documentos decían que el Correlacionador v2 estaba vigente. Lo publicado es **v1** |
| **H-015** | F1.5 | La pantalla describía un criterio de selección que no se aplica. Sale del payload |
| **H-016** | F4.1 | Se veían 5 insights por municipio y 1 evidencia por insight. Ahora **todos**: Funza pasa de 5 a 49 insights y de 5 a 183 evidencias |
| **H-019** | F5.3 | La etiqueta MVP vivía en una sola vista. La pinta el layout, así que está en todas |

Además, una **guarda de publicación**: `publicar()` se niega si no hay ninguna
gerencia `prd` declarada, o si alguna no tiene usuario activo con rol
`gerencia`. Sin números fijos en el código.

## Qué NO entra

- **Ningún secreto.** `.env` no está versionado; `.env.example` lista
  `COOKIE_SECRET` **vacío**. No hay cadenas de conexión en el diff.
- **Ninguna migración aplicada a la base principal.** Todo se verificó en el
  branch de Neon `remediacion-f0`, que **no es fuente de datos**: contiene
  informes republicados, usuarios de prueba y una calificación de prueba.
- `docs/auditoria.md` no se toca: vive en la rama `audit/2026-09-22` y sigue
  describiendo `96e10e0`, el commit auditado.

**Sí entra `config/usuarios.csv`**, con nombres y correos corporativos reales,
por decisión expresa del dueño del 2026-09-22. Queda en el historial de git.

## Riesgos aceptados

| | Qué se acepta | Quién |
|---|---|---|
| **R-A1** | La credencial de escritura de Neon se expuso en un chat y **no se rotará** | Dueño, durante la auditoría |
| **R-A2** | **No se adopta el token**: la identidad es un correo tecleado, así que quien conozca uno autorizado puede calificar por esa gerencia. **H-012 queda abierto.** Al publicar H1 y H2 hay que decir que la atribución es declarativa | Dueño, 2026-09-22 |
| **P-6** | **No se consulta a jurídica** por los datos personales de SECOP y de los calificadores en esa base | Dueño, 2026-09-22 |

## Qué queda abierto

- **F0b** entera: `informe_resultados.md` tiene dos afirmaciones falsas sobre la
  hipótesis bloqueante y una cifra sin productor. **Bloquea la decisión
  go/no-go**, no la distribución.
- **F2.3**: validar el Correlacionador v2 con linaje persistido. Mientras tanto
  el valor por defecto vuelve a **v1**, que es lo publicado, y una prueba impide
  cambiarlo en silencio.
- **F1–F6** restantes del plan.
- Los 7 municipios que el informe no pide calificar muestran sus insights **solo
  para consulta**, por decisión del dueño.

## Verificación

- `pytest` **333 passed** · `tsc --noEmit` limpio · `next build` compila ·
  `generar_contrato_ts.py --check` al día.
- Las tres migraciones se aplicaron, revirtieron y reaplicaron con
  `alembic check` limpio.
- Sobre el branch de Neon, con la app corriendo: alcance verificado con las
  Server Actions reales, republicación con **241/241 insights, 933/933 citas y
  10/10 scores**, y la lista congelada con **5 `prd` + 2 `adicional`**.

## Orden obligatorio

Las migraciones son **aditivas** y el código viejo tolera el esquema nuevo, pero
**el código nuevo no funciona sin él**. Por eso:

1. `pg_dump` de la base principal, fuera del repositorio.
2. `alembic upgrade head` con la cadena **directa** (por el `-pooler` no se
   migra), y confirmar con `alembic current` y `alembic check`.
3. Cargar usuarios y republicar el informe, **desde esta rama**. Nunca desde
   `main`: su `publicar()` no escribe `informe.origen`, que es NOT NULL.
4. Añadir **`COOKIE_SECRET`** en Vercel. Sin él la app no identifica a nadie y
   la ventana de calificación no arranca.
5. **Entonces** fusionar, que es cuando se despliega el código nuevo.

La secuencia completa, con sus verificaciones posteriores, está en
[docs/decisiones-remediacion.md](docs/decisiones-remediacion.md).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
