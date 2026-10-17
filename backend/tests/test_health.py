def test_health(client):
    respuesta = client.get("/api/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"


def test_health_db(client):
    respuesta = client.get("/api/health/db")
    assert respuesta.status_code == 200
    assert respuesta.json()["base_de_datos"] == "conectada"
