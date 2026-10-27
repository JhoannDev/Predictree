export type NivelRiesgo = "bajo" | "medio" | "alto";

export interface Ejecucion {
  id_ejecucion: number;
  fecha_corte: string;
  horizonte_dias: number;
  fecha_fin: string | null;
  reservas_procesadas: number;
  fechas_analizadas: number;
  fechas_criticas: number;
  codigo_version: string;
}

export interface Noche {
  fecha: string;
  reservas_registradas: number;
  habitaciones_reservadas: number;
  cancelaciones_estimadas: number;
  noshows_estimados: number;
  pickup_estimado: number;
  ocupacion_esperada: number;
  capacidad: number;
  porcentaje_ocupacion: number;
  tarifa_promedio: number | null;
  nivel_riesgo: NivelRiesgo;
  motivo: string | null;
  tipo_sugerencia: "incrementar" | "mantener" | "promocion" | null;
  ajuste_recomendado: number | null;
  tarifa_sugerida: number | null;
  tarifa_referencia: number | null;
  justificacion: string | null;
  dias_anticipacion: number;
  error_esperado_pct: number;
  banda_inf_pct: number;
  banda_sup_pct: number;
  exceso_habitaciones: number;
  eventos: string[];
}

export interface Estado {
  fecha_corte: string | null;
  horizonte_dias: number | null;
  version: string | null;
  estado_version: string | null;
  ultima_actualizacion: string | null;
  datos_simulados: boolean;
  /** Fecha de hoy según la hora del hotel (internet o, si no hay, el servidor). */
  hoy: string | null;
  desfase_dias: number | null;
  estado_fecha: "al_dia" | "desactualizado" | "adelantado" | "simulado" | "sin_datos";
  fuente_hora: "internet" | "equipo";
  reloj_equipo_correcto: boolean | null;
}

export interface Ocupacion {
  ejecucion: Ejecucion | null;
  noches: Noche[];
  umbral_medio: number;
  umbral_alto: number;
  mape_por_horizonte: Record<string, number>;
}

export interface Riesgo {
  ejecucion: Ejecucion | null;
  resumen: Record<NivelRiesgo, number>;
  noches: Noche[];
  umbral_medio: number;
  umbral_alto: number;
}

export interface ReservaPeso {
  id_reserva: number;
  codigo_reserva: string;
  fecha_llegada: string;
  fecha_salida: string;
  num_habitaciones: number;
  tipo_habitacion: string;
  canal_reserva: string;
  segmento: string;
  prob_cancelacion_pct: number;
  prob_noshow_pct: number;
  habitaciones_en_riesgo: number;
}

export interface DetalleNoche {
  noche: Noche;
  reservas_que_pesan: ReservaPeso[];
  habitaciones_en_riesgo_total: number;
  umbral_medio: number;
  umbral_alto: number;
}

export interface TarifaTipo {
  codigo: string;
  nombre: string;
  tarifa_catalogo: number;
  promedio_reservas: number | null;
  referencia: number | null;
}

export interface ReferenciaTarifa {
  modo: "automatica" | "manual";
  tipos: TarifaTipo[];
  moneda: string;
}

export interface Tarifas {
  ejecucion: Ejecucion | null;
  fechas_criticas: number;
  con_sugerencia: number;
  cobertura_pct: number;
  noches: Noche[];
  referencia: ReferenciaTarifa | null;
}

export interface MetricaResumen {
  f1: number | null;
  mape: number | null;
  meta: number | null;
  cumple_meta: boolean;
}

export interface Dashboard {
  ejecucion: Ejecucion | null;
  dias: number;
  ocupacion_media_pct: number | null;
  ocupacion_pico_pct: number | null;
  fecha_pico: string | null;
  reservas_evaluadas: number;
  prob_cancelacion_media_pct: number | null;
  prob_noshow_media_pct: number | null;
  habitaciones_en_riesgo: number | null;
  riesgo: Record<NivelRiesgo, number>;
  noches: Noche[];
  fechas_criticas: Noche[];
  proximas_atencion: Noche[];
  umbral_medio: number;
  umbral_alto: number;
  metricas: Record<string, MetricaResumen>;
}

