"""Crea o actualiza las tablas ejecutando los archivos .sql de la carpeta database/.

Uso (desde la carpeta backend, con el entorno virtual activado):
    python -m scripts.init_db

Ejecuta en orden alfabético todos los .sql, excepto los que empiezan con "00_"
(ese se corre una sola vez en pgAdmin como superusuario).
"""

from pathlib import Path

from app.db.session import engine

SQL_DIR = Path(__file__).resolve().parents[2] / "database"


def main() -> None:
    archivos = sorted(p for p in SQL_DIR.glob("*.sql") if not p.name.startswith("00_"))
    if not archivos:
        print(f"No se encontraron archivos .sql en {SQL_DIR}")
        return

    conexion = engine.raw_connection()
    try:
        with conexion.cursor() as cursor:
            for archivo in archivos:
                print(f"Ejecutando {archivo.name} ...")
                cursor.execute(archivo.read_text(encoding="utf-8"))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
    print("Base de datos lista.")


if __name__ == "__main__":
    main()
