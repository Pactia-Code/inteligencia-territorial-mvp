import type { Metadata } from "next";
import Image from "next/image";
import { salir } from "./acciones";
import { Nav } from "./Nav";
import { AVISO_CORTO } from "@/lib/aviso";
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
        {/*
          **La barra solo se dibuja con identidad**, y eso resuelve `/entrar`
          sin route groups ni middleware: alli nunca hay identidad —si la
          hubiera, la propia pagina redirige— asi que la pantalla de entrada
          queda limpia, que es lo que se pidio: logo, titulo, campo, boton y
          etiqueta MVP. En el resto de rutas la identidad esta garantizada por
          `exigirIdentidad`, asi que la barra sale siempre.
        */}
        {yo && (
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
          {/*
            Barra oscura, asi que el logo va en negativo. Este archivo si tiene
            transparencia real, al reves que el principal. No se recolorea ni se
            recorta: solo se escala en proporcion.
          */}
          <Image
            src="/marca/pactia-logo-blanco.png"
            alt="Pactia Fondo Inmobiliario"
            width={356}
            height={90}
            priority
            style={{ width: 96, height: "auto", display: "block" }}
          />
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
          {/*
            CA-M9.17: la marca va en **toda pantalla**, así que la pinta el
            layout y no cada página. Antes vivía solo en la vista de ciclo, con
            lo que `/priorizados` no la llevaba y cualquier vista nueva nacía
            sin ella (H-019). El texto corto es la desviación `M6-aviso`; el
            completo sigue en `informe.aviso`. Ver `lib/aviso.ts`.
          */}
          <span
            className="t-label etiqueta etiqueta-aviso"
            style={{ marginLeft: "auto", whiteSpace: "nowrap" }}
          >
            ⚠ {AVISO_CORTO}
          </span>

          <div>
            <form action={salir} style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
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
                  fontFamily: "inherit",
                }}
              >
                Salir
              </button>
            </form>
          </div>
        </header>
        )}
        {children}
      </body>
    </html>
  );
}
