"use client";

/**
 * El formulario de la pantalla de entrada.
 *
 * **El mensaje de fallo es el mismo pase lo que pase con el correo.** No dice
 * si existe, si esta desactivado o si nunca estuvo: decirlo convertiria esta
 * pantalla en un comprobador de quien trabaja aqui, y la lista de correos es
 * justo lo que no hace falta repartir. El detalle queda en el servidor.
 *
 * La unica excepcion es el despliegue sin `COOKIE_SECRET`, que no habla del
 * correo sino de la instalacion: ahi callar dejaria a alguien reintentando un
 * correo correcto contra un servidor que no puede emitir identidad.
 *
 * Funciona **sin JavaScript**: `useActionState` da un `formAction` que el
 * `<form>` envia igual. Lo que se pierde sin JS es el mensaje en pantalla, no
 * la entrada.
 */
import { useActionState } from "react";
import { entrar, type ResultadoIdentificacion } from "@/app/acciones";

export function Formulario({ destino }: { destino: string }) {
  const [resultado, accion, pendiente] = useActionState<
    ResultadoIdentificacion | null,
    FormData
  >(entrar, null);

  const fallo = resultado?.ok === false;
  const sinSecreto = fallo && resultado.motivo === "sin_secreto";
  const vacio = fallo && resultado.motivo === "vacio";

  return (
    <form action={accion} style={{ marginTop: "var(--space-6)" }}>
      <input type="hidden" name="destino" value={destino} />

      <label className="t-label" htmlFor="correo" style={{ display: "block" }}>
        Correo
      </label>
      <input
        id="correo"
        name="correo"
        type="email"
        autoComplete="email"
        autoFocus
        placeholder="nombre@pactia.com"
        defaultValue={fallo ? resultado.correo : ""}
        className="t-body"
        style={{
          display: "block",
          width: "100%",
          marginTop: "var(--space-1)",
          padding: "var(--space-3)",
          border: `1px solid ${fallo ? "var(--color-critical)" : "var(--color-border)"}`,
          borderRadius: "var(--radio-control)",
          fontFamily: "inherit",
          background: "var(--color-surface)",
        }}
      />

      <button
        type="submit"
        disabled={pendiente}
        className="t-h3"
        style={{
          width: "100%",
          marginTop: "var(--space-4)",
          padding: "var(--space-3) var(--space-4)",
          background: "var(--color-navy-700)",
          color: "#fff",
          border: "none",
          borderRadius: "var(--radio-control)",
          cursor: pendiente ? "progress" : "pointer",
          fontFamily: "inherit",
        }}
      >
        {pendiente ? "Entrando…" : "Entrar"}
      </button>

      {vacio && (
        <p
          className="t-body etiqueta etiqueta-critica"
          style={{ display: "block", margin: "var(--space-4) 0 0" }}
        >
          Escribe tu correo para entrar.
        </p>
      )}

      {sinSecreto && (
        <p
          className="t-body etiqueta etiqueta-critica"
          style={{ display: "block", margin: "var(--space-4) 0 0" }}
        >
          Este despliegue no tiene configurada la firma de identificación, así
          que no puede dejar entrar a nadie. No es tu correo: avisa a quien te
          compartió el enlace.
        </p>
      )}

      {fallo && !vacio && !sinSecreto && (
        <p
          className="t-body etiqueta etiqueta-critica"
          style={{ display: "block", margin: "var(--space-4) 0 0" }}
        >
          No podemos dejarte entrar con ese correo. Comprueba que lo escribiste
          bien; si crees que deberías tener acceso, avisa a quien te compartió
          el enlace.
        </p>
      )}
    </form>
  );
}
