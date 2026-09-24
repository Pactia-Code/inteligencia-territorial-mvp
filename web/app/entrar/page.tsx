/**
 * PANTALLA DE ENTRADA — correo, sin clave. Decision del dueno del 2026-09-24.
 *
 * **Lo que cambia y lo que no.** Antes el informe se leia con solo tener el
 * enlace y el correo se pedia al ir a calificar; ahora se entra primero. Eso
 * **mejora privacidad e imagen, no la atribucion**: sin clave, quien conozca un
 * correo autorizado sigue pudiendo entrar y calificar por esa gerencia. **R-A2
 * y H-012 siguen abiertos** y hay que declararlo al publicar H1 y H2. Una
 * pantalla de entrada *parece* autenticacion, y por eso conviene repetirlo
 * aqui, donde se lee el codigo.
 *
 * **Marca**, segun lo decidido:
 *
 * · `pactia-logo.png` **tiene el fondo opaco** —declara alfa y esta al 100%—,
 *   asi que va sobre una tarjeta `#FFFFFF` y solo ahi. Se pidio a
 *   comunicaciones una version transparente o SVG; hasta entonces, no se
 *   recorta ni se recolorea.
 * · Alrededor, **superficies neutras**: el logo es `#1D2559` y el primario del
 *   design system es `#0F4761`. Son azules distintos y el choque esta sin
 *   resolver, asi que esta pantalla evita enfrentarlos poniendo el unico azul
 *   fuerte en el logo. **No se toca ningun token.**
 * · El boton «Entrar» si usa navy: es un control, no una superficie, y sin
 *   color no se distingue del resto.
 *
 * La etiqueta «MVP» se pinta aqui a mano (CA-M9.17). En el resto de pantallas
 * la pone el layout, pero el layout **no dibuja la barra cuando no hay
 * identidad** — que es siempre en esta pagina.
 */
import type { Metadata } from "next";
import Image from "next/image";
import { redirect } from "next/navigation";
import { AVISO_CORTO } from "@/lib/aviso";
import { destinoSeguro } from "@/lib/destino";
import { identidadActual } from "@/lib/sesion";
import { Formulario } from "./Formulario";

export const metadata: Metadata = { title: "Entrar · Inteligencia Territorial" };

// Depende de la cookie, asi que se resuelve en cada peticion.
export const dynamic = "force-dynamic";

export default async function Entrar({
  searchParams,
}: {
  searchParams: Promise<{ destino?: string }>;
}) {
  const destino = destinoSeguro((await searchParams).destino);

  // Quien ya tiene cookie valida no vuelve a entrar. Tambien evita que esta
  // pantalla se quede accesible por detras con la sesion puesta.
  if (await identidadActual()) redirect(destino);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-surface-alt)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-6)",
        gap: "var(--space-4)",
      }}
    >
      <section
        className="superficie"
        style={{
          background: "var(--color-surface)",
          width: "100%",
          maxWidth: 420,
          padding: "var(--space-8)",
        }}
      >
        {/* Sobre #FFFFFF, que es la unica superficie donde este archivo vale. */}
        <Image
          src="/marca/pactia-logo.png"
          alt="Pactia Fondo Inmobiliario"
          width={874}
          height={282}
          priority
          // Proporcional y con margen: se fija el ancho y la altura se calcula.
          style={{ width: 200, height: "auto", display: "block" }}
        />

        <h1 className="t-h1" style={{ margin: "var(--space-6) 0 0" }}>
          Inteligencia Territorial
        </h1>
        <p className="t-meta prosa" style={{ margin: "var(--space-2) 0 0" }}>
          Entra con tu correo de Pactia para ver el informe del ciclo.
        </p>

        <Formulario destino={destino} />
      </section>

      <span className="t-label etiqueta etiqueta-aviso">⚠ {AVISO_CORTO}</span>
    </main>
  );
}
