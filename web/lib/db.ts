/**
 * Conexion a Neon.
 *
 * Driver HTTP de Neon a proposito: en serverless el modo de fallo es agotar
 * conexiones, y este no abre ninguna persistente. Nada de ORM — Alembic es la
 * unica autoridad del esquema (regla 2 de D8) y un ORM aqui seria una segunda
 * fuente de verdad.
 *
 * **DATABASE_URL en Vercel apunta al endpoint POOLED** (el host con `-pooler`),
 * al reves que el del pipeline: alli se migra y por el pooled no se puede.
 * Ver el README.
 */
import { neon } from "@neondatabase/serverless";

const url = process.env.DATABASE_URL;
if (!url) {
  throw new Error(
    "Falta DATABASE_URL. En Vercel va el endpoint POOLED de Neon; en local, " +
      "el mismo que usa el pipeline.",
  );
}

export const sql = neon(url);
