/**
 * Detalle del municipio: contexto, evidencia, score explicable y trazabilidad.
 *
 * Componente de servidor. Los controles de calificacion viven en `Calificar`,
 * que si es de cliente: necesita `useActionState` para enseniar el fallo en la
 * fila (F0.7). Siguen siendo un `<form>` con cinco botones de envio que
 * funciona sin JavaScript, asi que «clic 1 = registro» (CA-M7.6) se mantiene.
 */
import { describirComposicion } from "@/lib/seleccion";
import type { Informe, InsightPublicado, MunicipioDelInforme } from "@/lib/tipos";
import { Calificar } from "./Calificar";

function numero(valor: number, unidad: string): string {
  if (unidad.startsWith("%")) return `${valor.toFixed(1).replace(".", ",")} %`;
  if (unidad === "personas" || unidad === "predios") {
    return valor.toLocaleString("es-CO", { maximumFractionDigits: 0 });
  }
  return `$${valor.toLocaleString("es-CO", { maximumFractionDigits: 1 })} M`;
}

function Bloque({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section style={{ marginTop: "var(--space-6)" }}>
      <h3 className="t-h2" style={{ margin: "0 0 var(--space-3)" }}>
        {titulo}
      </h3>
      {children}
    </section>
  );
}

/** La anatomia de un dato del design system §3.1: valor, etiqueta, procedencia. */
function Contexto({ m }: { m: MunicipioDelInforme }) {
  if (!m.contexto.length) return null;
  return (
    <Bloque titulo="Contexto estructural">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "var(--space-3)",
        }}
      >
        {m.contexto.map((c) => (
          <div
            key={c.clave}
            className="superficie"
            style={{ padding: "var(--space-3)" }}
          >
            <div className="t-data-lg" style={{ color: "var(--color-navy-700)" }}>
              {numero(c.valor, c.unidad)}
            </div>
            <div className="t-body" style={{ marginTop: "var(--space-1)" }}>
              {c.etiqueta}
            </div>
            {/* El anio es obligatorio y no es decorativo: un informe de 2026 con
                deficit del censo 2018 se leeria como dato de hoy. */}
            <div className="t-meta" style={{ marginTop: "var(--space-1)" }}>
              {c.fuente} {c.anio}
            </div>
          </div>
        ))}
      </div>
    </Bloque>
  );
}

function Evidencia({ i }: { i: InsightPublicado }) {
  const e = i.evidencia[0];
  if (!e) return null;
  return (
    <div
      style={{
        background: "var(--color-navy-050)",
        borderLeft: "2px solid var(--color-navy-300)",
        padding: "var(--space-3)",
        marginTop: "var(--space-2)",
      }}
    >
      {e.cita_textual && (
        <p className="t-body prosa" style={{ margin: 0, fontStyle: "italic" }}>
          «{e.cita_textual}»
        </p>
      )}
      <p className="t-meta" style={{ margin: "var(--space-2) 0 0" }}>
        {e.fuente ?? "—"} · {e.fecha ?? "sin fecha"}
        {e.url && (
          <>
            {" · "}
            <a href={e.url} target="_blank" rel="noreferrer">
              ver en la fuente ↗
            </a>
          </>
        )}
      </p>
    </div>
  );
}

