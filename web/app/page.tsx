import { redirect } from "next/navigation";
import { ciclosPublicados } from "@/lib/consultas";
import { exigirIdentidad } from "@/lib/sesion";

// Se resuelve en cada peticion: que ciclo es el ultimo depende de la base,
// no del momento de compilar.
export const dynamic = "force-dynamic";

/** Lleva al ciclo con informe publicado mas reciente. */
export default async function Inicio() {
  await exigirIdentidad("/");
  const ciclos = await ciclosPublicados();
  if (!ciclos.length) {
    return (
      <main style={{ padding: "var(--space-12) var(--space-6)", maxWidth: 640 }}>
        <h1 className="t-h1">Inteligencia Territorial</h1>
        <p className="t-body">Aún no hay ningún informe publicado.</p>
      </main>
    );
  }
  redirect(`/ciclo/${ciclos[0].id_ciclo}`);
}
