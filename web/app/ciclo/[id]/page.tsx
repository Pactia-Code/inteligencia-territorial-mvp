/**
 * VISTA 1 — Ciclo actual. Es donde se miden H1 y H2 (design system §2).
 *
 * Componente de servidor: lee Neon aqui y el navegador nunca ve la cadena de
 * conexion. **Y nunca cruza el payload entero**: son 547 KB con 933
 * evidencias, de las cuales esta pantalla solo necesita 10 municipios con su
 * score, su linea de fuentes y su contexto. Las evidencias se piden al
 * desplegar un municipio.
 */
import { notFound } from "next/navigation";
import { cicloEsEditable, informeDelCiclo } from "@/lib/consultas";
import type { MunicipioDelInforme } from "@/lib/tipos";

export const dynamic = "force-dynamic";

function fecha(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Insignia de posicion: numero sobre navy-700, texto blanco (§2.2). */
function Posicion({ n }: { n: number }) {
  return (
    <span
      className="t-data"
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        minWidth: 28,
        height: 28,
        padding: "0 var(--space-2)",
        background: "var(--color-navy-700)",
        color: "#fff",
        borderRadius: "var(--radio-tarjeta)",
      }}
    >
      {n}
    </span>
  );
}

function FilaMunicipio({
  m,
  alterna,
}: {
  m: MunicipioDelInforme;
  alterna: boolean;
}) {
  return (
    <article
      style={{
        display: "grid",
        gridTemplateColumns: "auto 1fr auto",
        gap: "var(--space-4)",
        alignItems: "start",
        padding: "var(--space-4)",
        borderTop: "1px solid var(--color-border)",
        background: alterna ? "var(--color-navy-100)" : "transparent",
      }}
    >
      <Posicion n={m.puesto} />

      <div style={{ minWidth: 0 }}>
        <h3 className="t-h3" style={{ margin: 0 }}>
          {m.nombre}
        </h3>
        <p className="t-meta" style={{ margin: "var(--space-1) 0 0" }}>
          {m.departamento} · {m.divipola}
        </p>

        {/*
          La linea de fuentes. Va aqui, junto al nombre y al score, con el mismo
          peso visual — nunca al pie ni en un desplegable (M6-orden). Si fuera
          al pie, para cuando se lee el lector ya interpreto el puesto 1 como
          prioridad del ciclo. Nombres de fuente, nunca codigos (M6-src).
        */}
        <p
          className="t-meta"
          style={{ margin: "var(--space-2) 0 0", color: "var(--color-ink-muted)" }}
        >
          {m.fuentes.resumen}
        </p>

        {m.justificacion ? (
          <p className="t-body prosa" style={{ margin: "var(--space-3) 0 0" }}>
            {m.justificacion}
          </p>
        ) : (
          /* El hueco se pinta, no se oculta (§2.2): el Sintetizador aun no
             existe y la pantalla no debe fingir que el informe esta completo. */
          <p
            className="t-meta"
            style={{ margin: "var(--space-3) 0 0", fontStyle: "italic" }}
          >
            Justificación pendiente: la redacta el Sintetizador, que aún no está
            construido.
          </p>
        )}
      </div>

      <div style={{ textAlign: "right" }}>
        <div className="t-data">{m.score.toFixed(4)}</div>
        {m.calificable ? (
          <span
            className="t-label etiqueta etiqueta-aviso"
            style={{ marginTop: "var(--space-2)" }}
          >
            Se pide calificar
          </span>
        ) : (
          <span className="t-label etiqueta" style={{ marginTop: "var(--space-2)" }}>
            Opcional
          </span>
        )}
      </div>
    </article>
  );
}

export default async function VistaCiclo({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const idCiclo = Number(id);
  if (!Number.isInteger(idCiclo)) notFound();

  const informe = await informeDelCiclo(idCiclo);
  if (!informe) notFound();
  const editable = await cicloEsEditable(idCiclo);

  return (
    <main
      style={{
        maxWidth: 960,
        margin: "0 auto",
        padding: "var(--space-12) var(--space-6) var(--space-12)",
      }}
    >
      <header style={{ marginBottom: "var(--space-8)" }}>
        <p className="t-label" style={{ color: "var(--color-navy-700)", margin: 0 }}>
          Inteligencia Territorial
        </p>
        <h1 className="t-h1" style={{ margin: "var(--space-2) 0 0" }}>
          Ciclo {informe.ciclo}
        </h1>
        <p className="t-meta" style={{ margin: "var(--space-1) 0 0" }}>
          {fecha(informe.ventana.desde)} — {fecha(informe.ventana.hasta)} ·{" "}
          {informe.calificacion.mostrados} municipios · modelo{" "}
          {informe.corridas.version_scoring}
        </p>

        {/* CA-M6.5 y CA-M9.17: en el encabezado, no en el pie. Visible sin
            dominar: etiqueta de una linea, no banner de ancho completo. */}
        <p style={{ margin: "var(--space-4) 0 0" }}>
          <span className="t-label etiqueta etiqueta-aviso">{informe.aviso}</span>
        </p>

        {!editable && (
          <p style={{ margin: "var(--space-2) 0 0" }}>
            <span className="t-label etiqueta">
              Ciclo cerrado · se consulta, no se califica
            </span>
          </p>
        )}
      </header>

      <section className="superficie">
        <div
          style={{
            padding: "var(--space-4)",
            borderBottom: "1px solid var(--color-border)",
          }}
        >
          <h2 className="t-h2" style={{ margin: 0 }}>
            Municipios del ciclo
          </h2>
          <p className="t-meta" style={{ margin: "var(--space-1) 0 0" }}>
            Ordenados por score. Se pide calificar los{" "}
            {informe.calificacion.pedida_hasta_puesto} primeros; el resto es
            opcional y se cuenta aparte.
          </p>
        </div>

        {informe.municipios.map((m, i) => (
          <FilaMunicipio key={m.divipola} m={m} alterna={i % 2 === 1} />
        ))}
      </section>

      <p className="t-meta prosa" style={{ marginTop: "var(--space-6)" }}>
        El score va de 0 a 1 y es <strong>ordinal dentro de su corrida</strong>:
        no es una nota sobre 100 y no es comparable entre ciclos. Corrida de
        scoring {informe.corridas.scoring} · corrida de agentes{" "}
        {informe.corridas.agentes}.
      </p>
    </main>
  );
}
