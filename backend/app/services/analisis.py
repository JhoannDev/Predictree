"""Ejecución del análisis: predicciones por reserva, ocupación esperada, riesgo y tarifas sugeridas."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import BACKEND_DIR
from app.ml.datos import EntradasModelo, leer_entradas
from app.ml.explicacion import explicar
from app.ml.features import construir_features, construir_snapshots
from app.ml.modelo import ArtefactoModelo, cargar
from app.ml.ocupacion import esperado_por_noche
from app.services.tarifas import recalcular_sugerencias

RAIZ = BACKEND_DIR.parent


class SinModeloActivo(RuntimeError):
    """No hay una versión de modelo activa: primero hay que entrenar (scripts.entrenar_modelo)."""


@dataclass
class ResultadoAnalisis:
    id_ejecucion: int
    id_version: int
    reservas_procesadas: int
    fechas_analizadas: int
    fechas_criticas: int


def nivel_riesgo(porcentaje: float, umbral_medio: float, umbral_alto: float) -> str:
    if porcentaje >= umbral_alto:
        return "alto"
    if porcentaje >= umbral_medio:
        return "medio"
    return "bajo"


def version_activa(conexion: Connection) -> tuple[int, ArtefactoModelo]:
    fila = conexion.execute(
        text("SELECT id_version, ruta_artefacto FROM version_modelo WHERE activa")
    ).first()
    if fila is None:
        raise SinModeloActivo("No hay un modelo activo. Ejecuta: python -m scripts.entrenar_modelo")
    ruta = RAIZ / fila.ruta_artefacto
    if not ruta.exists():
        raise SinModeloActivo(
            f"No se encontró el archivo del modelo ({ruta}). Vuelve a entrenarlo."
        )
    return fila.id_version, cargar(ruta)


def _predicciones(
    art: ArtefactoModelo, entradas: EntradasModelo
) -> tuple[pd.DataFrame, np.ndarray, list[list[dict]]]:
    """Probabilidades, clase predicha y explicación de las reservas confirmadas que llegan en el horizonte."""
    corte = pd.Timestamp(entradas.fecha_corte)
    fin = corte + pd.Timedelta(days=entradas.horizonte)
    r = entradas.reservas
    futuras = r[
        (r["estado_reserva"] == "confirmada")
        & (r["fecha_llegada"] >= corte)
        & (r["fecha_llegada"] < fin)
    ].reset_index(drop=True)
    x = construir_features(
        futuras, np.full(len(futuras), corte), entradas.calendario, entradas.tarifa_base
    )
    prob = art.probabilidades(x)
    clase = art.clasificar(prob)
    pasadas = r[r["fecha_llegada"] < corte].sample(3000, random_state=0)
    referencia, _, _ = construir_snapshots(
        pasadas, (14,), entradas.calendario, entradas.tarifa_base
    )
    factores = explicar(art.modelo, x, referencia)
    return futuras, np.column_stack([prob, clase]), factores


def _guardar_predicciones(conexion, id_version, id_ejecucion, futuras, matriz, factores) -> None:
    nombres = ("se_presenta", "cancelacion", "no_show")
    conexion.execute(text("DELETE FROM prediccion WHERE id_version = :v"), {"v": id_version})
    filas = []
    for i, id_reserva in enumerate(futuras["id_reserva"].to_numpy()):
        pc = round(float(matriz[i, 1]) * 100, 2)
        pn = round(float(matriz[i, 2]) * 100, 2)
        if pc + pn > 100:
            pn = round(100 - pc, 2)
        filas.append(
            {
                "r": int(id_reserva), "v": id_version, "e": id_ejecucion, "pc": pc, "pn": pn,
                "res": nombres[int(matriz[i, 3])], "f": json.dumps(factores[i], ensure_ascii=False),
            }
        )  # fmt: skip
    if filas:
        conexion.execute(
            text(
                """
                INSERT INTO prediccion (id_reserva, id_version, id_ejecucion, prob_cancelacion_pct,
                    prob_noshow_pct, resultado_predicho, factores_explicativos)
                VALUES (:r, :v, :e, :pc, :pn, :res, CAST(:f AS jsonb))
                """
            ),
            filas,
        )


def _motivo(fecha, pct, hab, capacidad, eventos: pd.DataFrame) -> str:
    texto = f"Ocupación esperada {pct:.1f} % ({hab:.0f} de {capacidad} habitaciones)"
    activos = eventos[(eventos["fecha_inicio"] <= fecha) & (eventos["fecha_fin"] >= fecha)]
    nombres = activos[activos["tipo"].isin(["evento", "feriado"])]["nombre"].tolist()
    if nombres:
        texto += " · " + ", ".join(nombres)
    return texto[:200]


def _guardar_ocupacion(conexion, id_version, id_ejecucion, art, entradas) -> tuple[int, int]:
    corte = pd.Timestamp(entradas.fecha_corte)
    noches = pd.date_range(corte, periods=entradas.horizonte, freq="D")
    esp = esperado_por_noche(
        entradas.reservas,
        noches,
        pd.DatetimeIndex([corte] * len(noches)),
        art.probabilidades,
        entradas.calendario,
        entradas.tarifa_base,
    )
    dias = (noches - corte).days.to_numpy()
    base = esp["habitaciones_esperadas"].to_numpy()
    esperada, pickup = art.ocupacion_final(base, noches, entradas.calendario, dias)
    cap = entradas.capacidad

    conexion.execute(
        text("DELETE FROM ocupacion_esperada WHERE id_version = :v"), {"v": id_version}
    )
    eventos = pd.read_sql(
        text("SELECT nombre, tipo, fecha_inicio, fecha_fin FROM fecha_especial"), conexion
    )
    eventos["fecha_inicio"] = pd.to_datetime(eventos["fecha_inicio"])
    eventos["fecha_fin"] = pd.to_datetime(eventos["fecha_fin"])
    reglas = {
        f.nivel_riesgo: f
        for f in conexion.execute(text("SELECT * FROM regla_tarifa WHERE activa")).all()
    }
    criticas = 0
    for j, fecha in enumerate(noches):
        pct = float(esperada[j] / cap * 100)
        hab_res = float(esp["habitaciones_reservadas"].iloc[j])
        tarifa = float(esp["ingreso_reservado"].iloc[j] / hab_res) if hab_res > 0 else None
        id_ocup = conexion.execute(
            text(
                """
                INSERT INTO ocupacion_esperada (id_ejecucion, id_version, fecha_analizada,
                    reservas_registradas, habitaciones_reservadas, cancelaciones_estimadas,
                    noshows_estimados, pickup_estimado, ocupacion_esperada, capacidad_disponible,
                    porcentaje_ocupacion, tarifa_promedio)
                VALUES (:e, :v, :f, :rr, :hr, :ce, :ne, :pk, :oe, :cap, :pct, :t)
                RETURNING id_ocupacion
                """
            ),
            {
                "e": id_ejecucion, "v": id_version, "f": fecha.date(),
                "rr": int(esp["reservas_registradas"].iloc[j]), "hr": round(hab_res),
                "ce": round(float(esp["cancelaciones_estimadas"].iloc[j]), 2),
                "ne": round(float(esp["noshows_estimados"].iloc[j]), 2),
                "pk": round(float(pickup[j]), 2), "oe": round(float(esperada[j]), 2),
                "cap": cap, "pct": round(pct, 2),
                "t": round(tarifa, 2) if tarifa else None,
            },
        ).scalar_one()  # fmt: skip
        nivel = nivel_riesgo(pct, entradas.umbral_medio, entradas.umbral_alto)
        id_riesgo = conexion.execute(
            text(
                "INSERT INTO riesgo_overbooking (id_ocupacion, nivel_riesgo) VALUES (:o, :n) "
                "RETURNING id_riesgo"
            ),
            {"o": id_ocup, "n": nivel},
        ).scalar_one()
        if nivel == "alto":
            criticas += 1
            conexion.execute(
                text("INSERT INTO fecha_critica (id_riesgo, motivo) VALUES (:r, :m)"),
                {"r": id_riesgo, "m": _motivo(fecha, pct, esperada[j], cap, eventos)},
            )
        regla = reglas.get(nivel)
        if regla is not None:
            if nivel == "alto":
                # Dentro del rango de la regla: más cerca del máximo cuanto mayor sea la sobreocupación.
                avance = float(np.clip((pct - entradas.umbral_alto) / 12, 0, 1))
                ajuste = (
                    float(regla.ajuste_min)
                    + (float(regla.ajuste_max) - float(regla.ajuste_min)) * avance
                )
            else:
                ajuste = float(regla.ajuste_min)
            conexion.execute(
                text(
                    """
                    INSERT INTO sugerencia_tarifa (id_riesgo, id_regla, tarifa_referencia,
                        tipo_sugerencia, ajuste_recomendado, tarifa_sugerida, justificacion)
                    VALUES (:r, :g, :t, :tipo, :aj, :ts, :j)
                    """
                ),
                {
                    "r": id_riesgo, "g": regla.id_regla, "t": round(tarifa, 2) if tarifa else None,
                    "tipo": regla.tipo_sugerencia, "aj": round(ajuste, 2),
                    "ts": round(tarifa * (1 + ajuste / 100), 2) if tarifa else None,
                    "j": regla.justificacion,
                },
            )  # fmt: skip
    recalcular_sugerencias(conexion, id_ejecucion)
    return len(noches), criticas


def ejecutar_analisis(conexion: Connection, id_usuario: int) -> ResultadoAnalisis:
    """Corre el análisis completo para la fecha de corte y el horizonte configurados."""
    id_version, art = version_activa(conexion)
    entradas = leer_entradas(conexion)
    id_ejecucion = conexion.execute(
        text(
            """
            INSERT INTO ejecucion_analisis (id_usuario, id_version, fecha_corte, horizonte_dias)
            VALUES (:u, :v, :c, :h) RETURNING id_ejecucion
            """
        ),
        {"u": id_usuario, "v": id_version, "c": entradas.fecha_corte, "h": entradas.horizonte},
    ).scalar_one()
    futuras, matriz, factores = _predicciones(art, entradas)
    _guardar_predicciones(conexion, id_version, id_ejecucion, futuras, matriz, factores)
    n_fechas, n_criticas = _guardar_ocupacion(conexion, id_version, id_ejecucion, art, entradas)
    conexion.execute(
        text(
            """
            UPDATE ejecucion_analisis SET fecha_fin = now(), estado = 'completada',
                reservas_procesadas = :r, fechas_analizadas = :f, fechas_criticas = :c,
                mensaje = :m WHERE id_ejecucion = :i
            """
        ),
        {
            "r": len(futuras), "f": n_fechas, "c": n_criticas, "i": id_ejecucion,
            "m": f"Análisis hasta {entradas.fecha_corte + timedelta(days=entradas.horizonte - 1)}",
        },
    )  # fmt: skip
    return ResultadoAnalisis(id_ejecucion, id_version, len(futuras), n_fechas, n_criticas)
