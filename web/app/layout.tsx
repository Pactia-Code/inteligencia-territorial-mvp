import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Inteligencia Territorial",
  description: "Informe de ciclo del MVP de Inteligencia Territorial",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
