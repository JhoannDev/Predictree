from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_y_verificacion_de_clave():
    clave_hash = hash_password("MiClaveSegura1")
    assert clave_hash != "MiClaveSegura1"
    assert verify_password("MiClaveSegura1", clave_hash)
    assert not verify_password("otra_clave", clave_hash)


def test_token_contiene_el_usuario():
    token = create_access_token("42", {"rol": "revenue_management"})
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["rol"] == "revenue_management"
