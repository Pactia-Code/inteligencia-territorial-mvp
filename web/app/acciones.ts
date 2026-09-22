"use server";

/**
 * Acciones de servidor: identificarse y calificar.
 *
 * Van como Server Actions y no como una API aparte porque el PRD §4.3 lo pide
 * —«una sola app sobre la misma Postgres, sin API intermedia ni segundo
 * almacen»— y porque asi la calificacion funciona **sin JavaScript en el
 * cliente**: un `<form>` con cinco botones de envio, cada uno con su valor.
 * Eso es literalmente «clic 1 = registro» (CA-M7.6).
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { gerenciaDelCorreo } from "@/lib/consultas";
import { calificar, comentar, registrarSeguimiento } from "@/lib/escrituras";
import { ESTADO_SEGUIMIENTO } from "@/lib/contrato.generado";
import { EXIGEN_NOTA } from "@/lib/tablero";
import { COOKIE_CORREO, identidadActual } from "@/lib/sesion";

/** Un ano: la ventana de calificacion dura ciclos, no una sesion. */
const DURACION_COOKIE = 60 * 60 * 24 * 365;

export type ResultadoSeguimiento =
  | { ok: true }
  | { ok: false; motivo: "sin_identificar" | "estado_invalido" }
  | { ok: false; motivo: "falta_nota"; estado: string };

export type ResultadoIdentificacion =
  | { ok: true }
  | { ok: false; motivo: "vacio" | "no_autorizado"; correo: string };

/**
 * Guarda el correo si esta en la lista precargada.
 *
 * **No da de alta a nadie** (M9-acceso): quien no este, solo visualiza. El
 * mensaje de rechazo dice que hacer, nunca un error generico — una errata
 * durante la ventana se lleva por delante una respuesta de H2, y con siete
 * gerencias cada una pesa el 14%.
 */
export async function identificarse(
  _previo: ResultadoIdentificacion | null,
  datos: FormData,
): Promise<ResultadoIdentificacion> {
  const correo = String(datos.get("correo") ?? "").trim();
  if (!correo) return { ok: false, motivo: "vacio", correo };

  const usuario = await gerenciaDelCorreo(correo);
  if (!usuario) return { ok: false, motivo: "no_autorizado", correo };

  (await cookies()).set(COOKIE_CORREO, correo, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: DURACION_COOKIE,
    path: "/",
  });
  revalidatePath("/", "layout");
  return { ok: true };
}

/** Salir sin tener que borrar cookies a mano (design system §2.4). */
export async function cambiarCorreo(): Promise<void> {
  (await cookies()).delete(COOKIE_CORREO);
  revalidatePath("/", "layout");
}

/**
 * Registra una calificacion. Un clic, sin confirmacion ni boton de enviar.
 *
 * Si quien pulsa no esta identificado no se guarda nada y la pantalla pide el
 * correo: **leer es abierto, escribir no**.
 */
export async function registrarCalificacion(datos: FormData): Promise<void> {
  const yo = await identidadActual();
  if (!yo) return;
  const idInsight = Number(datos.get("id_insight"));
  const valor = Number(datos.get("valor"));
  await calificar(idInsight, yo.id_gerencia, valor);
  revalidatePath("/ciclo/[id]", "page");
}

/**
 * Cambia el estado de seguimiento de un municipio (CA-M9.9).
 *
 * **Nota obligatoria al pasar a `descartado` o `en_estructuracion`.** Son los
 * dos estados que cierran o comprometen: descartar apaga un municipio que el
 * sistema priorizo, y estructurar mueve recursos. Sin el porque, el historial
 * guarda que paso y no por que, que es la mitad que sirve.
 *
 * **Atribuye a PERSONA**, a diferencia de la calificacion, que atribuye a
 * gerencia. Es deliberado: ver la nota en `lib/sesion.ts`.
 */
export async function cambiarEstado(
  _previo: ResultadoSeguimiento | null,
  datos: FormData,
): Promise<ResultadoSeguimiento> {
  const yo = await identidadActual();
  if (!yo) return { ok: false, motivo: "sin_identificar" };

  const divipola = String(datos.get("divipola") ?? "");
  const estado = String(datos.get("estado") ?? "");
  const nota = String(datos.get("nota") ?? "").trim();
  const idCiclo = Number(datos.get("id_ciclo"));

  if (!ESTADO_SEGUIMIENTO.includes(estado as (typeof ESTADO_SEGUIMIENTO)[number])) {
    return { ok: false, motivo: "estado_invalido" };
  }
  if (EXIGEN_NOTA.includes(estado) && !nota) {
    return { ok: false, motivo: "falta_nota", estado };
  }

  await registrarSeguimiento({
    divipola,
    id_ciclo_origen: idCiclo,
    estado: estado as (typeof ESTADO_SEGUIMIENTO)[number],
    nota: nota || null,
    id_usuario: yo.id,
  });
  revalidatePath("/priorizados");
  return { ok: true };
}

/** Comentario libre y opcional (CA-M7.4), despues de haber calificado. */
export async function registrarComentario(datos: FormData): Promise<void> {
  const yo = await identidadActual();
  if (!yo) return;
  await comentar(
    Number(datos.get("id_insight")),
    yo.id_gerencia,
    String(datos.get("comentario") ?? "").trim(),
  );
  revalidatePath("/ciclo/[id]", "page");
}
