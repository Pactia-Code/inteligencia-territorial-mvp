"use client";

/**
 * Los cinco botones de calificacion, y lo que pasa cuando no se guarda.
 *
 * Estaba dentro de `Panel.tsx`, que es un componente de servidor. Se saca aqui
 * porque `useActionState` necesita cliente, y **eso es lo que hace visible el
 * fallo** (F0.7, H-045): antes la accion no devolvia nada, asi que un error de
 * escritura se veia exactamente igual que un exito.
 *
 * **Sigue funcionando sin JavaScript.** `useActionState` devuelve un
 * `formAction` que el `<form>` envia igual con JS desactivado, asi que «clic 1 =
 * registro» (CA-M7.6) se mantiene. Lo unico que se pierde sin JS es el mensaje
 * en la fila, no el registro.
 *
 * **La seleccion se conserva al fallar.** El resultado trae el valor pulsado, y
 * el boton se queda marcado aunque no se haya guardado: si se perdiera, habria
 * que recordar que se habia elegido, y ahi es donde se abandona.
 */
import { useActionState } from "react";
import {
  registrarCalificacion,
  registrarComentario,
  type ResultadoCalificacion,
  type ResultadoComentario,
} from "@/app/acciones";
import { mensajeDeCalificacion, seleccionVisible } from "@/lib/mensajes";
import type { InsightPublicado } from "@/lib/tipos";

const ESCALA = [1, 2, 3, 4, 5];

function Aviso({ texto }: { texto: string }) {
  return (
    <p
      className="t-body etiqueta etiqueta-critica"
      style={{ display: "block", margin: "var(--space-2) 0 0" }}
      role="status"
    >
      {texto}
    </p>
  );
}

export function Calificar({
  i,
  valor,
  puede,
}: {
  i: InsightPublicado;
  valor: number | undefined;
  puede: boolean;
}) {
  const [resultado, calificar, calificando] = useActionState<
    ResultadoCalificacion | null,
    FormData
  >(registrarCalificacion, null);
  const [comentario, comentar, comentando] = useActionState<
    ResultadoComentario | null,
    FormData
  >(registrarComentario, null);

  if (!puede) {
    return (
      <p className="t-meta" style={{ margin: "var(--space-2) 0 0" }}>
        Identifícate arriba para calificar este insight.
      </p>
    );
  }

  // Lo guardado manda; si la escritura fallo, se marca lo que se pulso para no
  // perder la seleccion de quien esta respondiendo. La regla vive en
  // `lib/mensajes.ts` para poder probarla sin montar el componente.
  const marcado = seleccionVisible(valor, resultado);
  const registrado = valor !== undefined || resultado?.ok === true;

  return (
    <div style={{ marginTop: "var(--space-3)" }}>
      <p className="t-meta" style={{ margin: "0 0 var(--space-2)" }}>
        ¿Qué tan relevante es para tu evaluación?
      </p>
      <form action={calificar} style={{ display: "flex", gap: "var(--space-1)" }}>
        <input type="hidden" name="id_insight" value={i.id} />
        {ESCALA.map((n) => (
          <button
            key={n}
            type="submit"
            name="valor"
            value={n}
            disabled={calificando}
            className="t-data"
            aria-label={`Calificar ${n} de 5`}
            aria-pressed={marcado === n}
            style={{
              minWidth: 44,
              minHeight: 44,
              border: "1px solid var(--color-navy-300)",
              borderRadius: "var(--radio-control)",
              background: marcado === n ? "var(--color-navy-700)" : "var(--color-surface)",
              color: marcado === n ? "#fff" : "var(--color-ink)",
              cursor: calificando ? "progress" : "pointer",
              fontFamily: "inherit",
            }}
          >
            {n}
          </button>
        ))}
      </form>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          maxWidth: 236,
          marginTop: "var(--space-1)",
        }}
      >
        <span className="t-meta">nada</span>
        <span className="t-meta">acción inmediata</span>
      </div>

      {resultado?.ok === false && (
        <Aviso texto={mensajeDeCalificacion(resultado.motivo)} />
      )}

      {/* La confirmacion no hace desaparecer la fila: hay que poder verificar
          que se respondio sin tener que recordarlo. */}
      {registrado && (
        <>
          <p style={{ margin: "var(--space-2) 0 0" }}>
            <span className="t-label etiqueta etiqueta-positiva">
              ✓ Calificación registrada
            </span>
          </p>
          {/* CA-M7.4: comentario libre y opcional, **despues** de registrar. */}
          <form action={comentar} style={{ marginTop: "var(--space-2)" }}>
            <input type="hidden" name="id_insight" value={i.id} />
            <textarea
              name="comentario"
              rows={2}
              placeholder="Comentario (opcional)"
              className="t-body"
              style={{
                width: "100%",
                padding: "var(--space-2)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radio-control)",
                fontFamily: "inherit",
                resize: "vertical",
              }}
            />
            <button
              type="submit"
              disabled={comentando}
              className="t-meta"
              style={{
                marginTop: "var(--space-1)",
                padding: "var(--space-1) var(--space-3)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radio-control)",
                background: "var(--color-surface)",
                cursor: comentando ? "progress" : "pointer",
                fontFamily: "inherit",
              }}
            >
              {comentando ? "Guardando…" : "Guardar comentario"}
            </button>
          </form>
          {comentario?.ok === false && (
            <Aviso texto={mensajeDeCalificacion(comentario.motivo)} />
          )}
          {comentario?.ok === true && (
            <p className="t-meta" style={{ margin: "var(--space-1) 0 0" }}>
              ✓ Comentario guardado
            </p>
          )}
        </>
      )}
    </div>
  );
}
