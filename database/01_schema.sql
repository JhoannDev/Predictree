-- =====================================================================
-- PredicTree · 01_schema.sql   (versión 4)
-- Estructura completa de la base de datos: 17 tablas.
--
-- Basada en el modelo entidad-relación del equipo (Sesión 07), completada
-- con lo que necesitan las pantallas, el modelo predictivo y los reportes.
-- Supuestos y fuentes de los datos: docs/supuestos_datos_simulados.md
--
-- Se ejecuta con:  python -m scripts.init_db        (carpeta backend)
-- Si cambias una tabla que ya existe:
--                  python -m scripts.reset_db --confirmar
-- =====================================================================


-- =====================================================================
-- 1. SEGURIDAD
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

COMMENT ON TABLE usuario IS
    'Personas autorizadas a ingresar a PredicTree. La clave se guarda solo como hash bcrypt.';


-- =====================================================================
-- 2. CONFIGURACIÓN, HOTEL Y CALENDARIO
-- =====================================================================

CREATE TABLE IF NOT EXISTS parametro_sistema (
    clave               VARCHAR(50)    PRIMARY KEY,
    valor               VARCHAR(100)   NOT NULL,
    tipo_dato           VARCHAR(10)    NOT NULL
        CONSTRAINT ck_parametro_tipo CHECK (tipo_dato IN ('entero', 'decimal', 'texto', 'fecha')),
    descripcion         VARCHAR(200)   NOT NULL,
    fecha_actualizacion TIMESTAMPTZ(0) NOT NULL DEFAULT now()
);

COMMENT ON TABLE parametro_sistema IS
    'Valores configurables sin tocar el código: fecha de corte, umbrales de riesgo, metas del modelo, moneda.';


CREATE TABLE IF NOT EXISTS tipo_habitacion (
    codigo             VARCHAR(20)   PRIMARY KEY,
    nombre             VARCHAR(60)   NOT NULL UNIQUE,
    cantidad           SMALLINT      NOT NULL CHECK (cantidad > 0),
    capacidad_personas SMALLINT      NOT NULL CHECK (capacidad_personas BETWEEN 1 AND 8),
    tarifa_base        NUMERIC(10,2) NOT NULL CHECK (tarifa_base > 0),
    descripcion        VARCHAR(200)  NOT NULL
);

COMMENT ON TABLE tipo_habitacion IS
    'Inventario del hotel por tipo. La capacidad total (240) es la suma de "cantidad". Tarifas en soles.';


CREATE TABLE IF NOT EXISTS fecha_especial (
    id_fecha_especial INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre            VARCHAR(80)  NOT NULL,
    tipo              VARCHAR(20)  NOT NULL
        CONSTRAINT ck_fecha_especial_tipo
        CHECK (tipo IN ('feriado', 'temporada_alta', 'temporada_baja', 'evento')),
    -- Solo para eventos: clase de evento. Los nombres son genéricos (sin artistas ni eventos concretos).
    categoria         VARCHAR(30)
        CONSTRAINT ck_fecha_especial_categoria
        CHECK (categoria IN ('concierto_masivo', 'evento_deportivo', 'cumbre_internacional', 'congreso_feria')),
    fecha_inicio      DATE         NOT NULL,
    fecha_fin         DATE         NOT NULL,
    -- TRUE si se repite cada año (feriados y temporadas); FALSE si es un evento puntual.
    recurrente        BOOLEAN      NOT NULL DEFAULT TRUE,
    -- Efecto supuesto sobre la demanda del hotel: 1.00 = normal, 1.30 = +30 %, 0.90 = -10 %.
    factor_demanda    NUMERIC(4,2) NOT NULL DEFAULT 1.00 CHECK (factor_demanda BETWEEN 0.50 AND 2.00),
    fuente            VARCHAR(150),
    CONSTRAINT ck_fecha_especial_rango CHECK (fecha_fin >= fecha_inicio),
    -- Un evento siempre tiene categoría y no es recurrente; feriados y temporadas no tienen categoría y sí lo son.
    CONSTRAINT ck_fecha_especial_evento CHECK (
        (tipo = 'evento' AND categoria IS NOT NULL AND NOT recurrente)
        OR (tipo <> 'evento' AND categoria IS NULL AND recurrente)
    ),
    CONSTRAINT uq_fecha_especial UNIQUE (nombre, fecha_inicio)
);