export interface Factor {
  variable: string;
  nombre: string;
  valor: string;
  efecto_pct: number;
  efecto_cancelacion_pct: number;
  efecto_noshow_pct: number;
  direccion: "aumenta" | "reduce";
}

export interface Prediccion {
  id_reserva: number;
  codigo_reserva: string;
  fecha_reserva: string;
  fecha_llegada: string;
  fecha_salida: string;
  noches: number;
  tipo_habitacion: string;
  num_habitaciones: number;
  canal_reserva: string;
  segmento: string;
  politica_tarifa: string;
  tarifa_noche: number;
  importe_total: number;
  prob_cancelacion_pct: number;
  prob_noshow_pct: number;
  prob_presentacion_pct: number;
  resultado_predicho: string;
  nivel_riesgo: NivelRiesgo;
  factores_explicativos: Factor[];
}

export interface PaginaPredicciones {
  total: number;
  pagina: number;
  tamano: number;
  items: Prediccion[];
}

export interface GrupoResumen {
  grupo: string;
  reservas: number;
  cancelacion: number;
  noshow: number;
}

export interface ResumenPredicciones {
  total: number;
  prob_cancelacion_media_pct: number;
  prob_noshow_media_pct: number;
  por_nivel: Record<NivelRiesgo, number>;
  histograma: { rango: string; reservas: number }[];
  por_canal: GrupoResumen[];
  por_segmento: GrupoResumen[];
  umbral_cancelacion_pct: number;
}

export interface MetricasClase {
  f1: number;
  precision: number;
  recall: number;
  accuracy: number;
  auc_roc: number | null;
  auc_pr: number | null;
  brier: number;
  tasa_real: number;
  tasa_predicha_media: number;
  casos: number;
}

export interface PuntoCalibracion {
  probabilidad_media: number;
  frecuencia_real: number;
  casos: number;
}

export interface MapeHorizonte {
  mape_con_pickup: number;
  mape_sin_pickup: number;
  mape_referencia: number;
}

export interface PuntoSerie {
  fecha: string;
  real_pct: number;
  esperada_14d_pct: number;
  esperada_30d_pct: number;
  referencia_pct: number;
}

export interface DeteccionNivel {
  umbral_pct: number;
  noches_alertadas: number;
  aciertos: number;
  recall: number | null;
  precision: number | null;
}

export interface RiesgoDeteccion {
  umbral_pct: number;
  noches_riesgo_reales: number;
  noches_evaluadas: number;
  por_horizonte: Record<string, { al_umbral: DeteccionNivel; alerta_temprana: DeteccionNivel }>;
}

export interface Evaluacion {
  tipo_evaluacion: "cancelacion" | "no_show" | "ocupacion";
  periodo_inicio: string;
  periodo_fin: string;
  registros_evaluados: number;
  f1_score: number | null;
  precision_score: number | null;
  recall_score: number | null;
  accuracy_score: number | null;
  mape: number | null;
  valor_meta: number;
  cumple_meta: boolean;
  detalle: {
    metricas?: MetricasClase;
    calibracion?: PuntoCalibracion[];
    mape_por_horizonte?: Record<string, MapeHorizonte>;
    horizonte_referencia_dias?: number;
    serie?: PuntoSerie[];
    riesgo_deteccion?: RiesgoDeteccion;
  };
}

export interface Modelo {
  version: {
    codigo_version: string;
    descripcion: string;
    algoritmo: string;
    fecha_entrenamiento: string;
    periodo_entrenamiento_inicio: string;
    periodo_entrenamiento_fin: string;
    estado_aprobacion: string;
    activa: boolean;
  } | null;
  evaluaciones: Evaluacion[];
  importancia_variables: { variable: string; nombre: string; importancia_pct: number }[];
  umbrales: Record<string, number>;
  metas: Record<string, number>;
  notas: string[];
}

export interface FiltrosPredicciones {
  pagina: number;
  tamano: number;
  orden: "llegada" | "prob_cancelacion" | "prob_noshow" | "importe";
  nivel?: NivelRiesgo | "";
  canal?: string;
  buscar?: string;
}