export function Panel({
  m,
  informe,
  pedidos,
  calificaciones,
  puedeCalificar,
}: {
  m: MunicipioDelInforme;
  informe: Informe;
  pedidos: InsightPublicado[];
  calificaciones: Record<number, { valor: number; comentario: string | null }>;
  puedeCalificar: boolean;
}) {
  const maximo = Math.max(...m.aportes_por_fuente.map((f) => f.aporte), 0.0001);

  return (
    <div className="superficie" style={{ padding: "var(--space-6)" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: "var(--space-4)",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 className="t-display" style={{ margin: 0 }}>
            {m.nombre}
          </h2>
          <p className="t-meta" style={{ margin: "var(--space-1) 0 0" }}>
            {m.departamento} · {m.divipola} · puesto {m.puesto}
          </p>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="t-meta">Score del ciclo (0 – 1)</div>
          <div className="t-data-lg" style={{ color: "var(--color-navy-700)" }}>
            {m.score.toFixed(4)}
          </div>
          <div className="t-meta">modelo {informe.corridas.version_scoring}</div>
        </div>
      </header>

      <Contexto m={m} />

      <Bloque titulo="Score explicable">
        {m.aportes_por_fuente.map((f) => (
          <div
            key={f.fuente}
            style={{
              display: "grid",
              gridTemplateColumns: "180px 1fr auto",
              gap: "var(--space-3)",
              alignItems: "center",
              marginBottom: "var(--space-2)",
            }}
          >
            <span className="t-body">{f.etiqueta}</span>
            <span
              style={{
                height: 10,
                background: "var(--color-border)",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <span
                style={{
                  display: "block",
                  height: "100%",
                  width: `${Math.round((f.aporte / maximo) * 100)}%`,
                  background: "var(--color-navy-700)",
                }}
              />
            </span>
            {/* Los factores sin datos se muestran, no se omiten: la ausencia
                informa, igual que en la linea de fuentes. */}
            <span className={f.sin_datos ? "t-meta" : "t-data"}>
              {f.sin_datos ? "(aún no hay)" : `+${f.aporte.toFixed(2)}`}
            </span>
          </div>
        ))}
      </Bloque>

      <Bloque
        titulo={
          m.calificable
            ? `Se pide calificar ${pedidos.length} insights`
            : "Insights del municipio"
        }
      >
        {m.calificable ? (
          <p className="t-meta prosa" style={{ margin: "0 0 var(--space-4)" }}>
            De los {m.insights.length} insights del municipio se piden estos{" "}
            {pedidos.length}
            {/* Del payload, no de un texto fijo: con la regla de relleno cada
                municipio recibe su propia mezcla, y escribirla a mano mentiría
                justo donde importa (M9-sel, H-015). */}
            {describirComposicion(m.composicion_pedida) && (
              <>
                {": "}
                <strong>{describirComposicion(m.composicion_pedida)}</strong>
              </>
            )}
            . Se priorizan los correlacionados —lo que ninguna fuente sola
            produce— y se completa con contratación y prensa; si un tipo no
            alcanza, entra lo que haya. Los elige código determinista con una
            semilla congelada, así que todas las gerencias reciben exactamente
            los mismos. El resto es opcional.
          </p>
        ) : (
          <p className="t-meta prosa" style={{ margin: "0 0 var(--space-4)" }}>
            En este municipio la calificación es opcional: {m.insights.length}{" "}
            insights disponibles.
          </p>
        )}

        {(m.calificable ? pedidos : m.insights.slice(0, 5)).map((i) => (
          <article
            key={i.id}
            style={{
              borderTop: "1px solid var(--color-border)",
              paddingTop: "var(--space-3)",
              marginTop: "var(--space-3)",
            }}
          >
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              <span className="t-label etiqueta">{i.categoria}</span>
              <span className="t-label etiqueta">{i.trayecto}</span>
              <span className="t-meta">
                señal {i.ids_senal.join(", ") || "—"}
              </span>
            </div>
            <p className="t-body prosa" style={{ margin: "var(--space-2) 0 0" }}>
              {i.resumen}
            </p>
            {i.implicacion_inmobiliaria && (
              <p className="t-body prosa" style={{ margin: "var(--space-2) 0 0" }}>
                <strong>Implicación:</strong> {i.implicacion_inmobiliaria}
              </p>
            )}
            <Evidencia i={i} />
            <Calificar
              i={i}
              valor={calificaciones[i.id]?.valor}
              puede={puedeCalificar}
            />
          </article>
        ))}
      </Bloque>
    </div>
  );
}