COMMENT ON TABLE fecha_especial IS
    'Feriados, temporadas y eventos de Lima. Los usa el generador de datos, el modelo (estacionalidad) y el dashboard.';
COMMENT ON COLUMN fecha_especial.categoria IS
    'Solo eventos: concierto_masivo, evento_deportivo, cumbre_internacional o congreso_feria.';
COMMENT ON COLUMN fecha_especial.recurrente IS
    'TRUE para feriados y temporadas (se repiten cada año); FALSE para eventos puntuales.';


-- =====================================================================
-- 3. CARGA Y VALIDACIÓN DE DATOS
-- =====================================================================

CREATE TABLE IF NOT EXISTS lote_carga (
    id_lote              INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_usuario           INTEGER        NOT NULL REFERENCES usuario (id_usuario),
    nombre_archivo       VARCHAR(150)   NOT NULL,
    origen_datos         VARCHAR(20)    NOT NULL
        CONSTRAINT ck_lote_origen CHECK (origen_datos IN ('archivo', 'generador')),
    fecha_carga          TIMESTAMPTZ(0) NOT NULL DEFAULT now(),
    registros_leidos     INTEGER        NOT NULL DEFAULT 0 CHECK (registros_leidos >= 0),
    registros_validos    INTEGER        NOT NULL DEFAULT 0 CHECK (registros_validos >= 0),
    registros_observados INTEGER        NOT NULL DEFAULT 0 CHECK (registros_observados >= 0),
    estado_validacion    VARCHAR(20)    NOT NULL DEFAULT 'pendiente'
        CONSTRAINT ck_lote_estado
        CHECK (estado_validacion IN ('pendiente', 'validado', 'con_observaciones', 'rechazado')),
    CONSTRAINT ck_lote_conteos CHECK (registros_validos + registros_observados <= registros_leidos)
);

COMMENT ON TABLE lote_carga IS
    'Cada archivo de reservas cargado (o generado) y el resultado de su validación.';


CREATE TABLE IF NOT EXISTS observacion_carga (
    id_observacion INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_lote        INTEGER      NOT NULL REFERENCES lote_carga (id_lote) ON DELETE CASCADE,
    numero_fila    INTEGER      NOT NULL CHECK (numero_fila > 0),
    codigo_reserva VARCHAR(30),
    campo          VARCHAR(50)  NOT NULL,
    tipo           VARCHAR(12)  NOT NULL
        CONSTRAINT ck_observacion_tipo CHECK (tipo IN ('error', 'advertencia')),
    mensaje        VARCHAR(200) NOT NULL
);

COMMENT ON TABLE observacion_carga IS
    'Detalle de cada problema encontrado al validar un archivo (pantalla Carga de datos y reporte R-04).';

CREATE INDEX IF NOT EXISTS ix_observacion_lote ON observacion_carga (id_lote);


