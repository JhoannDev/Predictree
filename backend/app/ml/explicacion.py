"""Explicación de cada predicción: qué variables empujan la probabilidad hacia arriba o abajo.

Método (equivalente a un SHAP aproximado por oclusión): para cada variable se reemplaza el valor de la
reserva por valores "típicos" tomados de reservas de referencia y se mide cuánto cambia la probabilidad.
Si al quitarle la información de esa variable la probabilidad baja, esa variable la estaba subiendo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.features import FEATURES, NOMBRES_LEGIBLES, describir_valor

N_REFERENCIAS = 20


def explicar(
    modelo,
    x: pd.DataFrame,
    referencia: pd.DataFrame,
    top: int = 4,
    semilla: int = 0,
) -> list[list[dict]]:
    """Para cada fila de ``x`` devuelve los ``top`` factores más influyentes (en puntos porcentuales).

    ``efecto_pct`` es el cambio en la probabilidad de "no llegar" (cancelación + no-show) atribuible a
    la variable: positivo = aumenta el riesgo, negativo = lo reduce.
    """
    rng = np.random.default_rng(semilla)
    ref = referencia.sample(
        min(N_REFERENCIAS, len(referencia)), random_state=int(rng.integers(1e6))
    )
    ref = ref.reset_index(drop=True)
    n, r = len(x), len(ref)

    def perdida_c_n(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        p = modelo.predict_proba(df[FEATURES])
        return p[:, 1], p[:, 2]

    base_c, base_n = perdida_c_n(x)
    efectos_c = np.zeros((n, len(FEATURES)))
    efectos_n = np.zeros((n, len(FEATURES)))
    for j, col in enumerate(FEATURES):
        rep = x.loc[x.index.repeat(r)].reset_index(drop=True).copy()
        valores = np.tile(ref[col].to_numpy(), n)
        if str(x[col].dtype) == "category":
            rep[col] = pd.Categorical(valores, categories=x[col].cat.categories)
        else:
            rep[col] = valores
        pc, pn = perdida_c_n(rep)
        efectos_c[:, j] = base_c - pc.reshape(n, r).mean(axis=1)
        efectos_n[:, j] = base_n - pn.reshape(n, r).mean(axis=1)

    total = (efectos_c + efectos_n) * 100
    resultado: list[list[dict]] = []
    valores_x = x.reset_index(drop=True)
    for i in range(n):
        orden = np.argsort(-np.abs(total[i]))[:top]
        lista = []
        for j in orden:
            col = FEATURES[j]
            if abs(total[i, j]) < 0.05:
                continue
            lista.append(
                {
                    "variable": col,
                    "nombre": NOMBRES_LEGIBLES[col],
                    "valor": describir_valor(col, valores_x.at[i, col]),
                    "efecto_pct": round(float(total[i, j]), 2),
                    "efecto_cancelacion_pct": round(float(efectos_c[i, j] * 100), 2),
                    "efecto_noshow_pct": round(float(efectos_n[i, j] * 100), 2),
                    "direccion": "aumenta" if total[i, j] > 0 else "reduce",
                }
            )
        resultado.append(lista)
    return resultado


def importancia_global(
    modelo, x: pd.DataFrame, y: np.ndarray, muestra: int = 6000, semilla: int = 0
) -> list[dict]:
    """Importancia de cada variable en el modelo (permutación): cuánto empeora el log-loss al barajarla."""
    from sklearn.metrics import log_loss

    rng = np.random.default_rng(semilla)
    idx = rng.choice(len(x), size=min(muestra, len(x)), replace=False)
    xs, ys = x.iloc[idx].reset_index(drop=True), y[idx]
    base = log_loss(ys, modelo.predict_proba(xs[FEATURES]), labels=[0, 1, 2])
    filas = []
    for col in FEATURES:
        peor = 0.0
        for _ in range(2):
            xp = xs.copy()
            xp[col] = xs[col].sample(frac=1, random_state=int(rng.integers(1e6))).to_numpy()
            if str(xs[col].dtype) == "category":
                xp[col] = pd.Categorical(xp[col], categories=xs[col].cat.categories)
            peor += log_loss(ys, modelo.predict_proba(xp[FEATURES]), labels=[0, 1, 2]) - base
        filas.append({"variable": col, "nombre": NOMBRES_LEGIBLES[col], "importancia": peor / 2})
    total = sum(max(f["importancia"], 0) for f in filas) or 1.0
    for f in filas:
        f["importancia_pct"] = round(max(f["importancia"], 0) / total * 100, 1)
        f["importancia"] = round(f["importancia"], 6)
    return sorted(filas, key=lambda f: -f["importancia"])
