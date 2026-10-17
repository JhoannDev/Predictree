"""Contraseñas (bcrypt) y tokens de sesión (JWT)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(clave: str) -> str:
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(clave: str, clave_hash: str) -> bool:
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), clave_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    ahora = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
