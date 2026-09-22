import type { NextConfig } from "next";

const config: NextConfig = {
  // La app no sirve imagenes remotas ni necesita optimizador.
  images: { unoptimized: true },
  // Fallar en compilacion antes que en produccion: el contrato generado desde
  // modelos.py solo protege si los tipos se comprueban de verdad.
  typescript: { ignoreBuildErrors: false },
  eslint: { ignoreDuringBuilds: false },
};

export default config;
