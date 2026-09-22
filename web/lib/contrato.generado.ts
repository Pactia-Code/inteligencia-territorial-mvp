// GENERADO AUTOMÁTICAMENTE — NO EDITAR A MANO.
//
// Sale de `src/territorial/almacen/modelos.py` vía
// `scripts/generar_contrato_ts.py`. Si cambias el modelo, regenera:
//
//     $py scripts\generar_contrato_ts.py
//
// `tests/test_contrato.py` falla si este archivo se queda atrás, que es lo que
// impide que la app escriba contra una columna que ya no existe.
//
// Solo las dos tablas que M9 puede escribir (CA-M9.16). Todo lo demás se lee.

// ---- calificacion ----
export const COLUMNAS_CALIFICACION = [
  "id",
  "id_insight",
  "id_gerencia",
  "id_usuario",
  "valor",
  "comentario",
  "creado_en",
] as const;

export interface FilaCalificacion {
  id: number;
  id_insight: number;
  id_gerencia: string;
  id_usuario: number | null;
  valor: number;  // 1-5, exigido por la base
  comentario: string | null;
  creado_en: string;
}

export type NuevaCalificacion = Pick<
  FilaCalificacion,
  | "id_insight"
  | "id_gerencia"
  | "id_usuario"
  | "valor"
  | "comentario"
>;

export const VALOR_CALIFICACION_MIN = 1;
export const VALOR_CALIFICACION_MAX = 5;

// ---- seguimiento ----
export const COLUMNAS_SEGUIMIENTO = [
  "id",
  "divipola",
  "id_ciclo_origen",
  "estado",
  "nota",
  "id_usuario",
  "fecha_cambio",
] as const;

export interface FilaSeguimiento {
  id: number;
  divipola: string;
  id_ciclo_origen: number;
  estado: "priorizado" | "en_revision" | "en_estructuracion" | "descartado";
  nota: string | null;
  id_usuario: number | null;
  fecha_cambio: string;
}

export type NuevaSeguimiento = Pick<
  FilaSeguimiento,
  | "divipola"
  | "id_ciclo_origen"
  | "estado"
  | "nota"
  | "id_usuario"
>;

export const ESTADO_SEGUIMIENTO = [
  "priorizado",
  "en_revision",
  "en_estructuracion",
  "descartado",
] as const;

// ---- identificacion ----
export const COLUMNAS_IDENTIFICACION = [
  "id",
  "id_usuario",
  "creado_en",
  "user_agent",
  "ip",
] as const;

export interface FilaIdentificacion {
  id: number;
  id_usuario: number;
  creado_en: string;
  user_agent: string | null;
  ip: string | null;
}

export type NuevaIdentificacion = Pick<
  FilaIdentificacion,
  | "id_usuario"
  | "user_agent"
  | "ip"
>;
