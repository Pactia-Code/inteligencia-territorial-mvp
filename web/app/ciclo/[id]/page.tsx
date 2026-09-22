/**
 * VISTA 1 — Ciclo actual. Es donde se miden H1 y H2 (design system §2).
 *
 * Todo se resuelve en el servidor. **El municipio seleccionado va en la URL**
 * (`?m=25286`) y no en estado de cliente: se puede enlazar, se puede volver
 * atras, y el payload de 586 KB nunca cruza el cable — cada peticion serializa
 * solo el municipio abierto.
 *
 * El detalle es un **despliegue lateral, no una ruta** (design system §3), asi
 * que CA-M9.3 sigue en tres vistas.
 */
import { notFound } from "next/navigation";
import {
  calificacionesDeLaGerencia,
  calificacionesDelUsuario,
  cicloEsEditable,
  informeDelCiclo,
} from "@/lib/consultas";
import { identidadActual } from "@/lib/sesion";
import type { InsightPublicado, MunicipioDelInforme } from "@/lib/tipos";
import { Identificarse } from "./Identificarse";
import { Panel } from "./Panel";

export const dynamic = "force-dynamic";

function fecha(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/**
 * La linea de fuentes. Es lo que sustituye a la exclusion por umbral (P1), y su
 * posicion **y su peso** son la decision M6-orden: al tamano del nombre, en
 * tinta plena, y **la ausencia en negrita** porque lo que falta informa mas que
 * lo que hay. Pintada en gris pequenio se leia como una nota tecnica.
 */
function LineaDeFuentes({ resumen }: { resumen: string }) {
  const corte = resumen.indexOf(", sin ");
  const hay = corte === -1 ? resumen : resumen.slice(0, corte);
  const falta = corte === -1 ? null : resumen.slice(corte + 2);
  return (
    <span style={{ fontSize: 14, lineHeight: 1.4, color: "var(--color-ink)" }}>
      {hay}
      {falta && (
        <>
          {", "}
          <strong style={{ fontWeight: 600 }}>{falta}</strong>
        </>
      )}
    </span>
  );
}

function Fila({
  m,
  informe,
  seleccionado,
  calificados,
}: {
  m: MunicipioDelInforme;
  informe: number;
  seleccionado: boolean;
  calificados: number;
}) {
  const pedidos = m.insights_pedidos.length;
  return (
    <a
      href={`/ciclo/${informe}?m=${m.divipola}`}
      style={{
        display: "grid",
        gridTemplateColumns: "auto 1fr auto",
        gap: "var(--space-4)",
        alignItems: "start",
        padding: "var(--space-4)",
        borderTop: "1px solid var(--color-border)",
        borderLeft: seleccionado
          ? "3px solid var(--color-navy-700)"
          : "3px solid transparent",
        background: seleccionado
          ? "var(--color-navy-050)"
          : m.puesto % 2 === 0
            ? "var(--color-navy-100)"
            : "transparent",
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <span
        className="t-data"
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          minWidth: 28,
          height: 28,
          background: "var(--color-navy-700)",
          color: "#fff",
          borderRadius: "var(--radio-tarjeta)",
        }}
      >
        {m.puesto}
      </span>

      <div style={{ minWidth: 0 }}>
        <span className="t-h3">{m.nombre}</span>
        <span className="t-meta" style={{ marginLeft: "var(--space-2)" }}>
          {m.departamento} · {m.divipola}
        </span>
        <div style={{ marginTop: "var(--space-2)" }}>
          <LineaDeFuentes resumen={m.fuentes.resumen} />
        </div>
        {m.justificacion && (
          <p className="t-body prosa" style={{ margin: "var(--space-2) 0 0" }}>
            {m.justificacion}
          </p>
        )}
      </div>

      <div style={{ textAlign: "right", whiteSpace: "nowrap" }}>
        <div className="t-data">{m.score.toFixed(4)}</div>
        {/*
          Contador **solo en los pedidos** (M9-carga). Un «0 de 5» repetido en
          siete filas se leeria como tarea pendiente, y no lo es: convertiria lo
          opcional en una lista de deberes sin hacer, que es justo lo que puede
          hundir H2 por fatiga.
        */}
        {m.calificable ? (
          <div style={{ marginTop: "var(--space-2)" }}>
            <span
              className="t-label"
              style={{
                display: "inline-block",
                padding: "var(--space-1) var(--space-2)",
                background: "var(--color-navy-700)",
                color: "#fff",
                borderRadius: "var(--radio-tarjeta)",
              }}
            >
              se pide
            </span>
            <div className="t-meta" style={{ marginTop: "var(--space-1)" }}>
              {calificados} de {pedidos} calificados
            </div>
          </div>
        ) : (
          // **Boton, no texto apagado.** Sin un control visible parece que no
          // hay nada que pulsar y la fila clicable no se descubre sola. Es un
          // `span` y no un `<button>` porque va dentro del enlace de la fila:
          // anidar dos elementos interactivos seria HTML invalido.
          <div style={{ marginTop: "var(--space-2)" }}>
            <span
              className="t-h3"
              style={{
                display: "inline-block",
                padding: "var(--space-2) var(--space-3)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radio-control)",
                background: "var(--color-surface-alt)",
                color: "var(--color-ink-muted)",
                fontWeight: 400,
              }}
            >
              Ver detalle
            </span>
          </div>
        )}
      </div>
    </a>
  );
}

export default async function VistaCiclo({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ m?: string }>;
}) {
  const { id } = await params;
  const { m: divipolaSel } = await searchParams;
  const idCiclo = Number(id);
  if (!Number.isInteger(idCiclo)) notFound();

  const informe = await informeDelCiclo(idCiclo);
  if (!informe) notFound();

  const editable = await cicloEsEditable(idCiclo);
  const yo = await identidadActual();
  const misCalificaciones = yo
    ? await calificacionesDeLaGerencia(idCiclo, yo.id_gerencia)
    : {};
  // A **su nombre**, no a nombre de su gerencia: con dos personas en una misma
  // gerencia las dos listas dejan de coincidir (F0.3).
  const aMiNombre = yo ? await calificacionesDelUsuario(idCiclo, yo.id) : [];

  const abierto: MunicipioDelInforme | null =
    informe.municipios.find((x) => x.divipola === divipolaSel) ?? null;

  const cuantosCalificados = (mun: MunicipioDelInforme) =>
    mun.insights_pedidos.filter((i) => misCalificaciones[i]).length;

  const pedidosDe = (mun: MunicipioDelInforme): InsightPublicado[] =>
    mun.insights.filter((i) => mun.insights_pedidos.includes(i.id));

  const faltaProsa = informe.municipios.every((x) => !x.justificacion);

  /** Donde vive cada insight calificado, para poder nombrarlo. */
  const ubicacion = new Map<number, { municipio: string; categoria: string }>();
  for (const mun of informe.municipios) {
    for (const ins of mun.insights) {
      ubicacion.set(ins.id, { municipio: mun.nombre, categoria: ins.categoria });
    }
  }

  return (
    <main style={{ padding: "var(--space-6)" }}>
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          flexWrap: "wrap",
          gap: "var(--space-4)",
          marginBottom: "var(--space-4)",
        }}
      >
        <h1 className="t-h1" style={{ margin: 0 }}>
          Informe del ciclo
        </h1>
        <span className="t-meta">
          {fecha(informe.ventana.desde)} – {fecha(informe.ventana.hasta)}
        </span>
        <span className="t-meta">
          {informe.calificacion.mostrados} municipios mostrados
        </span>
        {!editable && (
          <span className="t-label etiqueta">Ciclo cerrado · no se califica</span>
        )}
        {/*
          CA-M6.5 y CA-M9.17 piden el texto completo; se muestra el corto por
          decision de producto (pendiente `M6-aviso`). El largo sigue en el
          payload: `informe.aviso`.
        */}
        <span className="t-label etiqueta etiqueta-aviso" style={{ marginLeft: "auto" }}>
          ⚠ {informe.aviso_corto}
        </span>
      </header>

      {faltaProsa && (
        <p className="t-meta prosa" style={{ margin: "0 0 var(--space-4)" }}>
          Este informe aún no trae justificación redactada por municipio: la
          escribe el Sintetizador, que todavía no está construido. Las cifras,
          las fuentes y la evidencia sí están completas.
        </p>
      )}

      {/*
        Lo que figura **a nombre de quien mira**. Es la contrapartida visible de
        `calificacion.id_usuario`: si la atribucion es declarativa (R-A2, H-012
        abierto), lo menos que puede hacer el sistema es ensenarle a cada quien
        lo que consta como suyo, para que un error se vea el mismo dia y no al
        analizar H1. No muestra nada de nadie mas (CA-M7.2).
      */}
      {yo && (
        <details
          className="superficie"
          style={{ padding: "var(--space-4)", marginBottom: "var(--space-4)" }}
        >
          <summary className="t-h3" style={{ cursor: "pointer" }}>
            {aMiNombre.length === 0
              ? "Aún no figura ninguna calificación a tu nombre en este ciclo"
              : `${aMiNombre.length} ${
                  aMiNombre.length === 1 ? "calificación figura" : "calificaciones figuran"
                } a tu nombre en este ciclo`}
          </summary>
          <p className="t-meta" style={{ margin: "var(--space-2) 0 0" }}>
            Se identifican por el correo con el que entraste ({yo.correo}), y
            cuentan para tu gerencia: {yo.id_gerencia}.
          </p>
          {aMiNombre.length > 0 && (
            <ul className="t-body" style={{ margin: "var(--space-2) 0 0", paddingLeft: "var(--space-5)" }}>
              {aMiNombre.map((c) => {
                const donde = ubicacion.get(c.id_insight);
                return (
                  <li key={c.id_insight}>
                    <span className="t-data">{c.valor}</span>
                    {" · "}
                    {donde ? `${donde.municipio} · ${donde.categoria}` : "insight"}
                    {" · "}
                    <span className="t-meta">#{c.id_insight}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </details>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
          gap: "var(--space-6)",
          alignItems: "start",
        }}
      >
        <section className="superficie">
          {informe.municipios.map((x) => (
            <Fila
              key={x.divipola}
              m={x}
              informe={informe.ciclo}
              seleccionado={x.divipola === divipolaSel}
              calificados={cuantosCalificados(x)}
            />
          ))}
        </section>

        <aside style={{ position: "sticky", top: "var(--space-4)" }}>
          {abierto ? (
            <>
              {!yo && abierto.calificable && editable && <Identificarse />}
              <Panel
                m={abierto}
                informe={informe}
                pedidos={pedidosDe(abierto)}
                calificaciones={misCalificaciones}
                puedeCalificar={Boolean(yo) && editable}
              />
            </>
          ) : (
            <div className="superficie" style={{ padding: "var(--space-8)" }}>
              <p className="t-body" style={{ margin: 0 }}>
                Elige un municipio de la lista para ver su evidencia, su contexto
                y de qué está hecho su score.
              </p>
              <p className="t-meta" style={{ margin: "var(--space-3) 0 0" }}>
                Se pide calificar {informe.calificacion.pedidas_por_municipio}{" "}
                insights en cada uno de los{" "}
                {informe.calificacion.pedida_hasta_puesto} primeros. Los demás
                quedan abiertos y se cuentan aparte.
              </p>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}
