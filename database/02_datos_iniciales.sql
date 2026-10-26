-- =====================================================================
-- PredicTree · 02_datos_iniciales.sql   (versión 2)
-- Configuración, inventario de habitaciones, reglas de tarifa y calendario
-- de fechas especiales 2024-2027. Fuentes y supuestos en
-- docs/supuestos_datos_simulados.md
-- Es seguro ejecutarlo varias veces: no duplica ni pisa valores editados.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Parámetros del sistema
-- ---------------------------------------------------------------------
INSERT INTO parametro_sistema (clave, valor, tipo_dato, descripcion) VALUES
    ('fecha_corte', '2026-10-31', 'fecha',
     '"Hoy" de la simulación. Antes: reservas con resultado final. Desde aquí: reservas futuras a predecir.'),
    ('horizonte_prediccion_dias', '90', 'entero',
     'Cuántos días después de la fecha de corte se calcula la ocupación esperada.'),
    ('umbral_riesgo_medio', '90', 'decimal',
     'Porcentaje de ocupación esperada desde el cual el riesgo es MEDIO.'),
    ('umbral_riesgo_alto', '98', 'decimal',
     'Porcentaje de ocupación esperada desde el cual el riesgo es ALTO (fecha crítica).'),
    ('meta_f1_cancelacion', '0.80', 'decimal', 'Meta mínima de F1 para cancelaciones (Business Case).'),
    ('meta_f1_noshow', '0.75', 'decimal', 'Meta mínima de F1 para no-shows (Business Case).'),
    ('meta_mape_ocupacion', '15', 'decimal', 'Meta máxima de MAPE (%) de la ocupación esperada (Business Case).'),
    ('moneda', 'PEN', 'texto', 'Moneda de todas las tarifas e importes (PEN = soles).')
ON CONFLICT (clave) DO NOTHING;

-- ---------------------------------------------------------------------
-- Inventario del hotel: 240 habitaciones (tarifas base en soles)
-- ---------------------------------------------------------------------
INSERT INTO tipo_habitacion (codigo, nombre, cantidad, capacidad_personas, tarifa_base, descripcion) VALUES
    ('king', 'Estándar King', 150, 2, 390.00, 'Habitación estándar con una cama king.'),
    ('doble', 'Estándar Doble', 70, 4, 420.00, 'Habitación estándar con dos camas.'),
    ('junior_suite', 'Junior Suite', 16, 3, 650.00, 'Más amplia, con acceso al Executive Lounge.'),
    ('suite', 'Suite', 4, 4, 1150.00, 'Suite con sala independiente y kitchenette.')
ON CONFLICT (codigo) DO NOTHING;

-- ---------------------------------------------------------------------
-- Reglas de sugerencia de tarifa (supuestos del equipo, Sesión 07)
-- ---------------------------------------------------------------------
INSERT INTO regla_tarifa (nombre_regla, nivel_riesgo, tipo_sugerencia, ajuste_min, ajuste_max, justificacion) VALUES
    ('Riesgo alto: incrementar tarifa', 'alto', 'incrementar', 5, 8,
     'La ocupación esperada alcanza o supera el umbral de riesgo alto; se sugiere ajustar la tarifa al alza.'),
    ('Riesgo medio: mantener tarifa', 'medio', 'mantener', 0, 0,
     'La ocupación esperada está cerca de la capacidad; se sugiere mantener la tarifa actual.'),
    ('Riesgo bajo: evaluar promoción', 'bajo', 'promocion', -3, -3,
     'La ocupación esperada está por debajo del umbral medio; se sugiere evaluar una promoción.')
ON CONFLICT (nombre_regla) DO NOTHING;

