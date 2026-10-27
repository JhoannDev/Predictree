"""Entrena el modelo de IA, lo evalúa con datos que no vio y lo registra en la base de datos.

Uso (desde la carpeta backend, con el entorno virtual activado):

    python -m scripts.entrenar_modelo                    # entrena v1.0 y la deja activa
    python -m scripts.entrenar_modelo --version v1.1     # otra versión
    python -m scripts.entrenar_modelo --reemplazar       # reemplaza la versión si ya existe
    python -m scripts.entrenar_modelo --sin-activar      # registra la versión pero no la activa

Guarda el modelo en models/ (ignorado por Git) y las métricas en version_modelo y evaluacion_modelo.
Después, ejecuta el análisis con:  python -m scripts.ejecutar_analisis
"""

import argparse
import json
import sys
import time

from sqlalchemy import text

from app.core.config import BACKEND_DIR
from app.db.session import engine
from app.ml.datos import leer_entradas
from app.ml.modelo import HORIZONTES_MAPE, entrenar_y_evaluar, guardar

MODELOS_DIR = BACKEND_DIR.parent / "models"
HORIZONTE_MAPE_REFERENCIA = 30  # el MAPE que se compara con la meta del Business Case


def registrar(
    conexion, art, ev, ruta_relativa: str, activar: bool, reemplazar: bool, entradas
) -> int:
    existente = conexion.execute(
        text("SELECT id_version FROM version_modelo WHERE codigo_version = :c"),
        {"c": art.codigo_version},
    ).scalar()
    if existente and not reemplazar:
        sys.exit(f"La versión {art.codigo_version} ya existe. Usa --reemplazar o --version otra.")
    if existente:
        conexion.execute(text("DELETE FROM version_modelo WHERE id_version = :i"), {"i": existente})
    if activar:
        conexion.execute(text("UPDATE version_modelo SET activa = FALSE WHERE activa"))

    id_version = conexion.execute(
        text(
            """
            INSERT INTO version_modelo (codigo_version, descripcion, periodo_entrenamiento_inicio,
                periodo_entrenamiento_fin, hiperparametros, ruta_artefacto, estado_aprobacion, activa)
            VALUES (:cod, :desc, :ini, :fin, CAST(:hp AS jsonb), :ruta, :est, :act)
            RETURNING id_version
            """
        ),
        {
            "cod": art.codigo_version,
            "desc": "Cancelación y no-show (multiclase) + ocupación esperada con pickup",
            "ini": art.periodo_entrenamiento[0],
            "fin": art.periodo_entrenamiento[1],
            "hp": json.dumps(art.hiperparametros),
            "ruta": ruta_relativa,
            "est": "aprobado" if activar else "en_evaluacion",
            "act": activar,
        },
    ).scalar_one()

    p = entradas.parametros
    periodo_ini, periodo_fin = ev["periodo_prueba"]
    detalle_comun = {
        "periodo_prueba": ev["periodo_prueba"],
        "por_horizonte": ev["por_horizonte"],
        "importancia_variables": ev["importancia_variables"],
        "umbrales": {"cancelacion": art.umbral_cancelacion, "no_show": art.umbral_noshow},
    }
    for tipo, meta_clave in (("cancelacion", "meta_f1_cancelacion"), ("no_show", "meta_f1_noshow")):
        m = ev[tipo]
        meta = float(p[meta_clave])
        detalle = {**detalle_comun, "metricas": m, "calibracion": ev[f"calibracion_{tipo}"]}
        conexion.execute(
            text(
                """
                INSERT INTO evaluacion_modelo (id_version, tipo_evaluacion, periodo_inicio, periodo_fin,
                    registros_evaluados, f1_score, precision_score, recall_score, accuracy_score,
                    valor_meta, cumple_meta, detalle)
                VALUES (:v, :t, :pi, :pf, :n, :f1, :pr, :re, :ac, :meta, :cumple, CAST(:d AS jsonb))
                """
            ),
            {
                "v": id_version, "t": tipo, "pi": periodo_ini, "pf": periodo_fin,
                "n": ev["fotos_prueba"], "f1": m["f1"], "pr": m["precision"], "re": m["recall"],
                "ac": m["accuracy"], "meta": meta, "cumple": m["f1"] >= meta,
                "d": json.dumps(detalle),
            },
        )  # fmt: skip

    mape_ref = ev["ocupacion"]["mape_por_horizonte"][str(HORIZONTE_MAPE_REFERENCIA)][
        "mape_con_pickup"
    ]
    meta_mape = float(p["meta_mape_ocupacion"])
    detalle_ocup = {
        "horizonte_referencia_dias": HORIZONTE_MAPE_REFERENCIA,
        "mape_por_horizonte": ev["ocupacion"]["mape_por_horizonte"],
        "pickup": {str(k): [round(c, 4) for c in v] for k, v in art.pickup.items()},
        "serie": ev["ocupacion"]["serie"],
        "riesgo_deteccion": ev["riesgo_deteccion"],
    }
    conexion.execute(
        text(
            """
            INSERT INTO evaluacion_modelo (id_version, tipo_evaluacion, periodo_inicio, periodo_fin,
                registros_evaluados, mape, valor_meta, cumple_meta, detalle)
            VALUES (:v, 'ocupacion', :pi, :pf, :n, :mape, :meta, :cumple, CAST(:d AS jsonb))
            """
        ),
        {
            "v": id_version, "pi": periodo_ini, "pf": periodo_fin,
            "n": ev["ocupacion"]["noches_evaluadas"], "mape": mape_ref, "meta": meta_mape,
            "cumple": mape_ref <= meta_mape, "d": json.dumps(detalle_ocup),
        },
    )  # fmt: skip
    return id_version


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--version", default="v1.0")
    ap.add_argument("--reemplazar", action="store_true")
    ap.add_argument("--sin-activar", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    print("Leyendo reservas de la base de datos...")
    with engine.connect() as c:
        entradas = leer_entradas(c)
    print(f"  {len(entradas.reservas):,} reservas · corte {entradas.fecha_corte}")

    print("Entrenando y evaluando (tarda menos de un minuto)...")
    art, ev = entrenar_y_evaluar(
        entradas.reservas,
        entradas.calendario,
        entradas.tarifa_base,
        entradas.capacidad,
        entradas.fecha_corte,
        codigo_version=args.version,
        umbral_riesgo=entradas.umbral_medio,
    )

    ruta = MODELOS_DIR / f"predictree_{args.version}.joblib"
    guardar(art, ruta)
    with engine.begin() as c:
        id_version = registrar(
            c, art, ev, f"models/{ruta.name}", not args.sin_activar, args.reemplazar, entradas
        )

    print(f"\nModelo {args.version} guardado en {ruta} (id_version {id_version})")
    print(f"Periodo de prueba: {ev['periodo_prueba'][0]} a {ev['periodo_prueba'][1]}\n")
    for etiqueta, clave, meta in (
        ("Cancelación", "cancelacion", entradas.parametros["meta_f1_cancelacion"]),
        ("No-show", "no_show", entradas.parametros["meta_f1_noshow"]),
    ):
        m = ev[clave]
        print(
            f"{etiqueta:12} F1 {m['f1']:.3f} (meta {meta}) · precisión {m['precision']:.3f} · "
            f"recall {m['recall']:.3f} · AUC {m['auc_roc']:.3f}"
        )
    print("\nError de la ocupación esperada (MAPE) según los días de anticipación:")
    for h in HORIZONTES_MAPE:
        d = ev["ocupacion"]["mape_por_horizonte"][str(h)]
        print(
            f"  {h:>2} días: {d['mape_con_pickup']:.1f} %   (sin pickup: {d['mape_sin_pickup']:.1f} %, referencia estacional: {d['mape_referencia']:.1f} %)"
        )
    print(f"\nListo en {time.time() - t0:.0f} s.")


if __name__ == "__main__":
    main()
