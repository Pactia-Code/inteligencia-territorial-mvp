/**
 * La pantalla de una vista que la navegacion ya anuncia y que aun no existe.
 *
 * `Nav.tsx` enlaza a `/historico` y, para el administrador, a `/metricas`.
 * Ninguna de las dos esta construida —son H-014 y CA-M9.13 a CA-M9.15, del
 * bloque P3 del plan— y hasta ahora las dos daban el 404 de Next. **En plena
 * ventana de calificacion un 404 se lee como «el sistema esta roto»**, y quien
 * lo ve no distingue entre una vista pendiente y una averia.
 *
 * Asi que dice tres cosas, en este orden: que **leer el informe no depende de
 * esto**, que ira aqui y que no esta hecho todavia. No promete fecha: no la
 * hay hasta que se decida el go/no-go.
 *
 * **La etiqueta «MVP» no se pinta aqui**: la pone el layout en toda pantalla
 * (CA-M9.17), que es justo lo que F5.3 arreglo para que ninguna vista nueva
 * naciera sin ella (H-019).
 */
import Link from "next/link";

export function Proximamente({
  titulo,
  que,
}: {
  titulo: string;
  /** Que se vera aqui cuando exista. En una frase, sin jerga de criterios. */
  que: string;
}) {
  return (
    <main style={{ padding: "var(--space-8) var(--space-6)", maxWidth: 640 }}>
      <p className="t-label etiqueta" style={{ marginBottom: "var(--space-3)" }}>
        próximamente
      </p>

      <h1 className="t-h1" style={{ margin: 0 }}>
        {titulo}
      </h1>

      <div className="superficie" style={{ padding: "var(--space-6)", marginTop: "var(--space-4)" }}>
        <p className="t-body prosa" style={{ margin: 0 }}>
          {que}
        </p>
        <p className="t-body prosa" style={{ margin: "var(--space-3) 0 0" }}>
          Todavía no está construida. <strong>Leer el informe y calificar no
          dependen de esta vista</strong>, así que puedes seguir con lo tuyo.
        </p>
      </div>

      <p style={{ marginTop: "var(--space-4)" }}>
        <Link href="/" className="t-body">
          Volver al informe
        </Link>
      </p>
    </main>
  );
}