CREATE TABLE IF NOT EXISTS reserva (
    id_reserva             INTEGER       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_lote                INTEGER       NOT NULL REFERENCES lote_carga (id_lote) ON DELETE CASCADE,
    codigo_reserva         VARCHAR(30)   NOT NULL UNIQUE,

    -- Fechas (las columnas calculadas las llena PostgreSQL automáticamente)
    fecha_reserva          DATE          NOT NULL,
    fecha_llegada          DATE          NOT NULL,
    fecha_salida           DATE          NOT NULL,
    anticipacion_dias      INTEGER       GENERATED ALWAYS AS (fecha_llegada - fecha_reserva) STORED,
    noches                 INTEGER       GENERATED ALWAYS AS (fecha_salida - fecha_llegada) STORED,

    -- Estancia
    tipo_habitacion        VARCHAR(20)   NOT NULL REFERENCES tipo_habitacion (codigo),
    num_habitaciones       SMALLINT      NOT NULL DEFAULT 1 CHECK (num_habitaciones BETWEEN 1 AND 30),
    adultos                SMALLINT      NOT NULL CHECK (adultos BETWEEN 1 AND 8),
    ninos                  SMALLINT      NOT NULL DEFAULT 0 CHECK (ninos BETWEEN 0 AND 6),

    -- Comercial (montos en soles)
    canal_reserva          VARCHAR(20)   NOT NULL
        CONSTRAINT ck_reserva_canal
        CHECK (canal_reserva IN ('web_hilton', 'ota', 'agencia_viajes', 'corporativo', 'telefono')),
    segmento               VARCHAR(20)   NOT NULL
        CONSTRAINT ck_reserva_segmento CHECK (segmento IN ('ocio', 'negocios', 'grupo', 'evento')),
    politica_tarifa        VARCHAR(20)   NOT NULL
        CONSTRAINT ck_reserva_politica CHECK (politica_tarifa IN ('flexible', 'no_reembolsable')),
    tarifa_noche           NUMERIC(10,2) NOT NULL CHECK (tarifa_noche > 0),
    importe_total          NUMERIC(12,2) GENERATED ALWAYS AS
                               ((fecha_salida - fecha_llegada) * num_habitaciones * tarifa_noche) STORED,

    -- Perfil del huésped (sin datos personales: Ley 29733)
    procedencia            VARCHAR(15)   NOT NULL
        CONSTRAINT ck_reserva_procedencia CHECK (procedencia IN ('nacional', 'extranjero')),
    huesped_recurrente     BOOLEAN       NOT NULL DEFAULT FALSE,
    cancelaciones_previas  SMALLINT      NOT NULL DEFAULT 0 CHECK (cancelaciones_previas >= 0),
    solicitudes_especiales SMALLINT      NOT NULL DEFAULT 0 CHECK (solicitudes_especiales >= 0),

    -- Resultado (variable objetivo del modelo)
    estado_reserva         VARCHAR(15)   NOT NULL
        CONSTRAINT ck_reserva_estado
        CHECK (estado_reserva IN ('confirmada', 'completada', 'cancelada', 'no_show')),
    fecha_cancelacion      DATE,

    CONSTRAINT ck_reserva_fechas CHECK (fecha_salida > fecha_llegada AND fecha_reserva <= fecha_llegada),
    CONSTRAINT ck_reserva_cancelacion CHECK (
        (estado_reserva = 'cancelada') = (fecha_cancelacion IS NOT NULL)
        AND (fecha_cancelacion IS NULL
             OR fecha_cancelacion BETWEEN fecha_reserva AND fecha_llegada)
    )
);

COMMENT ON TABLE reserva IS
    'Reservas simuladas. Llegadas antes de la fecha de corte: completada, cancelada o no_show (entrenan el modelo). '
    'Llegadas desde la fecha de corte: confirmada o cancelada (las confirmadas son las que se predicen).';
COMMENT ON COLUMN reserva.fecha_cancelacion IS
    'Solo para reservas canceladas. NO se usa como variable del modelo (revelaría el resultado).';
COMMENT ON COLUMN reserva.importe_total IS
    'Noches x habitaciones x tarifa por noche, en soles. Lo calcula PostgreSQL.';

CREATE INDEX IF NOT EXISTS ix_reserva_lote ON reserva (id_lote);
CREATE INDEX IF NOT EXISTS ix_reserva_llegada ON reserva (fecha_llegada);
CREATE INDEX IF NOT EXISTS ix_reserva_estado ON reserva (estado_reserva);


-- =====================================================================
-- 4. MODELO PREDICTIVO
-- =====================================================================

