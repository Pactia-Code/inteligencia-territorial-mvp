"use client";

/**
 * Cambio de estado con **nota obligatoria** al descartar o estructurar
 * (CA-M9.9).
 *
 * La comprobacion vive en el servidor, no aqui: un `required` de HTML se salta
 * con cualquier cliente, y el historial sin el porque guarda que paso y no por
 * que. Este componente solo **muestra** el resultado.
 */
import { useActionState, useState } from "react";
import { cambiarEstado, type ResultadoSeguimiento } from "@/app/acciones";
import { EXIGEN_NOTA } from "@/lib/tablero";

const ESTADOS: { valor: string; etiqueta: string }[] = [
  { valor: "priorizado", etiqueta: "priorizado" },
  { valor: "en_revision", etiqueta: "en revisión" },
  { valor: "en_estructuracion", etiqueta: "en estructuración" },
  { valor: "descartado", etiqueta: "descartado" },
];

export function CambiarEstado({
  divipola,
  idCiclo,
  estadoActual,
  puede,
}: {
  divipola: string;
  idCiclo: number;
  estadoActual: string;
  puede: boolean;
}) {
  const [resultado, accion, pendiente] = useActionState<
    ResultadoSeguimiento | null,
    FormData
  >(cambiarEstado, null);
  const [estado, setEstado] = useState(estadoActual);
  const notaObligatoria = EXIGEN_NOTA.includes(estado);

  if (!puede) {
    return (
      <p className="t-meta" style={{ margin: 0 }}>
        Identifícate para cambiar el estado. Consultar el historial no lo
        requiere.
      </p>
    );
  }

  return (
    <form action={accion}>
      <input type="hidden" name="divipola" value={divipola} />
      <input type="hidden" name="id_ciclo" value={idCiclo} />

      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
        {ESTADOS.map((e) => (
          <label
            key={e.valor}
            className="t-body"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-1)",
              padding: "var(--space-2) var(--space-3)",
              border: `1px solid ${
                estado === e.valor ? "var(--color-navy-700)" : "var(--color-border)"
              }`,
              borderRadius: "var(--radio-control)",
              background:
                estado === e.valor ? "var(--color-navy-100)" : "var(--color-surface)",
              cursor: "pointer",
            }}
          >
            <input
              type="radio"
              name="estado"
              value={e.valor}
              checked={estado === e.valor}
              onChange={() => setEstado(e.valor)}
            />
            {e.etiqueta}
          </label>
        ))}
      </div>

      <div style={{ marginTop: "var(--space-3)" }}>
        <label className="t-meta" htmlFor={`nota-${divipola}`}>
          {notaObligatoria
            ? "Nota (obligatoria: este estado cierra o compromete)"
            : "Nota (opcional)"}
        </label>
        <textarea
          id={`nota-${divipola}`}
          name="nota"
          rows={2}
          className="t-body"
          style={{
            display: "block",
            width: "100%",
            marginTop: "var(--space-1)",
            padding: "var(--space-2)",
            border: `1px solid ${
              resultado?.ok === false && resultado.motivo === "falta_nota"
                ? "var(--color-critical)"
                : "var(--color-border)"
            }`,
            borderRadius: "var(--radio-control)",
            fontFamily: "inherit",
            resize: "vertical",
          }}
        />
      </div>

      <button
        type="submit"
        disabled={pendiente}
        className="t-h3"
        style={{
          marginTop: "var(--space-3)",
          padding: "var(--space-2) var(--space-4)",
          background: "var(--color-navy-700)",
          color: "#fff",
          border: "none",
          borderRadius: "var(--radio-control)",
          cursor: "pointer",
        }}
      >
        {pendiente ? "Guardando…" : "Registrar cambio"}
      </button>

      {resultado?.ok === false && resultado.motivo === "falta_nota" && (
        <p
          className="t-body etiqueta etiqueta-critica"
          style={{ display: "block", margin: "var(--space-3) 0 0" }}
        >
          Pasar a <strong>{resultado.estado.replace("_", " ")}</strong> necesita
          una nota. Es el estado que cierra o compromete: sin el porqué, el
          historial guarda qué pasó y no por qué.
        </p>
      )}
      {resultado?.ok === true && (
        <p
          className="t-label etiqueta etiqueta-positiva"
          style={{ display: "inline-block", margin: "var(--space-3) 0 0" }}
        >
          ✓ Cambio registrado
        </p>
      )}
    </form>
  );
}
