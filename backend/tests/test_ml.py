"""Pruebas de las reglas básicas del modelo (sin entrenar nada)."""

from datetime import date

import numpy as np
import pandas as pd

from app.ml.calendario import construir_calendario
from app.ml.features import FEATURES, construir_features, construir_snapshots, etiquetas
from app.ml.modelo import mape
from app.ml.ocupacion import ocupacion_real

TARIFAS = {"king": 300.0, "doble": 280.0, "junior_suite": 420.0, "suite": 700.0}


def _reservas() -> pd.DataFrame:
    base = {
        "tipo_habitacion": "king", "num_habitaciones": 1, "adultos": 2, "ninos": 0,
        "canal_reserva": "ota", "segmento": "ocio", "politica_tarifa": "flexible",
        "tarifa_noche": 300.0, "procedencia": "nacional", "huesped_recurrente": False,
        "cancelaciones_previas": 0, "solicitudes_especiales": 0,
    }  # fmt: skip
    filas = [
        {**base, "id_reserva": 1, "fecha_reserva": "2026-01-01", "fecha_llegada": "2026-02-10",
         "fecha_salida": "2026-02-12", "estado_reserva": "completada", "fecha_cancelacion": None},
        {**base, "id_reserva": 2, "fecha_reserva": "2026-01-01", "fecha_llegada": "2026-02-10",
         "fecha_salida": "2026-02-11", "estado_reserva": "cancelada",
         "fecha_cancelacion": "2026-02-05"},
        {**base, "id_reserva": 3, "fecha_reserva": "2026-02-08", "fecha_llegada": "2026-02-10",
         "fecha_salida": "2026-02-13", "estado_reserva": "no_show", "fecha_cancelacion": None},
    ]  # fmt: skip
    df = pd.DataFrame(filas)
    for c in ("fecha_reserva", "fecha_llegada", "fecha_salida", "fecha_cancelacion"):
        df[c] = pd.to_datetime(df[c])
    return df


def _calendario():
    cal = pd.DataFrame(
        {
            "tipo": ["feriado"],
            "fecha_inicio": ["2026-02-11"],
            "fecha_fin": ["2026-02-11"],
            "factor_demanda": [0.9],
        }
    )
    return construir_calendario(cal, date(2025, 12, 1), date(2026, 6, 1))


def test_las_variables_no_incluyen_el_resultado():
    assert "estado_reserva" not in FEATURES
    assert "fecha_cancelacion" not in FEATURES


def test_foto_solo_incluye_reservas_vigentes():
    x, y, info = construir_snapshots(_reservas(), (1, 3, 7), _calendario(), TARIFAS)

    def vigentes(h):
        return sorted(info[info["horizonte"] == h]["id_reserva"].tolist())

    assert vigentes(7) == [1, 2]  # la 2 aún no se cancela (cancela 5 días antes); la 3 no existe
    assert vigentes(3) == [1]  # la 2 ya se canceló; la 3 se reserva recién 2 días antes
    assert vigentes(1) == [1, 3]  # la 3 ya existe; la 2 sigue cancelada
    assert len(x) == len(y) == len(info)


def test_features_usan_la_fecha_de_referencia():
    r = _reservas().iloc[[0]]
    x = construir_features(r, pd.to_datetime(["2026-02-05"]), _calendario(), TARIFAS)
    assert x["dias_hasta_llegada"].iloc[0] == 5
    assert x["dias_desde_reserva"].iloc[0] == 35
    assert x["hay_feriado_estadia"].iloc[0] == 1  # la estadía incluye el feriado del 11


def test_etiquetas_y_mape():
    assert etiquetas(_reservas()).tolist() == [0, 1, 2]
    assert mape(np.array([100.0, 200.0]), np.array([110.0, 180.0])) == 10.0


def test_ocupacion_real_cuenta_solo_huespedes_que_se_presentaron():
    noches = pd.date_range("2026-02-09", "2026-02-13")
    real = ocupacion_real(_reservas(), noches)
    assert real.tolist() == [0, 1, 1, 0, 0]  # solo la reserva 1 (10 y 11 de febrero)
