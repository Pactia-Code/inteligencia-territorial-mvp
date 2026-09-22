/**
 * VISTA 2 — Municipios priorizados (CA-M9.8 a CA-M9.12).
 *
 * Tabla de densidad alta. Los filtros y el orden viajan **en la URL** igual que
 * el municipio abierto en la vista de ciclo: se enlazan, se comparten y no
 * hacen falta ni estado de cliente ni JavaScript.
 */
import { historialDe, tablero, type FilaTablero } from "@/lib/tablero";
import { identidadActual } from "@/lib/sesion";
import { CambiarEstado } from "./CambiarEstado";

export const dynamic = "force-dynamic";

const ESTADOS = ["priorizado", "en_revision", "en_estructuracion", "descartado"];

const ETIQUETA: Record<string, string> = {
  priorizado: "priorizado",
  en_revision: "en revisión",
  en_estructuracion: "en estructuración",
  descartado: "descartado",
};

/** El color acompaña, nunca informa solo: cada estado lleva su texto (§1.4). */
const CLASE: Record<string, string> = {
  priorizado: "etiqueta",
  en_revision: "etiqueta etiqueta-aviso",
  en_estructuracion: "etiqueta etiqueta-positiva",
  descartado: "etiqueta etiqueta-critica",
};

function fecha(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function Enlace({
  activo,
  href,
  children,
}: {
  activo: boolean;
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      className="t-meta"
      style={{
        padding: "var(--space-1) var(--space-2)",
        borderRadius: "var(--radio-control)",
        textDecoration: "none",
        background: activo ? "var(--color-navy-700)" : "var(--color-surface)",
        color: activo ? "#fff" : "var(--color-navy-500)",
        border: "1px solid var(--color-border)",
      }}
    >
      {children}
    </a>
  );
}

export default async function Priorizados({
  searchParams,
}: {
  searchParams: Promise<{
    estado?: string;
    ciclo?: string;
    depto?: string;
    orden?: string;
    abierto?: string;
  }>;
}) {
  const q = await searchParams;
  const yo = await identidadActual();
  let filas = await tablero();

  const ciclos = [...new Set(filas.flatMap((f) => f.ciclos))].sort();
  const deptos = [...new Set(filas.map((f) => f.departamento))].sort();

  // CA-M9.12: filtrar por estado, ciclo y departamento.
  if (q.estado) filas = filas.filter((f) => f.estado === q.estado);
  if (q.ciclo) filas = filas.filter((f) => f.ciclos.includes(Number(q.ciclo)));
  if (q.depto) filas = filas.filter((f) => f.departamento === q.depto);

  // CA-M9.12: ordenar por score o por fecha del ultimo cambio.
  const orden = q.orden === "fecha" ? "fecha" : "score";
  filas.sort((a, b) =>
    orden === "fecha"
      ? (b.fecha_cambio ?? "").localeCompare(a.fecha_cambio ?? "")
      : b.score - a.score,
  );

  const conFiltro = (clave: string, valor: string | null) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(q)) if (v && k !== "abierto") p.set(k, v);
    if (valor === null) p.delete(clave);
    else p.set(clave, valor);
    return `/priorizados?${p.toString()}`;
  };

  const abierta: FilaTablero | undefined = filas.find(
    (f) => f.divipola === q.abierto,
  );
  const historial = abierta ? await historialDe(abierta.divipola) : [];

  return (
    <main style={{ padding: "var(--space-6)", maxWidth: 1200, margin: "0 auto" }}>
      <h1 className="t-h1" style={{ margin: "0 0 var(--space-2)" }}>
        Municipios priorizados
      </h1>
      <p className="t-meta prosa" style={{ margin: "0 0 var(--space-4)" }}>
        Todo municipio que entra al top 3 de un informe publicado aparece aquí
        con estado <strong>priorizado</strong>, sin alta manual. Cada cambio
        queda como historial: el estado vigente es el último.
      </p>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "var(--space-2)",
          alignItems: "center",
          marginBottom: "var(--space-4)",
        }}
      >
        <span className="t-label">estado</span>
        <Enlace activo={!q.estado} href={conFiltro("estado", null)}>
          todos
        </Enlace>
        {ESTADOS.map((e) => (
          <Enlace key={e} activo={q.estado === e} href={conFiltro("estado", e)}>
            {ETIQUETA[e]}
          </Enlace>
        ))}

        <span className="t-label" style={{ marginLeft: "var(--space-4)" }}>
          ciclo
        </span>
        <Enlace activo={!q.ciclo} href={conFiltro("ciclo", null)}>
          todos
        </Enlace>
        {ciclos.map((c) => (
          <Enlace key={c} activo={q.ciclo === String(c)} href={conFiltro("ciclo", String(c))}>
            {c}
          </Enlace>
        ))}

        <span className="t-label" style={{ marginLeft: "var(--space-4)" }}>
          departamento
        </span>
        <Enlace activo={!q.depto} href={conFiltro("depto", null)}>
          todos
        </Enlace>
        {deptos.map((d) => (
          <Enlace key={d} activo={q.depto === d} href={conFiltro("depto", d)}>
            {d}
          </Enlace>
        ))}

        <span className="t-label" style={{ marginLeft: "auto" }}>
          orden
        </span>
        <Enlace activo={orden === "score"} href={conFiltro("orden", "score")}>
          score
        </Enlace>
        <Enlace activo={orden === "fecha"} href={conFiltro("orden", "fecha")}>
          último cambio
        </Enlace>
      </div>

      {!filas.length ? (
        <div className="superficie" style={{ padding: "var(--space-8)" }}>
          <p className="t-body" style={{ margin: 0 }}>
            Ningún municipio coincide con estos filtros.
          </p>
          <p style={{ margin: "var(--space-3) 0 0" }}>
            <a href="/priorizados">Quitar los filtros</a>
          </p>
        </div>
      ) : (
        <section className="superficie">
          <div
            className="t-label"
            style={{
              display: "grid",
              gridTemplateColumns: "1.6fr .7fr 1fr .9fr 1fr auto",
              gap: "var(--space-3)",
              padding: "var(--space-3) var(--space-4)",
              borderBottom: "1px solid var(--color-border)",
              color: "var(--color-ink-muted)",
            }}
          >
            <span>municipio</span>
            <span>score</span>
            <span>ciclos</span>
            <span>estado</span>
            <span>último cambio</span>
            <span />
          </div>

          {filas.map((f, i) => (
            <div key={f.divipola}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1.6fr .7fr 1fr .9fr 1fr auto",
                  gap: "var(--space-3)",
                  alignItems: "center",
                  padding: "var(--space-3) var(--space-4)",
                  borderTop: i ? "1px solid var(--color-border)" : "none",
                  background:
                    f.divipola === q.abierto
                      ? "var(--color-navy-050)"
                      : i % 2
                        ? "var(--color-navy-100)"
                        : "transparent",
                }}
              >
                <div>
                  <span className="t-h3">{f.nombre}</span>
                  <div className="t-meta">
                    {f.departamento} · {f.divipola}
                  </div>
                </div>
                <span className="t-data">{f.score.toFixed(4)}</span>
                {/* CA-M9.11: en que ciclos y en que puesto. Distingue una senal
                    persistente de una puntual. */}
                <span className="t-meta">
                  {f.ciclos
                    .map((c) => `c${c}: puesto ${f.puestos[c]}`)
                    .join(" · ")}
                </span>
                <span className={`t-label ${CLASE[f.estado]}`}>
                  {ETIQUETA[f.estado]}
                </span>
                <span className="t-meta">
                  {fecha(f.fecha_cambio)}
                  {f.usuario && <> · {f.usuario}</>}
                </span>
                <a
                  href={
                    f.divipola === q.abierto
                      ? conFiltro("estado", q.estado ?? null)
                      : `${conFiltro("estado", q.estado ?? null)}&abierto=${f.divipola}`
                  }
                  className="t-meta"
                >
                  {f.divipola === q.abierto ? "cerrar" : "cambiar estado"}
                </a>
              </div>

              {f.divipola === q.abierto && (
                <div
                  style={{
                    padding: "var(--space-4)",
                    background: "var(--color-navy-050)",
                    borderTop: "1px solid var(--color-border)",
                  }}
                >
                  <CambiarEstado
                    divipola={f.divipola}
                    idCiclo={f.ciclos[f.ciclos.length - 1]}
                    estadoActual={f.estado}
                    puede={Boolean(yo)}
                  />

                  <h3 className="t-h3" style={{ margin: "var(--space-6) 0 var(--space-2)" }}>
                    Historial
                  </h3>
                  {historial.length ? (
                    <ol style={{ margin: 0, paddingLeft: "var(--space-4)" }}>
                      {historial.map((h) => (
                        <li key={h.id} style={{ marginBottom: "var(--space-2)" }}>
                          <span className={`t-label ${CLASE[h.estado]}`}>
                            {ETIQUETA[h.estado]}
                          </span>{" "}
                          <span className="t-meta">
                            {fecha(h.fecha_cambio)}
                            {h.usuario && <> · {h.usuario}</>}
                            {h.gerencia && <> ({h.gerencia})</>}
                          </span>
                          {h.nota && (
                            <p className="t-body prosa" style={{ margin: "var(--space-1) 0 0" }}>
                              {h.nota}
                            </p>
                          )}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="t-meta" style={{ margin: 0 }}>
                      Sin cambios todavía: entró al tablero como{" "}
                      <strong>priorizado</strong> al publicarse el informe del
                      ciclo {f.ciclos[f.ciclos.length - 1]}.
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
