"""Calendario de demanda: factor, eventos y feriados por fecha (tabla fecha_especial).

El calendario se conoce con anticipación (feriados, temporadas y eventos programados), así que usarlo
como variable del modelo no es "hacer trampa": un hotel real también lo sabe de antemano.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TablaCalendario:
    """Valores del calendario para cada día entre ``inicio`` y ``inicio + n - 1``."""

    inicio: date
    factor: np.ndarray  # factor_demanda acumulado del día (1.0 = normal)
    evento: np.ndarray  # hay un evento ese día
    feriado: np.ndarray  # es feriado ese día
    # Sumas acumuladas (con un 0 al inicio) para promediar rápido sobre una estadía.
    _acum_factor: np.ndarray
    _acum_evento: np.ndarray
    _acum_feriado: np.ndarray

    @property
    def n_dias(self) -> int:
        return len(self.factor)

    def indice(self, fechas: pd.Series | np.ndarray | pd.DatetimeIndex) -> np.ndarray:
        """Posición de cada fecha dentro de la tabla (se valida que esté dentro del rango)."""
        base = np.datetime64(self.inicio, "D")
        pos = (np.asarray(pd.to_datetime(fechas)).astype("datetime64[D]") - base).astype(int)
        if pos.size and (pos.min() < 0 or pos.max() >= self.n_dias):
            raise ValueError("Hay fechas fuera del rango del calendario.")
        return pos

    def promedio_estadia(self, llegada: np.ndarray, salida: np.ndarray) -> dict[str, np.ndarray]:
        """Promedio del factor, y si hubo evento/feriado, durante las noches de cada estadía."""
        a, b = self.indice(llegada), self.indice(salida)
        noches = np.maximum(b - a, 1)
        return {
            "factor": (self._acum_factor[b] - self._acum_factor[a]) / noches,
            "evento": (self._acum_evento[b] - self._acum_evento[a]) > 0,
            "feriado": (self._acum_feriado[b] - self._acum_feriado[a]) > 0,
        }


def construir_calendario(calendario: pd.DataFrame, inicio: date, fin: date) -> TablaCalendario:
    """Arma la tabla diaria a partir de fecha_especial (tipo, fecha_inicio, fecha_fin, factor_demanda)."""
    n = (fin - inicio).days + 1
    factor = np.ones(n)
    evento = np.zeros(n, dtype=bool)
    feriado = np.zeros(n, dtype=bool)
    for fila in calendario.itertuples(index=False):
        a = max((pd.Timestamp(fila.fecha_inicio).date() - inicio).days, 0)
        b = min((pd.Timestamp(fila.fecha_fin).date() - inicio).days, n - 1)
        if b < a:
            continue
        factor[a : b + 1] *= float(fila.factor_demanda)
        if fila.tipo == "evento":
            evento[a : b + 1] = True
        if fila.tipo == "feriado":
            feriado[a : b + 1] = True
    factor = np.clip(factor, 0.5, 1.6)

    def acumular(valores: np.ndarray) -> np.ndarray:
        return np.concatenate([[0.0], np.cumsum(valores.astype(float))])

    return TablaCalendario(
        inicio=inicio,
        factor=factor,
        evento=evento,
        feriado=feriado,
        _acum_factor=acumular(factor),
        _acum_evento=acumular(evento),
        _acum_feriado=acumular(feriado),
    )
