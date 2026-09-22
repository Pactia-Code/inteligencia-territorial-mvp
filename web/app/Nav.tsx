"use client";

/**
 * Las tres vistas de CA-M9.3 mas el panel del administrador.
 *
 * Unico componente de cliente de la barra, y solo para saber en que ruta
 * estamos. La identidad la resuelve el servidor y llega por props: aqui no se
 * consulta nada.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";

const VISTAS = [
  { href: "/", etiqueta: "Ciclo", prefijo: "/ciclo" },
  { href: "/priorizados", etiqueta: "Priorizados", prefijo: "/priorizados" },
  { href: "/historico", etiqueta: "Histórico", prefijo: "/historico" },
];

export function Nav({ esAdmin }: { esAdmin: boolean }) {
  const ruta = usePathname();
  const vistas = esAdmin
    ? [...VISTAS, { href: "/metricas", etiqueta: "Métricas", prefijo: "/metricas" }]
    : VISTAS;

  return (
    <nav style={{ display: "flex", gap: "var(--space-1)" }}>
      {vistas.map((v) => {
        const activa = ruta === v.href || ruta.startsWith(v.prefijo);
        return (
          <Link
            key={v.href}
            href={v.href}
            className="t-h3"
            style={{
              padding: "var(--space-2) var(--space-4)",
              borderRadius: "var(--radio-tarjeta)",
              textDecoration: "none",
              color: "#fff",
              background: activa ? "var(--color-navy-500)" : "transparent",
              fontWeight: activa ? 600 : 400,
            }}
          >
            {v.etiqueta}
          </Link>
        );
      })}
    </nav>
  );
}
