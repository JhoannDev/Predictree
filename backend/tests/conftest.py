import os
import uuid

os.environ.setdefault("VERIFICAR_HORA_INTERNET", "false")  # las pruebas no usan la red

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Usuario  # noqa: E402


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
