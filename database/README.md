# Base de datos (PostgreSQL)

| Archivo | Qué hace | Cómo se ejecuta |
|---|---|---|
| `00_crear_bd.sql` | Crea el usuario `predictree_app` y la base `predictree` | Una sola vez, en pgAdmin, conectado como `postgres` |
| `01_schema.sql` | Crea las tablas | `python -m scripts.init_db` (carpeta `backend`) |
| `02_vistas.sql` *(pendiente)* | Vistas de los reportes R-01 a R-04 | Igual que el anterior |

`scripts.init_db` ejecuta en orden alfabético todos los `.sql` de esta carpeta, excepto los que empiezan con `00_`.
Por eso los archivos llevan número al inicio.

**Regla del equipo:** cualquier cambio a una tabla se hace en estos archivos (y se sube a GitHub),
nunca solo "a mano" en pgAdmin; así todos tienen exactamente la misma base de datos.
