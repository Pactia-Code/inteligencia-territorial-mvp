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
import { cookies, headers } from "next/headers";
import {
  cicloEsEditable,
  cicloPublicadoDelInsight,
  gerenciaDelCorreo,
  informeDelCiclo,
} from "@/lib/consultas";
import { puedeCalificar, puedeMoverSeguimiento } from "@/lib/alcance";
import type { MotivoCalificacion } from "@/lib/mensajes";
import {
  calificar,
  comentar,
  registrarIdentificacion,
  registrarSeguimiento,
} from "@/lib/escrituras";
import { ESTADO_SEGUIMIENTO } from "@/lib/contrato.generado";
import { firmar, haySecreto } from "@/lib/firma";
import { EXIGEN_NOTA } from "@/lib/tablero";
import { COOKIE_CORREO, identidadActual } from "@/lib/sesion";

/** Un ano: la ventana de calificacion dura ciclos, no una sesion. */
const DURACION_COOKIE = 60 * 60 * 24 * 365;

export type ResultadoSeguimiento =
  | { ok: true }
  | {
      ok: false;
      motivo: "sin_identificar" | "estado_invalido" | "fuera_de_alcance";
    }
  | { ok: false; motivo: "falta_nota"; estado: string };

/**
 * Lo que devuelve calificar. **Lleva el valor que se pulsó**, y no es un
 * detalle: si falla, la pantalla tiene que poder seguir marcando el botón que
 * la persona eligió. Perder la selección al fallar obliga a recordar qué se
 * había pulsado, que es exactamente cuando se abandona (F0.7, H-045).
 */
export type ResultadoCalificacion =
  | { ok: true; valor: number }
  | { ok: false; motivo: MotivoCalificacion; valor: number | null };

export type ResultadoComentario =
  | { ok: true }
  | { ok: false; motivo: MotivoCalificacion };

export type ResultadoIdentificacion =
  | { ok: true }
  | { ok: false; motivo: "vacio" | "no_autorizado" | "sin_secreto"; correo: string };

/**
 * Guarda el correo si esta en la lista precargada, en una cookie **firmada**.
 *
 * **No da de alta a nadie** (M9-acceso): quien no este, solo visualiza. El
 * mensaje de rechazo dice que hacer, nunca un error generico — una errata
 * durante la ventana se lleva por delante una respuesta de H2.
 *
 * Tres cosas que F0.3 anadio y conviene no deshacer:
 *
 * · **Solo se emite cookie para un correo registrado y activo.** Antes tambien
 *   se comprobaba, pero la cookie era texto plano y se podia poner a mano.
 * · **La cookie va firmada.** Sin firma valida no hay identidad.
 * · **Queda rastro** en `identificacion`. No autentica —el dueno no adopto el
 *   token, R-A2— pero deja algo que mirar si una calificacion se discute.
 */