-- ---------------------------------------------------------------------
-- Fechas especiales 2024-2027 (feriados, temporadas y eventos)
-- factor_demanda: 1.00 = demanda normal; 1.30 = +30 %; 0.90 = -10 %.
-- ---------------------------------------------------------------------
INSERT INTO fecha_especial (nombre, tipo, fecha_inicio, fecha_fin, factor_demanda, fuente) VALUES
    ('Año Nuevo', 'feriado', '2024-01-01', '2024-01-01', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Semana Santa (Jueves y Viernes Santo)', 'feriado', '2024-03-28', '2024-03-29', 0.90, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día del Trabajo', 'feriado', '2024-05-01', '2024-05-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Arica y Día de la Bandera', 'feriado', '2024-06-07', '2024-06-07', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('San Pedro y San Pablo', 'feriado', '2024-06-29', '2024-06-29', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de la Fuerza Aérea del Perú', 'feriado', '2024-07-23', '2024-07-23', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Fiestas Patrias', 'feriado', '2024-07-28', '2024-07-29', 1.10, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Junín', 'feriado', '2024-08-06', '2024-08-06', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Santa Rosa de Lima', 'feriado', '2024-08-30', '2024-08-30', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Combate de Angamos', 'feriado', '2024-10-08', '2024-10-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de Todos los Santos', 'feriado', '2024-11-01', '2024-11-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Inmaculada Concepción', 'feriado', '2024-12-08', '2024-12-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Ayacucho', 'feriado', '2024-12-09', '2024-12-09', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Navidad', 'feriado', '2024-12-25', '2024-12-25', 1.05, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Temporada alta de turismo receptivo (julio-agosto)', 'temporada_alta', '2024-07-01', '2024-08-31', 1.10, 'MINCETUR: llegadas de turistas internacionales por mes (2024)'),
    ('Temporada baja corporativa (verano, enero-febrero)', 'temporada_baja', '2024-01-04', '2024-02-28', 0.92, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Año Nuevo', 'feriado', '2025-01-01', '2025-01-01', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Semana Santa (Jueves y Viernes Santo)', 'feriado', '2025-04-17', '2025-04-18', 0.90, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día del Trabajo', 'feriado', '2025-05-01', '2025-05-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Arica y Día de la Bandera', 'feriado', '2025-06-07', '2025-06-07', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('San Pedro y San Pablo', 'feriado', '2025-06-29', '2025-06-29', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de la Fuerza Aérea del Perú', 'feriado', '2025-07-23', '2025-07-23', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Fiestas Patrias', 'feriado', '2025-07-28', '2025-07-29', 1.10, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Junín', 'feriado', '2025-08-06', '2025-08-06', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Santa Rosa de Lima', 'feriado', '2025-08-30', '2025-08-30', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Combate de Angamos', 'feriado', '2025-10-08', '2025-10-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de Todos los Santos', 'feriado', '2025-11-01', '2025-11-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Inmaculada Concepción', 'feriado', '2025-12-08', '2025-12-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Ayacucho', 'feriado', '2025-12-09', '2025-12-09', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Navidad', 'feriado', '2025-12-25', '2025-12-25', 1.05, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Temporada alta de turismo receptivo (julio-agosto)', 'temporada_alta', '2025-07-01', '2025-08-31', 1.10, 'MINCETUR: llegadas de turistas internacionales por mes (2024)'),
    ('Temporada baja corporativa (verano, enero-febrero)', 'temporada_baja', '2025-01-04', '2025-02-28', 0.92, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Año Nuevo', 'feriado', '2026-01-01', '2026-01-01', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Semana Santa (Jueves y Viernes Santo)', 'feriado', '2026-04-02', '2026-04-03', 0.90, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día del Trabajo', 'feriado', '2026-05-01', '2026-05-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Arica y Día de la Bandera', 'feriado', '2026-06-07', '2026-06-07', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('San Pedro y San Pablo', 'feriado', '2026-06-29', '2026-06-29', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de la Fuerza Aérea del Perú', 'feriado', '2026-07-23', '2026-07-23', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Fiestas Patrias', 'feriado', '2026-07-28', '2026-07-29', 1.10, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Junín', 'feriado', '2026-08-06', '2026-08-06', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Santa Rosa de Lima', 'feriado', '2026-08-30', '2026-08-30', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Combate de Angamos', 'feriado', '2026-10-08', '2026-10-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de Todos los Santos', 'feriado', '2026-11-01', '2026-11-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Inmaculada Concepción', 'feriado', '2026-12-08', '2026-12-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Ayacucho', 'feriado', '2026-12-09', '2026-12-09', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Navidad', 'feriado', '2026-12-25', '2026-12-25', 1.05, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Temporada alta de turismo receptivo (julio-agosto)', 'temporada_alta', '2026-07-01', '2026-08-31', 1.10, 'MINCETUR: llegadas de turistas internacionales por mes (2024)'),
    ('Temporada baja corporativa (verano, enero-febrero)', 'temporada_baja', '2026-01-04', '2026-02-28', 0.92, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Año Nuevo', 'feriado', '2027-01-01', '2027-01-01', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Semana Santa (Jueves y Viernes Santo)', 'feriado', '2027-03-25', '2027-03-26', 0.90, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día del Trabajo', 'feriado', '2027-05-01', '2027-05-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Arica y Día de la Bandera', 'feriado', '2027-06-07', '2027-06-07', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('San Pedro y San Pablo', 'feriado', '2027-06-29', '2027-06-29', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de la Fuerza Aérea del Perú', 'feriado', '2027-07-23', '2027-07-23', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Fiestas Patrias', 'feriado', '2027-07-28', '2027-07-29', 1.10, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Junín', 'feriado', '2027-08-06', '2027-08-06', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Santa Rosa de Lima', 'feriado', '2027-08-30', '2027-08-30', 1.00, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Combate de Angamos', 'feriado', '2027-10-08', '2027-10-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Día de Todos los Santos', 'feriado', '2027-11-01', '2027-11-01', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Inmaculada Concepción', 'feriado', '2027-12-08', '2027-12-08', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Batalla de Ayacucho', 'feriado', '2027-12-09', '2027-12-09', 0.95, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Navidad', 'feriado', '2027-12-25', '2027-12-25', 1.05, 'El Peruano / Caretas: 16 feriados nacionales vigentes desde 2024'),
    ('Temporada alta de turismo receptivo (julio-agosto)', 'temporada_alta', '2027-07-01', '2027-08-31', 1.10, 'MINCETUR: llegadas de turistas internacionales por mes (2024)'),
    ('Temporada baja corporativa (verano, enero-febrero)', 'temporada_baja', '2027-01-04', '2027-02-28', 0.92, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Fiestas de fin de año', 'temporada_alta', '2023-12-20', '2024-01-03', 1.12, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Fiestas de fin de año', 'temporada_alta', '2024-12-20', '2025-01-03', 1.12, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Fiestas de fin de año', 'temporada_alta', '2025-12-20', '2026-01-03', 1.12, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)'),
    ('Fiestas de fin de año', 'temporada_alta', '2026-12-20', '2027-01-03', 1.12, 'Supuesto del equipo (ver docs/supuestos_datos_simulados.md)')
ON CONFLICT (nombre, fecha_inicio) DO NOTHING;

-- Eventos: nombres genéricos a propósito (sin artistas ni eventos concretos). Las fechas de los cuatro
-- primeros están inspiradas en eventos reales de Lima; el último es inventado y cae dentro del horizonte
-- de predicción, para que la demostración muestre cómo el sistema anticipa un evento futuro.
INSERT INTO fecha_especial (nombre, tipo, categoria, fecha_inicio, fecha_fin, factor_demanda, recurrente, fuente) VALUES
    ('Cumbre internacional de líderes', 'evento', 'cumbre_internacional', '2024-11-10', '2024-11-16', 1.40, FALSE, 'Supuesto del equipo, inspirado en eventos reales de Lima (ver docs/supuestos_datos_simulados.md)'),
    ('Final deportiva internacional', 'evento', 'evento_deportivo', '2025-11-28', '2025-11-30', 1.35, FALSE, 'Supuesto del equipo, inspirado en eventos reales de Lima (ver docs/supuestos_datos_simulados.md)'),
    ('Concierto masivo internacional', 'evento', 'concierto_masivo', '2026-05-20', '2026-05-20', 1.10, FALSE, 'Supuesto del equipo, inspirado en eventos reales de Lima (ver docs/supuestos_datos_simulados.md)'),
    ('Serie de conciertos masivos', 'evento', 'concierto_masivo', '2026-10-07', '2026-10-10', 1.30, FALSE, 'Supuesto del equipo, inspirado en eventos reales de Lima (ver docs/supuestos_datos_simulados.md)'),
    ('Congreso internacional de negocios', 'evento', 'congreso_feria', '2026-11-17', '2026-11-19', 1.25, FALSE, 'Supuesto del equipo (fecha inventada para la demostración)')
ON CONFLICT (nombre, fecha_inicio) DO NOTHING;
