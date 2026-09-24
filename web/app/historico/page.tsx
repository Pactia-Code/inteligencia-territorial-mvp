/**
 * VISTA 3 — Historico de informes publicados (CA-M9.7). **Sin construir.**
 *
 * Es la subfase F4.3 del plan (H-014, 1 d) y vive en el bloque P3: las
 * capacidades del PRD que el MVP no llego a construir. Hasta entonces esto
 * evita el 404, que durante la ronda se lee como una averia.
 */
import { exigirIdentidad } from "@/lib/sesion";
import { Proximamente } from "../Proximamente";

// Depende de la cookie de identificacion, asi que se resuelve por peticion.
export const dynamic = "force-dynamic";

export default async function Historico() {
  await exigirIdentidad("/historico");
  return (
    <Proximamente
      titulo="Histórico"
      que="Aquí se podrán consultar los informes de ciclos anteriores, con el
           que se publicó en cada uno y las calificaciones que recibió."
    />
  );
}
