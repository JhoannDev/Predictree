"""Rutas de análisis: dashboard, predicciones por reserva y métricas del modelo."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.api.deps import CurrentUser, DbSession
from app.schemas.analisis import (
    DashboardOut,
    EjecucionOut,
    ModeloOut,
    NocheOut,
    PrediccionesPagina,
    PrediccionesResumen,
)
from app.services.analisis import SinModeloActivo, ejecutar_analisis
from app.services.consultas import filas, noches, num, parametros, ultima_ejecucion

router = APIRouter(tags=["Análisis"])

NIVEL_SQL = {
    "alto": "p.prob_cancelacion_pct >= :u * 2",
    "medio": "p.prob_cancelacion_pct >= :u AND p.prob_cancelacion_pct < :u * 2",
    "bajo": "p.prob_cancelacion_pct < :u",
}
ORDENES = {
    "llegada": "r.fecha_llegada ASC, r.id_reserva",
    "prob_cancelacion": "p.prob_cancelacion_pct DESC, r.fecha_llegada",
    "prob_noshow": "p.prob_noshow_pct DESC, r.fecha_llegada",
    "importe": "r.importe_total DESC, r.fecha_llegada",
}


_filas = filas
_num = num


def _evaluaciones(db, id_version: int) -> list[dict[str, Any]]:
    return _filas(
        db,
        """
        SELECT tipo_evaluacion, periodo_inicio, periodo_fin, registros_evaluados, f1_score,
               precision_score, recall_score, accuracy_score, mape, valor_meta, cumple_meta, detalle
        FROM evaluacion_modelo WHERE id_version = :v ORDER BY id_evaluacion
        """,
        v=id_version,
    )


def _umbral_cancelacion_pct(db) -> float:
    """Umbral (en %) de cancelación del modelo: desde ahí el riesgo es medio; el doble es riesgo alto."""
    fila = db.execute(
        text(
            """
            SELECT e.detalle->'umbrales'->>'cancelacion'
            FROM evaluacion_modelo e JOIN version_modelo v USING (id_version)
            WHERE v.activa AND e.tipo_evaluacion = 'cancelacion'
            """
        )
    ).first()
    return round(float(fila[0]) * 100, 2) if fila and fila[0] else 15.0


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    db: DbSession,
    _: CurrentUser,
    dias: Annotated[int, Query(ge=7, le=90)] = 90,
) -> DashboardOut:
    ejec = ultima_ejecucion(db)
    if ejec is None:
        return DashboardOut(ejecucion=None)
    p = parametros(db)
    todas = [NocheOut(**n) for n in noches(db, ejec, dias)]
    resumen = _filas(
        db,
        """
        SELECT count(*) AS n, avg(prob_cancelacion_pct) AS pc, avg(prob_noshow_pct) AS pn
        FROM prediccion WHERE id_ejecucion = :e
        """,
        e=ejec["id_ejecucion"],
    )[0]
    # Habitaciones que se espera perder en el periodo mostrado (cancelaciones + no-shows).
    en_riesgo = sum(n.cancelaciones_estimadas + n.noshows_estimados for n in todas)
    riesgo = {"bajo": 0, "medio": 0, "alto": 0}
    for n in todas:
        riesgo[n.nivel_riesgo] += 1
    pico = max(todas, key=lambda n: n.porcentaje_ocupacion)
    metricas: dict[str, Any] = {}
    for e in _evaluaciones(db, ejec["id_version"]):
        metricas[e["tipo_evaluacion"]] = {
            "f1": _num(e["f1_score"]),
            "mape": _num(e["mape"]),
            "meta": _num(e["valor_meta"]),
            "cumple_meta": e["cumple_meta"],
        }
    atencion = [n for n in todas if n.nivel_riesgo != "bajo"]
    atencion.sort(key=lambda n: (n.nivel_riesgo != "alto", n.fecha))
    return DashboardOut(
        ejecucion=EjecucionOut(**{k: v for k, v in ejec.items() if k != "id_version"}),
        dias=dias,
        ocupacion_media_pct=round(sum(n.porcentaje_ocupacion for n in todas) / len(todas), 1),
        ocupacion_pico_pct=pico.porcentaje_ocupacion,
        fecha_pico=pico.fecha,
        prob_cancelacion_media_pct=round(_num(resumen["pc"], 0), 1),
        prob_noshow_media_pct=round(_num(resumen["pn"], 0), 1),
        reservas_evaluadas=resumen["n"],
        habitaciones_en_riesgo=round(en_riesgo, 1),
        riesgo=riesgo,
        noches=todas,
        fechas_criticas=[n for n in todas if n.nivel_riesgo == "alto"],
        proximas_atencion=atencion[:6],
        umbral_medio=float(p.get("umbral_riesgo_medio", 90)),
        umbral_alto=float(p.get("umbral_riesgo_alto", 98)),
        metricas=metricas,
    )


@router.get("/predicciones", response_model=PrediccionesPagina)
def predicciones(
    db: DbSession,
    _: CurrentUser,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=5, le=100)] = 20,
    orden: Literal["llegada", "prob_cancelacion", "prob_noshow", "importe"] = "prob_cancelacion",
    nivel: Literal["alto", "medio", "bajo"] | None = None,
    canal: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    buscar: Annotated[str | None, Query(max_length=30)] = None,
) -> PrediccionesPagina:
    u = _umbral_cancelacion_pct(db)
    filtros, params = (
        ["p.id_version = (SELECT id_version FROM version_modelo WHERE activa)"],
        {"u": u},
    )
    if nivel:
        filtros.append(NIVEL_SQL[nivel])
    if canal:
        filtros.append("r.canal_reserva = :canal")
        params["canal"] = canal
    if desde:
        filtros.append("r.fecha_llegada >= CAST(:desde AS date)")
        params["desde"] = desde
    if hasta:
        filtros.append("r.fecha_llegada <= CAST(:hasta AS date)")
        params["hasta"] = hasta
    if buscar:
        filtros.append("r.codigo_reserva ILIKE :buscar")
        params["buscar"] = f"%{buscar}%"
    donde = " AND ".join(filtros)
    total = db.execute(
        text(f"SELECT count(*) FROM prediccion p JOIN reserva r USING (id_reserva) WHERE {donde}"),
        params,
    ).scalar_one()
    filas = _filas(
        db,
        f"""
        SELECT r.id_reserva, r.codigo_reserva, r.fecha_reserva, r.fecha_llegada, r.fecha_salida,
               r.noches, r.tipo_habitacion, r.num_habitaciones, r.canal_reserva, r.segmento,
               r.politica_tarifa, r.tarifa_noche, r.importe_total, p.prob_cancelacion_pct,
               p.prob_noshow_pct, p.prob_presentacion_pct, p.resultado_predicho,
               CASE WHEN p.prob_cancelacion_pct >= :u * 2 THEN 'alto'
                    WHEN p.prob_cancelacion_pct >= :u THEN 'medio' ELSE 'bajo' END AS nivel_riesgo,
               p.factores_explicativos
        FROM prediccion p JOIN reserva r USING (id_reserva)
        WHERE {donde} ORDER BY {ORDENES[orden]} LIMIT :lim OFFSET :off
        """,
        **params,
        lim=tamano,
        off=(pagina - 1) * tamano,
    )
    for f in filas:
        for k in ("tarifa_noche", "importe_total", "prob_cancelacion_pct", "prob_noshow_pct", "prob_presentacion_pct"):  # fmt: skip
            f[k] = float(f[k])
    return PrediccionesPagina(total=total, pagina=pagina, tamano=tamano, items=filas)


@router.get("/predicciones/resumen", response_model=PrediccionesResumen)
def predicciones_resumen(db: DbSession, _: CurrentUser) -> PrediccionesResumen:
    u = _umbral_cancelacion_pct(db)
    base = "FROM prediccion p JOIN reserva r USING (id_reserva) WHERE p.id_version = (SELECT id_version FROM version_modelo WHERE activa)"  # fmt: skip
    gen = _filas(
        db,
        f"""
        SELECT count(*) AS n, coalesce(avg(prob_cancelacion_pct), 0) AS pc,
               coalesce(avg(prob_noshow_pct), 0) AS pn,
               count(*) FILTER (WHERE prob_cancelacion_pct >= :u * 2) AS alto,
               count(*) FILTER (WHERE prob_cancelacion_pct >= :u AND prob_cancelacion_pct < :u * 2) AS medio,
               count(*) FILTER (WHERE prob_cancelacion_pct < :u) AS bajo {base}
        """,
        u=u,
    )[0]
    histograma = _filas(
        db,
        f"""
        SELECT least(floor(prob_cancelacion_pct / 5), 7)::int AS tramo, count(*) AS reservas {base}
        GROUP BY 1 ORDER BY 1
        """,
    )
    nombres = {t["tramo"]: t["reservas"] for t in histograma}
    hist = [
        {
            "rango": f"{i * 5}–{i * 5 + 5} %" if i < 7 else "35 % o más",
            "reservas": nombres.get(i, 0),
        }
        for i in range(8)
    ]

    def agrupar(col: str):
        filas = _filas(
            db,
            f"""
            SELECT r.{col} AS grupo, count(*) AS reservas, avg(prob_cancelacion_pct) AS cancelacion,
                   avg(prob_noshow_pct) AS noshow {base} GROUP BY 1 ORDER BY 3 DESC
            """,
        )
        return [
            {
                "grupo": f["grupo"],
                "reservas": f["reservas"],
                "cancelacion": round(float(f["cancelacion"]), 1),
                "noshow": round(float(f["noshow"]), 1),
            }
            for f in filas
        ]

    return PrediccionesResumen(
        total=gen["n"],
        prob_cancelacion_media_pct=round(float(gen["pc"]), 1),
        prob_noshow_media_pct=round(float(gen["pn"]), 1),
        por_nivel={"alto": gen["alto"], "medio": gen["medio"], "bajo": gen["bajo"]},
        histograma=hist,
        por_canal=agrupar("canal_reserva"),
        por_segmento=agrupar("segmento"),
        umbral_cancelacion_pct=u,
    )


@router.get("/modelo", response_model=ModeloOut)
def modelo(db: DbSession, _: CurrentUser) -> ModeloOut:
    version = _filas(
        db,
        """
        SELECT id_version, codigo_version, descripcion, algoritmo, fecha_entrenamiento,
               periodo_entrenamiento_inicio, periodo_entrenamiento_fin, hiperparametros,
               estado_aprobacion, activa
        FROM version_modelo WHERE activa
        """,
    )
    if not version:
        return ModeloOut(version=None)
    v = version[0]
    par = parametros(db)
    evals = _evaluaciones(db, v["id_version"])
    salida = []
    importancia: list[dict[str, Any]] = []
    umbrales: dict[str, float] = {}
    for e in evals:
        det = e.pop("detalle") or {}
        for k in (
            "f1_score",
            "precision_score",
            "recall_score",
            "accuracy_score",
            "mape",
            "valor_meta",
        ):
            e[k] = _num(e[k])
        e["detalle"] = {k: val for k, val in det.items() if k != "importancia_variables"}
        importancia = det.get("importancia_variables", importancia)
        umbrales = {**umbrales, **det.get("umbrales", {})}
        salida.append(e)
    return ModeloOut(
        version=v,
        evaluaciones=salida,
        importancia_variables=importancia,
        umbrales=umbrales,
        metas={
            "f1_cancelacion": float(par.get("meta_f1_cancelacion", 0.80)),
            "f1_noshow": float(par.get("meta_f1_noshow", 0.75)),
            "mape_ocupacion": float(par.get("meta_mape_ocupacion", 15)),
            "deteccion_riesgo_pct": 80.0,
        },
        notas=[
            "Los datos de reservas son simulados (ver docs/supuestos_datos_simulados.md).",
            "Las métricas se calculan sobre llegadas posteriores al periodo de entrenamiento, "
            "que el modelo no vio al aprender.",
            "La ocupación esperada = reservadas - cancelaciones - no-shows + pickup histórico.",
        ],
    )


@router.post("/analisis/ejecutar", response_model=EjecucionOut)
def ejecutar(db: DbSession, usuario: CurrentUser) -> EjecucionOut:
    """Vuelve a correr el análisis completo con el modelo activo."""
    try:
        r = ejecutar_analisis(db.connection(), usuario.id_usuario)
    except SinModeloActivo as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from None
    db.commit()
    ejec = ultima_ejecucion(db)
    assert ejec is not None and ejec["id_ejecucion"] == r.id_ejecucion
    return EjecucionOut(**{k: v for k, v in ejec.items() if k != "id_version"})
