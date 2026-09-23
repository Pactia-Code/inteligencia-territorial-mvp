"use client";

/**
 * Identificacion por correo. **El sistema no envia nada**: el correo es el
 * identificador que la persona escribe para poder calificar.
 *
 * Se pide **una sola vez** y se recuerda en cookie; pedirlo en cada
 * calificacion rompe los <=2 clics de CA-M7.1.
 */
import { useActionState } from "react";
import { identificarse, type ResultadoIdentificacion } from "@/app/acciones";

export function Identificarse() {
  const [resultado, accion, pendiente] = useActionState<
    ResultadoIdentificacion | null,
    FormData
  >(identificarse, null);

  return (
    <div
      className="superficie"
      style={{ padding: "var(--space-4)", marginBottom: "var(--space-4)" }}
    >
      <p className="t-h3" style={{ margin: 0 }}>
        Para calificar, identifícate
      </p>
      <p className="t-meta" style={{ margin: "var(--space-1) 0 var(--space-3)" }}>
        Leer no requiere identificarse. El correo solo sirve para saber a qué
        gerencia atribuir la calificación.
      </p>

      <form action={accion} style={{ display: "flex", gap: "var(--space-2)" }}>
        <input
          name="correo"
          type="email"
          required
          placeholder="tu.correo@pactia.com"
          defaultValue={resultado?.ok === false ? resultado.correo : ""}
          className="t-body"
          style={{
            flex: 1,
            minWidth: 0,
            padding: "var(--space-2)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radio-control)",
            fontFamily: "inherit",
          }}
        />
        <button
          type="submit"
          disabled={pendiente}
          className="t-h3"
          style={{
            padding: "var(--space-2) var(--space-4)",
            background: "var(--color-navy-700)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radio-control)",
            cursor: "pointer",
          }}
        >
          {pendiente ? "Comprobando…" : "Continuar"}
        </button>
      </form>

      {/*
        **Nunca un error generico.** Una errata durante la ventana de
        calificacion se lleva por delante una respuesta de H2, y con siete
        gerencias cada una pesa el 14%. El mensaje dice que pasa y a quien
        escribir.
      */}
      {resultado?.ok === false && resultado.motivo === "sin_secreto" && (
        <p
          className="t-body etiqueta etiqueta-aviso"
          style={{ display: "block", margin: "var(--space-3) 0 0" }}
        >
          Este despliegue no tiene configurada la firma de identificación
          (COOKIE_SECRET), así que no puede identificar a nadie. Leer el informe
          sigue funcionando; avisa a quien te compartió el enlace.
        </p>
      )}

      {resultado?.ok === false && resultado.motivo === "no_autorizado" && (
        <p
          className="t-body etiqueta etiqueta-aviso"
          style={{ display: "block", margin: "var(--space-3) 0 0" }}
        >
          Este correo no está en la lista de gerencias autorizadas, así que no
          puede calificar — el informe sí se puede leer entero. Si crees que
          debería estar, escribe a quien te compartió el enlace.
        </p>
      )}
    </div>
  );
}
