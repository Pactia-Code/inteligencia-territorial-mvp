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
  /** «Directo» o «Correlacionado»: como llego al informe. Trabajo de M4. */
  trayecto: string;
  /**
   * De que cuota entro si se pide calificar: `correlacionado`,
   * `contratacion`, `prensa` o `relleno`. `null` si no se pide.
   */
  tipo_pedido: string | null;
  ids_senal: number[];
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
  /**
   * Los que se **piden** calificar. Los elige codigo determinista con la
   * semilla congelada (`informes/seleccion.py`), asi que las siete gerencias
   * reciben exactamente los mismos (CA-M6.6). Vacio donde todo es opcional.
   */
  insights_pedidos: number[];
  /**
   * Que composicion salio: `{correlacionado: 3, contratacion: 1, prensa: 1}`,
   * o la que toque tras el relleno. Al analizar H1 hara falta saber si las
   * calificaciones bajas venian de correlacionados o de directos.
   */
  composicion_pedida: Record<string, number>;
}

/**
 * Una gerencia autorizada a calificar, congelada al publicar (F0.1b).
 *
 * `tipo` distingue las 7 del PRD de las anadidas despues: H2 se reporta sobre
 * las `prd` y los `adicional` van por separado; H1, con y sin ellos. La fuente
 * de la marca es `config/gerencias.json`, y queda congelada en el payload.
 */
export interface GerenciaAutorizada {
  id_gerencia: string;
  tipo: "prd" | "adicional";
}

export interface Informe {
  /**
   * El texto que CA-M6.5 y CA-M9.17 exigen. Va en el payload para que no se
   * olvide al pintar, y queda en el registro de cada informe publicado.
   */
  aviso: string;
  /**
   * Lo que se muestra: «MVP». **Desviacion deliberada** de esos dos criterios
   * (pendiente `M6-aviso`). La version corta dice que es una version temprana
   * y **quita la parte que informa** — que nadie reviso el contenido.
   */
  aviso_corto: string;
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
  calificacion: {
    mostrados: number;
    pedida_hasta_puesto: number;
    pedidas_por_municipio: number;
    /** Congelada: con ella se recomputa la muestra y se audita CA-M6.6. */
    semilla: number;
    /**
     * El denominador de H2, congelado al publicar (H-005 / F0.1): las
     * gerencias autorizadas a calificar en ese momento, ordenadas y **cada una
     * con su marca** `prd` o `adicional` (F0.1b). La tasa de respuesta se
     * computa contra esta lista, no contra `usuario` hoy.
     */
    gerencias: GerenciaAutorizada[];
  };
  municipios: MunicipioDelInforme[];
}
