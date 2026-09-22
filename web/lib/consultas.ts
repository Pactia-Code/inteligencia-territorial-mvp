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
 * Resuelve el correo a su gerencia. `null` si no esta en la lista precargada.
 *
 * La app **nunca escribe** en `usuario` (M9-acceso): quien no este, no
 * califica. Eso mantiene las escrituras en las dos tablas de CA-M9.16 y deja
 * el denominador de H2 conocido antes de medir.
 */
export async function gerenciaDelCorreo(
  correo: string,
): Promise<{ id_gerencia: string; nombre: string; rol: string } | null> {
  const filas = await sql`
    SELECT id_gerencia, nombre, rol
      FROM usuario
     WHERE lower(correo) = lower(${correo})
       AND activo
  `;
  return filas.length
    ? (filas[0] as { id_gerencia: string; nombre: string; rol: string })
    : null;
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
