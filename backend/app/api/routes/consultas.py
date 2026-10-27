"""Rutas de consulta de las pantallas de análisis: estado, ocupación, riesgo y detalle de noche."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession
from app.core.reloj import hora_hotel
from app.schemas.analisis import (
    DetalleNocheOut,
    EjecucionOut,
    EstadoOut,
    NocheOut,
    OcupacionOut,
    ReservaPesoOut,
    RiesgoOut,
)
from app.services.consultas import (
    estado_de_la_fecha,
    filas,
    mape_por_horizonte,
    noches,
    num,
    parametros,
    ultima_ejecucion,
)

router = APIRouter(tags=["Consultas"])


def _ejecucion_out(ejec: dict) -> EjecucionOut:
    return EjecucionOut(**{k: v for k, v in ejec.items() if k != "id_version"})


@router.get("/estado", response_model=EstadoOut)
def estado(db: DbSession, _: CurrentUser) -> EstadoOut:
    """Barra superior: fecha de corte, versión del modelo y si los datos están al día."""
    ejec = ultima_ejecucion(db)
    version = filas(db, "SELECT codigo_version, estado_aprobacion FROM version_modelo WHERE activa")
    simulados = True
    if ejec:
        lote = filas(
            db,
            "SELECT l.origen_datos FROM ejecucion_analisis e "
            "LEFT JOIN lote_carga l USING (id_lote) WHERE e.id_ejecucion = :e",
            e=ejec["id_ejecucion"],
        )
        simulados = not lote or lote[0]["origen_datos"] in (None, "generador")
    reloj = hora_hotel()
    corte = ejec["fecha_corte"] if ejec else None
    return EstadoOut(
        fecha_corte=corte,
        horizonte_dias=ejec["horizonte_dias"] if ejec else None,
        version=version[0]["codigo_version"] if version else None,
        estado_version=version[0]["estado_aprobacion"] if version else None,
        ultima_actualizacion=ejec["fecha_fin"] if ejec else None,
        datos_simulados=simulados,
        hoy=reloj.hoy,
        desfase_dias=(reloj.hoy - corte).days if corte else None,
        estado_fecha=estado_de_la_fecha(corte, reloj.hoy, simulados),
        fuente_hora=reloj.fuente,
        reloj_equipo_correcto=reloj.reloj_equipo_correcto,
    )


@router.get("/ocupacion", response_model=OcupacionOut)
def ocupacion(
    db: DbSession,
    _: CurrentUser,
    dias: Annotated[int, Query(ge=7, le=90)] = 90,
) -> OcupacionOut:
    ejec = ultima_ejecucion(db)
    if ejec is None:
        return OcupacionOut(ejecucion=None)
    p = parametros(db)
    return OcupacionOut(
        ejecucion=_ejecucion_out(ejec),
        noches=[NocheOut(**n) for n in noches(db, ejec, dias)],
        umbral_medio=float(p.get("umbral_riesgo_medio", 90)),
        umbral_alto=float(p.get("umbral_riesgo_alto", 98)),
        mape_por_horizonte={
            str(h): v for h, v in mape_por_horizonte(db, ejec["id_version"]).items()
        },
    )


@router.get("/riesgo", response_model=RiesgoOut)
def riesgo(
    db: DbSession,
    _: CurrentUser,
    dias: Annotated[int, Query(ge=7, le=90)] = 90,
) -> RiesgoOut:
    ejec = ultima_ejecucion(db)
    if ejec is None:
        return RiesgoOut(ejecucion=None)
    p = parametros(db)
    lista = [NocheOut(**n) for n in noches(db, ejec, dias)]
    resumen = {"bajo": 0, "medio": 0, "alto": 0}
    for n in lista:
        resumen[n.nivel_riesgo] += 1
    return RiesgoOut(
        ejecucion=_ejecucion_out(ejec),
        resumen=resumen,
        noches=lista,
        umbral_medio=float(p.get("umbral_riesgo_medio", 90)),
        umbral_alto=float(p.get("umbral_riesgo_alto", 98)),
    )


@router.get("/noches/{fecha}", response_model=DetalleNocheOut)
def detalle_noche(fecha: date, db: DbSession, _: CurrentUser) -> DetalleNocheOut:
    """Una noche con las reservas que más pesan en su riesgo (mayor chance de no llegar)."""
    ejec = ultima_ejecucion(db)
    if ejec is None:
        raise HTTPException(status_code=404, detail="Todavía no se ejecutó ningún análisis.")
    todas = noches(db, ejec)
    noche = next((n for n in todas if n["fecha"] == fecha), None)
    if noche is None:
        raise HTTPException(status_code=404, detail="Esa fecha está fuera del periodo analizado.")
    p = parametros(db)
    reservas = filas(
        db,
        """
        SELECT r.id_reserva, r.codigo_reserva, r.fecha_llegada, r.fecha_salida, r.num_habitaciones,
               r.tipo_habitacion, r.canal_reserva, r.segmento,
               p.prob_cancelacion_pct, p.prob_noshow_pct,
               r.num_habitaciones * (p.prob_cancelacion_pct + p.prob_noshow_pct) / 100
                   AS habitaciones_en_riesgo
        FROM reserva r
        JOIN prediccion p ON p.id_reserva = r.id_reserva AND p.id_ejecucion = :e
        WHERE r.estado_reserva = 'confirmada'
          AND r.fecha_llegada <= :f AND r.fecha_salida > :f
        ORDER BY habitaciones_en_riesgo DESC, r.id_reserva
        """,
        e=ejec["id_ejecucion"],
        f=fecha,
    )
    total = sum(float(r["habitaciones_en_riesgo"]) for r in reservas)
    pesan = [
        ReservaPesoOut(
            **{
                **r,
                "prob_cancelacion_pct": float(r["prob_cancelacion_pct"]),
                "prob_noshow_pct": float(r["prob_noshow_pct"]),
                "habitaciones_en_riesgo": round(float(r["habitaciones_en_riesgo"]), 2),
            }
        )
        for r in reservas[:8]
    ]
    return DetalleNocheOut(
        noche=NocheOut(**noche),
        reservas_que_pesan=pesan,
        habitaciones_en_riesgo_total=round(total, 1),
        umbral_medio=float(p.get("umbral_riesgo_medio", 90)),
        umbral_alto=float(p.get("umbral_riesgo_alto", 98)),
    )


__all__ = ["router", "num"]
