-- =====================================================================
-- PredicTree · 00_crear_bd.sql
-- Crea el usuario de la aplicación y la base de datos.
-- Se ejecuta UNA sola vez, conectado como el superusuario "postgres"
-- (en pgAdmin: Query Tool sobre la base "postgres").
-- Ejecuta cada sentencia por separado: selecciónala y presiona F5.
-- Cambia la contraseña y usa la misma en backend/.env (DATABASE_URL).
-- =====================================================================

CREATE USER predictree_app WITH PASSWORD 'PredicTree2026';

CREATE DATABASE predictree OWNER predictree_app;
