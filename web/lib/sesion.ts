/**
 * Identificacion por correo. **No hay sesion ni autenticacion.**
 *
 * El correo se guarda en una cookie por conveniencia: pedirlo en cada
 * calificacion rompe los <=2 clics de CA-M7.1. **La cookie no anade riesgo**:
 * sin autenticacion cualquiera puede teclear un correo ajeno con ella o sin
 * ella. El riesgo viene de la decision de no autenticar, y esta registrado —
 * la atribucion es declarativa y hay que decirlo al publicar H2.
 *
 * Y se resuelve a **gerencia, no a persona**: `calificacion` atribuye asi
 * (CA-M7.2), y mostrar un nombre propio sugeriria algo que el sistema no
 * guarda.
 */
import { cookies } from "next/headers";
import { gerenciaDelCorreo } from "./consultas";

export const COOKIE_CORREO = "correo";

export interface Identidad {
  /**
   * El id de fila de `usuario`. Hace falta para `seguimiento.id_usuario`.
   *
   * **Y aqui hay una asimetria deliberada que conviene no «corregir»:**
   * `seguimiento` atribuye a PERSONA y `calificacion` a GERENCIA. No es un
   * descuido. El seguimiento necesita saber quien cambio un estado —es una
   * decision operativa con consecuencias—; la calificacion no debe saberlo,
   * porque CA-M7.2 exige que sea independiente y que nadie vea la de otro.
   * Igualarlas por consistencia romperia una de las dos.
   */
  id: number;
  correo: string;
  id_gerencia: string;
  nombre: string;
  rol: string;
}

/** Quien esta calificando, o `null` si nadie se ha identificado todavia. */
export async function identidadActual(): Promise<Identidad | null> {
  const correo = (await cookies()).get(COOKIE_CORREO)?.value;
  if (!correo) return null;
  const usuario = await gerenciaDelCorreo(correo);
  return usuario ? { correo, ...usuario } : null;
}

/** Solo el administrador ve el panel de metricas (CA-M9.14). */
export async function esAdministrador(): Promise<boolean> {
  const yo = await identidadActual();
  return yo?.rol === "administrador";
}
