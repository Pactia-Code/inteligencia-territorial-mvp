/**
 * Las **dos unicas** escrituras de la app (CA-M9.16): `calificacion` y
 * `seguimiento`. Todo lo demas del pipeline es de solo lectura.
 *
 * La forma de estas tablas no se escribe a mano: viene de
 * `contrato.generado.ts`, derivado de `modelos.py`. Si alguien cambia el
 * modelo sin regenerar, `tests/test_contrato.py` rompe el suite de Python. Eso
 * es lo que impide escribir contra una columna que ya no existe.
 *
 * **La app nunca escribe en `usuario`** (M9-acceso): quien no este precargado
 * no califica, y asi el denominador de H2 se conoce antes de medir.
 */
import { sql } from "./db";
import {
  VALOR_CALIFICACION_MAX,
  VALOR_CALIFICACION_MIN,
  type FilaSeguimiento,
} from "./contrato.generado";

export class CalificacionInvalida extends Error {}

/**
 * Registra o corrige la calificacion de un insight por una gerencia.
 *
 * **Es un upsert, no un insert**, y eso es CA-M7.6: «se guarda al instante, sin
 * boton de enviar; una gerencia puede calificar 2 insights hoy y 4 maniana sin
 * perder lo hecho». Y tambien puede corregirse: se apoya en la restriccion
 * unica `(id_insight, id_gerencia)` que CA-M7.2 ya creo en el modelo.
 */
export async function calificar(
  idInsight: number,
  idGerencia: string,
  valor: number,
  comentario: string | null = null,
): Promise<void> {
  if (!Number.isInteger(valor) || valor < VALOR_CALIFICACION_MIN || valor > VALOR_CALIFICACION_MAX) {
    // Se comprueba aqui ademas de en la base: un error de validacion legible
    // vale mas que un fallo de restriccion en medio de la ventana.
    throw new CalificacionInvalida(
      `la calificacion debe estar entre ${VALOR_CALIFICACION_MIN} y ${VALOR_CALIFICACION_MAX}, llego ${valor}`,
    );
  }
  await sql`
    INSERT INTO calificacion (id_insight, id_gerencia, valor, comentario, creado_en)
         VALUES (${idInsight}, ${idGerencia}, ${valor}, ${comentario}, now())
    ON CONFLICT (id_insight, id_gerencia)
      DO UPDATE SET valor = EXCLUDED.valor,
                    comentario = COALESCE(EXCLUDED.comentario, calificacion.comentario)
  `;
}

/** El comentario libre y opcional de CA-M7.4. No borra la calificacion. */
export async function comentar(
  idInsight: number,
  idGerencia: string,
  comentario: string,
): Promise<void> {
  await sql`
    UPDATE calificacion
       SET comentario = ${comentario || null}
     WHERE id_insight = ${idInsight}
       AND id_gerencia = ${idGerencia}
  `;
}

/**
 * Un cambio de estado de seguimiento. **Inserta, nunca sobrescribe**: la tabla
 * es de historial (PRD §4.2), asi que cada cambio deja su fila.
 */
export async function registrarSeguimiento(
  fila: Pick<FilaSeguimiento, "divipola" | "id_ciclo_origen" | "estado" | "nota" | "id_usuario">,
): Promise<void> {
  await sql`
    INSERT INTO seguimiento (divipola, id_ciclo_origen, estado, nota, id_usuario, fecha_cambio)
         VALUES (${fila.divipola}, ${fila.id_ciclo_origen}, ${fila.estado},
                 ${fila.nota}, ${fila.id_usuario}, now())
  `;
}
