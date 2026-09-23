/**
 * Que se le dice a alguien cuando su calificacion no se guarda. F0.7, H-045.
 *
 * **El fallo silencioso era el problema.** La accion no devolvia nada: si la
 * escritura fallaba —driver caido, alcance denegado, lo que fuera— la pantalla
 * se recargaba igual y la persona veia su calificacion sin registrar, sin un
 * solo aviso. En una ventana de calificacion eso no se descubre: se descubre al
 * analizar H2, cuando ya no hay nada que hacer.
 *
 * Los textos viven aqui, separados del componente, por una razon concreta: el
 * `switch` es **exhaustivo sobre el tipo**, asi que anadir un motivo nuevo sin
 * su mensaje es error de compilacion. Un motivo sin texto seria otra vez un
 * fallo mudo, que es justo lo que se venia a quitar.
 *
 * **Nunca un mensaje generico.** Cada uno dice que paso y que hacer: una errata
 * durante la ventana se lleva por delante una respuesta de H2.
 */
import type { MotivoSinAlcance } from "./alcance";

export type MotivoCalificacion =
  | MotivoSinAlcance
  | "valor_invalido"
  | "error_al_guardar";

export function mensajeDeCalificacion(motivo: MotivoCalificacion): string {
  switch (motivo) {
    case "sin_identificar":
      return "No se guardó: identifícate con tu correo más arriba y vuelve a pulsar.";
    case "ciclo_cerrado":
      return "No se guardó: este ciclo ya se cerró porque se publicó el informe del siguiente. Puedes leerlo, no calificarlo.";
    case "rol_no_califica":
      return "No se guardó: esta cuenta es de administración y no califica. Entra con el correo de tu gerencia.";
    case "gerencia_no_congelada":
      return "No se guardó: tu gerencia no figura entre las autorizadas en este informe. Escribe a quien te compartió el enlace.";
    case "insight_no_pedido":
      return "No se guardó: este insight es de consulta. Se califican solo los que el informe pide, para que todas las gerencias respondan sobre los mismos.";
    case "fuera_de_alcance":
      return "No se guardó: este insight no pertenece al informe publicado. Vuelve a cargar la página, es probable que haya cambiado mientras la tenías abierta.";
    case "valor_invalido":
      return "No se guardó: la calificación tiene que ser un número del 1 al 5.";
    case "error_al_guardar":
      return "No se guardó: falló la escritura en la base. Tu selección sigue marcada; vuelve a pulsar en un momento.";
    default: {
      // Exhaustividad comprobada por el compilador: si alguien anade un motivo
      // y no lo redacta, esto deja de compilar.
      const nunca: never = motivo;
      return nunca;
    }
  }
}

/**
 * Que boton queda marcado despues de intentar calificar.
 *
 * Esta aqui, y no dentro del componente, para que se pueda **comprobar
 * ejecutandola**: es la regla que evita el peor caso de H-045, que es fallar y
 * ademas borrar lo que la persona habia elegido.
 *
 * Lo guardado manda sobre lo pulsado: si la fila ya tiene un 4 registrado y un
 * intento de cambiarlo a 5 falla, lo cierto sigue siendo el 4.
 */
export function seleccionVisible(
  valorGuardado: number | undefined,
  resultado: { ok: boolean; valor?: number | null } | null,
): number | undefined {
  if (valorGuardado !== undefined) return valorGuardado;
  if (resultado && !resultado.ok && typeof resultado.valor === "number") {
    return resultado.valor;
  }
  return undefined;
}

/** Los motivos existentes, para poder comprobar que todos tienen texto. */
export const MOTIVOS_CALIFICACION: MotivoCalificacion[] = [
  "sin_identificar",
  "ciclo_cerrado",
  "rol_no_califica",
  "gerencia_no_congelada",
  "insight_no_pedido",
  "fuera_de_alcance",
  "valor_invalido",
  "error_al_guardar",
];
