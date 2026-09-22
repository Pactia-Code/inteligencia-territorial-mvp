/**
 * Las **unicas** escrituras de la app: `calificacion`, `seguimiento` y
 * `identificacion`. Todo lo demas del pipeline es de solo lectura.
 *
 * CA-M9.16 enumera las dos primeras. `identificacion` es **dato de sesion**
 * —quien se identifico, cuando y desde que navegador— y se anadio en F0.3 como
 * ampliacion deliberada, registrada en `docs/decisiones-remediacion.md`. Como
 * las otras dos, su forma sale de `modelos.py` via el contrato generado.
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
  type FilaIdentificacion,
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
  idUsuario: number,
  comentario: string | null = null,
): Promise<void> {
  if (!Number.isInteger(valor) || valor < VALOR_CALIFICACION_MIN || valor > VALOR_CALIFICACION_MAX) {
    // Se comprueba aqui ademas de en la base: un error de validacion legible
    // vale mas que un fallo de restriccion en medio de la ventana.
    throw new CalificacionInvalida(
      `la calificacion debe estar entre ${VALOR_CALIFICACION_MIN} y ${VALOR_CALIFICACION_MAX}, llego ${valor}`,
    );
  }
  // `id_usuario` se actualiza tambien al corregir: la fila es una por
  // (insight, gerencia), y lo util de auditar es **quien la dejo asi**.
  await sql`
    INSERT INTO calificacion (id_insight, id_gerencia, valor, comentario, id_usuario, creado_en)
         VALUES (${idInsight}, ${idGerencia}, ${valor}, ${comentario}, ${idUsuario}, now())
    ON CONFLICT (id_insight, id_gerencia)
      DO UPDATE SET valor = EXCLUDED.valor,
                    comentario = COALESCE(EXCLUDED.comentario, calificacion.comentario),
                    id_usuario = EXCLUDED.id_usuario
  `;
}

/**
 * Deja constancia de una identificacion. F0.3, residual de H-012.
 *
 * **No autentica a nadie**: el dueno no adopto el token (R-A2), asi que esto no
 * demuestra quien es la persona, solo deja rastro de que esa cuenta se
 * identifico. Si una calificacion se discute, hay algo que mirar.
 *
 * La `ip` llega **solo si el despliegue la pone** en `x-forwarded-for` —en
 * Vercel si, en local casi nunca— y por eso es anulable: no se configura nada
 * para obtenerla.
 */
export async function registrarIdentificacion(
  fila: Pick<FilaIdentificacion, "id_usuario" | "user_agent" | "ip">,
): Promise<void> {
  await sql`
    INSERT INTO identificacion (id_usuario, user_agent, ip, creado_en)
         VALUES (${fila.id_usuario}, ${fila.user_agent}, ${fila.ip}, now())
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
