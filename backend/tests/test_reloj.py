"""Pruebas de la hora del hotel: zona horaria y corrección con la hora de internet."""

from datetime import UTC, datetime, timedelta

from app.core import reloj


def test_sin_internet_usa_el_equipo_en_zona_lima(monkeypatch):
    monkeypatch.setattr(reloj, "_diferencia_internet", lambda: None)
    h = reloj.hora_hotel()
    assert h.fuente == "equipo" and h.reloj_equipo_correcto is None
    assert h.ahora.utcoffset() == timedelta(hours=-5)  # Lima no usa horario de verano


def test_con_internet_corrige_un_reloj_mal_puesto(monkeypatch):
    # el equipo está 3 días atrasado respecto a internet
    monkeypatch.setattr(reloj, "_diferencia_internet", lambda: timedelta(days=3))
    h = reloj.hora_hotel()
    esperado = (datetime.now(UTC) + timedelta(days=3)).astimezone(h.ahora.tzinfo)
    assert h.fuente == "internet" and h.reloj_equipo_correcto is False
    assert abs(h.ahora - esperado) < timedelta(seconds=5)


def test_reloj_con_poca_diferencia_es_correcto(monkeypatch):
    monkeypatch.setattr(reloj, "_diferencia_internet", lambda: timedelta(seconds=40))
    assert reloj.hora_hotel().reloj_equipo_correcto is True


def test_la_consulta_a_internet_se_reutiliza(monkeypatch):
    llamadas = []
    monkeypatch.setattr(reloj.settings, "verificar_hora_internet", True)
    monkeypatch.setattr(reloj, "_consultar_internet", lambda: llamadas.append(1) or timedelta(0))
    reloj.reiniciar_cache()
    reloj.hora_hotel()
    reloj.hora_hotel()
    reloj.reiniciar_cache()
    assert len(llamadas) == 1
