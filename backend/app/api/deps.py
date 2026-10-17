"""Dependencias compartidas por las rutas: sesión de base de datos y usuario autenticado."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Usuario

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Usuario:
    sin_acceso = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión no válida o expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None:
        raise sin_acceso
    try:
        payload = decode_access_token(credenciales.credentials)
        id_usuario = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise sin_acceso from None

    usuario = db.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo:
        raise sin_acceso
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]
