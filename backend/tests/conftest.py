import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models import Usuario


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def usuario_prueba():
    """Crea un usuario temporal en la base de datos y lo elimina al terminar la prueba."""
    nombre = f"test_{uuid.uuid4().hex[:8]}"
    clave = "ClavePrueba123"
    with SessionLocal() as db:
        db.add(
            Usuario(
                nombre_usuario=nombre,
                nombre_completo="Usuario de prueba",
                clave_hash=hash_password(clave),
                rol="revenue_management",
                activo=True,
            )
        )
        db.commit()
    yield nombre, clave
    with SessionLocal() as db:
        db.execute(delete(Usuario).where(Usuario.nombre_usuario == nombre))
        db.commit()
