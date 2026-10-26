"""Borra TODAS las tablas de la base predictree y las vuelve a crear desde database/*.sql.

Úsalo solo en desarrollo, cuando cambies la estructura de una tabla que ya existe.
Se pierden todos los datos (incluidos los usuarios).

Uso (desde la carpeta backend, con el entorno virtual activado):
    python -m scripts.reset_db --confirmar

Después vuelve a crear tu usuario:
    python -m scripts.crear_usuario --usuario admin --nombre "Tu Nombre"
"""

import argparse
import sys

from app.db.session import engine
from scripts import init_db


def borrar_tablas() -> list[str]:
    conexion = engine.raw_connection()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tablas = [fila[0] for fila in cursor.fetchall()]
            for tabla in tablas:
                cursor.execute(f'DROP TABLE IF EXISTS "{tabla}" CASCADE')
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
    return tablas


def main() -> None:
    parser = argparse.ArgumentParser(description="Reinicia la base de datos de PredicTree.")
    parser.add_argument(
        "--confirmar", action="store_true", help="Confirma que quieres borrar todos los datos"
    )
    args = parser.parse_args()
    if not args.confirmar:
        sys.exit("Esto borra TODOS los datos. Si estás seguro, agrega --confirmar.")

    tablas = borrar_tablas()
    print(f"Tablas eliminadas: {len(tablas)}")
    init_db.main()
    print("Recuerda volver a crear tu usuario con: python -m scripts.crear_usuario ...")


if __name__ == "__main__":
    main()
