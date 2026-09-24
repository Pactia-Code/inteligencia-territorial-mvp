/**
 * PANEL DEL ADMINISTRADOR — metricas del experimento (CA-M9.13 a CA-M9.15).
 * **Sin construir.**
 *
 * Es la subfase F4.2 del plan (H-014 y H-010 en interfaz, 3 d), del bloque P3.
 *
 * **Sigue siendo solo para administrador aunque no haya nada que enseñar.**
 * CA-M9.14 restringe la visibilidad de estas metricas, y la restriccion se
 * implementa ahora y no cuando existan los datos: si la ruta se abriera hoy,
 * el dia que se llene nadie se acordaria de cerrarla.
 *
 * A quien no es administrador se le devuelve **404, no «no autorizado»**: un
 * mensaje de prohibido confirmaria que la ruta existe, y aqui no hay nada que
 * confirmar. La entrada del menu tampoco se le muestra (`Nav.tsx`).
 */
import { notFound } from "next/navigation";
import { esAdministrador, exigirIdentidad } from "@/lib/sesion";
import { Proximamente } from "../Proximamente";

// Depende de la cookie de identificacion, asi que se resuelve por peticion.
export const dynamic = "force-dynamic";

export default async function Metricas() {
  // Sin identidad se va a entrar; **con identidad pero sin ser administrador,
  // 404**. Son dos respuestas distintas a proposito: la primera es «di quien
  // eres», la segunda es «aqui no hay nada para ti», y un 404 no confirma que
  // la ruta exista.
  await exigirIdentidad("/metricas");
  if (!(await esAdministrador())) notFound();

  return (
    <Proximamente
      titulo="Métricas"
      que="Aquí irá el panel del experimento: cuántas gerencias han calificado,
           la tasa de respuesta por condición, la tasa de rechazo del validador
           desglosada por regla y la descarga en CSV."
    />
  );
}
