/**
 * Detalle del municipio: contexto, evidencia, score explicable y trazabilidad.
 *
 * Componente de servidor. Los controles de calificacion viven en `Calificar`,
 * que si es de cliente: necesita `useActionState` para enseniar el fallo en la
 * fila (F0.7). Siguen siendo un `<form>` con cinco botones de envio que
 * funciona sin JavaScript, asi que «clic 1 = registro» (CA-M7.6) se mantiene.
 */
import { describirComposicion } from "@/lib/seleccion";
import type {
  Evidencia as EvidenciaPublicada,
  Informe,
  InsightPublicado,
  MunicipioDelInforme,
} from "@/lib/tipos";
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

/** Una cita, con su procedencia. Nivel 2 del design system §3.3. */
function Cita({ e }: { e: EvidenciaPublicada }) {
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

/**
 * Toda la evidencia de un insight: la primera a la vista, las demas a un clic.
 *
 * **Antes se pintaba solo `evidencia[0]`** (H-016), y eso escondia justo lo que
 * el sistema tiene de propio: el consolidado 1092 de Ibague cruza 12 citas —7
 * de SECOP y 5 de prensa— y en pantalla se veia una. Calificar un cruce viendo
 * una sola de sus doce fuentes es calificar otra cosa.
 *
 * El `<details>` funciona **sin JavaScript**, que es la misma razon por la que
 * los botones de calificar son un `<form>`: la pantalla tiene que servir aunque
 * el navegador no ejecute nada.
 */
function Evidencia({ i }: { i: InsightPublicado }) {
  const [primera, ...resto] = i.evidencia ?? [];
  if (!primera) return null;
  return (
    <>
      <Cita e={primera} />
      {resto.length > 0 && (
        <details style={{ marginTop: "var(--space-2)" }}>
          <summary className="t-meta" style={{ cursor: "pointer" }}>
            {resto.length === 1
              ? "Ver la otra evidencia"
              : `Ver las otras ${resto.length} evidencias`}
          </summary>
          {resto.map((e, n) => (
            <Cita key={`${i.id}-${n}`} e={e} />
          ))}
        </details>
      )}
    </>
  );
}

/** Un insight con su evidencia, y los controles si se puede calificar. */
function Ficha({
  i,
  valor,
  conCalificacion = false,
  puede = false,
}: {
  i: InsightPublicado;
  valor?: number;
  /** Sin controles, la ficha es solo lectura. No cambia quien puede calificar. */
  conCalificacion?: boolean;
  puede?: boolean;
}) {
  return (
    <article
      style={{
        borderTop: "1px solid var(--color-border)",
        paddingTop: "var(--space-3)",
        marginTop: "var(--space-3)",
      }}
    >
      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
        <span className="t-label etiqueta">{i.categoria}</span>
        <span className="t-label etiqueta">{i.trayecto}</span>
        <span className="t-meta">señal {i.ids_senal.join(", ") || "—"}</span>
        <span className="t-meta">
          {i.evidencia.length === 1
            ? "1 evidencia"
            : `${i.evidencia.length} evidencias`}
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
      {conCalificacion && <Calificar i={i} valor={valor} puede={puede} />}
    </article>
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

  // Lo pedido arriba y el resto debajo. **El conjunto de arriba es el mismo que
  // se pintaba antes**, para no mover qué insights llevan controles.
  const principales = m.calificable ? pedidos : m.insights.slice(0, 5);
  const arriba = new Set(principales.map((i) => i.id));
  const resto = m.insights.filter((i) => !arriba.has(i.id));
  const restoEvidencias = resto.reduce((n, i) => n + i.evidencia.length, 0);

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
            los mismos. <strong>El resto del municipio queda abajo para
            consulta</strong>: se califica solo lo pedido, para que H1 y H2
            comparen sobre la misma base.
          </p>
        ) : (
          <p className="t-meta prosa" style={{ margin: "0 0 var(--space-4)" }}>
            En este municipio <strong>no se pide calificación</strong>. Sus{" "}
            {m.insights.length} insights están aquí para consulta: los primeros
            abajo y los demás en la lista desplegable.
          </p>
        )}

        {principales.map((i) => (
          // Controles solo donde el informe pidió calificación: en los demás
          // municipios estos cinco son de consulta, como el resto. La misma
          // regla vive en el servidor (`lib/alcance.ts`), que es lo que la
          // hace regla y no apariencia.
          <Ficha
            key={i.id}
            i={i}
            valor={calificaciones[i.id]?.valor}
            conCalificacion={m.calificable}
            puede={puedeCalificar}
          />
        ))}

        {/*
          **El resto del municipio, que antes no se veía** (H-016). Funza tiene
          49 insights y la pantalla pintaba 5: el informe publicaba evidencia
          que nadie podía leer, y CA-M9.4 pide «los insights que lo sustentan».
          Va cerrado por defecto porque lo pedido es lo que hay que responder y
          una lista de 49 abierta lo enterraría; y va en `<details>`, que se
          abre **sin JavaScript**.

          Sin controles de calificación a propósito: **esto es presentación y no
          cambia quién puede calificar qué.** Los botones siguen exactamente en
          los mismos insights que antes.
        */}
        {resto.length > 0 && (
          <details style={{ marginTop: "var(--space-5)" }}>
            <summary className="t-h3" style={{ cursor: "pointer" }}>
              {resto.length === 1
                ? "Ver el otro insight del municipio"
                : `Ver los otros ${resto.length} insights del municipio`}
            </summary>
            <p className="t-meta prosa" style={{ margin: "var(--space-2) 0 0" }}>
              Con {restoEvidencias}{" "}
              {restoEvidencias === 1 ? "evidencia" : "evidencias"}. Son de
              consulta y no se califican.
            </p>
            {resto.map((i) => (
              <Ficha key={i.id} i={i} />
            ))}
          </details>
        )}
      </Bloque>
    </div>
  );
}
