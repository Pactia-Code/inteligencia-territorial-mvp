/**
 * Todo el SQL de la app, en un solo sitio.
 *
 * La app **solo lee** del pipeline (CA-M9.16). Sus escrituras son
 * `calificacion` y `seguimiento`, y viven aparte en `escrituras.ts` con el
 * contrato generado desde `modelos.py`.
 *
 * Las lecturas son pocas porque M6 ya compuso el informe: la vista de ciclo
 * entera es **una fila**. Eso no es casualidad, es el reparto — M6 compone,
 * M9 pinta.
 */
import { sql } from "./db";
import type { Informe } from "./tipos";

/** El informe vigente de un ciclo. Define tambien la corrida canonica (A9). */
export async function informeDelCiclo(idCiclo: number): Promise<Informe | null> {
  const filas = await sql`
    SELECT contenido
      FROM informe
     WHERE id_ciclo = ${idCiclo}
       AND estado = 'publicado'
  `;
  return filas.length ? (filas[0].contenido as Informe) : null;
}

/** Ciclos con informe publicado, del mas reciente al mas antiguo. */
export async function ciclosPublicados(): Promise<
  { id_ciclo: number; fecha_publicacion: string }[]
> {
  const filas = await sql`
    SELECT id_ciclo, fecha_publicacion
      FROM informe
     WHERE estado = 'publicado'
     ORDER BY id_ciclo DESC
  `;
  return filas as { id_ciclo: number; fecha_publicacion: string }[];
}

/**
 * Si un ciclo admite calificaciones (CA-M7.7).
 *
 * Derivado, sin campo nuevo: se cierra cuando se publica el informe de un ciclo
 * posterior. Los cerrados se ven y no se editan.
 */
export async function cicloEsEditable(idCiclo: number): Promise<boolean> {
  const filas = await sql`
    SELECT 1
      FROM informe
     WHERE estado = 'publicado'
       AND id_ciclo > ${idCiclo}
     LIMIT 1
  `;
  return filas.length === 0;
}

/**
 * Identificacion por correo: resuelve el correo a su gerencia.
 *
 * **El sistema no envia correos.** No hay canal de notificacion (11.4/3): el
 * enlace se comparte a mano y el correo es el identificador que la persona
 * **escribe** en pantalla para poder calificar. Si buscas el servicio de
 * envio, no existe.
 *
 * Devuelve `null` si no esta en la lista precargada — entonces esa persona
 * **solo visualiza**. La app **nunca escribe** en `usuario` (M9-acceso), lo que
 * mantiene las escrituras en las dos tablas de CA-M9.16 y deja el denominador
 * de H2 conocido antes de medir.
 */
export async function gerenciaDelCorreo(
  correo: string,
): Promise<{ id: number; id_gerencia: string; nombre: string; rol: string } | null> {
  const filas = await sql`
    SELECT id, id_gerencia, nombre, rol
      FROM usuario
     WHERE lower(correo) = lower(${correo})
       AND activo
  `;
  return filas.length
    ? (filas[0] as { id: number; id_gerencia: string; nombre: string; rol: string })
    : null;
}

/**
 * Las calificaciones que figuran **a nombre de esta persona** en el ciclo.
 *
 * Distinto de `calificacionesDeLaGerencia`: aquella es lo que la gerencia tiene
 * registrado —y es lo que la pantalla usa para rellenar los controles, porque
 * la unicidad es por gerencia—; esta es **quien las escribio**. Con dos
 * personas en una misma gerencia las dos listas dejan de coincidir, y ver la
 * propia es lo que permite a alguien comprobar que lo que figura a su nombre es
 * lo que realmente puso.
 *
 * No enseña nada de nadie mas, asi que no roza CA-M7.2.
 */
export async function calificacionesDelUsuario(
  idCiclo: number,
  idUsuario: number,
): Promise<{ id_insight: number; valor: number }[]> {
  const filas = await sql`
    SELECT c.id_insight, c.valor
      FROM calificacion c
      JOIN insight i ON i.id = c.id_insight
      JOIN corrida_agentes ca ON ca.id = i.id_corrida
     WHERE ca.id_ciclo = ${idCiclo}
       AND c.id_usuario = ${idUsuario}
     ORDER BY c.id_insight
  `;
  return filas as { id_insight: number; valor: number }[];
}

/**
 * Lo que esa gerencia ya califico en ese ciclo.
 *
 * Solo lo suyo: CA-M7.2 prohibe que una gerencia vea la calificacion de otra,
 * un promedio o cuantas han respondido.
 */
export async function calificacionesDeLaGerencia(
  idCiclo: number,
  idGerencia: string,
): Promise<Record<number, { valor: number; comentario: string | null }>> {
  const filas = await sql`
    SELECT c.id_insight, c.valor, c.comentario
      FROM calificacion c
      JOIN insight i ON i.id = c.id_insight
      JOIN corrida_agentes ca ON ca.id = i.id_corrida
     WHERE ca.id_ciclo = ${idCiclo}
       AND c.id_gerencia = ${idGerencia}
  `;
  const mapa: Record<number, { valor: number; comentario: string | null }> = {};
  for (const f of filas as {
    id_insight: number;
    valor: number;
    comentario: string | null;
  }[]) {
    mapa[f.id_insight] = { valor: f.valor, comentario: f.comentario };
  }
  return mapa;
}
