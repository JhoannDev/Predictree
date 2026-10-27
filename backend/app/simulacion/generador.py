"""Generador de reservas simuladas de PredicTree.

Crea la historia de reservas del hotel (y las reservas futuras ya registradas a la fecha de corte)
con reglas definidas en docs/supuestos_datos_simulados.md. Los datos son 100 % inventados, pero se
comportan como los de un hotel real:

* la demanda depende del día de la semana, de la temporada, de feriados y de eventos
  (tabla ``fecha_especial``), crece ~6 % al año y tiene variación aleatoria;
* el hotel acepta más reservas que habitaciones (sobreventa controlada), por lo que en pocas noches
  de mucha demanda se presentan más huéspedes que habitaciones y hay reubicaciones;
* cancelaciones y no-shows salen de modelos con factores reales (canal, política de tarifa,
  anticipación, huésped recurrente, etc.) más un componente aleatorio que ningún modelo puede
  adivinar. Así el modelo de IA tiene patrones que aprender, pero no un problema trivial.

El generador no toca la base de datos: recibe el calendario y los tipos de habitación como tablas
(DataFrame) y devuelve las reservas. La carga a PostgreSQL la hace scripts/generar_datos.py.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------------------------
# Catálogos y supuestos (ver docs/supuestos_datos_simulados.md)
# --------------------------------------------------------------------------------------------

CANALES = ("web_hilton", "ota", "agencia_viajes", "corporativo", "telefono")
SEGMENTOS = ("ocio", "negocios", "grupo", "evento")
TIPOS = ("king", "doble", "junior_suite", "suite")

CANAL_OBJETIVO = {
    "ota": 0.40,
    "web_hilton": 0.25,
    "corporativo": 0.20,
    "agencia_viajes": 0.10,
    "telefono": 0.05,
}
SEGMENTO_OBJETIVO = {"ocio": 0.45, "negocios": 0.35, "grupo": 0.10, "evento": 0.10}
PROCEDENCIA_OBJETIVO = {"extranjero": 0.70, "nacional": 0.30}
POLITICA_OBJETIVO = {"flexible": 0.75, "no_reembolsable": 0.25}

# Peso de cada día de la semana en las llegadas (lunes=0). Hotel urbano: más negocios de lunes a jueves.
LLEGADAS_POR_DIA_SEMANA = np.array([1.12, 1.12, 1.06, 1.00, 0.92, 0.88, 0.90])

# Cuánto cambia el peso de cada segmento según el día de llegada (lunes-jueves / viernes-domingo).
SEGMENTO_DIA = {
    "ocio": (0.80, 1.30),
    "negocios": (1.25, 0.55),
    "grupo": (1.00, 1.00),
    "evento": (1.00, 1.00),
}

# Cómo se reparten los canales dentro de cada segmento (punto de partida; luego se ajusta para que
# el total coincida con CANAL_OBJETIVO). Columnas: web_hilton, ota, agencia_viajes, corporativo, telefono.
CANAL_POR_SEGMENTO_INICIAL = {
    "ocio": (0.26, 0.56, 0.10, 0.00, 0.08),
    "negocios": (0.20, 0.22, 0.02, 0.50, 0.06),
    "grupo": (0.10, 0.05, 0.45, 0.30, 0.10),
    "evento": (0.15, 0.10, 0.25, 0.40, 0.10),
}

# Tipo de habitación según segmento. Columnas: king, doble, junior_suite, suite.
TIPO_POR_SEGMENTO = {
    "ocio": (0.55, 0.35, 0.08, 0.02),
    "negocios": (0.72, 0.20, 0.06, 0.02),
    "grupo": (0.60, 0.38, 0.02, 0.00),
    "evento": (0.60, 0.30, 0.08, 0.02),
}

# Noches de estadía (1 a 10) según segmento.
NOCHES_PMF = {
    "ocio": (0.18, 0.32, 0.22, 0.11, 0.07, 0.04, 0.03, 0.01, 0.01, 0.01),
    "negocios": (0.36, 0.38, 0.17, 0.05, 0.02, 0.01, 0.005, 0.005, 0.0, 0.0),
    "grupo": (0.20, 0.33, 0.25, 0.12, 0.05, 0.03, 0.01, 0.01, 0.0, 0.0),
    "evento": (0.20, 0.33, 0.25, 0.12, 0.05, 0.03, 0.01, 0.01, 0.0, 0.0),
}

ADULTOS_PMF = {  # 1 a 4 adultos por habitación
    "ocio": (0.20, 0.55, 0.15, 0.10),
    "negocios": (0.85, 0.14, 0.01, 0.00),
    "grupo": (0.25, 0.50, 0.15, 0.10),
    "evento": (0.45, 0.40, 0.10, 0.05),
}
P_CON_NINOS = {"ocio": 0.22, "negocios": 0.01, "grupo": 0.08, "evento": 0.03}
P_EXTRANJERO = {"ocio": 0.82, "negocios": 0.60, "grupo": 0.65, "evento": 0.65}
P_RECURRENTE = {"ocio": 0.08, "negocios": 0.32, "grupo": 0.05, "evento": 0.04}

# Probabilidad de reservar más de una habitación: (2 habitaciones, 3 a 4, 5 a 30)
HABITACIONES_MULTIPLES = {
    "ocio": (0.04, 0.00, 0.00),
    "negocios": (0.02, 0.00, 0.00),
    "grupo": (0.07, 0.04, 0.03),
    "evento": (0.07, 0.04, 0.03),
}

# Política de tarifa: probabilidad de "no_reembolsable" por canal.
P_NO_REEMBOLSABLE = {
    "ota": 0.38,
    "web_hilton": 0.22,
    "corporativo": 0.08,
    "agencia_viajes": 0.20,
    "telefono": 0.15,
}

# Tasas base con tarifa flexible, por canal (docs, sección 5).
CANCELACION_BASE = {
    "ota": 0.26,
    "agencia_viajes": 0.15,
    "corporativo": 0.12,
    "telefono": 0.10,
    "web_hilton": 0.09,
}
NOSHOW_BASE = {
    "ota": 0.030,
    "agencia_viajes": 0.025,
    "corporativo": 0.015,
    "telefono": 0.015,
    "web_hilton": 0.010,
}
CANCELACION_NO_REEMBOLSABLE = 0.03
NOSHOW_FACTOR_NO_REEMBOLSABLE = 0.6

# Efecto de cada factor sobre la probabilidad (en escala logit). Positivo = más probable.
CANCELACION_SEGMENTO = {"ocio": 0.0, "negocios": 0.10, "grupo": 0.40, "evento": 0.20}
CANCELACION_EFECTOS = {
    "anticipacion": 0.30,  # por cada unidad de log(1 + días de anticipación)
    "recurrente": -0.60,
    "previa": 0.35,  # por cada cancelación previa (máx. 3)
    "varias_habitaciones": 0.30,
    "extranjero": 0.15,
    "evento": -0.30,
    "solicitudes": -0.25,
}
NOSHOW_EFECTOS = {
    "anticipacion": 0.12,
    "recurrente": -0.70,
    "con_ninos": -0.35,
    "nacional": 0.35,
    "solicitudes": -0.40,
    "negocios": 0.30,
    "evento": -0.25,
    "ota_nacional_flexible": 0.90,
}
# Parte "impredecible" de cada decisión (desviación estándar, escala logit)
RUIDO_CANCELACION = 0.70
RUIDO_NOSHOW = 0.60

# Un evento atrae huéspedes que llegan en varios días y se quedan varias noches: su efecto sobre las
# llegadas es algo mayor que el factor publicado en fecha_especial.
EFECTO_EVENTO = 1.3

TARIFA_FIN_DE_SEMANA = 0.92
TARIFA_NO_REEMBOLSABLE = 0.90

# log(1 + 20 días): punto de referencia para el efecto de la anticipación
ANTICIPACION_MEDIA_REFERENCIA = 3.0


@dataclass(frozen=True)
class ConfigGenerador:
    """Parámetros del generador. Los valores por defecto son los del proyecto."""

    semilla: int = 20261031
    fecha_inicio: date = date(2024, 1, 1)  # primera llegada que se entrega
    fecha_corte: date = date(2026, 10, 31)  # el "hoy" de la simulación
    horizonte_dias: int = 90
    # días que se simulan antes de fecha_inicio, para que enero no empiece "vacío"
    dias_calentamiento: int = 18
    ocupacion_objetivo: float = 0.68
    crecimiento_anual: float = 0.06
    cancelacion_objetivo: float = 0.14
    noshow_objetivo: float = 0.02
    margen_sobreventa: float = 0.10  # el hotel acepta hasta 110 % de las habitaciones "en libros"
    sigma_diaria: float = 0.07
    escala_inicial: float = 72.0  # reservas por día antes de aplicar temporada y día de la semana
    calibrar: bool = True
    iteraciones_max: int = 6
    tolerancia_ocupacion: float = 0.003
    dias_excluidos_inicio: int = 10  # los primeros días no cuentan para la ocupación (arranque)


# --------------------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------------------


def _sigmoide(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def _logit(p: float | np.ndarray) -> float | np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _muestrear(rng: np.random.Generator, probabilidades: np.ndarray) -> np.ndarray:
    """Elige una categoría por fila según su fila de probabilidades (N x k)."""
    acumulada = np.cumsum(probabilidades, axis=1)
    acumulada /= acumulada[:, -1:]
    u = rng.random(len(probabilidades))[:, None]
    return np.minimum((u > acumulada).sum(axis=1), probabilidades.shape[1] - 1)


def _calibrar_intercepto(z: np.ndarray, objetivo: float, peso: np.ndarray | None = None) -> float:
    """Busca el desplazamiento d tal que el promedio de sigmoide(z + d) (por peso) sea ``objetivo``."""
    peso = np.ones_like(z) if peso is None else peso
    bajo, alto = -20.0, 20.0
    for _ in range(60):
        medio = (bajo + alto) / 2
        if float(np.mean(peso * _sigmoide(z + medio))) < objetivo:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


def _canal_por_segmento() -> np.ndarray:
    """Matriz P(canal | segmento) ajustada (IPF) para que los totales coincidan con CANAL_OBJETIVO."""
    comparte = np.array([SEGMENTO_OBJETIVO[s] for s in SEGMENTOS])
    destino_canal = np.array([CANAL_OBJETIVO[c] for c in CANALES])
    inicial = np.array([CANAL_POR_SEGMENTO_INICIAL[s] for s in SEGMENTOS])
    conjunta = comparte[:, None] * inicial
    for _ in range(200):
        conjunta *= (destino_canal / conjunta.sum(axis=0))[None, :]
        conjunta *= (comparte / conjunta.sum(axis=1))[:, None]
    return conjunta / conjunta.sum(axis=1, keepdims=True)


def _a_fecha(valor) -> date:
    return pd.Timestamp(valor).date()


def _factores_calendario(
    calendario: pd.DataFrame, dia0: date, n_dias: int
) -> tuple[np.ndarray, np.ndarray]:
    """Factor de demanda y marca de "hay evento" por cada día desde dia0."""
    factor = np.ones(n_dias)
    evento = np.zeros(n_dias, dtype=bool)
    for fila in calendario.itertuples(index=False):
        inicio = (_a_fecha(fila.fecha_inicio) - dia0).days
        fin = (_a_fecha(fila.fecha_fin) - dia0).days
        a, b = max(inicio, 0), min(fin, n_dias - 1)
        if b < a:
            continue
        efecto = float(fila.factor_demanda)
        if fila.tipo == "evento":
            efecto = 1 + EFECTO_EVENTO * (efecto - 1)
        factor[a : b + 1] *= efecto
        if fila.tipo == "evento":
            evento[a : b + 1] = True
    return np.clip(factor, 0.5, 1.6), evento


def _probabilidades_segmento() -> np.ndarray:
    """Probabilidad de cada segmento por (día de la semana, hay evento)."""
    tabla = np.zeros((7, 2, len(SEGMENTOS)))
    for dia in range(7):
        for hay_evento in (0, 1):
            pesos = []
            for segmento in SEGMENTOS:
                lunes_jueves, viernes_domingo = SEGMENTO_DIA[segmento]
                peso = SEGMENTO_OBJETIVO[segmento] * (lunes_jueves if dia <= 3 else viernes_domingo)
                if hay_evento and segmento == "evento":
                    peso *= 3.0
                if hay_evento and segmento == "grupo":
                    peso *= 1.5
                pesos.append(peso)
            pesos = np.array(pesos)
            tabla[dia, hay_evento] = pesos / pesos.sum()
    return tabla


# --------------------------------------------------------------------------------------------
# Simulación
# --------------------------------------------------------------------------------------------


@dataclass
class _Contexto:
    cfg: ConfigGenerador
    dia0: date
    n_dias: int
    idx_inicio: int  # índice de fecha_inicio
    idx_corte: int
    factor: np.ndarray
    evento: np.ndarray
    cantidad_tipo: np.ndarray
    capacidad_tipo: np.ndarray  # personas por habitación
    tarifa_base: np.ndarray
    capacidad_total: int
    canal_dado_segmento: np.ndarray
    prob_segmento: np.ndarray


def _crear_contexto(
    cfg: ConfigGenerador, calendario: pd.DataFrame, tipos: pd.DataFrame
) -> _Contexto:
    dia0 = cfg.fecha_inicio - timedelta(days=cfg.dias_calentamiento)
    fin = cfg.fecha_corte + timedelta(days=cfg.horizonte_dias)
    n_dias = (fin - dia0).days
    factor, evento = _factores_calendario(calendario, dia0, n_dias)
    tipos = tipos.set_index("codigo").loc[list(TIPOS)]
    return _Contexto(
        cfg=cfg,
        dia0=dia0,
        n_dias=n_dias,
        idx_inicio=(cfg.fecha_inicio - dia0).days,
        idx_corte=(cfg.fecha_corte - dia0).days,
        factor=factor,
        evento=evento,
        cantidad_tipo=tipos["cantidad"].to_numpy(dtype=int),
        capacidad_tipo=tipos["capacidad_personas"].to_numpy(dtype=int),
        tarifa_base=tipos["tarifa_base"].to_numpy(dtype=float),
        capacidad_total=int(tipos["cantidad"].sum()),
        canal_dado_segmento=_canal_por_segmento(),
        prob_segmento=_probabilidades_segmento(),
    )


def _simular(ctx: _Contexto, escala: float) -> dict[str, np.ndarray]:
    """Una pasada completa: demanda, atributos, resultados y aceptación de reservas."""
    cfg = ctx.cfg
    rng = np.random.default_rng(cfg.semilla)
    n_dias = ctx.n_dias
    dia = np.arange(n_dias)
    dow0 = ctx.dia0.weekday()
    dia_semana = (dow0 + dia) % 7

    # ---- Demanda por día de llegada ------------------------------------------------------
    f = np.concatenate([ctx.factor, np.full(2, ctx.factor[-1])])
    factor_suavizado = (f[:-2] + f[1:-1] + f[2:]) / 3  # una estadía típica cubre 2-3 noches
    ref = (date(2025, 7, 1) - ctx.dia0).days
    crecimiento = (1 + cfg.crecimiento_anual) ** ((dia - ref) / 365.25)
    ar = np.zeros(n_dias)
    choque = rng.normal(0, 0.02, n_dias)
    for t in range(1, n_dias):
        ar[t] = 0.85 * ar[t - 1] + choque[t]
    ruido = np.exp(ar + rng.normal(0, cfg.sigma_diaria, n_dias))
    # En días de evento el efecto del evento manda sobre el patrón de la semana.
    peso_semana = np.where(ctx.evento, 1.0, LLEGADAS_POR_DIA_SEMANA[dia_semana])
    lam = escala * peso_semana * factor_suavizado * crecimiento * ruido
    llegadas_por_dia = rng.poisson(lam)
    ll = np.repeat(dia, llegadas_por_dia)  # índice del día de llegada de cada reserva
    n = len(ll)
    dow_ll = dia_semana[ll]
    ev_ll = ctx.evento[ll]

    # ---- Perfil de la reserva -------------------------------------------------------------
    seg = _muestrear(rng, ctx.prob_segmento[dow_ll, ev_ll.astype(int)])
    canal = _muestrear(rng, ctx.canal_dado_segmento[seg])
    tipo = _muestrear(rng, np.array([TIPO_POR_SEGMENTO[s] for s in SEGMENTOS])[seg])
    pmf_noches = np.array([NOCHES_PMF[s] for s in SEGMENTOS])
    noches = 1 + _muestrear(rng, pmf_noches[seg])

    # Habitaciones por reserva
    p_multi = np.array([HABITACIONES_MULTIPLES[s] for s in SEGMENTOS])[seg]
    u = rng.random(n)
    habs = np.ones(n, dtype=int)
    habs[u < p_multi[:, 0] + p_multi[:, 1] + p_multi[:, 2]] = 2
    habs[u < p_multi[:, 1] + p_multi[:, 2]] = rng.integers(3, 5, n)[
        u < p_multi[:, 1] + p_multi[:, 2]
    ]
    grande = u < p_multi[:, 2]
    habs[grande] = np.minimum(30, 5 + rng.geometric(0.12, n)[grande] - 1)
    tipo = np.where((habs > 3) & (tipo >= 2), 0, tipo)  # los bloques grandes van en estándar

    # Huéspedes
    adultos_base = 1 + _muestrear(rng, np.array([ADULTOS_PMF[s] for s in SEGMENTOS])[seg])
    adultos = np.minimum(8, np.maximum(adultos_base, np.minimum(habs, 8)))
    con_ninos = rng.random(n) < np.array([P_CON_NINOS[s] for s in SEGMENTOS])[seg]
    ninos = np.where(con_ninos, 1 + _muestrear(rng, np.tile([0.6, 0.3, 0.1], (n, 1))), 0)
    personas = adultos + ninos
    sube_a_doble = (personas > ctx.capacidad_tipo[tipo] * habs) & (tipo < 2)
    tipo = np.where(sube_a_doble, 1, tipo)
    exceso = np.maximum(0, adultos + ninos - ctx.capacidad_tipo[tipo] * habs)
    quitar_ninos = np.minimum(exceso, ninos)
    ninos = ninos - quitar_ninos
    exceso = exceso - quitar_ninos
    adultos = adultos - np.minimum(exceso, adultos - 1)

    extranjero = rng.random(n) < np.array([P_EXTRANJERO[s] for s in SEGMENTOS])[seg]
    recurrente = rng.random(n) < np.array([P_RECURRENTE[s] for s in SEGMENTOS])[seg]
    tiene_previas = rng.random(n) < np.where(recurrente, 0.01, 0.07)
    previas = np.where(tiene_previas, np.minimum(5, 1 + rng.geometric(0.6, n) - 1), 0)
    media_solicitudes = 0.4 + 0.5 * recurrente + 0.6 * (tipo >= 2)
    solicitudes = np.minimum(5, rng.poisson(media_solicitudes))

    # Canal, política y tarifa
    nombre_canal = np.array(CANALES)
    p_nr = np.array([P_NO_REEMBOLSABLE[c] for c in CANALES])[canal]
    no_reembolsable = rng.random(n) < p_nr
    mult = ctx.factor[ll] * np.where(dow_ll >= 4, TARIFA_FIN_DE_SEMANA, 1.0)
    mult = (
        mult * np.where(no_reembolsable, TARIFA_NO_REEMBOLSABLE, 1.0) * rng.uniform(0.95, 1.05, n)
    )
    tarifa = np.round(ctx.tarifa_base[tipo] * mult, 2)

    # Anticipación (días entre la reserva y la llegada)
    anticipacion = np.zeros(n, dtype=int)
    es_ocio, es_neg = seg == 0, seg == 1
    es_gru = seg >= 2
    anticipacion[es_neg] = np.minimum(21, np.rint(rng.exponential(6.0, es_neg.sum()))).astype(int)
    anticipacion[es_ocio] = np.minimum(120, np.rint(rng.gamma(1.1, 26.0, es_ocio.sum()))).astype(
        int
    )
    anticipacion[es_gru] = np.minimum(180, 30 + np.rint(rng.gamma(2.0, 25.0, es_gru.sum()))).astype(
        int
    )
    reserva = ll - anticipacion  # puede ser negativo (reservas hechas antes del arranque)

    # ---- Cancelación -----------------------------------------------------------------------
    x = np.log1p(anticipacion) - ANTICIPACION_MEDIA_REFERENCIA
    base_c = np.where(
        no_reembolsable,
        CANCELACION_NO_REEMBOLSABLE,
        np.array([CANCELACION_BASE[c] for c in CANALES])[canal],
    )
    e = CANCELACION_EFECTOS
    z_c = (
        _logit(base_c)
        + e["anticipacion"] * x
        + e["recurrente"] * recurrente
        + e["previa"] * np.minimum(previas, 3)
        + e["varias_habitaciones"] * (habs > 1)
        + e["extranjero"] * extranjero
        + e["evento"] * ev_ll
        + e["solicitudes"] * (solicitudes > 0)
        + np.array([CANCELACION_SEGMENTO[s] for s in SEGMENTOS])[seg]
        + rng.normal(0, RUIDO_CANCELACION, n)
    )
    z_c = z_c + _calibrar_intercepto(z_c, cfg.cancelacion_objetivo)
    p_c = _sigmoide(z_c)
    cancela = rng.random(n) < p_c

    # Día de la cancelación: muchas ocurren 1-3 días antes (límite de cancelación gratuita)
    dias_antes_beta = np.floor(anticipacion * rng.beta(1.3, 2.6, n)).astype(int)
    dias_antes_cerca = np.minimum(anticipacion, rng.integers(1, 4, n))
    dias_antes = np.where(rng.random(n) < 0.35, dias_antes_cerca, dias_antes_beta)
    dia_cancelacion = ll - dias_antes

    # ---- No-show (solo entre quienes no cancelan) --------------------------------------------
    base_n = np.array([NOSHOW_BASE[c] for c in CANALES])[canal]
    base_n = np.where(no_reembolsable, base_n * NOSHOW_FACTOR_NO_REEMBOLSABLE, base_n)
    g = NOSHOW_EFECTOS
    es_ota = canal == CANALES.index("ota")
    z_n = (
        _logit(base_n)
        + g["anticipacion"] * x
        + g["recurrente"] * recurrente
        + g["con_ninos"] * (ninos > 0)
        + g["nacional"] * (~extranjero)
        + g["solicitudes"] * (solicitudes > 0)
        + g["negocios"] * es_neg
        + g["evento"] * ev_ll
        + g["ota_nacional_flexible"] * (es_ota & ~extranjero & ~no_reembolsable)
        + rng.normal(0, RUIDO_NOSHOW, n)
    )
    z_n = z_n + _calibrar_intercepto(z_n, cfg.noshow_objetivo, peso=1 - p_c)
    no_show = (~cancela) & (rng.random(n) < _sigmoide(z_n))

    # ---- Aceptación: el hotel solo acepta reservas mientras le quede espacio -------------------
    # Solo existen las reservas hechas antes de la fecha de corte.
    existe = reserva < ctx.idx_corte
    aceptada = np.zeros(n, dtype=bool)
    indices = np.flatnonzero(existe)
    orden = indices[np.lexsort((rng.random(len(indices)), reserva[indices]))]

    limite_total = int(ctx.capacidad_total * (1 + cfg.margen_sobreventa))
    limite_tipo = np.floor(ctx.cantidad_tipo * (1 + cfg.margen_sobreventa)).astype(int)
    en_libros = np.zeros(n_dias + 12, dtype=np.int32)
    en_libros_tipo = np.zeros((len(TIPOS), n_dias + 12), dtype=np.int32)
    liberar: dict[int, list[int]] = defaultdict(list)
    dia_proceso = int(reserva[orden[0]]) if len(orden) else 0
    ll_l, noches_l, habs_l, tipo_l = ll.tolist(), noches.tolist(), habs.tolist(), tipo.tolist()
    res_l, canc_l, dcanc_l = reserva.tolist(), cancela.tolist(), dia_cancelacion.tolist()
    for i in orden.tolist():
        r = res_l[i]
        while dia_proceso <= r:  # primero se liberan las cancelaciones que ya ocurrieron
            for j in liberar.pop(dia_proceso, ()):
                a, b = ll_l[j], ll_l[j] + noches_l[j]
                en_libros[a:b] -= habs_l[j]
                en_libros_tipo[tipo_l[j], a:b] -= habs_l[j]
            dia_proceso += 1
        if canc_l[i] and dcanc_l[i] <= r:  # se cancela el mismo día: nunca ocupa inventario
            aceptada[i] = True
            continue
        a, b, h, t = ll_l[i], ll_l[i] + noches_l[i], habs_l[i], tipo_l[i]
        if (
            en_libros[a:b].max() + h <= limite_total
            and en_libros_tipo[t, a:b].max() + h <= limite_tipo[t]
        ):
            en_libros[a:b] += h
            en_libros_tipo[t, a:b] += h
            aceptada[i] = True
            if canc_l[i]:
                liberar[dcanc_l[i]].append(i)

    return {
        "ll": ll, "reserva": reserva, "noches": noches, "habs": habs, "tipo": tipo, "seg": seg,
        "canal": canal, "adultos": adultos, "ninos": ninos, "no_reembolsable": no_reembolsable,
        "tarifa": tarifa, "extranjero": extranjero, "recurrente": recurrente, "previas": previas,
        "solicitudes": solicitudes, "cancela": cancela, "no_show": no_show,
        "dia_cancelacion": dia_cancelacion, "aceptada": aceptada, "existe": existe,
        "nombre_canal": nombre_canal,
    }  # fmt: skip


def _presentes_por_noche(ctx: _Contexto, d: dict[str, np.ndarray]) -> np.ndarray:
    """Habitaciones ocupadas por noche (solo reservas aceptadas que se presentaron)."""
    se_presenta = d["aceptada"] & ~d["cancela"] & ~d["no_show"] & (d["ll"] < ctx.idx_corte)
    diff = np.zeros(ctx.n_dias + 13)
    inicio = d["ll"][se_presenta]
    np.add.at(diff, inicio, d["habs"][se_presenta])
    np.add.at(diff, inicio + d["noches"][se_presenta], -d["habs"][se_presenta])
    return np.cumsum(diff)[: ctx.n_dias]


def _ocupacion_media(ctx: _Contexto, d: dict[str, np.ndarray]) -> float:
    presentes = _presentes_por_noche(ctx, d)
    a = ctx.idx_inicio + ctx.cfg.dias_excluidos_inicio
    b = ctx.idx_corte
    return float(np.mean(np.minimum(presentes[a:b], ctx.capacidad_total) / ctx.capacidad_total))


def generar_reservas(
    cfg: ConfigGenerador, calendario: pd.DataFrame, tipos: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Genera las reservas. Devuelve (reservas, información de la corrida).

    ``calendario``: columnas tipo, fecha_inicio, fecha_fin, factor_demanda (tabla fecha_especial).
    ``tipos``: columnas codigo, cantidad, capacidad_personas, tarifa_base (tabla tipo_habitacion).
    """
    ctx = _crear_contexto(cfg, calendario, tipos)
    escala = cfg.escala_inicial
    iteraciones = 0
    d = _simular(ctx, escala)
    ocupacion = _ocupacion_media(ctx, d)
    while cfg.calibrar and iteraciones < cfg.iteraciones_max:
        if abs(ocupacion - cfg.ocupacion_objetivo) <= cfg.tolerancia_ocupacion:
            break
        escala *= cfg.ocupacion_objetivo / ocupacion
        d = _simular(ctx, escala)
        ocupacion = _ocupacion_media(ctx, d)
        iteraciones += 1

    # ---- Armado de la tabla ----------------------------------------------------------------
    sale = d["aceptada"] & d["existe"] & (d["ll"] >= ctx.idx_inicio)
    conservar = np.flatnonzero(sale)
    azar = np.random.default_rng(cfg.semilla + 1)
    conservar = conservar[
        np.lexsort((azar.random(len(conservar)), d["ll"][conservar], d["reserva"][conservar]))
    ]

    def fechas(indices: np.ndarray) -> np.ndarray:
        return (pd.Timestamp(ctx.dia0) + pd.to_timedelta(indices, unit="D")).date  # type: ignore[attr-defined]

    ll = d["ll"][conservar]
    reserva = d["reserva"][conservar]
    cancela = d["cancela"][conservar]
    dcanc = d["dia_cancelacion"][conservar]
    futura = ll >= ctx.idx_corte
    # Para llegadas futuras solo se conoce una cancelación si ocurrió antes del corte.
    cancelada = cancela & (~futura | (dcanc < ctx.idx_corte))
    estado = np.where(
        cancelada,
        "cancelada",
        np.where(futura, "confirmada", np.where(d["no_show"][conservar], "no_show", "completada")),
    )
    fecha_reserva = fechas(reserva)
    codigo_anio = pd.DatetimeIndex(fecha_reserva).year
    numero = pd.Series(codigo_anio).groupby(codigo_anio).cumcount().to_numpy() + 1
    codigos = [f"DTL-{a}-{k:06d}" for a, k in zip(codigo_anio, numero, strict=True)]
    fecha_cancelacion = np.where(cancelada, fechas(dcanc).astype(object), None)

    reservas = pd.DataFrame(
        {
            "codigo_reserva": codigos,
            "fecha_reserva": fecha_reserva,
            "fecha_llegada": fechas(ll),
            "fecha_salida": fechas(ll + d["noches"][conservar]),
            "tipo_habitacion": np.array(TIPOS)[d["tipo"][conservar]],
            "num_habitaciones": d["habs"][conservar],
            "adultos": d["adultos"][conservar],
            "ninos": d["ninos"][conservar],
            "canal_reserva": d["nombre_canal"][d["canal"][conservar]],
            "segmento": np.array(SEGMENTOS)[d["seg"][conservar]],
            "politica_tarifa": np.where(
                d["no_reembolsable"][conservar], "no_reembolsable", "flexible"
            ),
            "tarifa_noche": d["tarifa"][conservar],
            "procedencia": np.where(d["extranjero"][conservar], "extranjero", "nacional"),
            "huesped_recurrente": d["recurrente"][conservar],
            "cancelaciones_previas": d["previas"][conservar],
            "solicitudes_especiales": d["solicitudes"][conservar],
            "estado_reserva": estado,
            "fecha_cancelacion": fecha_cancelacion,
        }
    )
    info = {
        "escala_final": escala,
        "iteraciones_calibracion": iteraciones,
        "ocupacion_media_calibrada": ocupacion,
        "reservas_denegadas": int(
            (d["existe"] & ~d["aceptada"] & (d["ll"] >= ctx.idx_inicio)).sum()
        ),
        "capacidad_total": ctx.capacidad_total,
        "limite_sobreventa": int(ctx.capacidad_total * (1 + cfg.margen_sobreventa)),
    }
    return reservas, info


