/**
 * Quien puede escribir que, decidido **en el servidor**. F0.4, hallazgo H-013.
 *
 * Antes las acciones de escritura solo comprobaban que hubiera alguien
 * identificado. Todo lo demas venia del formulario, y un formulario es una
 * peticion HTTP que cualquiera puede construir: bastaba con mandar otro
 * `id_insight` para calificar algo que no estaba en ningun informe publicado, o
 * de un ciclo ya cerrado. Esas filas entrarian en H1 y en H2 sin que ninguna
 * gerencia las hubiera visto.
 *
 * Las reglas estan aqui, en funciones puras y sin base de datos, por dos
 * razones: se prueban sin levantar nada, y se leen de corrido en un solo sitio
 * en vez de repartidas por tres acciones.
 *
 * **La lista de gerencias es la congelada en el payload del informe**
 * (`calificacion.gerencias`, F0.1 y F0.1b), no el estado de `usuario` hoy. Esa
 * es justamente la diferencia que importa: una gerencia dada de alta despues de
 * publicar **no** puede calificar ese informe, porque no estaba en el
 * denominador con el que se va a medir H2.
 */

/** Lo que la vista congelo sobre quien podia calificar. */
export interface GerenciaCongelada {
  id_gerencia: string;
  tipo: "prd" | "adicional";
}

/** Lo minimo que hace falta saber de quien escribe. */
export interface QuienEscribe {
  rol: string;
  id_gerencia: string;
}

export type MotivoSinAlcance =
  | "sin_identificar"
  | "fuera_de_alcance"
  | "ciclo_cerrado"
  | "rol_no_califica"
  | "gerencia_no_congelada";

export type Veredicto = { ok: true } | { ok: false; motivo: MotivoSinAlcance };

const SI: Veredicto = { ok: true };
const no = (motivo: MotivoSinAlcance): Veredicto => ({ ok: false, motivo });

/**
 * Si esta persona puede calificar o comentar en este informe.
 *
 * El orden de las comprobaciones es el orden en que se descubren, de lo mas
 * general a lo mas particular, para que el motivo que sale sea el util.
 *
 * `rol_no_califica` deja fuera al **administrador**: CA-M9.14 le da el panel de
 * metricas, no papeleta. Si calificara, su voto entraria en H1 y ademas seria
 * el unico que ve el avance de las demas gerencias mientras opina.
 */
export function puedeCalificar(
  yo: QuienEscribe | null,
  gerenciasCongeladas: GerenciaCongelada[] | undefined,
  cicloEditable: boolean,
): Veredicto {
  if (!yo) return no("sin_identificar");
  if (!cicloEditable) return no("ciclo_cerrado");
  if (yo.rol !== "gerencia") return no("rol_no_califica");

  // Un informe publicado antes de F0.1 no lleva la lista. No se supone que la
  // pase: se trata como que nadie estaba autorizado, que es lo conservador.
  // La republicacion de F0.6 es lo que pone la lista en su sitio.
  const congeladas = gerenciasCongeladas ?? [];
  if (!congeladas.some((g) => g.id_gerencia === yo.id_gerencia)) {
    return no("gerencia_no_congelada");
  }
  return SI;
}

/**
 * Si esta persona puede mover el estado de seguimiento de este municipio.
 *
 * Mas abierto que calificar, y a proposito: CA-M9.9 dice **cualquier gerencia**,
 * y el seguimiento es una decision operativa que no alimenta H1 ni H2. Lo que
 * si se exige es que el municipio **este en un informe publicado**: mover un
 * municipio que el sistema nunca priorizo seria un historial sobre algo que
 * nadie propuso.
 *
 * Tampoco se cierra con el ciclo: CA-M7.7 congela la calificacion, no el
 * seguimiento, y un municipio se sigue trabajando despues de que su ciclo pase.
 */
export function puedeMoverSeguimiento(
  yo: QuienEscribe | null,
  divipolasDelInforme: string[],
  divipola: string,
): Veredicto {
  if (!yo) return no("sin_identificar");
  if (!divipolasDelInforme.includes(divipola)) return no("fuera_de_alcance");
  return SI;
}
