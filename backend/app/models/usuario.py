from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    """Tabla "usuario" (definida en database/01_schema.sql)."""

    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column(String(30), unique=True)
    nombre_completo: Mapped[str] = mapped_column(String(100))
    clave_hash: Mapped[str] = mapped_column(String(256))
    rol: Mapped[str] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
