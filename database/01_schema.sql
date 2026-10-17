-- =====================================================================
-- PredicTree · 01_schema.sql
-- Estructura de tablas. Lo ejecuta automáticamente:
--     python -m scripts.init_db   (desde la carpeta backend)
--
-- Por ahora contiene solo la tabla "usuario", copiada del modelo
-- entidad-relación del equipo (Sesión 07), para que funcione el login.
--
-- SIGUIENTE PASO DEL EQUIPO: reemplazar este archivo por el script
-- completo de las 12 tablas (sin las políticas RLS de Supabase, que
-- pueden ir en un archivo aparte solo para Supabase) y agregar las
-- vistas de los reportes en 02_vistas.sql.
-- =====================================================================

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario      INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_usuario  VARCHAR(30)    NOT NULL UNIQUE,
    nombre_completo VARCHAR(100)   NOT NULL,
    clave_hash      VARCHAR(256)   NOT NULL,
    rol             VARCHAR(30)    NOT NULL,
    activo          BOOLEAN        NOT NULL DEFAULT TRUE,
    fecha_creacion  TIMESTAMPTZ(0) NOT NULL DEFAULT now()
);

COMMENT ON TABLE usuario IS 'Personas autorizadas a ingresar a PredicTree (la clave se guarda solo como hash bcrypt).';
