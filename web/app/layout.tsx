import type { Metadata } from "next";
import { cambiarCorreo } from "./acciones";
import { Nav } from "./Nav";
import { esAdministrador, identidadActual } from "@/lib/sesion";
import "./globals.css";

export const metadata: Metadata = {
  title: "Inteligencia Territorial",
  description: "Informe de ciclo del MVP de Inteligencia Territorial",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const yo = await identidadActual();
  const admin = await esAdministrador();

  return (
    <html lang="es">
      <body>
        <header
          style={{
            background: "var(--color-navy-700)",
            color: "#fff",
            padding: "var(--space-3) var(--space-6)",
            display: "flex",
            alignItems: "center",
            gap: "var(--space-6)",
          }}
        >
          <span className="t-h2" style={{ whiteSpace: "nowrap" }}>
            Inteligencia Territorial
          </span>
          <Nav esAdmin={admin} />

          {/*
            **Sin identidad de persona.** `calificacion` atribuye a GERENCIA, no
            a persona, y es deliberado (CA-M7.2): mostrar un nombre propio
            sugeriria una atribucion que el sistema no guarda. Antes de
            identificarse, este espacio queda vacio — leer no requiere correo.
          */}
          <div style={{ marginLeft: "auto" }}>
            {yo && (
              <form action={cambiarCorreo} style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
                <span className="t-meta" style={{ color: "#fff", opacity: 0.85 }}>
                  Calificando como <strong>{yo.id_gerencia}</strong>
                </span>
                <button
                  type="submit"
                  className="t-meta"
                  style={{
                    background: "transparent",
                    color: "#fff",
                    border: "1px solid rgba(255,255,255,.4)",
                    borderRadius: "var(--radio-control)",
                    padding: "var(--space-1) var(--space-2)",
                    cursor: "pointer",
                  }}
                >
                  cambiar correo
                </button>
              </form>
            )}
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
