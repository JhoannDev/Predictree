from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models import Usuario
from app.schemas.auth import LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: DbSession) -> TokenResponse:
    usuario = db.scalar(select(Usuario).where(Usuario.nombre_usuario == datos.nombre_usuario))
    credenciales_validas = (
        usuario is not None and usuario.activo and verify_password(datos.clave, usuario.clave_hash)
    )
    if not credenciales_validas:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos"
        )
    token = create_access_token(str(usuario.id_usuario), {"rol": usuario.rol})
    return TokenResponse(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router.get("/me", response_model=UsuarioOut)
def me(usuario: CurrentUser) -> Usuario:
    return usuario
