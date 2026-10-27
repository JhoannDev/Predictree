"""Entrenamiento, evaluación y uso del modelo de cancelación y no-show.

Un solo modelo multiclase (HistGradientBoostingClassifier) estima, para cada reserva, tres
probabilidades que suman 100 %: se presenta, cancela, no se presenta (no-show).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.ml.calendario import TablaCalendario
from app.ml.explicacion import importancia_global
from app.ml.features import FEATURES, construir_snapshots
from app.ml.ocupacion import (
    HORIZONTES_PICKUP,
    ajustar_pickup,
    esperado_por_noche,
    ocupacion_real,
    patron_estacional,
    prediccion_ocupacion,
    serie_estacional,
)

# Fotos de cada reserva: al reservar (-1) y a estos días antes de la llegada.
HORIZONTES_ENTRENAMIENTO = (-1, 1, 3, 7, 14, 30, 60)
HORIZONTES_MAPE = (7, 14, 30, 60, 90)
HIPERPARAMETROS = {
    "learning_rate": 0.05,
    "max_leaf_nodes": 15,
    "min_samples_leaf": 300,
    "l2_regularization": 2.0,
    "random_state": 0,
}


@dataclass
class ArtefactoModelo:
    """Todo lo que hace falta para predecir: se guarda en un solo archivo .joblib."""

    codigo_version: str
    modelo: HistGradientBoostingClassifier
    umbral_cancelacion: float
    umbral_noshow: float
    pickup: dict[int, list[float]]
    patron: list[float]
    features: list[str]
    hiperparametros: dict
    periodo_entrenamiento: tuple[date, date]
    creado: str = ""
    notas: dict = field(default_factory=dict)

    def probabilidades(self, x: pd.DataFrame) -> np.ndarray:
        """(n, 3): se presenta, cancelación, no-show. Cada fila suma 1."""
        return self.modelo.predict_proba(x[self.features])

    def clasificar(self, prob: np.ndarray) -> np.ndarray:
        """Clase predicha (0, 1 o 2): la que más supera su umbral; si ninguna, "se presenta"."""
        score_c = prob[:, 1] / self.umbral_cancelacion
        score_n = prob[:, 2] / self.umbral_noshow
        clase = np.zeros(len(prob), dtype=int)
        clase[(score_c >= 1) & (score_c >= score_n)] = 1
        clase[(score_n >= 1) & (score_n > score_c)] = 2
        return clase

    def ocupacion_final(
        self,
        base: np.ndarray,
        noches: pd.DatetimeIndex,
        calendario: TablaCalendario,
        dias_hasta_la_noche: np.ndarray | int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """(ocupación esperada, pickup) a partir de las reservas netas de cada noche."""
        estacional = serie_estacional(np.array(self.patron), noches, calendario)
        return prediccion_ocupacion(self.pickup, base, estacional, dias_hasta_la_noche)


def guardar(artefacto: ArtefactoModelo, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefacto, ruta, compress=3)


def cargar(ruta: Path) -> ArtefactoModelo:
    return joblib.load(ruta)


# --------------------------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------------------------


def _mejor_umbral(y_binario: np.ndarray, p: np.ndarray) -> float:
    """Umbral que maximiza el F1 (se busca en datos de validación, nunca en los de prueba)."""
    mejor, umbral = -1.0, 0.5
    for u in np.linspace(0.02, 0.9, 89):
        f1 = f1_score(y_binario, (p >= u).astype(int), zero_division=0)
        if f1 > mejor:
            mejor, umbral = f1, float(u)
    return umbral


def metricas_clase(y: np.ndarray, prob: np.ndarray, clase: int, pred: np.ndarray) -> dict:
    """Métricas de una clase (cancelación o no-show) contra "todo lo demás"."""
    real = (y == clase).astype(int)
    predicho = (pred == clase).astype(int)
    p = prob[:, clase]
    dos_clases = real.min() != real.max()
    return {
        "f1": round(float(f1_score(real, predicho, zero_division=0)), 4),
        "precision": round(float(precision_score(real, predicho, zero_division=0)), 4),
        "recall": round(float(recall_score(real, predicho, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(real, predicho)), 4),
        "auc_roc": round(float(roc_auc_score(real, p)), 4) if dos_clases else None,
        "auc_pr": round(float(average_precision_score(real, p)), 4) if dos_clases else None,
        "brier": round(float(brier_score_loss(real, p)), 5),
        "tasa_real": round(float(real.mean()), 4),
        "tasa_predicha_media": round(float(p.mean()), 4),
        "casos": int(real.sum()),
    }


def calibracion(y: np.ndarray, prob: np.ndarray, clase: int, tramos: int = 8) -> list[dict]:
    """Probabilidad estimada vs. frecuencia real, por tramos de probabilidad (curva de calibración)."""
    real = (y == clase).astype(int)
    p = prob[:, clase]
    limites = np.unique(np.quantile(p, np.linspace(0, 1, tramos + 1)))
    grupo = np.clip(np.searchsorted(limites, p, side="right") - 1, 0, len(limites) - 2)
    filas = []
    for g in range(len(limites) - 1):
        m = grupo == g
        if m.sum() == 0:
            continue
        filas.append(
            {
                "probabilidad_media": round(float(p[m].mean()), 4),
                "frecuencia_real": round(float(real[m].mean()), 4),
                "casos": int(m.sum()),
            }
        )
    return filas


def mape(real: np.ndarray, pred: np.ndarray) -> float:
    ok = real > 0
    return float(np.mean(np.abs(pred[ok] - real[ok]) / real[ok]) * 100)


# --------------------------------------------------------------------------------------------
# Entrenamiento
# --------------------------------------------------------------------------------------------


def entrenar_y_evaluar(
    reservas: pd.DataFrame,
    calendario: TablaCalendario,
    tarifa_base: dict[str, float],
    capacidad: int,
    fecha_corte: date,
    inicio_validacion: date = date(2026, 3, 1),
    fin_entrenamiento: date = date(2026, 4, 30),
    codigo_version: str = "v1.0",
    umbral_riesgo: float = 90.0,
    verbose: bool = True,
) -> tuple[ArtefactoModelo, dict]:
    """Entrena el modelo con la historia, lo evalúa en el periodo de prueba y mide el MAPE.

    * Entrenamiento: llegadas hasta ``fin_entrenamiento``.
    * Validación (elegir nº de árboles y umbrales): llegadas desde ``inicio_validacion`` hasta
      ``fin_entrenamiento``.
    * Prueba: llegadas posteriores a ``fin_entrenamiento`` y anteriores a la fecha de corte.
    """

    def log(*args):
        if verbose:
            print(*args, flush=True)

    corte = pd.Timestamp(fecha_corte)
    resueltas = reservas[pd.to_datetime(reservas["fecha_llegada"]) < corte].reset_index(drop=True)
    x, y, info = construir_snapshots(resueltas, HORIZONTES_ENTRENAMIENTO, calendario, tarifa_base)
    llegada = pd.to_datetime(info["fecha_llegada"])
    ini_val, fin_ent = pd.Timestamp(inicio_validacion), pd.Timestamp(fin_entrenamiento)
    m_train = (llegada < ini_val).to_numpy()
    m_valid = ((llegada >= ini_val) & (llegada <= fin_ent)).to_numpy()
    m_test = (llegada > fin_ent).to_numpy()
    log(
        f"  fotos: entrenamiento {m_train.sum():,} · validación {m_valid.sum():,} · prueba {m_test.sum():,}"
    )

    # 1) Modelo con entrenamiento solo: sirve para elegir nº de árboles y umbrales con la validación.
    base = HistGradientBoostingClassifier(
        categorical_features="from_dtype", max_iter=400, **HIPERPARAMETROS
    ).fit(x[m_train], y[m_train])
    mejor_iter, mejor_ll = 1, np.inf
    for i, p in enumerate(base.staged_predict_proba(x[m_valid]), start=1):
        if i % 5 == 0 or i == 1:
            ll_i = log_loss(y[m_valid], p, labels=[0, 1, 2])
            if ll_i < mejor_ll:
                mejor_iter, mejor_ll = i, ll_i
    log(f"  árboles elegidos con la validación: {mejor_iter}")
    base = HistGradientBoostingClassifier(
        categorical_features="from_dtype", max_iter=mejor_iter, **HIPERPARAMETROS
    ).fit(x[m_train], y[m_train])
    prob_val = base.predict_proba(x[m_valid])
    umbral_c = _mejor_umbral((y[m_valid] == 1).astype(int), prob_val[:, 1])
    umbral_n = _mejor_umbral((y[m_valid] == 2).astype(int), prob_val[:, 2])
    log(f"  umbrales (validación): cancelación {umbral_c:.2f} · no-show {umbral_n:.2f}")

    # 2) Modelo final: entrena con todo hasta fin_entrenamiento.
    m_fit = m_train | m_valid
    modelo = HistGradientBoostingClassifier(
        categorical_features="from_dtype", max_iter=mejor_iter, **HIPERPARAMETROS
    ).fit(x[m_fit], y[m_fit])
    artefacto = ArtefactoModelo(
        codigo_version=codigo_version,
        modelo=modelo,
        umbral_cancelacion=umbral_c,
        umbral_noshow=umbral_n,
        pickup={},
        patron=[],
        features=list(FEATURES),
        hiperparametros={
            **HIPERPARAMETROS,
            "max_iter": mejor_iter,
            "horizontes": list(HORIZONTES_ENTRENAMIENTO),
        },
        periodo_entrenamiento=(
            pd.to_datetime(resueltas["fecha_llegada"]).min().date(),
            fin_entrenamiento,
        ),
        creado=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    )

    # 3) Clasificación en el periodo de prueba (datos que el modelo nunca vio).
    prob_t = artefacto.probabilidades(x[m_test])
    pred_t = artefacto.clasificar(prob_t)
    yt = y[m_test]
    evaluacion: dict = {
        "periodo_prueba": [str(fin_ent.date() + pd.Timedelta(days=1)), str((corte - pd.Timedelta(days=1)).date())],
        "fotos_prueba": int(m_test.sum()),
        "cancelacion": metricas_clase(yt, prob_t, 1, pred_t),
        "no_show": metricas_clase(yt, prob_t, 2, pred_t),
        "calibracion_cancelacion": calibracion(yt, prob_t, 1),
        "calibracion_no_show": calibracion(yt, prob_t, 2),
        "accuracy_multiclase": round(float(accuracy_score(yt, pred_t)), 4),
        "log_loss": round(float(log_loss(yt, prob_t, labels=[0, 1, 2])), 4),
        "log_loss_sin_modelo": round(float(log_loss(yt, np.tile(np.bincount(y[m_fit], minlength=3) / m_fit.sum(), (len(yt), 1)), labels=[0, 1, 2])), 4),
    }  # fmt: skip
    por_horizonte = {}
    info_t = info[m_test].reset_index(drop=True)
    for h in HORIZONTES_ENTRENAMIENTO:
        m = (info_t["horizonte"] == h).to_numpy()
        if m.sum() < 200:
            continue
        por_horizonte["al_reservar" if h == -1 else f"{h}_dias"] = {
            "cancelacion": metricas_clase(yt[m], prob_t[m], 1, pred_t[m]),
            "no_show": metricas_clase(yt[m], prob_t[m], 2, pred_t[m]),
        }
    evaluacion["por_horizonte"] = por_horizonte
    evaluacion["importancia_variables"] = importancia_global(modelo, x[m_test], yt)[:10]

    # 4) Pickup y patrón estacional (aprendidos en el periodo de entrenamiento) y MAPE en la prueba.
    log("  calculando pickup y MAPE de ocupación...")
    pr = artefacto.probabilidades
    noches_ajuste = pd.date_range("2024-02-01", fin_ent, freq="D")
    real_ajuste = ocupacion_real(resueltas, noches_ajuste)
    patron = patron_estacional(real_ajuste, noches_ajuste, calendario)
    artefacto.patron = [float(v) for v in patron]
    artefacto.pickup = ajustar_pickup(
        resueltas, noches_ajuste, patron, pr, calendario, tarifa_base, HORIZONTES_PICKUP
    )
    noches_prueba = pd.date_range(
        fin_ent + pd.Timedelta(days=1), corte - pd.Timedelta(days=1), freq="D"
    )
    real = ocupacion_real(resueltas, noches_prueba)
    referencia = serie_estacional(patron, noches_prueba, calendario)
    mape_ref = round(mape(real, referencia), 2)
    mape_h, series = {}, {}
    for h in HORIZONTES_MAPE:
        esp = esperado_por_noche(
            resueltas,
            noches_prueba,
            noches_prueba - pd.Timedelta(days=h),
            pr,
            calendario,
            tarifa_base,
        )
        sin_pickup = esp["habitaciones_esperadas"].to_numpy()
        con_pickup, _ = artefacto.ocupacion_final(sin_pickup, noches_prueba, calendario, h)
        mape_h[str(h)] = {
            "mape_con_pickup": round(mape(real, con_pickup), 2),
            "mape_sin_pickup": round(mape(real, sin_pickup), 2),
            "mape_referencia": mape_ref,
        }
        series[h] = con_pickup
    # Detección de noches de riesgo (RNF-03): ¿cuántas noches que terminaron con ocupación real en
    # riesgo medio o alto había anticipado el modelo?
    limite = umbral_riesgo / 100 * capacidad
    reales_riesgo = real >= limite
    deteccion = {}
    for h in (7, 14, 30):
        fila = {}
        for nombre, margen in (("al_umbral", 0.0), ("alerta_temprana", 5.0)):
            alerta = series[h] >= (umbral_riesgo - margen) / 100 * capacidad
            aciertos = int((alerta & reales_riesgo).sum())
            fila[nombre] = {
                "umbral_pct": umbral_riesgo - margen,
                "noches_alertadas": int(alerta.sum()),
                "aciertos": aciertos,
                "recall": round(aciertos / max(int(reales_riesgo.sum()), 1), 3),
                "precision": round(aciertos / max(int(alerta.sum()), 1), 3),
            }
        deteccion[str(h)] = fila
    evaluacion["riesgo_deteccion"] = {
        "umbral_pct": umbral_riesgo,
        "noches_riesgo_reales": int(reales_riesgo.sum()),
        "noches_evaluadas": len(noches_prueba),
        "por_horizonte": deteccion,
    }
    evaluacion["ocupacion"] = {
        "noches_evaluadas": len(noches_prueba),
        "mape_por_horizonte": mape_h,
        "serie": [
            {
                "fecha": str(f.date()),
                "real_pct": round(float(r) / capacidad * 100, 1),
                "esperada_14d_pct": round(float(e) / capacidad * 100, 1),
                "esperada_30d_pct": round(float(e30) / capacidad * 100, 1),
                "referencia_pct": round(float(rf) / capacidad * 100, 1),
            }
            for f, r, e, e30, rf in zip(
                noches_prueba, real, series[14], series[30], referencia, strict=True
            )
        ],
    }
    return artefacto, evaluacion