CREATE TABLE IF NOT EXISTS version_modelo (
    id_version                   INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_version               VARCHAR(20)    NOT NULL UNIQUE,
    descripcion                  VARCHAR(200)   NOT NULL,
    algoritmo                    VARCHAR(60)    NOT NULL DEFAULT 'HistGradientBoostingClassifier',
    fecha_entrenamiento          TIMESTAMPTZ(0) NOT NULL DEFAULT now(),
    periodo_entrenamiento_inicio DATE           NOT NULL,
    periodo_entrenamiento_fin    DATE           NOT NULL,
    hiperparametros              JSONB,
    ruta_artefacto               VARCHAR(255)   NOT NULL,
    estado_aprobacion            VARCHAR(20)    NOT NULL DEFAULT 'en_evaluacion'
        CONSTRAINT ck_version_estado
        CHECK (estado_aprobacion IN ('en_evaluacion', 'aprobado', 'rechazado', 'retirado')),
    activa                       BOOLEAN        NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_version_periodo CHECK (periodo_entrenamiento_fin >= periodo_entrenamiento_inicio),
    CONSTRAINT ck_version_activa_aprobada CHECK (NOT activa OR estado_aprobacion = 'aprobado')
);

COMMENT ON TABLE version_modelo IS
    'Cada modelo entrenado. Solo una versión puede estar activa, y debe estar aprobada.';
COMMENT ON COLUMN version_modelo.ruta_artefacto IS
    'Archivo .joblib con el modelo entrenado (carpeta models/).';

CREATE UNIQUE INDEX IF NOT EXISTS uq_version_una_activa ON version_modelo (activa) WHERE activa;


CREATE TABLE IF NOT EXISTS evaluacion_modelo (
    id_evaluacion       INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_version          INTEGER        NOT NULL REFERENCES version_modelo (id_version) ON DELETE CASCADE,
    tipo_evaluacion     VARCHAR(15)    NOT NULL
        CONSTRAINT ck_evaluacion_tipo CHECK (tipo_evaluacion IN ('cancelacion', 'no_show', 'ocupacion')),
    periodo_inicio      DATE           NOT NULL,
    periodo_fin         DATE           NOT NULL,
    registros_evaluados INTEGER        NOT NULL CHECK (registros_evaluados > 0),
    -- Métricas de clasificación en escala 0 a 1 (como las metas del SRS: F1 >= 0.80).
    f1_score            NUMERIC(5,4)   CHECK (f1_score BETWEEN 0 AND 1),
    precision_score     NUMERIC(5,4)   CHECK (precision_score BETWEEN 0 AND 1),
    recall_score        NUMERIC(5,4)   CHECK (recall_score BETWEEN 0 AND 1),
    accuracy_score      NUMERIC(5,4)   CHECK (accuracy_score BETWEEN 0 AND 1),
    -- Error de la ocupación en porcentaje (meta: MAPE <= 15 %).
    mape                NUMERIC(6,2)   CHECK (mape >= 0),
    valor_meta          NUMERIC(6,4)   NOT NULL,
    cumple_meta         BOOLEAN        NOT NULL,
    detalle             JSONB,
    fecha_evaluacion    TIMESTAMPTZ(0) NOT NULL DEFAULT now(),
    CONSTRAINT ck_evaluacion_periodo CHECK (periodo_fin >= periodo_inicio),
    CONSTRAINT ck_evaluacion_metrica CHECK (
        (tipo_evaluacion = 'ocupacion' AND mape IS NOT NULL)
        OR (tipo_evaluacion <> 'ocupacion' AND f1_score IS NOT NULL)
    )
);

COMMENT ON TABLE evaluacion_modelo IS
    'Métricas de cada versión frente a sus metas. Alimenta el reporte R-03.';
COMMENT ON COLUMN evaluacion_modelo.detalle IS
    'Datos adicionales en JSON, por ejemplo la matriz de confusión.';

CREATE INDEX IF NOT EXISTS ix_evaluacion_version ON evaluacion_modelo (id_version);


