"""Pruebas de las rutas de análisis.

Necesitan que ya se haya entrenado el modelo y corrido el análisis:

python -m scripts.entrenar_modelo
python -m scripts.ejecutar_analisis
"""

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal


@pytest.fixture
def headers(client, usuario_prueba):
    nombre, clave = usuario_prueba
    token = client.post("/api/auth/login", json={"nombre_usuario": nombre, "clave": clave}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def hay_analisis():
    with SessionLocal() as db:
        n = db.execute(
            text("SELECT count(*) FROM ejecucion_analisis WHERE estado='completada'")
        ).scalar()
    if not n:
        pytest.skip(
            "Primero ejecuta: python -m scripts.entrenar_modelo y scripts.ejecutar_analisis"
        )


@pytest.mark.parametrize(
    "ruta", ["/api/dashboard", "/api/predicciones", "/api/predicciones/resumen", "/api/modelo"]
)
def test_rutas_exigen_sesion(client, ruta):
    assert client.get(ruta).status_code == 401


def test_dashboard(client, headers, hay_analisis):
    d = client.get("/api/dashboard", headers=headers).json()
    assert d["ejecucion"]["fechas_analizadas"] == len(d["noches"]) == 90
    assert sum(d["riesgo"].values()) == 90
    assert all(n["nivel_riesgo"] == "alto" for n in d["fechas_criticas"])
    for n in d["noches"]:
        esperado = (
            n["habitaciones_reservadas"]
            - n["cancelaciones_estimadas"]
            - n["noshows_estimados"]
            + n["pickup_estimado"]
        )
        assert abs(esperado - n["ocupacion_esperada"]) < 0.1  # la fórmula de la ocupación se cumple


def test_predicciones_suman_100_y_tienen_explicacion(client, headers, hay_analisis):
    r = client.get("/api/predicciones?tamano=50", headers=headers).json()
    assert r["total"] > 0
    for it in r["items"]:
        suma = it["prob_cancelacion_pct"] + it["prob_noshow_pct"] + it["prob_presentacion_pct"]
        assert abs(suma - 100) < 0.01
        assert it["factores_explicativos"], "toda predicción debe traer su explicación"


def test_filtro_por_nivel_y_orden(client, headers, hay_analisis):
    r = client.get(
        "/api/predicciones?nivel=alto&orden=prob_cancelacion&tamano=30", headers=headers
    ).json()
    probs = [i["prob_cancelacion_pct"] for i in r["items"]]
    assert probs == sorted(probs, reverse=True)
    assert all(i["nivel_riesgo"] == "alto" for i in r["items"])


def test_modelo_expone_metricas(client, headers, hay_analisis):
    m = client.get("/api/modelo", headers=headers).json()
    assert m["version"]["activa"] is True
    tipos = {e["tipo_evaluacion"] for e in m["evaluaciones"]}
    assert tipos == {"cancelacion", "no_show", "ocupacion"}
