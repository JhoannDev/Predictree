# Base de datos (PostgreSQL)

| Archivo | Qué hace | Cómo se ejecuta |
|---|---|---|
| `00_crear_bd.sql` | Crea el usuario `predictree_app` y la base `predictree` | Una sola vez, en pgAdmin, conectado como `postgres` |
| `01_schema.sql` | Crea las 17 tablas | `python -m scripts.init_db` (carpeta `backend`) |
| `02_datos_iniciales.sql` | Parámetros, inventario de 240 habitaciones, reglas de tarifa y calendario 2024-2027 | Lo ejecuta el mismo `init_db` |
| `03_vistas.sql` *(pendiente)* | Vistas de los reportes R-01 a R-04 | Igual que los anteriores |

`scripts.init_db` ejecuta en orden alfabético todos los `.sql` de esta carpeta, excepto los que empiezan con `00_`.
Es seguro ejecutarlo varias veces: solo crea lo que falta.

Los supuestos de los datos simulados y sus fuentes públicas están en `docs/supuestos_datos_simulados.md`.

## Cambiar la estructura de una tabla

`CREATE TABLE IF NOT EXISTS` no modifica tablas que ya existen. Si cambias una columna en `01_schema.sql`:

```powershell
python -m scripts.reset_db --confirmar
python -m scripts.crear_usuario --usuario admin --nombre "Tu Nombre"
```

`reset_db` borra todas las tablas y datos y las vuelve a crear. Como los datos son simulados, se regeneran.

## Tablas por grupo

| Grupo | Tablas |
|---|---|
| Seguridad | `usuario` |
| Configuración y hotel | `parametro_sistema`, `tipo_habitacion`, `fecha_especial` |
| Carga de datos | `lote_carga`, `observacion_carga`, `reserva` |
| Modelo predictivo | `version_modelo`, `evaluacion_modelo`, `ejecucion_analisis`, `prediccion` |
| Ocupación y riesgo | `ocupacion_esperada`, `riesgo_overbooking`, `fecha_critica` |
| Tarifas | `regla_tarifa`, `sugerencia_tarifa` |
| Reportes | `reporte_generado` |

Cada tabla y las columnas clave tienen descripción dentro de la base: en pgAdmin, clic en la tabla → pestaña **Properties** o **SQL**.

**Regla del equipo:** cualquier cambio a una tabla se hace en estos archivos (y se sube a GitHub),
nunca solo "a mano" en pgAdmin; así todos tienen exactamente la misma base de datos.