CREATE TABLE IF NOT EXISTS ejecucion_analisis (
    id_ejecucion        INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_usuario          INTEGER        NOT NULL REFERENCES usuario (id_usuario),
    id_version          INTEGER        NOT NULL REFERENCES version_modelo (id_version) ON DELETE CASCADE,
    id_lote             INTEGER        REFERENCES lote_carga (id_lote) ON DELETE SET NULL,
    fecha_corte         DATE           NOT NULL,
    horizonte_dias      SMALLINT       NOT NULL CHECK (horizonte_dias > 0),
    fecha_inicio        TIMESTAMPTZ(0) NOT NULL DEFAULT now(),
    fecha_fin           TIMESTAMPTZ(0),
    reservas_procesadas INTEGER        NOT NULL DEFAULT 0 CHECK (reservas_procesadas >= 0),
    fechas_analizadas   INTEGER        NOT NULL DEFAULT 0 CHECK (fechas_analizadas >= 0),
    fechas_criticas     INTEGER        NOT NULL DEFAULT 0 CHECK (fechas_criticas >= 0),
    estado              VARCHAR(12)    NOT NULL DEFAULT 'en_proceso'
        CONSTRAINT ck_ejecucion_estado CHECK (estado IN ('en_proceso', 'completada', 'error')),
    mensaje             VARCHAR(300),
    CONSTRAINT ck_ejecucion_fechas CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);

COMMENT ON TABLE ejecucion_analisis IS
    'Cada vez que se actualiza el análisis (predicciones, ocupación, riesgo y tarifas). '
    'El dashboard muestra la última ejecución completada como "Última actualización".';


CREATE TABLE IF NOT EXISTS prediccion (
    id_prediccion         INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_reserva            INTEGER        NOT NULL REFERENCES reserva (id_reserva) ON DELETE CASCADE,
    id_version            INTEGER        NOT NULL REFERENCES version_modelo (id_version) ON DELETE CASCADE,
    id_ejecucion          INTEGER        REFERENCES ejecucion_analisis (id_ejecucion) ON DELETE SET NULL,
    -- Probabilidades en porcentaje (0 a 100). Las tres suman 100.
    prob_cancelacion_pct  NUMERIC(5,2)   NOT NULL CHECK (prob_cancelacion_pct BETWEEN 0 AND 100),
    prob_noshow_pct       NUMERIC(5,2)   NOT NULL CHECK (prob_noshow_pct BETWEEN 0 AND 100),
    prob_presentacion_pct NUMERIC(5,2)   GENERATED ALWAYS AS
                              (100 - prob_cancelacion_pct - prob_noshow_pct) STORED,
    resultado_predicho    VARCHAR(12)    NOT NULL
        CONSTRAINT ck_prediccion_resultado
        CHECK (resultado_predicho IN ('se_presenta', 'cancelacion', 'no_show')),
    factores_explicativos JSONB          NOT NULL DEFAULT '[]'::jsonb,
    fecha_prediccion      TIMESTAMPTZ(0) NOT NULL DEFAULT now(),
    CONSTRAINT ck_prediccion_suma CHECK (prob_cancelacion_pct + prob_noshow_pct <= 100),
    CONSTRAINT uq_prediccion_reserva_version UNIQUE (id_reserva, id_version)
);

COMMENT ON TABLE prediccion IS
    'Probabilidad (%) de cancelación, no-show y presentación por reserva, con los factores que la explican (RF-13).';
COMMENT ON COLUMN prediccion.factores_explicativos IS
    'Lista JSON de los factores con más peso, p. ej. [{"factor": "anticipacion_dias", "efecto": "aumenta", "peso": 0.21}].';

CREATE INDEX IF NOT EXISTS ix_prediccion_version ON prediccion (id_version);


-- =====================================================================
-- 5. OCUPACIÓN, RIESGO Y FECHAS CRÍTICAS
-- =====================================================================

