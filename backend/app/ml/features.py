"""Variables (features) del modelo predictivo de cancelación y no-show.

Regla de oro: solo se usa lo que se sabe en la fecha de la predicción ("fecha de referencia").
Nunca se usa ``estado_reserva`` ni ``fecha_cancelacion`` como variable: son el resultado que se
quiere predecir.

La predicción se hace *a una fecha de referencia*: no es lo mismo una reserva de hace 90 días que
llega mañana (ya "sobrevivió" casi todo el periodo en que se cancela) que una que llega en 3 meses.
Por eso el modelo aprende con "fotos" (snapshots) de cada reserva a distintos días antes de la llegada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.calendario import TablaCalendario

CLASES = ("se_presenta", "cancelacion", "no_show")

CATEGORIAS: dict[str, list[str]] = {
    "canal_reserva": ["web_hilton", "ota", "agencia_viajes", "corporativo", "telefono"],
    "segmento": ["ocio", "negocios", "grupo", "evento"],
    "politica_tarifa": ["flexible", "no_reembolsable"],
    "tipo_habitacion": ["king", "doble", "junior_suite", "suite"],
    "procedencia": ["nacional", "extranjero"],
}
NUMERICAS = [
    "dias_hasta_llegada",
    "dias_desde_reserva",
    "noches",
    "num_habitaciones",
    "adultos",
    "ninos",
    "tarifa_relativa",
    "huesped_recurrente",
    "cancelaciones_previas",
    "solicitudes_especiales",
    "dia_semana_llegada",
    "mes_llegada",
    "factor_demanda_estadia",
    "hay_evento_estadia",
    "hay_feriado_estadia",
]
FEATURES = [*CATEGORIAS, *NUMERICAS]

# Nombres para mostrar en pantalla (explicación de cada predicción).
NOMBRES_LEGIBLES = {
    "canal_reserva": "Canal de reserva",
    "segmento": "Segmento",
    "politica_tarifa": "Política de tarifa",
    "tipo_habitacion": "Tipo de habitación",
    "procedencia": "Procedencia",
    "dias_hasta_llegada": "Días hasta la llegada (desde la fecha de corte)",
    "dias_desde_reserva": "Antigüedad de la reserva",
    "noches": "Noches de estadía",
    "num_habitaciones": "Habitaciones reservadas",
    "adultos": "Adultos",
    "ninos": "Niños",
    "tarifa_relativa": "Tarifa frente a la tarifa base",
    "huesped_recurrente": "Huésped recurrente",
    "cancelaciones_previas": "Cancelaciones previas",
    "solicitudes_especiales": "Solicitudes especiales del huésped",
    "dia_semana_llegada": "Día de la semana de llegada",
    "mes_llegada": "Mes de llegada",
    "factor_demanda_estadia": "Nivel de demanda de las fechas",
    "hay_evento_estadia": "Evento durante la estadía",
    "hay_feriado_estadia": "Feriado durante la estadía",
}
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip
_TEXTO_CATEGORIA = {
    "web_hilton": "Web Hilton",
    "ota": "OTA (agencia en línea)",
    "agencia_viajes": "Agencia de viajes",
    "corporativo": "Corporativo",
    "telefono": "Teléfono",
    "no_reembolsable": "No reembolsable",
    "junior_suite": "Junior Suite",
}


def describir_valor(feature: str, valor: object) -> str:
    """Texto del valor de una variable para mostrar al usuario."""
    if feature in CATEGORIAS:
        texto = str(valor)
        return _TEXTO_CATEGORIA.get(texto, texto.replace("_", " ").capitalize())
    v = float(valor)  # type: ignore[arg-type]
    if feature == "dias_hasta_llegada":
        d = int(v)
        if d <= 0:
            return "Llega el mismo día de la fecha de corte" if d == 0 else "Ya llegó"
        return "Falta 1 día" if d == 1 else f"Faltan {d} días"
    if feature == "dias_desde_reserva":
        d = int(v)
        return (
            "Reservó el mismo día"
            if d <= 0
            else ("Reservó hace 1 día" if d == 1 else f"Reservó hace {d} días")
        )
    if feature == "solicitudes_especiales":
        n = int(v)
        return "Ninguna" if n == 0 else ("1 solicitud" if n == 1 else f"{n} solicitudes")
    if feature == "cancelaciones_previas":
        n = int(v)
        return "Ninguna" if n == 0 else ("1 cancelación" if n == 1 else f"{n} cancelaciones")
    if feature == "num_habitaciones":
        n = int(v)
        return "1 habitación" if n == 1 else f"{n} habitaciones"
    if feature == "adultos":
        n = int(v)
        return "1 adulto" if n == 1 else f"{n} adultos"
    if feature == "ninos":
        n = int(v)
        return "Ninguno" if n == 0 else ("1 niño" if n == 1 else f"{n} niños")
    if feature == "noches":
        return f"{int(v)} noche" + ("" if int(v) == 1 else "s")
    if feature in ("huesped_recurrente", "hay_evento_estadia", "hay_feriado_estadia"):
        return "Sí" if v >= 0.5 else "No"
    if feature == "tarifa_relativa":
        return f"{v * 100:.0f} % de la tarifa base"
    if feature == "factor_demanda_estadia":
        return f"{(v - 1) * 100:+.0f} % vs. normal"
    if feature == "dia_semana_llegada":
        return _DIAS[int(v)].capitalize()
    if feature == "mes_llegada":
        return _MESES[int(v) - 1].capitalize()
    return f"{int(v)}"


def _a_dias(serie: pd.Series | np.ndarray) -> np.ndarray:
    return np.asarray(pd.to_datetime(serie)).astype("datetime64[D]")


def construir_features(
    reservas: pd.DataFrame,
    fecha_ref: pd.Series | np.ndarray,
    calendario: TablaCalendario,
    tarifa_base: dict[str, float],
) -> pd.DataFrame:
    """Variables de cada reserva tal como se conocían en ``fecha_ref`` (una fecha por reserva)."""
    llegada = _a_dias(reservas["fecha_llegada"])
    salida = _a_dias(reservas["fecha_salida"])
    reserva = _a_dias(reservas["fecha_reserva"])
    ref = _a_dias(fecha_ref)
    estadia = calendario.promedio_estadia(llegada, salida)
    llegada_ts = pd.DatetimeIndex(llegada)
    tarifa = reservas["tarifa_noche"].to_numpy(dtype=float)
    base = reservas["tipo_habitacion"].map(tarifa_base).to_numpy(dtype=float)

    datos: dict[str, object] = {}
    for columna, categorias in CATEGORIAS.items():
        datos[columna] = pd.Categorical(reservas[columna].to_numpy(), categories=categorias)
    datos["dias_hasta_llegada"] = (llegada - ref).astype(int)
    datos["dias_desde_reserva"] = (ref - reserva).astype(int)
    datos["noches"] = (salida - llegada).astype(int)
    datos["num_habitaciones"] = reservas["num_habitaciones"].to_numpy(dtype=int)
    datos["adultos"] = reservas["adultos"].to_numpy(dtype=int)
    datos["ninos"] = reservas["ninos"].to_numpy(dtype=int)
    datos["tarifa_relativa"] = tarifa / base
    datos["huesped_recurrente"] = reservas["huesped_recurrente"].to_numpy(dtype=bool).astype(int)
    datos["cancelaciones_previas"] = reservas["cancelaciones_previas"].to_numpy(dtype=int)
    datos["solicitudes_especiales"] = reservas["solicitudes_especiales"].to_numpy(dtype=int)
    datos["dia_semana_llegada"] = llegada_ts.dayofweek.to_numpy()
    datos["mes_llegada"] = llegada_ts.month.to_numpy()
    datos["factor_demanda_estadia"] = estadia["factor"]
    datos["hay_evento_estadia"] = estadia["evento"].astype(int)
    datos["hay_feriado_estadia"] = estadia["feriado"].astype(int)
    return pd.DataFrame(datos, index=reservas.index)[FEATURES]


def etiquetas(reservas: pd.DataFrame) -> np.ndarray:
    """0 = se presenta (completada), 1 = cancelación, 2 = no-show. Solo para reservas con resultado."""
    mapa = {"completada": 0, "cancelada": 1, "no_show": 2}
    return reservas["estado_reserva"].map(mapa).to_numpy(dtype=int)


def construir_snapshots(
    reservas: pd.DataFrame,
    horizontes: tuple[int, ...],
    calendario: TablaCalendario,
    tarifa_base: dict[str, float],
) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame]:
    """Una "foto" de cada reserva a ``h`` días antes de la llegada, para cada h en ``horizontes``.

    Solo entra la reserva si, ese día, ya estaba hecha y todavía no se había cancelado (así se
    ve en la práctica: no se predice la cancelación de algo que ya se canceló).

    Devuelve (variables, etiquetas, información de cada foto: id_reserva, horizonte, fecha de llegada).
    """
    partes_x, partes_y, partes_info = [], [], []
    llegada = pd.to_datetime(reservas["fecha_llegada"])
    reserva = pd.to_datetime(reservas["fecha_reserva"])
    cancelacion = pd.to_datetime(reservas["fecha_cancelacion"])
    for h in horizontes:
        ref = llegada - pd.Timedelta(days=h)
        vigente = (reserva <= ref) & (cancelacion.isna() | (cancelacion >= ref))
        sub = reservas[vigente.to_numpy()]
        if sub.empty:
            continue
        partes_x.append(construir_features(sub, ref[vigente.to_numpy()], calendario, tarifa_base))
        partes_y.append(etiquetas(sub))
        partes_info.append(
            pd.DataFrame(
                {
                    "id_reserva": sub["id_reserva"].to_numpy(),
                    "horizonte": h,
                    "fecha_llegada": llegada[vigente.to_numpy()].to_numpy(),
                }
            )
        )
    x = pd.concat(partes_x, ignore_index=True)
    # concat de categorías iguales conserva el tipo "category"
    return x, np.concatenate(partes_y), pd.concat(partes_info, ignore_index=True)
