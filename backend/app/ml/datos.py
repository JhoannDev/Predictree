"""Lectura de los datos que necesita el modelo desde PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.ml.calendario import TablaCalendario, construir_calendario


@dataclass
class EntradasModelo:
    reservas: pd.DataFrame
    calendario: TablaCalendario
    tarifa_base: dict[str, float]
    capacidad: int
    parametros: dict[str, str]

    @property
    def fecha_corte(self) -> date:
        return date.fromisoformat(self.parametros["fecha_corte"])

    @property
    def horizonte(self) -> int:
        return int(self.parametros["horizonte_prediccion_dias"])

    @property
    def umbral_medio(self) -> float:
        return float(self.parametros["umbral_riesgo_medio"])

    @property
    def umbral_alto(self) -> float:
        return float(self.parametros["umbral_riesgo_alto"])


def leer_entradas(conexion: Connection) -> EntradasModelo:
    parametros = dict(conexion.execute(text("SELECT clave, valor FROM parametro_sistema")).all())
    reservas = pd.read_sql(text("SELECT * FROM reserva"), conexion)
    if reservas.empty:
        raise SystemExit("No hay reservas. Ejecuta primero: python -m scripts.generar_datos")
    for col in ("fecha_llegada", "fecha_salida", "fecha_reserva", "fecha_cancelacion"):
        reservas[col] = pd.to_datetime(reservas[col])
    reservas["tarifa_noche"] = reservas["tarifa_noche"].astype(float)
    cal = pd.read_sql(
        text("SELECT tipo, fecha_inicio, fecha_fin, factor_demanda FROM fecha_especial"), conexion
    )
    cal["factor_demanda"] = cal["factor_demanda"].astype(float)
    tipos = pd.read_sql(text("SELECT codigo, cantidad, tarifa_base FROM tipo_habitacion"), conexion)
    tarifa_base = dict(zip(tipos["codigo"], tipos["tarifa_base"].astype(float), strict=True))
    corte = date.fromisoformat(parametros["fecha_corte"])
    horizonte = int(parametros["horizonte_prediccion_dias"])
    inicio = reservas["fecha_llegada"].min().date() - timedelta(days=30)
    fin = max(corte + timedelta(days=horizonte + 120), reservas["fecha_salida"].max().date())
    return EntradasModelo(
        reservas=reservas,
        calendario=construir_calendario(cal, inicio, fin),
        tarifa_base=tarifa_base,
        capacidad=int(tipos["cantidad"].sum()),
        parametros=parametros,
    )
