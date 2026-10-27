"""Pruebas del generador de reservas simuladas (no necesitan la base de datos)."""

from datetime import date

import pandas as pd
import pytest

from app.simulacion.generador import ConfigGenerador, generar_reservas, ocupacion_real_por_noche
from app.simulacion.reporte import verificar_coherencia

TIPOS = pd.DataFrame(
    {
        "codigo": ["king", "doble", "junior_suite", "suite"],
        "cantidad": [150, 70, 16, 4],
        "capacidad_personas": [2, 4, 3, 4],
        "tarifa_base": [390.0, 420.0, 650.0, 1150.0],
    }
)
CALENDARIO = pd.DataFrame(
    {
        "tipo": ["feriado", "temporada_baja", "evento"],
        "fecha_inicio": [date(2025, 4, 17), date(2025, 1, 4), date(2025, 3, 10)],
        "fecha_fin": [date(2025, 4, 18), date(2025, 2, 28), date(2025, 3, 12)],
        "factor_demanda": [0.90, 0.92, 1.40],
    }
)
# Un periodo corto y sin calibrar, para que las pruebas sean rápidas.
CFG = ConfigGenerador(
    fecha_inicio=date(2025, 1, 1),
    fecha_corte=date(2025, 4, 15),
    horizonte_dias=30,
    calibrar=False,
)


@pytest.fixture(scope="module")
def resultado():
    reservas, info = generar_reservas(CFG, CALENDARIO, TIPOS)
    return reservas, info


def test_la_misma_semilla_da_las_mismas_reservas(resultado):
    otra, _ = generar_reservas(CFG, CALENDARIO, TIPOS)
    pd.testing.assert_frame_equal(resultado[0], otra)


def test_otra_semilla_da_otras_reservas(resultado):
    otra, _ = generar_reservas(ConfigGenerador(**{**CFG.__dict__, "semilla": 7}), CALENDARIO, TIPOS)
    assert not otra["tarifa_noche"].equals(resultado[0]["tarifa_noche"])


def test_cumple_las_reglas_de_coherencia(resultado):
    fallas = [nombre for nombre, ok in verificar_coherencia(resultado[0], CFG, TIPOS) if not ok]
    assert not fallas, f"Reglas que no se cumplen: {fallas}"


def test_hay_historia_y_reservas_futuras(resultado):
    estados = set(resultado[0]["estado_reserva"])
    assert {"completada", "cancelada", "no_show", "confirmada"} <= estados
    assert len(resultado[0]) > 5000


def test_la_ocupacion_esta_acotada(resultado):
    reservas, info = resultado
    ocupacion = ocupacion_real_por_noche(reservas, info["capacidad_total"])
    assert ocupacion["ocupacion_pct"].between(0, 100).all()
    assert (ocupacion["reubicaciones"] >= 0).all()
    assert (ocupacion["presentes"] >= 0).all()


def test_las_tasas_son_razonables(resultado):
    reservas = resultado[0]
    pasadas = reservas[pd.to_datetime(reservas["fecha_llegada"]) < pd.Timestamp(CFG.fecha_corte)]
    cancelacion = (pasadas["estado_reserva"] == "cancelada").mean()
    no_show = (pasadas["estado_reserva"] == "no_show").mean()
    assert 0.08 < cancelacion < 0.22
    assert 0.005 < no_show < 0.05
    # Las OTA cancelan más que la web propia: es la señal que debe aprender el modelo.
    por_canal = pasadas.groupby("canal_reserva")["estado_reserva"].apply(
        lambda s: (s == "cancelada").mean()
    )
    assert por_canal["ota"] > por_canal["web_hilton"]
