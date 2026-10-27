"""Formatos de datos de las pantallas de análisis."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class EjecucionOut(BaseModel):
    id_ejecucion: int
    fecha_corte: date
    horizonte_dias: int
    fecha_fin: datetime | None
    reservas_procesadas: int
    fechas_analizadas: int
    fechas_criticas: int
    codigo_version: str


class NocheOut(BaseModel):
    fecha: date
    reservas_registradas: int
    habitaciones_reservadas: int
    cancelaciones_estimadas: float
    noshows_estimados: float
    pickup_estimado: float
    ocupacion_esperada: float
    capacidad: int
    porcentaje_ocupacion: float
    tarifa_promedio: float | None
    nivel_riesgo: str
    motivo: str | None = None
    tipo_sugerencia: str | None = None
    ajuste_recomendado: float | None = None
    tarifa_sugerida: float | None = None
    tarifa_referencia: float | None = None
    justificacion: str | None = None
    dias_anticipacion: int = 0
    error_esperado_pct: float = 0
    banda_inf_pct: float = 0
    banda_sup_pct: float = 0
    exceso_habitaciones: float = 0
    eventos: list[str] = []


class EstadoOut(BaseModel):
    fecha_corte: date | None
    horizonte_dias: int | None
    version: str | None
    estado_version: str | None
    ultima_actualizacion: datetime | None
    datos_simulados: bool = True
    hoy: date | None = None  # fecha de hoy según la hora del hotel (internet o servidor)
    desfase_dias: int | None = None  # hoy − fecha de corte
    estado_fecha: str = "sin_datos"  # al_dia | desactualizado | adelantado | simulado | sin_datos
    fuente_hora: str = "equipo"  # internet | equipo
    reloj_equipo_correcto: bool | None = None  # None: no se pudo comparar con internet


class DashboardOut(BaseModel):
    ejecucion: EjecucionOut | None
    dias: int = 90
    ocupacion_media_pct: float | None = None
    ocupacion_pico_pct: float | None = None
    fecha_pico: date | None = None
    prob_cancelacion_media_pct: float | None = None
    prob_noshow_media_pct: float | None = None
    reservas_evaluadas: int = 0
    habitaciones_en_riesgo: float | None = None
    riesgo: dict[str, int] = {}
    noches: list[NocheOut] = []
    fechas_criticas: list[NocheOut] = []
    proximas_atencion: list[NocheOut] = []
    umbral_medio: float = 90
    umbral_alto: float = 98
    metricas: dict[str, Any] = {}


class OcupacionOut(BaseModel):
    ejecucion: EjecucionOut | None
    noches: list[NocheOut] = []
    umbral_medio: float = 90
    umbral_alto: float = 98
    mape_por_horizonte: dict[str, float] = {}


class RiesgoOut(BaseModel):
    ejecucion: EjecucionOut | None
    resumen: dict[str, int] = {}
    noches: list[NocheOut] = []
    umbral_medio: float = 90
    umbral_alto: float = 98


class ReservaPesoOut(BaseModel):
    id_reserva: int
    codigo_reserva: str
    fecha_llegada: date
    fecha_salida: date
    num_habitaciones: int
    tipo_habitacion: str
    canal_reserva: str
    segmento: str
    prob_cancelacion_pct: float
    prob_noshow_pct: float
    habitaciones_en_riesgo: float


class DetalleNocheOut(BaseModel):
    noche: NocheOut
    reservas_que_pesan: list[ReservaPesoOut]
    habitaciones_en_riesgo_total: float
    umbral_medio: float
    umbral_alto: float


class PrediccionOut(BaseModel):
    id_reserva: int
    codigo_reserva: str
    fecha_reserva: date
    fecha_llegada: date
    fecha_salida: date
    noches: int
    tipo_habitacion: str
    num_habitaciones: int
    canal_reserva: str
    segmento: str
    politica_tarifa: str
    tarifa_noche: float
    importe_total: float
    prob_cancelacion_pct: float
    prob_noshow_pct: float
    prob_presentacion_pct: float
    resultado_predicho: str
    nivel_riesgo: str
    factores_explicativos: list[dict[str, Any]]


class PrediccionesPagina(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[PrediccionOut]


class PrediccionesResumen(BaseModel):
    total: int
    prob_cancelacion_media_pct: float
    prob_noshow_media_pct: float
    por_nivel: dict[str, int]
    histograma: list[dict[str, Any]]
    por_canal: list[dict[str, Any]]
    por_segmento: list[dict[str, Any]]
    umbral_cancelacion_pct: float


class ModeloOut(BaseModel):
    version: dict[str, Any] | None
    evaluaciones: list[dict[str, Any]] = []
    importancia_variables: list[dict[str, Any]] = []
    umbrales: dict[str, float] = {}
    metas: dict[str, float] = {}
    notas: list[str] = []


class TarifaTipoOut(BaseModel):
    codigo: str
    nombre: str
    tarifa_catalogo: float
    promedio_reservas: float | None
    referencia: float | None


class ReferenciaTarifaOut(BaseModel):
    modo: str
    tipos: list[TarifaTipoOut]
    moneda: str = "PEN"


class ReferenciaTarifaIn(BaseModel):
    modo: str
    tarifas: dict[str, float] = {}


class TarifasOut(BaseModel):
    ejecucion: EjecucionOut | None
    fechas_criticas: int = 0
    con_sugerencia: int = 0
    cobertura_pct: float = 100
    noches: list[NocheOut] = []
    referencia: ReferenciaTarifaOut | None = None
