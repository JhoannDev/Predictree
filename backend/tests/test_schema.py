"""Verifica que la base de datos tenga la estructura y los datos iniciales esperados."""

from sqlalchemy import text

from app.db.session import engine

TABLAS_ESPERADAS = {
    "usuario",
    "parametro_sistema",
    "tipo_habitacion",
    "fecha_especial",
    "lote_carga",
    "observacion_carga",
    "reserva",
    "version_modelo",
    "evaluacion_modelo",
    "ejecucion_analisis",
    "prediccion",
    "ocupacion_esperada",
    "riesgo_overbooking",
    "fecha_critica",
    "regla_tarifa",
    "sugerencia_tarifa",
    "reporte_generado",
}


def _valor(sql: str):
    with engine.connect() as conexion:
        return conexion.execute(text(sql)).scalar_one_or_none()


def test_existen_todas_las_tablas():
    with engine.connect() as conexion:
        filas = conexion.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        existentes = {fila[0] for fila in filas}
    faltantes = TABLAS_ESPERADAS - existentes
    assert not faltantes, f"Faltan tablas (ejecuta python -m scripts.init_db): {faltantes}"


def test_el_hotel_tiene_240_habitaciones():
    assert _valor("SELECT sum(cantidad) FROM tipo_habitacion") == 240


def test_parametros_principales():
    assert _valor("SELECT valor FROM parametro_sistema WHERE clave = 'moneda'") == "PEN"
    assert _valor("SELECT valor FROM parametro_sistema WHERE clave = 'fecha_corte'") is not None


def test_calendario_y_reglas_cargados():
    feriados_2026 = _valor(
        "SELECT sum(fecha_fin - fecha_inicio + 1) FROM fecha_especial "
        "WHERE tipo = 'feriado' AND extract(year FROM fecha_inicio) = 2026"
    )
    assert feriados_2026 == 16
    assert _valor("SELECT count(*) FROM regla_tarifa") >= 3


def test_eventos_genericos_con_categoria():
    eventos = _valor("SELECT count(*) FROM fecha_especial WHERE tipo = 'evento'")
    assert eventos == 5
    con_categoria = _valor(
        "SELECT count(*) FROM fecha_especial "
        "WHERE tipo = 'evento' AND categoria IS NOT NULL AND NOT recurrente"
    )
    assert con_categoria == eventos
    # Feriados y temporadas no llevan categoría y sí se repiten cada año.
    mal_clasificados = _valor(
        "SELECT count(*) FROM fecha_especial "
        "WHERE tipo <> 'evento' AND (categoria IS NOT NULL OR NOT recurrente)"
    )
    assert mal_clasificados == 0


def test_ocupacion_esperada_tiene_reubicaciones():
    columnas = _valor(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name = 'ocupacion_esperada' AND column_name = 'reubicaciones_reales'"
    )
    assert columnas == 1
