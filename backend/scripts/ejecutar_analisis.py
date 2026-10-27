"""Ejecuta el análisis con el modelo activo: predicciones, ocupación esperada y riesgo a 90 días.

Uso (desde la carpeta backend, con el entorno virtual activado):

    python -m scripts.ejecutar_analisis
    python -m scripts.ejecutar_analisis --usuario admin
"""

import argparse
import sys
import time

from sqlalchemy import text

from app.db.session import engine
from app.services.analisis import SinModeloActivo, ejecutar_analisis


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--usuario", default="admin", help="Usuario que figura como autor del análisis")
    args = ap.parse_args()

    t0 = time.time()
    with engine.begin() as c:
        id_usuario = c.execute(
            text("SELECT id_usuario FROM usuario WHERE nombre_usuario = :u"), {"u": args.usuario}
        ).scalar()
        if id_usuario is None:
            sys.exit(f"No existe el usuario '{args.usuario}'. Crea uno con scripts.crear_usuario.")
        try:
            r = ejecutar_analisis(c, id_usuario)
        except SinModeloActivo as e:
            sys.exit(str(e))
    print(
        f"Análisis #{r.id_ejecucion} listo en {time.time() - t0:.0f} s: "
        f"{r.reservas_procesadas:,} reservas evaluadas · {r.fechas_analizadas} fechas · "
        f"{r.fechas_criticas} fechas críticas."
    )


if __name__ == "__main__":
    main()