CREATE TABLE IF NOT EXISTS ocupacion_esperada (
    id_ocupacion            INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ejecucion            INTEGER        NOT NULL
        REFERENCES ejecucion_analisis (id_ejecucion) ON DELETE CASCADE,
    id_version              INTEGER        NOT NULL REFERENCES version_modelo (id_version) ON DELETE CASCADE,
    fecha_analizada         DATE           NOT NULL,
    -- Lo que hay reservado para esa noche
    reservas_registradas    INTEGER        NOT NULL CHECK (reservas_registradas >= 0),
    habitaciones_reservadas INTEGER        NOT NULL CHECK (habitaciones_reservadas >= 0),
    -- Lo que estima el modelo (cantidades esperadas, por eso pueden tener decimales)
    cancelaciones_estimadas NUMERIC(7,2)   NOT NULL CHECK (cancelaciones_estimadas >= 0),
    noshows_estimados       NUMERIC(7,2)   NOT NULL CHECK (noshows_estimados >= 0),
    -- Reservas que todavía no llegan pero se espera recibir (pickup histórico, según los días que faltan)
    pickup_estimado         NUMERIC(7,2)   NOT NULL DEFAULT 0 CHECK (pickup_estimado >= 0),
    ocupacion_esperada      NUMERIC(7,2)   NOT NULL CHECK (ocupacion_esperada >= 0),
    capacidad_disponible    INTEGER        NOT NULL CHECK (capacidad_disponible > 0),
    -- Puede superar 100 %: eso es justamente el riesgo de overbooking.
    porcentaje_ocupacion    NUMERIC(6,2)   NOT NULL CHECK (porcentaje_ocupacion >= 0),
    tarifa_promedio         NUMERIC(10,2)  CHECK (tarifa_promedio > 0),
    -- Lo que realmente pasó (solo fechas anteriores a la fecha de corte; sirve para el MAPE)
    cancelaciones_reales    INTEGER        CHECK (cancelaciones_reales >= 0),
    noshows_reales          INTEGER        CHECK (noshows_reales >= 0),
    ocupacion_real          INTEGER        CHECK (ocupacion_real >= 0),
    -- Huéspedes con reserva que se presentaron y no tuvieron habitación (se reubican en otro hotel).
    reubicaciones_reales    INTEGER        CHECK (reubicaciones_reales >= 0),
    fecha_calculo           TIMESTAMPTZ(0) NOT NULL DEFAULT now(),
    CONSTRAINT uq_ocupacion_version_fecha UNIQUE (id_version, fecha_analizada)
);

COMMENT ON TABLE ocupacion_esperada IS
    'Por cada noche: habitaciones reservadas, cancelaciones y no-shows estimados, ocupación esperada y '
    'tarifa promedio (soles). En fechas pasadas también guarda lo que realmente ocurrió.';

COMMENT ON COLUMN ocupacion_esperada.reubicaciones_reales IS
    'Reubicaciones (walk rate) de esa noche: huéspedes que se presentaron sin habitación disponible. '
    'Solo fechas pasadas; es el indicador de overbooking que el Business Case busca reducir.';

-- Versión 4: si la tabla ya existía, agrega la columna sin borrar datos.
ALTER TABLE ocupacion_esperada
    ADD COLUMN IF NOT EXISTS pickup_estimado NUMERIC(7,2) NOT NULL DEFAULT 0 CHECK (pickup_estimado >= 0);

COMMENT ON COLUMN ocupacion_esperada.pickup_estimado IS
    'Habitaciones que se espera sumar por reservas aún no hechas (pickup). '
    'ocupacion_esperada = reservadas - cancelaciones - no-shows + pickup.';

CREATE INDEX IF NOT EXISTS ix_ocupacion_fecha ON ocupacion_esperada (fecha_analizada);


CREATE TABLE IF NOT EXISTS riesgo_overbooking (
    id_riesgo           INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_ocupacion        INTEGER        NOT NULL UNIQUE
        REFERENCES ocupacion_esperada (id_ocupacion) ON DELETE CASCADE,
    nivel_riesgo        VARCHAR(5)     NOT NULL
        CONSTRAINT ck_riesgo_nivel CHECK (nivel_riesgo IN ('bajo', 'medio', 'alto')),
    fecha_clasificacion TIMESTAMPTZ(0) NOT NULL DEFAULT now()
);

COMMENT ON TABLE riesgo_overbooking IS
    'Nivel de riesgo de cada fecha según los umbrales de parametro_sistema (90 % y 98 %).';


CREATE TABLE IF NOT EXISTS fecha_critica (
    id_fecha_critica     INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_riesgo            INTEGER        NOT NULL UNIQUE
        REFERENCES riesgo_overbooking (id_riesgo) ON DELETE CASCADE,
    motivo               VARCHAR(200)   NOT NULL,
    fecha_identificacion TIMESTAMPTZ(0) NOT NULL DEFAULT now()
);

