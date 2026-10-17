"""Formatos de datos que entran y salen de la API de autenticación."""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    nombre_usuario: str = Field(min_length=1, max_length=30)
    clave: str = Field(min_length=1, max_length=72)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre_usuario: str
    nombre_completo: str
    rol: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
