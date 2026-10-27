"""Genera las reservas simuladas, las guarda en CSV y las carga en PostgreSQL.

Uso (desde la carpeta backend, con el entorno virtual activado):

    python -m scripts.generar_datos                 # genera, guarda CSV y carga en la base
    python -m scripts.generar_datos --solo-csv      # solo genera los archivos, sin tocar la base
    python -m scripts.generar_datos --reemplazar    # reemplaza la carga anterior del generador

Lee de la base de datos el calendario (fecha_especial), los tipos de habitación y los parámetros
(fecha de corte y horizonte). Escribe en data/generados/ (carpeta ignorada por Git):

    reservas_historial.csv, ocupacion_real_por_noche.csv, reporte_validacion.md
"""

import argparse
import sys
import time
from datetime import date

import pandas as pd
from sqlalchemy import text

from app.core.config import BACKEND_DIR
from app.db.session import engine
from app.simulacion.generador import ConfigGenerador, generar_reservas, ocupacion_real_por_noche
from app.simulacion.reporte import construir_reporte, resumen_corto

DATOS_DIR = BACKEND_DIR.parent / "data" / "generados"
NOMBRE_ARCHIVO = "reservas_historial.csv"


def leer_entradas(conexion):
    """Calendario, tipos de habitación y parámetros que usa el generador."""
    parametros = dict(conexion.execute(text("SELECT clave, valor FROM parametro_sistema")).all())
    calendario = pd.read_sql(
        text("SELECT tipo, fecha_inicio, fecha_fin, factor_demanda FROM fecha_especial"), conexion
    )
    calendario["factor_demanda"] = calendario["factor_demanda"].astype(float)
    tipos = pd.read_sql(
        text("SELECT codigo, cantidad, capacidad_personas, tarifa_base FROM tipo_habitacion"),
        conexion,
    )
    tipos["tarifa_base"] = tipos["tarifa_base"].astype(float)
    if calendario.empty or tipos.empty:
        sys.exit("Faltan datos iniciales. Ejecuta primero: python -m scripts.init_db")
    return parametros, calendario, tipos


def cargar_en_base(conexion, reservas: pd.DataFrame, usuario: str, reemplazar: bool) -> None:
    """Inserta un lote de carga (origen 'generador') y sus reservas, en una sola transacción."""
    id_usuario = conexion.execute(
        text("SELECT id_usuario FROM usuario WHERE nombre_usuario = :u"), {"u": usuario}
    ).scalar_one_or_none()
    if id_usuario is None:
        sys.exit(
            f"No existe el usuario '{usuario}'. Créalo con: "
            f'python -m scripts.crear_usuario --usuario {usuario} --nombre "Tu Nombre"'
        )

    previos = conexion.execute(
        text("SELECT count(*) FROM lote_carga WHERE origen_datos = 'generador'")
    ).scalar_one()
    if previos and not reemplazar:
        sys.exit(
            "Ya hay datos generados en la base. Si quieres volver a generarlos, usa --reemplazar "
            "(borra la carga anterior del generador y sus reservas)."
        )
    if previos:
        conexion.execute(text("DELETE FROM lote_carga WHERE origen_datos = 'generador'"))

    total = len(reservas)
    id_lote = conexion.execute(
        text(
            "INSERT INTO lote_carga (id_usuario, nombre_archivo, origen_datos, registros_leidos, "
            "registros_validos, registros_observados, estado_validacion) "
            "VALUES (:u, :n, 'generador', :t, :t, 0, 'validado') RETURNING id_lote"
        ),
        {"u": id_usuario, "n": NOMBRE_ARCHIVO, "t": total},
    ).scalar_one()

    datos = reservas.copy()
    datos["fecha_cancelacion"] = (
        datos["fecha_cancelacion"].astype(object).where(datos["fecha_cancelacion"].notna(), None)
    )
    datos.insert(0, "id_lote", id_lote)
    datos.to_sql(
        "reserva", conexion, if_exists="append", index=False, method="multi", chunksize=2000
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los datos simulados de PredicTree.")
    parser.add_argument(
        "--usuario", default="admin", help="Usuario que figura como autor de la carga"
    )
    parser.add_argument(
        "--semilla", type=int, default=None, help="Semilla aleatoria (por defecto, la del proyecto)"
    )
    parser.add_argument("--solo-csv", action="store_true", help="No cargar en la base de datos")
    parser.add_argument(
        "--reemplazar", action="store_true", help="Reemplazar una carga anterior del generador"
    )
    args = parser.parse_args()

    with engine.connect() as conexion:
        parametros, calendario, tipos = leer_entradas(conexion)

    opciones = {
        "fecha_corte": date.fromisoformat(parametros["fecha_corte"]),
        "horizonte_dias": int(parametros["horizonte_prediccion_dias"]),
    }
    if args.semilla is not None:
        opciones["semilla"] = args.semilla
    cfg = ConfigGenerador(**opciones)

    print(f"Generando reservas (corte {cfg.fecha_corte:%d/%m/%Y}, semilla {cfg.semilla})...")
    inicio = time.time()
    reservas, info = generar_reservas(cfg, calendario, tipos)
    ocupacion = ocupacion_real_por_noche(reservas, info["capacidad_total"])
    print(f"  listo en {time.time() - inicio:.0f} s")

    DATOS_DIR.mkdir(parents=True, exist_ok=True)
    reservas.to_csv(DATOS_DIR / NOMBRE_ARCHIVO, index=False, encoding="utf-8")
    ocupacion.to_csv(DATOS_DIR / "ocupacion_real_por_noche.csv", index=False, encoding="utf-8")
    reporte = construir_reporte(reservas, ocupacion, info, cfg, tipos)
    (DATOS_DIR / "reporte_validacion.md").write_text(reporte, encoding="utf-8")
    print(resumen_corto(reservas, ocupacion, cfg))
    print(f"Archivos guardados en: {DATOS_DIR}")

    if args.solo_csv:
        print("Modo --solo-csv: no se cargó nada en la base de datos.")
        return

    print("Cargando en PostgreSQL...")
    with engine.begin() as conexion:
        cargar_en_base(conexion, reservas, args.usuario, args.reemplazar)
    with engine.connect() as conexion:
        filas = conexion.execute(
            text("SELECT estado_reserva, count(*) FROM reserva GROUP BY 1 ORDER BY 2 DESC")
        ).all()
    print("Reservas en la base de datos por estado:")
    for estado, cantidad in filas:
        print(f"  {estado:<12} {cantidad:>8,}")
    print("Listo. Abre data/generados/reporte_validacion.md para revisar el realismo de los datos.")


if __name__ == "__main__":
    main()