# --------------------------------------------------------------------------------------------
# Ocupación real por noche (a partir de las reservas)
# --------------------------------------------------------------------------------------------


def ocupacion_real_por_noche(reservas: pd.DataFrame, capacidad_total: int) -> pd.DataFrame:
    """Por cada noche: habitaciones en libros, huéspedes presentes, ocupación % y reubicaciones.

    * ``en_libros``: reservas no canceladas (confirmadas, completadas y no-show).
    * ``presentes``: reservas completadas (se presentaron).
    * ``reubicaciones``: presentes por encima de la capacidad (no hay habitación para ellos).
    """
    ini = pd.Timestamp(min(reservas["fecha_llegada"]))
    fin = pd.Timestamp(max(reservas["fecha_salida"]))
    noches = pd.date_range(ini, fin - pd.Timedelta(days=1), freq="D")
    n = len(noches)

    def acumular(sub: pd.DataFrame) -> np.ndarray:
        a = (pd.to_datetime(sub["fecha_llegada"]) - ini).dt.days.to_numpy()
        b = (pd.to_datetime(sub["fecha_salida"]) - ini).dt.days.to_numpy()
        diff = np.zeros(n + 1)
        np.add.at(diff, a, sub["num_habitaciones"].to_numpy())
        np.add.at(diff, b, -sub["num_habitaciones"].to_numpy())
        return np.cumsum(diff)[:n]

    en_libros = acumular(reservas[reservas["estado_reserva"] != "cancelada"])
    presentes = acumular(reservas[reservas["estado_reserva"] == "completada"])
    return pd.DataFrame(
        {
            "fecha": noches.date,
            "en_libros": en_libros.astype(int),
            "presentes": presentes.astype(int),
            "ocupacion_pct": np.minimum(presentes, capacidad_total) / capacidad_total * 100,
            "reubicaciones": np.maximum(0, presentes - capacidad_total).astype(int),
        }
    )
