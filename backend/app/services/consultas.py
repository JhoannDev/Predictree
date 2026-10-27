"""Consultas compartidas por las rutas de análisis (últimos resultados, noches, bandas de error)."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
from sqlalchemy import text


def filas(db, sql: str, **params) -> list[dict[str, Any]]:
    return [dict(f._mapping) for f in db.execute(text(sql), params)]


def num(valor, defecto=None):
    return float(valor) if valor is not None else defecto


def parametros(db) -> dict[str, str]:
    return {f["clave"]: f["valor"] for f in filas(db, "SELECT clave, valor FROM parametro_sistema")}


def ultima_ejecucion(db) -> dict[str, Any] | None:
    f = filas(
        db,
        """
        SELECT e.id_ejecucion, e.fecha_corte, e.horizonte_dias, e.fecha_fin, e.reservas_procesadas,
               e.fechas_analizadas, e.fechas_criticas, v.codigo_version, e.id_version
        FROM ejecucion_analisis e JOIN version_modelo v USING (id_version)
        WHERE e.estado = 'completada' ORDER BY e.id_ejecucion DESC LIMIT 1
        """,
    )
    return f[0] if f else None


def estado_de_la_fecha(fecha_corte: date | None, hoy: date, simulados: bool) -> str:
    """Compara la fecha de los datos con la fecha de hoy (hora del hotel).

    - ``simulado``: son datos de demostración; su fecha de corte hace de "hoy" aunque no coincida.
    - ``al_dia``: los datos llegan hasta hoy o ayer (la carga se hace al cierre de cada día).
    - ``desactualizado``: los datos son de hace 2 días o más.
    - ``adelantado``: los datos son de una fecha posterior a hoy (reloj mal puesto o datos erróneos).
    """
    if fecha_corte is None:
        return "sin_datos"
    if simulados:
        return "simulado"
    desfase = (hoy - fecha_corte).days
    if desfase < 0:
        return "adelantado"
    return "al_dia" if desfase <= 1 else "desactualizado"


def mape_por_horizonte(db, id_version: int) -> dict[int, float]:
    """MAPE (en %) del modelo según los días de anticipación, de la evaluación de ocupación."""
    f = filas(
        db,
        """
        SELECT detalle->'mape_por_horizonte' AS m FROM evaluacion_modelo
        WHERE id_version = :v AND tipo_evaluacion = 'ocupacion'
        """,
        v=id_version,
    )
    if not f or not f[0]["m"]:
        return {}
    return {int(h): float(d["mape_con_pickup"]) for h, d in f[0]["m"].items()}


def error_esperado_pct(tabla: dict[int, float], dias: int) -> float:
    """Error relativo esperado (%) para una noche a ``dias`` días de la fecha de corte."""
    if not tabla:
        return 0.0
    h = np.array(sorted(tabla))
    return float(np.interp(dias, h, [tabla[k] for k in h]))


CAMPOS_NUMERICOS = (
    "cancelaciones_estimadas",
    "noshows_estimados",
    "pickup_estimado",
    "ocupacion_esperada",
    "porcentaje_ocupacion",
    "tarifa_promedio",
    "ajuste_recomendado",
    "tarifa_sugerida",
    "tarifa_referencia",
)


def noches(db, ejec: dict[str, Any], dias: int | None = None) -> list[dict[str, Any]]:
    """Noches del último análisis, con riesgo, sugerencia y banda de error."""
    lista = filas(
        db,
        """
        SELECT o.fecha_analizada AS fecha, o.reservas_registradas, o.habitaciones_reservadas,
               o.cancelaciones_estimadas, o.noshows_estimados, o.pickup_estimado,
               o.ocupacion_esperada, o.capacidad_disponible AS capacidad, o.porcentaje_ocupacion,
               o.tarifa_promedio, r.nivel_riesgo, fc.motivo,
               s.tipo_sugerencia, s.ajuste_recomendado, s.tarifa_sugerida, s.tarifa_referencia,
               s.justificacion
        FROM ocupacion_esperada o
        JOIN riesgo_overbooking r USING (id_ocupacion)
        LEFT JOIN fecha_critica fc USING (id_riesgo)
        LEFT JOIN sugerencia_tarifa s USING (id_riesgo)
        WHERE o.id_ejecucion = :e ORDER BY o.fecha_analizada
        """,
        e=ejec["id_ejecucion"],
    )
    tabla = mape_por_horizonte(db, ejec["id_version"])
    especiales = filas(
        db,
        "SELECT nombre, fecha_inicio, fecha_fin FROM fecha_especial "
        "WHERE tipo IN ('evento', 'feriado') ORDER BY fecha_inicio",
    )
    if dias:
        lista = lista[:dias]
    for n in lista:
        for k in CAMPOS_NUMERICOS:
            if k in n:
                n[k] = num(n[k])
        d = (n["fecha"] - ejec["fecha_corte"]).days
        m = error_esperado_pct(tabla, d) / 100
        n["dias_anticipacion"] = d
        n["error_esperado_pct"] = round(m * 100, 1)
        n["banda_inf_pct"] = round(n["porcentaje_ocupacion"] * (1 - m), 1)
        n["banda_sup_pct"] = round(n["porcentaje_ocupacion"] * (1 + m), 1)
        n["eventos"] = [
            e["nombre"] for e in especiales if e["fecha_inicio"] <= n["fecha"] <= e["fecha_fin"]
        ]
        n["exceso_habitaciones"] = round(n["ocupacion_esperada"] - n["capacidad"], 1)
    return lista
