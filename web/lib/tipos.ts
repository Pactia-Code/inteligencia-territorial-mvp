/**
 * La forma del payload que compone M6 (`informes/composicion.py`).
 *
 * **No se escribe a mano lo que ya esta generado.** Las tablas que la app
 * escribe viven en `contrato.generado.ts`, derivado de `modelos.py`. Esto es
 * otra cosa: el payload es una columna JSON, no un esquema de tablas, asi que
 * su forma se declara aqui. Si M6 cambia el payload, esto cambia con el — y lo
 * que lo delata es el `tsc --noEmit`, no un generador.
 *
 * Los codigos de factor **no se usan para pintar**: cada factor trae su
 * `fuente` en castellano y la vista de ciclo usa `aportes_por_fuente`
 * (M6-src). El mapa de factor a fuente vive en Python, en un solo sitio.
 */

export interface Aporte {
  codigo: string;
  descripcion: string;
  fuente: string;
  crudo: number | null;
  normalizado: number | null;
  peso: number;
  aporte: number;
  sin_cobertura: boolean;
  hay_dato: boolean;
  motivo: string;
}

export interface AportePorFuente {
  fuente: string;
  etiqueta: string;
  aporte: number;
  peso: number;
  codigos: string[];
  sin_datos: boolean;
}

export interface CampoContexto {
  clave: string;
  etiqueta: string;
  valor: number;
  unidad: string;
  fuente: string;
  anio: number | null;
}

export interface Evidencia {
  url?: string;
  fecha?: string;
  cita_textual?: string;
  fuente?: string;
  id_senal?: number;
}

export interface InsightPublicado {
  id: number;
  categoria: string;
  resumen: string;
  implicacion_inmobiliaria: string | null;
  origen: string;
  evidencia: Evidencia[];
}

export interface MunicipioDelInforme {
  puesto: number;
  ranking_en_la_corrida: number;
  divipola: string;
  nombre: string;
  departamento: string;
  score: number;
  fuentes: {
    presentes: string[];
    ausentes: string[];
    /** «licencias y prensa, sin contratacion». Va junto al puesto (M6-orden). */
    resumen: string;
  };
  factores: Aporte[];
  aportes_por_fuente: AportePorFuente[];
  cobertura: {
    dias_cubiertos: number;
    dias_ventana: number;
    sin_cobertura: boolean;
    ultima_fecha_captura: string | null;
  };
  fraccion_informada: number | null;
  contexto: CampoContexto[];
  /** Los escribe el Sintetizador. Llegan vacios; la pantalla pinta el hueco. */
  justificacion: string | null;
  sugerencias: string[];
  /** M9-carga: la calificacion PEDIDA es sobre los primeros. */
  calificable: boolean;
  insights: InsightPublicado[];
}

export interface Informe {
  /** CA-M6.5 y CA-M9.17. Viene en el payload para que no se olvide al pintar. */
  aviso: string;
  ciclo: number;
  ventana: { desde: string | null; hasta: string | null };
  corridas: {
    scoring: number;
    agentes: number;
    version_scoring: string;
    version_pipeline: string | null;
    version_clasificador: string | null;
    version_correlacionador: string | null;
    pesos: Record<string, number>;
  };
  corte: {
    cohorte: string | null;
    por_fuente: Record<string, { corte: string | null; municipios_con_fecha: number }>;
    municipios_sin_fecha: string[];
  };
  calificacion: { mostrados: number; pedida_hasta_puesto: number };
  municipios: MunicipioDelInforme[];
}
