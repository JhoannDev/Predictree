"""Crea un usuario para ingresar a PredicTree (la contraseña se guarda como hash bcrypt).

Uso (desde la carpeta backend, con el entorno virtual activado):
    python -m scripts.crear_usuario --usuario admin --nombre "Usuario demo"

Te pedirá la contraseña dos veces (no se muestra mientras la escribes).
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Usuario


def pedir_clave() -> str:
    clave = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if len(clave) < 8:
        sys.exit("La contraseña debe tener al menos 8 caracteres.")
    if len(clave.encode("utf-8")) > 72:
        sys.exit("La contraseña no puede superar 72 caracteres.")
    if clave != getpass.getpass("Repite la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")
    return clave


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea un usuario de PredicTree.")
    parser.add_argument("--usuario", required=True, help="Nombre de usuario para iniciar sesión")
    parser.add_argument("--nombre", required=True, help="Nombre completo visible en pantalla")
    parser.add_argument("--rol", default="revenue_management", help="Rol del usuario")
    parser.add_argument("--clave", help="Contraseña (si no se indica, se pide por teclado)")
    args = parser.parse_args()

    clave = args.clave or pedir_clave()

    with SessionLocal() as db:
        existe = db.scalar(select(Usuario).where(Usuario.nombre_usuario == args.usuario))
        if existe:
            sys.exit(f"Ya existe un usuario llamado '{args.usuario}'.")
        db.add(
            Usuario(
                nombre_usuario=args.usuario,
                nombre_completo=args.nombre,
                clave_hash=hash_password(clave),
                rol=args.rol,
                activo=True,
            )
        )
        db.commit()
    print(f"Usuario '{args.usuario}' creado correctamente.")


if __name__ == "__main__":
    main()
