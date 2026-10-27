# Datos simulados

Los datos de PredicTree son **100 % simulados** y creados por el equipo (no hay datos reales del
DoubleTree by Hilton Lima Miraflores ni datasets públicos).

El generador está en `backend/app/simulacion/`. Para crearlos, desde la carpeta `backend` y con el
entorno virtual activado:

```powershell
python -m scripts.generar_datos
```

Genera las reservas con una semilla fija (cualquiera obtiene exactamente los mismos datos), las guarda
en `data/generados/` y las carga en PostgreSQL. Las reglas y supuestos están en
`docs/supuestos_datos_simulados.md`.

Archivos que produce (carpeta `data/generados/`, no se sube a GitHub):

- `reservas_historial.csv`
- `ocupacion_real_por_noche.csv`
- `reporte_validacion.md` (compara lo generado con lo esperado)
