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
  "valor",
  "comentario",
  "creado_en",
] as const;

export interface FilaCalificacion {
  id: number;
  id_insight: number;
  id_gerencia: string;
  valor: number;  // 1-5, exigido por la base
  comentario: string | null;
  creado_en: string;
}

export type NuevaCalificacion = Pick<
  FilaCalificacion,
  | "id_insight"
  | "id_gerencia"
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
