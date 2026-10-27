"""Punto de entrada de la API. Ejecutar con:  uvicorn app.main:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analisis, auth, consultas, health, tarifas
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "API de PredicTree: predicción de cancelación y no-show, ocupación esperada "
        "y riesgo de overbooking para el DoubleTree by Hilton Lima Miraflores."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(analisis.router, prefix=API_PREFIX)
app.include_router(consultas.router, prefix=API_PREFIX)
app.include_router(tarifas.router, prefix=API_PREFIX)