COMMENT ON TABLE fecha_critica IS
    'Fechas con riesgo alto, destacadas en el dashboard y el calendario, con el motivo.';


-- =====================================================================
-- 6. SUGERENCIAS DE TARIFA (INFORMATIVAS)
-- =====================================================================

CREATE TABLE IF NOT EXISTS regla_tarifa (
    id_regla        INTEGER      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_regla    VARCHAR(60)  NOT NULL UNIQUE,
    nivel_riesgo    VARCHAR(5)   NOT NULL
        CONSTRAINT ck_regla_nivel CHECK (nivel_riesgo IN ('bajo', 'medio', 'alto')),
    -- Sub-rango opcional dentro del nivel (NULL = aplica a todo el nivel).
    ocupacion_min   NUMERIC(5,2),
    ocupacion_max   NUMERIC(5,2),
    tipo_sugerencia VARCHAR(15)  NOT NULL
        CONSTRAINT ck_regla_tipo CHECK (tipo_sugerencia IN ('incrementar', 'mantener', 'promocion')),
    ajuste_min      NUMERIC(5,2) NOT NULL,
    ajuste_max      NUMERIC(5,2) NOT NULL,
    justificacion   VARCHAR(300) NOT NULL,
    activa          BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_regla_ajuste CHECK (ajuste_min <= ajuste_max),
    CONSTRAINT ck_regla_rango CHECK (ocupacion_min IS NULL OR ocupacion_max IS NULL
                                     OR ocupacion_min < ocupacion_max)
);

COMMENT ON TABLE regla_tarifa IS
    'Reglas que generan las sugerencias de tarifa. Ajustes en porcentaje (p. ej. 5 a 8 = +5 % a +8 %).';

CREATE UNIQUE INDEX IF NOT EXISTS uq_regla_activa_por_nivel
    ON regla_tarifa (nivel_riesgo) WHERE activa AND ocupacion_min IS NULL AND ocupacion_max IS NULL;


CREATE TABLE IF NOT EXISTS sugerencia_tarifa (
    id_sugerencia      INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_riesgo          INTEGER        NOT NULL UNIQUE
        REFERENCES riesgo_overbooking (id_riesgo) ON DELETE CASCADE,
    id_regla           INTEGER        NOT NULL REFERENCES regla_tarifa (id_regla),
    tarifa_referencia  NUMERIC(10,2)  CHECK (tarifa_referencia > 0),
    tipo_sugerencia    VARCHAR(15)    NOT NULL
        CONSTRAINT ck_sugerencia_tipo CHECK (tipo_sugerencia IN ('incrementar', 'mantener', 'promocion')),
    ajuste_recomendado NUMERIC(5,2)   NOT NULL,
    tarifa_sugerida    NUMERIC(10,2)  CHECK (tarifa_sugerida > 0),
    justificacion      VARCHAR(300)   NOT NULL,
    fecha_generacion   TIMESTAMPTZ(0) NOT NULL DEFAULT now()
);

COMMENT ON TABLE sugerencia_tarifa IS
    'Sugerencia informativa por fecha (RF-14), en soles. PredicTree nunca modifica tarifas reales.';


-- =====================================================================
-- 7. REPORTES
-- =====================================================================

CREATE TABLE IF NOT EXISTS reporte_generado (
    id_reporte       INTEGER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_usuario       INTEGER        NOT NULL REFERENCES usuario (id_usuario),
    codigo_reporte   CHAR(4)        NOT NULL
        CONSTRAINT ck_reporte_codigo CHECK (codigo_reporte IN ('R-01', 'R-02', 'R-03', 'R-04')),
    formato          VARCHAR(5)     NOT NULL
        CONSTRAINT ck_reporte_formato CHECK (formato IN ('PDF', 'XLSX')),
    filtros          VARCHAR(300),
    fecha_generacion TIMESTAMPTZ(0) NOT NULL DEFAULT now()
);

COMMENT ON TABLE reporte_generado IS
    'Bitácora de los reportes R-01 a R-04 exportados.';
