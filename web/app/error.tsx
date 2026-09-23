"use client";

/**
 * Lo que se ve cuando algo revienta de verdad. F0.7, H-045.
 *
 * No sustituye al mensaje de la fila: **ese es el importante**, porque un fallo
 * al guardar una calificacion se atiende en el sitio y sin perder la seleccion.
 * Esto es la red de abajo, para lo que no se puede atender ahi —una consulta
 * que falla al pintar la pagina, por ejemplo—. Sin este archivo, Next muestra
 * su pantalla generica: fondo blanco, «Application error» y nada que hacer.
 *
 * Dice tres cosas, en este orden: que **leer el informe no depende de esto**,
 * que se puede reintentar, y a quien avisar. En plena ventana de calificacion,
 * una pantalla sin salida se lee como «el sistema no funciona» y se cierra.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main style={{ padding: "var(--space-8)", maxWidth: 640 }}>
      <h1 className="t-h1" style={{ margin: 0 }}>
        Algo falló al cargar esta página
      </h1>
      <p className="t-body prosa" style={{ margin: "var(--space-3) 0 0" }}>
        No se perdió nada de lo que ya habías guardado. Puedes reintentar; si
        vuelve a fallar, avisa a quien te compartió el enlace.
      </p>
      <div style={{ display: "flex", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
        <button
          type="button"
          onClick={reset}
          className="t-h3"
          style={{
            padding: "var(--space-2) var(--space-4)",
            background: "var(--color-navy-700)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radio-control)",
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Reintentar
        </button>
        <a
          href="/"
          className="t-h3"
          style={{
            padding: "var(--space-2) var(--space-4)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radio-control)",
            textDecoration: "none",
            color: "var(--color-ink)",
          }}
        >
          Volver al inicio
        </a>
      </div>
      {/* El `digest` es lo unico que permite encontrar este fallo concreto en
          los registros del servidor. Sin el, un aviso no se puede rastrear. */}
      {error.digest && (
        <p className="t-meta" style={{ margin: "var(--space-4) 0 0" }}>
          Referencia para soporte: {error.digest}
        </p>
      )}
    </main>
  );
}
