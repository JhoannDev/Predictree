"""Rutas de sugerencias de tarifa y de la tarifa de referencia editable."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.analisis import (
    EjecucionOut,
    NocheOut,
    ReferenciaTarifaIn,
    ReferenciaTarifaOut,
    TarifasOut,
    TarifaTipoOut,
)
from app.services.consultas import noches, ultima_ejecucion
from app.services.tarifas import (
    TarifaInvalida,
    guardar_referencia,
    leer_referencia,
    promedio_reservado,
    recalcular_sugerencias,
    tipos_habitacion,
)

router = APIRouter(prefix="/tarifas", tags=["Tarifas"])


def _referencia(db) -> ReferenciaTarifaOut:
    modo, manual = leer_referencia(db)
    promedios = promedio_reservado(db)
    return ReferenciaTarifaOut(
        modo=modo,
        tipos=[
            TarifaTipoOut(
                codigo=t["codigo"],
                nombre=t["nombre"],
                tarifa_catalogo=t["tarifa_base"],
                promedio_reservas=round(promedios[t["codigo"]], 2)
                if t["codigo"] in promedios
                else None,
                referencia=manual.get(t["codigo"]),
            )
            for t in tipos_habitacion(db)
        ],
    )


@router.get("", response_model=TarifasOut)
def tarifas(
    db: DbSession,
    _: CurrentUser,
    nivel: Literal["alto", "medio", "bajo"] | None = None,
    dias: Annotated[int, Query(ge=7, le=90)] = 90,
) -> TarifasOut:
    ejec = ultima_ejecucion(db)
    if ejec is None:
        return TarifasOut(ejecucion=None, referencia=_referencia(db))
    todas = noches(db, ejec, dias)
    criticas = [n for n in todas if n["nivel_riesgo"] == "alto"]
    con = [n for n in criticas if n["tipo_sugerencia"] is not None]
    lista = [n for n in todas if nivel is None or n["nivel_riesgo"] == nivel]
    return TarifasOut(
        ejecucion=EjecucionOut(**{k: v for k, v in ejec.items() if k != "id_version"}),
        fechas_criticas=len(criticas),
        con_sugerencia=len(con),
        cobertura_pct=round(len(con) / len(criticas) * 100, 1) if criticas else 100.0,
        noches=[NocheOut(**n) for n in lista],
        referencia=_referencia(db),
    )


@router.get("/referencia", response_model=ReferenciaTarifaOut)
def ver_referencia(db: DbSession, _: CurrentUser) -> ReferenciaTarifaOut:
    return _referencia(db)


@router.put("/referencia", response_model=ReferenciaTarifaOut)
def cambiar_referencia(
    datos: ReferenciaTarifaIn, db: DbSession, _: CurrentUser
) -> ReferenciaTarifaOut:
    """Guarda la tarifa de referencia y recalcula las sugerencias (no cambia tarifas reales)."""
    try:
        guardar_referencia(db, datos.modo, datos.tarifas)
    except TarifaInvalida as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from None
    ejec = ultima_ejecucion(db)
    if ejec is not None:
        recalcular_sugerencias(db.connection(), ejec["id_ejecucion"])
    db.commit()
    return _referencia(db)
