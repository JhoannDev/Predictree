"""Pruebas de las rutas de consulta: estado, ocupación, riesgo, noches y tarifas.

Necesitan el modelo entrenado y el análisis ejecutado (ver test_analisis.py).
"""

from datetime import date

import pytest
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.consultas import error_esperado_pct
from app.services.tarifas import recalcular_sugerencias

from .test_analisis import hay_analisis, headers  # noqa: F401


@pytest.mark.parametrize(
    "ruta",
    ["/api/estado", "/api/ocupacion", "/api/riesgo", "/api/noches/2026-11-05", "/api/tarifas"],
)
def test_rutas_exigen_sesion(client, ruta):
    assert client.get(ruta).status_code == 401


def test_estado(client, headers, hay_analisis):  # noqa: F811
    e = client.get("/api/estado", headers=headers).json()
    assert e["fecha_corte"] == "2026-10-31"
    assert e["version"] and e["datos_simulados"] is True


def test_ocupacion_con_banda(client, headers, hay_analisis):  # noqa: F811
    r = client.get("/api/ocupacion?dias=30", headers=headers).json()
    assert len(r["noches"]) == 30
    for n in r["noches"]:
        assert n["banda_inf_pct"] <= n["porcentaje_ocupacion"] <= n["banda_sup_pct"]
    # a más anticipación, banda más ancha
    assert r["noches"][-1]["error_esperado_pct"] >= r["noches"][0]["error_esperado_pct"]
    assert set(r["mape_por_horizonte"]) >= {"7", "30", "90"}


def test_riesgo_resumen_coincide(client, headers, hay_analisis):  # noqa: F811
    r = client.get("/api/riesgo", headers=headers).json()
    assert sum(r["resumen"].values()) == len(r["noches"]) == 90
    for n in r["noches"]:
        pct = n["porcentaje_ocupacion"]
        esperado = "alto" if pct >= 98 else "medio" if pct >= 90 else "bajo"
        assert n["nivel_riesgo"] == esperado


def test_detalle_de_noche(client, headers, hay_analisis):  # noqa: F811
    d = client.get("/api/noches/2026-11-05", headers=headers).json()
    assert d["noche"]["fecha"] == "2026-11-05"
    pesan = d["reservas_que_pesan"]
    assert pesan and len(pesan) <= 8
    riesgos = [p["habitaciones_en_riesgo"] for p in pesan]
    assert riesgos == sorted(riesgos, reverse=True)
    assert d["habitaciones_en_riesgo_total"] >= sum(riesgos) - 0.5


def test_noche_fuera_del_periodo(client, headers, hay_analisis):  # noqa: F811
    assert client.get("/api/noches/2030-01-01", headers=headers).status_code == 404


def test_dashboard_por_rango(client, headers, hay_analisis):  # noqa: F811
    d7 = client.get("/api/dashboard?dias=7", headers=headers).json()
    assert len(d7["noches"]) == 7 and sum(d7["riesgo"].values()) == 7
    assert d7["ocupacion_pico_pct"] == max(n["porcentaje_ocupacion"] for n in d7["noches"])


def test_toda_noche_tiene_sugerencia(client, headers, hay_analisis):  # noqa: F811
    t = client.get("/api/tarifas", headers=headers).json()
    assert t["cobertura_pct"] == 100  # RNF-12
    for n in t["noches"]:
        assert n["tarifa_referencia"] and n["tarifa_sugerida"]
        esperado = n["tarifa_referencia"] * (1 + n["ajuste_recomendado"] / 100)
        assert abs(esperado - n["tarifa_sugerida"]) < 0.02
    assert client.get("/api/tarifas?nivel=alto", headers=headers).status_code == 200


def test_tarifa_de_referencia_manual_y_vuelta_a_automatica(client, headers, hay_analisis):  # noqa: F811
    try:
        # Modo manual sin todas las tarifas: se rechaza.
        mal = client.put(
            "/api/tarifas/referencia",
            json={"modo": "manual", "tarifas": {"king": 400}},
            headers=headers,
        )
        assert mal.status_code == 422
        malo = client.put(
            "/api/tarifas/referencia",
            json={
                "modo": "manual",
                "tarifas": {"king": -1, "doble": 1, "junior_suite": 1, "suite": 1},
            },
            headers=headers,
        )
        assert malo.status_code == 422

        tarifas = {"king": 400, "doble": 450, "junior_suite": 700, "suite": 1200}
        ok = client.put(
            "/api/tarifas/referencia", json={"modo": "manual", "tarifas": tarifas}, headers=headers
        )
        assert ok.status_code == 200 and ok.json()["modo"] == "manual"
        for n in client.get("/api/tarifas", headers=headers).json()["noches"]:
            assert 400 <= n["tarifa_referencia"] <= 1200
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM parametro_sistema WHERE clave LIKE 'tarifa\\_ref%'"))
            ejec = db.execute(
                text("SELECT max(id_ejecucion) FROM ejecucion_analisis WHERE estado='completada'")
            ).scalar()
            recalcular_sugerencias(db.connection(), ejec)
            db.commit()
    assert client.get("/api/tarifas/referencia", headers=headers).json()["modo"] == "automatica"


def test_error_esperado_crece_con_la_anticipacion():
    tabla = {7: 4.0, 30: 7.0, 90: 9.0}
    assert error_esperado_pct(tabla, 0) == 4.0
    assert error_esperado_pct(tabla, 18.5) == pytest.approx(5.5)
    assert error_esperado_pct(tabla, 200) == 9.0
    assert error_esperado_pct({}, 10) == 0.0


def test_estado_de_la_fecha():
    from app.services.consultas import estado_de_la_fecha

    corte = date(2026, 10, 31)
    assert estado_de_la_fecha(None, date(2026, 10, 31), False) == "sin_datos"
    assert estado_de_la_fecha(corte, date(2026, 10, 27), True) == "simulado"
    assert estado_de_la_fecha(corte, date(2026, 10, 31), False) == "al_dia"
    assert estado_de_la_fecha(corte, date(2026, 11, 1), False) == "al_dia"
    assert estado_de_la_fecha(corte, date(2026, 11, 2), False) == "desactualizado"
    assert estado_de_la_fecha(corte, date(2026, 10, 30), False) == "adelantado"


def test_estado_incluye_fecha_de_hoy(client, headers, hay_analisis):  # noqa: F811
    e = client.get("/api/estado", headers=headers).json()
    assert e["estado_fecha"] == "simulado"
    assert e["hoy"] and e["fuente_hora"] in ("internet", "equipo")
    assert (
        e["desfase_dias"]
        == (
            __import__("datetime").date.fromisoformat(e["hoy"])
            - __import__("datetime").date(2026, 10, 31)
        ).days
    )
