/**
 * VISTA 1 — Ciclo actual. Es donde se miden H1 y H2 (design system §2).
 *
 * Componente de servidor: lee Neon aqui y el navegador nunca ve la cadena de
 * conexion. **Y nunca cruza el payload entero**: son 576 KB con 933
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

/**
 * La linea de fuentes. Es lo que sustituye a la exclusion por umbral (P1), y
 * su posicion **y su peso** son la decision M6-orden.
 *
 * Se pinto primero en `t-meta` —12px gris— y en pantalla quedaba idéntica al
 * DIVIPOLA y a los metadatos: tres lineas grises seguidas que el ojo salta
 * entero. La posicion era correcta y **el peso no**, asi que M6-orden no se
 * cumplia aunque el elemento estuviera donde toca.
 *
 * Ahora va al tamano del nombre, en tinta plena, y **la ausencia en negrita**:
 * lo que falta informa mas que lo que hay, asi que es lo que tiene que saltar.
 * No se usa color para distinguirla — §1.4 dice que el color nunca porta
 * informacion por si solo, y anadir un color con significado propio seria
 * inventar semantica que la paleta no tiene.
 */
function LineaDeFuentes({ resumen }: { resumen: string }) {
  const corte = resumen.indexOf(", sin ");
  const hay = corte === -1 ? resumen : resumen.slice(0, corte);
  const falta = corte === -1 ? null : resumen.slice(corte + 2);
  return (
    <p
      style={{
        margin: "var(--space-2) 0 0",
        fontSize: 14,
        lineHeight: 1.4,
        color: "var(--color-ink)",
      }}
    >
      {hay}
      {falta && (
        <>
          {", "}
          <strong style={{ fontWeight: 600 }}>{falta}</strong>
        </>
      )}
    </p>
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
          <span
            className="t-meta"
            style={{ fontWeight: 400, marginLeft: "var(--space-2)" }}
          >
            {m.departamento} · {m.divipola}
          </span>
        </h3>

        <LineaDeFuentes resumen={m.fuentes.resumen} />

        {/* El hueco de la justificacion **no se repite por fila**: diez veces la
            misma frase se lee como un error del sistema y no como un estado
            esperado, y ademas competia con la linea de fuentes. Se dice una vez
            en el encabezado. */}
        {m.justificacion && (
          <p className="t-body prosa" style={{ margin: "var(--space-3) 0 0" }}>
            {m.justificacion}
          </p>
        )}
      </div>

      <div style={{ textAlign: "right", whiteSpace: "nowrap" }}>
        <div className="t-data">{m.score.toFixed(4)}</div>
        {/* Lo pedido resalta; lo opcional casi calla. Antes los dos eran
            pastillas y la pedida usaba el ambar de «contenido no validado»,
            que mezclaba una advertencia de procedencia con una peticion de
            accion. El ambar se reserva para la marca del informe. */}
        {m.calificable ? (
          <span
            className="t-label"
            style={{
              display: "inline-block",
              marginTop: "var(--space-2)",
              padding: "var(--space-1) var(--space-2)",
              background: "var(--color-navy-700)",
              color: "#fff",
              borderRadius: "var(--radio-tarjeta)",
            }}
          >
            Se pide calificar
          </span>
        ) : (
          <span
            className="t-meta"
            style={{ display: "inline-block", marginTop: "var(--space-2)" }}
          >
            opcional
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

  const faltaProsa = informe.municipios.every((m) => !m.justificacion);

  return (
    <main
      style={{
        maxWidth: 960,
        margin: "0 auto",
        padding: "var(--space-12) var(--space-6)",
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
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "var(--space-2)",
            marginTop: "var(--space-4)",
          }}
        >
          <span className="t-label etiqueta etiqueta-aviso">{informe.aviso}</span>
          {!editable && (
            <span className="t-label etiqueta">
              Ciclo cerrado · se consulta, no se califica
            </span>
          )}
        </div>

        {/* Una vez, no diez. */}
        {faltaProsa && (
          <p
            className="t-meta prosa"
            style={{ margin: "var(--space-4) 0 0" }}
          >
            Este informe aún no trae justificación redactada por municipio: la
            escribe el Sintetizador, que todavía no está construido. Las cifras,
            las fuentes y la evidencia sí están completas.
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
            <strong>{informe.calificacion.pedida_hasta_puesto} primeros</strong>;
            los demás quedan abiertos y se cuentan aparte.
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