export async function identificarse(
  _previo: ResultadoIdentificacion | null,
  datos: FormData,
): Promise<ResultadoIdentificacion> {
  const correo = String(datos.get("correo") ?? "").trim();
  if (!correo) return { ok: false, motivo: "vacio", correo };

  // Fallar cerrado: sin secreto no se emite identidad. Un despliegue mal
  // configurado no debe degradarse a «cualquiera es quien dice ser».
  if (!haySecreto()) return { ok: false, motivo: "sin_secreto", correo };

  const usuario = await gerenciaDelCorreo(correo);
  if (!usuario) return { ok: false, motivo: "no_autorizado", correo };

  const cabeceras = await headers();
  await registrarIdentificacion({
    id_usuario: usuario.id,
    user_agent: cabeceras.get("user-agent")?.slice(0, 300) ?? null,
    // Lo que el despliegue ya da, sin configurar nada: en Vercel viene
    // `x-forwarded-for`; en local no suele venir y queda en nulo.
    ip: cabeceras.get("x-forwarded-for")?.split(",")[0]?.trim() ?? null,
  });

  (await cookies()).set(COOKIE_CORREO, firmar(correo), {
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
 * Comprueba en el servidor que esta persona puede escribir sobre este insight.
 *
 * **Nada de esto se fia del formulario** (F0.4, H-013): el `id_insight` llega en
 * la peticion y se resuelve contra la base para saber a que informe publicado
 * pertenece; el ciclo y la lista de gerencias salen de ahi, no del cliente.
 */
async function alcanceSobreInsight(
  idInsight: number,
  yo: { rol: string; id_gerencia: string } | null,
) {
  const idCiclo = await cicloPublicadoDelInsight(idInsight);
  if (idCiclo === null) return { ok: false as const, motivo: "fuera_de_alcance" as const };
  const [informe, editable] = await Promise.all([
    informeDelCiclo(idCiclo),
    cicloEsEditable(idCiclo),
  ]);
  return puedeCalificar(yo, informe?.calificacion.gerencias, editable);
}

/**
 * Registra una calificacion. Un clic, sin confirmacion ni boton de enviar.
 *
 * Si quien pulsa no esta identificado no se guarda nada y la pantalla pide el
 * correo: **leer es abierto, escribir no**. Y desde F0.4 tampoco se guarda si
 * el insight no esta en un informe publicado, si el ciclo ya se cerro, si quien
 * pulsa es administrador o si su gerencia no estaba en la lista congelada.
 *
 * **Devuelve resultado** desde F0.7 (H-045): antes no devolvia nada, asi que un
 * fallo de escritura se veia igual que un exito y la calificacion se perdia sin
 * que nadie se enterara hasta analizar H2.
 *
 * Sigue funcionando **sin JavaScript en el cliente**: `useActionState` da un
 * `formAction` que el `<form>` envia igual con JS desactivado. Lo unico que se
 * pierde entonces es el mensaje en la fila, no el registro.
 */
export async function registrarCalificacion(
  _previo: ResultadoCalificacion | null,
  datos: FormData,
): Promise<ResultadoCalificacion> {
  const yo = await identidadActual();
  const idInsight = Number(datos.get("id_insight"));
  const valor = Number(datos.get("valor"));
  const elegido = Number.isInteger(valor) ? valor : null;

  if (!Number.isInteger(idInsight) || elegido === null) {
    return { ok: false, motivo: "valor_invalido", valor: elegido };
  }

  const alcance = await alcanceSobreInsight(idInsight, yo);
  if (!alcance.ok || !yo) {
    return { ok: false, motivo: alcance.ok ? "sin_identificar" : alcance.motivo, valor: elegido };
  }

  try {
    await calificar(idInsight, yo.id_gerencia, elegido, yo.id);
  } catch {
    // No se propaga: un error aqui no debe tumbar la pagina entera. La fila
    // dice que no se guardo y conserva la seleccion, que es lo accionable.
    return { ok: false, motivo: "error_al_guardar", valor: elegido };
  }
  revalidatePath("/ciclo/[id]", "page");
  return { ok: true, valor: elegido };
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

  // F0.4 (H-013): el municipio tiene que estar en un informe **publicado**. El
  // `divipola` y el `id_ciclo` llegan del formulario, asi que se comprueban
  // contra el payload y no se dan por buenos.
  const informe = await informeDelCiclo(idCiclo);
  const alcance = puedeMoverSeguimiento(
    yo,
    (informe?.municipios ?? []).map((m) => m.divipola),
    divipola,
  );
  if (!alcance.ok) return { ok: false, motivo: "fuera_de_alcance" };

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

/**
 * Comentario libre y opcional (CA-M7.4), despues de haber calificado.
 *
 * Mismo alcance que calificar, y por el mismo motivo: el comentario viaja en la
 * misma fila de `calificacion` y se lee junto a la nota al analizar H1.
 */
export async function registrarComentario(
  _previo: ResultadoComentario | null,
  datos: FormData,
): Promise<ResultadoComentario> {
  const yo = await identidadActual();
  const idInsight = Number(datos.get("id_insight"));
  if (!Number.isInteger(idInsight)) {
    return { ok: false, motivo: "fuera_de_alcance" };
  }

  const alcance = await alcanceSobreInsight(idInsight, yo);
  if (!alcance.ok || !yo) {
    return { ok: false, motivo: alcance.ok ? "sin_identificar" : alcance.motivo };
  }

  try {
    await comentar(
      idInsight,
      yo.id_gerencia,
      String(datos.get("comentario") ?? "").trim(),
    );
  } catch {
    return { ok: false, motivo: "error_al_guardar" };
  }
  revalidatePath("/ciclo/[id]", "page");
  return { ok: true };
}
