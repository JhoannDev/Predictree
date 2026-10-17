def test_login_correcto_y_consulta_de_perfil(client, usuario_prueba):
    nombre, clave = usuario_prueba
    respuesta = client.post("/api/auth/login", json={"nombre_usuario": nombre, "clave": clave})
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["usuario"]["nombre_usuario"] == nombre

    perfil = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {datos['access_token']}"}
    )
    assert perfil.status_code == 200
    assert perfil.json()["nombre_usuario"] == nombre


def test_login_con_clave_incorrecta(client, usuario_prueba):
    nombre, _ = usuario_prueba
    respuesta = client.post(
        "/api/auth/login", json={"nombre_usuario": nombre, "clave": "incorrecta"}
    )
    assert respuesta.status_code == 401


def test_perfil_sin_token(client):
    assert client.get("/api/auth/me").status_code == 401
