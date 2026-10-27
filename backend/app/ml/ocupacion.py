"""Ocupación esperada por noche a partir de las reservas y del modelo.

Para cada noche se suman las habitaciones que ya están reservadas y se descuentan las cancelaciones y
los no-shows que el modelo estima. Como todavía faltan reservas por llegar (los huéspedes reservan con
pocos días de anticipación), se agrega el *pickup*: un factor, aprendido de la historia, que depende de
cuántos días faltan para la noche.

    ocupación esperada = reservadas - cancelaciones estimadas - no-shows estimados + pickup
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.calendario import TablaCalendario
from app.ml.features import construir_features

HORIZONTES_PICKUP = (0, 1, 2, 3, 5, 7, 10, 14, 21, 30, 45, 60, 75, 90)


def _dias(serie: pd.Series | np.ndarray | pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(pd.to_datetime(serie)).astype("datetime64[D]")


def esperado_por_noche(
    reservas: pd.DataFrame,
    noches: pd.DatetimeIndex,
    asof: pd.DatetimeIndex,
    predecir,
    calendario: TablaCalendario,
    tarifa_base: dict[str, float],
) -> pd.DataFrame:
    """Reservas, habitaciones y pérdidas estimadas de cada noche, "vistas" desde la fecha ``asof``.

    ``noches`` y ``asof`` tienen el mismo largo: ``asof[j]`` es la fecha en que se hace el cálculo
    para la noche ``noches[j]``. ``predecir(X)`` devuelve la matriz (n, 3) de probabilidades
    (se presenta, cancelación, no-show).

    Qué se sabe en la fecha ``asof``:
      * Huéspedes que llegaron antes (llegada < asof): el resultado ya se conoce; cuentan solo los
        que se presentaron (estado "completada").
      * Reservas que llegan desde asof: cuentan si ya estaban hechas y no se habían cancelado; sus
        cancelaciones y no-shows se estiman con el modelo.
    """
    noches = pd.DatetimeIndex(noches)
    asof = pd.DatetimeIndex(asof)
    n_noches = len(noches)
    inicio = noches[0]

    llegada = _dias(reservas["fecha_llegada"])
    salida = _dias(reservas["fecha_salida"])
    d0 = np.datetime64(inicio.date(), "D")
    primera = np.maximum((llegada - d0).astype(int), 0)
    ultima = np.minimum((salida - d0).astype(int) - 1, n_noches - 1)
    cuenta = np.maximum(ultima - primera + 1, 0)

    idx_reserva = np.repeat(np.arange(len(reservas)), cuenta)
    desplazamiento = np.arange(cuenta.sum()) - np.repeat(np.cumsum(cuenta) - cuenta, cuenta)
    idx_noche = np.repeat(primera, cuenta) + desplazamiento

    a = _dias(asof)[idx_noche]
    ll = llegada[idx_reserva]
    res = _dias(reservas["fecha_reserva"])[idx_reserva]
    cancel_serie = pd.to_datetime(reservas["fecha_cancelacion"])
    cancel = _dias(cancel_serie.fillna(pd.Timestamp("2100-01-01")))[idx_reserva]
    habs = reservas["num_habitaciones"].to_numpy(dtype=float)[idx_reserva]
    tarifa = reservas["tarifa_noche"].to_numpy(dtype=float)[idx_reserva]
    completada = (reservas["estado_reserva"] == "completada").to_numpy()[idx_reserva]

    conocida = ll < a  # ya llegó: se sabe si se presentó
    vigente = (res <= a) & (cancel >= a) & ~conocida
    presente_conocido = conocida & completada

    p_cancel = np.zeros(len(idx_reserva))
    p_noshow = np.zeros(len(idx_reserva))
    pares = np.flatnonzero(vigente)
    if len(pares):
        sub = reservas.iloc[idx_reserva[pares]]
        x = construir_features(sub, a[pares], calendario, tarifa_base)
        prob = predecir(x)
        p_cancel[pares] = prob[:, 1]
        p_noshow[pares] = prob[:, 2]

    cuenta_reserva = (vigente | presente_conocido).astype(float)
    hab_reservadas = habs * (vigente | presente_conocido)
    minlen = n_noches
    return pd.DataFrame(
        {
            "fecha": noches,
            "reservas_registradas": np.bincount(idx_noche, cuenta_reserva, minlength=minlen),
            "habitaciones_reservadas": np.bincount(idx_noche, hab_reservadas, minlength=minlen),
            "cancelaciones_estimadas": np.bincount(idx_noche, habs * p_cancel, minlength=minlen),
            "noshows_estimados": np.bincount(idx_noche, habs * p_noshow, minlength=minlen),
            "ingreso_reservado": np.bincount(idx_noche, hab_reservadas * tarifa, minlength=minlen),
        }
    ).assign(
        habitaciones_esperadas=lambda d: (
            d["habitaciones_reservadas"] - d["cancelaciones_estimadas"] - d["noshows_estimados"]
        )
    )


def ocupacion_real(reservas: pd.DataFrame, noches: pd.DatetimeIndex) -> np.ndarray:
    """Habitaciones ocupadas por huéspedes que se presentaron (estado "completada") en cada noche."""
    noches = pd.DatetimeIndex(noches)
    d0 = np.datetime64(noches[0].date(), "D")
    comp = reservas[reservas["estado_reserva"] == "completada"]
    a = (_dias(comp["fecha_llegada"]) - d0).astype(int)
    b = (_dias(comp["fecha_salida"]) - d0).astype(int)
    diff = np.zeros(len(noches) + 1)
    np.add.at(diff, np.clip(a, 0, len(noches)), comp["num_habitaciones"].to_numpy(dtype=float))
    np.add.at(diff, np.clip(b, 0, len(noches)), -comp["num_habitaciones"].to_numpy(dtype=float))
    return np.cumsum(diff)[: len(noches)]


def patron_estacional(
    real: np.ndarray, noches: pd.DatetimeIndex, calendario: TablaCalendario
) -> np.ndarray:
    """Ocupación típica (habitaciones) de cada día de la semana en un día "normal" (factor = 1)."""
    noches = pd.DatetimeIndex(noches)
    factor = calendario.factor[calendario.indice(noches)]
    dia = noches.dayofweek.to_numpy()
    return np.array([(real[dia == d] / factor[dia == d]).mean() for d in range(7)])


def serie_estacional(
    patron: np.ndarray, noches: pd.DatetimeIndex, calendario: TablaCalendario
) -> np.ndarray:
    """Ocupación que se esperaría solo por el día de la semana y el calendario (sin mirar reservas)."""
    noches = pd.DatetimeIndex(noches)
    return patron[noches.dayofweek.to_numpy()] * calendario.factor[calendario.indice(noches)]


def ajustar_pickup(
    reservas: pd.DataFrame,
    noches: pd.DatetimeIndex,
    patron: np.ndarray,
    predecir,
    calendario: TablaCalendario,
    tarifa_base: dict[str, float],
    horizontes: tuple[int, ...] = HORIZONTES_PICKUP,
) -> dict[int, list[float]]:
    """Coeficientes (a, b, c) por horizonte: real ≈ a + b · (reservas netas) + c · (patrón estacional).

    Las reservas netas son lo reservado menos cancelaciones y no-shows estimados. Aprende de la
    historia cuántas habitaciones se suman todavía a esa distancia de la noche (el "pickup").
    """
    real = ocupacion_real(reservas, noches)
    estacional = serie_estacional(patron, noches, calendario)
    tabla: dict[int, list[float]] = {}
    for h in horizontes:
        base = esperado_por_noche(
            reservas, noches, noches - pd.Timedelta(days=h), predecir, calendario, tarifa_base
        )["habitaciones_esperadas"].to_numpy()
        x = np.column_stack([np.ones(len(noches)), base, estacional])
        coef = np.linalg.lstsq(x, real, rcond=None)[0]
        tabla[h] = [float(c) for c in coef]
    return tabla


def prediccion_ocupacion(
    tabla: dict[int, list[float]],
    base: np.ndarray,
    estacional: np.ndarray,
    dias_hasta_la_noche: np.ndarray | int,
) -> tuple[np.ndarray, np.ndarray]:
    """(ocupación esperada, pickup) en habitaciones. ocupación = reservas netas + pickup."""
    h = np.array(sorted(tabla))
    dias = np.asarray(dias_hasta_la_noche, dtype=float)
    a, b, c = (np.interp(dias, h, [tabla[k][i] for k in h]) for i in range(3))
    total = a + b * base + c * estacional
    pickup = np.maximum(total - base, 0.0)
    return base + pickup, pickup
