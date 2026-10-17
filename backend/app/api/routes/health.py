from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter(prefix="/health", tags=["Estado"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok", "servicio": "PredicTree API"}


@router.get("/db")
def health_db(db: DbSession) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "base_de_datos": "conectada"}
