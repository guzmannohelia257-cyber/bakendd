-- ============================================================
-- PLATAFORMA INTELIGENTE DE ATENCIÓN DE EMERGENCIAS VEHICULARES
-- Base de Datos Completa - SQL Server (T-SQL)
-- ============================================================

CREATE DATABASE emergencias_vehiculares;
GO
USE emergencias_vehiculares;
GO

-- ==========================================
-- 1. CATÁLOGOS (Diccionarios)
-- ==========================================

CREATE TABLE ESTADO_INCIDENTE (
    id_estado       INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL,   -- pendiente | en_proceso | atendido | cancelado
    descripcion     VARCHAR(200) NULL
);

CREATE TABLE CATEGORIA_PROBLEMA (
    id_categoria    INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL,   -- bateria | llanta | choque | motor | otros | incierto
    descripcion     VARCHAR(200) NULL,
    icono_url       VARCHAR(255) NULL        -- ícono para la app móvil
);

CREATE TABLE PRIORIDAD (
    id_prioridad    INT IDENTITY(1,1) PRIMARY KEY,
    nivel           VARCHAR(50)  NOT NULL,   -- baja | media | alta | critica
    orden           INT          NOT NULL    -- para ordenar/filtrar (1=baja ... 4=critica)
);

CREATE TABLE ESTADO_ASIGNACION (
    id_estado_asignacion INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- pendiente | aceptada | rechazada | en_camino | completada
);

CREATE TABLE TIPO_EVIDENCIA (
    id_tipo_evidencia INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- imagen | audio | texto
);

CREATE TABLE ROL (
    id_rol          INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- cliente | taller | tecnico | admin
);

CREATE TABLE METODO_PAGO (
    id_metodo_pago  INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- tarjeta | transferencia | efectivo | qr
);

CREATE TABLE ESTADO_PAGO (
    id_estado_pago  INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- pendiente | procesando | completado | fallido | reembolsado
);


-- ==========================================
-- 2. ENTIDADES PRINCIPALES
-- ==========================================

-- 2.1 USUARIO (clientes y admins de la app móvil)
CREATE TABLE USUARIO (
    id_usuario      INT IDENTITY(1,1) PRIMARY KEY,
    id_rol          INT          NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    telefono        VARCHAR(20)  NULL,
    password_hash   VARCHAR(255) NOT NULL,              -- contraseña hasheada (bcrypt)
    push_token      VARCHAR(255) NULL,                  -- token FCM/APNs para notificaciones push
    activo          BIT          NOT NULL DEFAULT 1,
    created_at      DATETIME2    NOT NULL DEFAULT GETDATE(),
    updated_at      DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_rol) REFERENCES ROL(id_rol)
);

-- 2.2 VEHÍCULO
CREATE TABLE VEHICULO (
    id_vehiculo     INT IDENTITY(1,1) PRIMARY KEY,
    id_usuario      INT          NOT NULL,
    placa           VARCHAR(20)  NOT NULL,
    marca           VARCHAR(50)  NULL,
    modelo          VARCHAR(50)  NULL,
    anio            INT          NULL,                  -- año del vehículo (ayuda a la IA)
    color           VARCHAR(30)  NULL,                  -- color (ayuda a la IA a identificarlo en fotos)
    activo          BIT          NOT NULL DEFAULT 1,
    created_at      DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_usuario) REFERENCES USUARIO(id_usuario)
);

-- 2.3 TALLER
CREATE TABLE TALLER (
    id_taller       INT IDENTITY(1,1) PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    telefono        VARCHAR(20)  NULL,
    password_hash   VARCHAR(255) NOT NULL,              -- los talleres también se autentican
    push_token      VARCHAR(255) NULL,                  -- para notificaciones push al taller
    latitud         FLOAT        NULL,
    longitud        FLOAT        NULL,
    direccion       VARCHAR(255) NULL,
    capacidad_max   INT          NOT NULL DEFAULT 5,    -- máx incidentes simultáneos que puede manejar
    activo          BIT          NOT NULL DEFAULT 1,
    verificado      BIT          NOT NULL DEFAULT 0,    -- admin valida al taller antes de operar
    created_at      DATETIME2    NOT NULL DEFAULT GETDATE(),
    updated_at      DATETIME2    NOT NULL DEFAULT GETDATE()
);

-- 2.4 SERVICIOS QUE OFRECE CADA TALLER (para el motor de asignación inteligente)
CREATE TABLE TALLER_SERVICIO (
    id_taller_servicio INT IDENTITY(1,1) PRIMARY KEY,
    id_taller       INT          NOT NULL,
    id_categoria    INT          NOT NULL,              -- qué tipo de problema atiende
    servicio_movil  BIT          NOT NULL DEFAULT 0,    -- ¿puede ir al lugar del incidente?
    FOREIGN KEY (id_taller) REFERENCES TALLER(id_taller),
    FOREIGN KEY (id_categoria) REFERENCES CATEGORIA_PROBLEMA(id_categoria),
    CONSTRAINT UQ_taller_categoria UNIQUE (id_taller, id_categoria)
);

-- 2.5 TÉCNICO
CREATE TABLE TECNICO (
    id_tecnico      INT IDENTITY(1,1) PRIMARY KEY,
    id_taller       INT          NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    telefono        VARCHAR(20)  NULL,
    disponible      BIT          NOT NULL DEFAULT 1,
    latitud         FLOAT        NULL,                  -- ubicación actual del técnico
    longitud        FLOAT        NULL,                  -- para que el taller vea dónde está
    activo          BIT          NOT NULL DEFAULT 1,
    created_at      DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_taller) REFERENCES TALLER(id_taller)
);


-- ==========================================
-- 3. NÚCLEO TRANSACCIONAL
-- ==========================================

-- 3.1 INCIDENTE
CREATE TABLE INCIDENTE (
    id_incidente        INT IDENTITY(1,1) PRIMARY KEY,
    id_usuario          INT          NOT NULL,
    id_vehiculo         INT          NOT NULL,
    id_estado           INT          NOT NULL,
    id_categoria        INT          NULL,              -- clasificado por IA
    id_prioridad        INT          NULL,              -- prioridad asignada por IA
    latitud             FLOAT        NOT NULL,
    longitud            FLOAT        NOT NULL,
    descripcion_usuario VARCHAR(MAX) NULL,              -- texto libre del usuario (opcional)
    resumen_ia          VARCHAR(MAX) NULL,              -- ficha estructurada generada por IA
    clasificacion_ia_confianza FLOAT NULL,              -- % de confianza de la IA (0.0 - 1.0)
    requiere_revision_manual BIT NOT NULL DEFAULT 0,   -- TRUE si la IA no pudo clasificar bien
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    updated_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_usuario)    REFERENCES USUARIO(id_usuario),
    FOREIGN KEY (id_vehiculo)   REFERENCES VEHICULO(id_vehiculo),
    FOREIGN KEY (id_estado)     REFERENCES ESTADO_INCIDENTE(id_estado),
    FOREIGN KEY (id_categoria)  REFERENCES CATEGORIA_PROBLEMA(id_categoria),
    FOREIGN KEY (id_prioridad)  REFERENCES PRIORIDAD(id_prioridad)
);


-- ==========================================
-- 4. TABLAS INTERMEDIAS Y TRAZABILIDAD
-- ==========================================

-- 4.1 ASIGNACIÓN (incidente → taller → técnico)
CREATE TABLE ASIGNACION (
    id_asignacion       INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_taller           INT          NOT NULL,
    id_tecnico          INT          NULL,              -- puede asignarse después
    id_estado_asignacion INT         NOT NULL,
    eta_minutos         INT          NULL,              -- tiempo estimado de llegada
    costo_estimado      DECIMAL(10,2) NULL,
    nota_taller         VARCHAR(MAX) NULL,              -- observaciones del taller
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    updated_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_incidente)          REFERENCES INCIDENTE(id_incidente),
    FOREIGN KEY (id_taller)             REFERENCES TALLER(id_taller),
    FOREIGN KEY (id_tecnico)            REFERENCES TECNICO(id_tecnico),
    FOREIGN KEY (id_estado_asignacion)  REFERENCES ESTADO_ASIGNACION(id_estado_asignacion)
);

-- 4.2 EVIDENCIA (fotos, audios, texto)
CREATE TABLE EVIDENCIA (
    id_evidencia        INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_tipo_evidencia   INT          NOT NULL,          -- imagen | audio | texto
    url_archivo         VARCHAR(500) NOT NULL,          -- URL en almacenamiento (S3, GCS, etc.)
    transcripcion_audio VARCHAR(MAX) NULL,              -- resultado del módulo de speech-to-text
    descripcion_ia      VARCHAR(MAX) NULL,              -- análisis de la imagen por visión artificial
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_incidente)        REFERENCES INCIDENTE(id_incidente),
    FOREIGN KEY (id_tipo_evidencia)   REFERENCES TIPO_EVIDENCIA(id_tipo_evidencia)
);

-- 4.3 HISTORIAL DE ESTADOS del incidente
CREATE TABLE HISTORIAL_ESTADO_INCIDENTE (
    id_historial        INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_estado_anterior  INT          NULL,              -- NULL si es el estado inicial
    id_estado_nuevo     INT          NOT NULL,
    observacion         VARCHAR(500) NULL,
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_incidente)       REFERENCES INCIDENTE(id_incidente),
    FOREIGN KEY (id_estado_anterior) REFERENCES ESTADO_INCIDENTE(id_estado),
    FOREIGN KEY (id_estado_nuevo)    REFERENCES ESTADO_INCIDENTE(id_estado)
);

-- 4.4 HISTORIAL DE ESTADOS de la asignación
CREATE TABLE HISTORIAL_ESTADO_ASIGNACION (
    id_historial        INT IDENTITY(1,1) PRIMARY KEY,
    id_asignacion       INT          NOT NULL,
    id_estado_anterior  INT          NULL,
    id_estado_nuevo     INT          NOT NULL,
    observacion         VARCHAR(500) NULL,
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_asignacion)      REFERENCES ASIGNACION(id_asignacion),
    FOREIGN KEY (id_estado_anterior) REFERENCES ESTADO_ASIGNACION(id_estado_asignacion),
    FOREIGN KEY (id_estado_nuevo)    REFERENCES ESTADO_ASIGNACION(id_estado_asignacion)
);


-- ==========================================
-- 5. NOTIFICACIONES, PAGOS Y MÉTRICAS
-- ==========================================

-- 5.1 NOTIFICACION
CREATE TABLE NOTIFICACION (
    id_notificacion     INT IDENTITY(1,1) PRIMARY KEY,
    id_usuario          INT          NULL,              -- NULL si el destino es un taller
    id_taller           INT          NULL,              -- NULL si el destino es un usuario
    id_incidente        INT          NULL,
    titulo              VARCHAR(100) NOT NULL,
    mensaje             VARCHAR(MAX) NOT NULL,
    leido               BIT          NOT NULL DEFAULT 0,
    enviado_push        BIT          NOT NULL DEFAULT 0, -- si ya se mandó el push al dispositivo
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CHK_notif_destino CHECK (
        (id_usuario IS NOT NULL AND id_taller IS NULL) OR
        (id_usuario IS NULL AND id_taller IS NOT NULL)
    ),
    FOREIGN KEY (id_usuario)    REFERENCES USUARIO(id_usuario),
    FOREIGN KEY (id_taller)     REFERENCES TALLER(id_taller),
    FOREIGN KEY (id_incidente)  REFERENCES INCIDENTE(id_incidente)
);

-- 5.2 PAGO
CREATE TABLE PAGO (
    id_pago             INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_metodo_pago      INT          NOT NULL,
    id_estado_pago      INT          NOT NULL,
    monto_total         DECIMAL(10,2) NOT NULL,
    comision_plataforma DECIMAL(10,2) NOT NULL,        -- 10% del monto_total
    monto_taller        DECIMAL(10,2) NOT NULL,        -- 90% del monto_total
    referencia_externa  VARCHAR(100) NULL,             -- ID de la transacción en la pasarela de pago
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    updated_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_incidente)      REFERENCES INCIDENTE(id_incidente),
    FOREIGN KEY (id_metodo_pago)    REFERENCES METODO_PAGO(id_metodo_pago),
    FOREIGN KEY (id_estado_pago)    REFERENCES ESTADO_PAGO(id_estado_pago)
);

-- 5.3 MÉTRICA (KPIs por incidente)
CREATE TABLE METRICA (
    id_metrica              INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente            INT NOT NULL UNIQUE,
    fecha_inicio            DATETIME2 NULL,            -- cuando el usuario reportó
    fecha_asignacion        DATETIME2 NULL,            -- cuando se asignó el taller
    fecha_llegada_tecnico   DATETIME2 NULL,            -- cuando el técnico llegó
    fecha_fin               DATETIME2 NULL,            -- cuando se marcó como atendido
    tiempo_respuesta_min    INT       NULL,            -- fecha_asignacion - fecha_inicio
    tiempo_llegada_min      INT       NULL,            -- fecha_llegada_tecnico - fecha_asignacion
    tiempo_resolucion_min   INT       NULL,            -- fecha_fin - fecha_inicio
    calificacion_cliente    INT       NULL,            -- 1 a 5 estrellas
    comentario_cliente      VARCHAR(MAX) NULL,
    FOREIGN KEY (id_incidente) REFERENCES INCIDENTE(id_incidente)
);

-- 5.4 CANDIDATO_ASIGNACION (log del motor de asignación inteligente)
-- Guarda qué talleres fueron evaluados y por qué se eligió uno
CREATE TABLE CANDIDATO_ASIGNACION (
    id_candidato        INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_taller           INT          NOT NULL,
    distancia_km        FLOAT        NULL,
    score_total         FLOAT        NULL,             -- puntaje calculado por el motor
    seleccionado        BIT          NOT NULL DEFAULT 0,
    motivo_rechazo      VARCHAR(255) NULL,
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (id_incidente)  REFERENCES INCIDENTE(id_incidente),
    FOREIGN KEY (id_taller)     REFERENCES TALLER(id_taller)
);

-- 5.5 MENSAJE (chat opcional entre cliente y taller)
CREATE TABLE MENSAJE (
    id_mensaje          INT IDENTITY(1,1) PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_usuario          INT          NULL,             -- NULL si lo envía el taller
    id_taller           INT          NULL,             -- NULL si lo envía el usuario
    contenido           VARCHAR(MAX) NOT NULL,
    leido               BIT          NOT NULL DEFAULT 0,
    created_at          DATETIME2    NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CHK_msg_origen CHECK (
        (id_usuario IS NOT NULL AND id_taller IS NULL) OR
        (id_usuario IS NULL AND id_taller IS NOT NULL)
    ),
    FOREIGN KEY (id_incidente)  REFERENCES INCIDENTE(id_incidente),
    FOREIGN KEY (id_usuario)    REFERENCES USUARIO(id_usuario),
    FOREIGN KEY (id_taller)     REFERENCES TALLER(id_taller)
);


-- ==========================================
-- 6. ÍNDICES PARA RENDIMIENTO
-- ==========================================

-- Búsquedas frecuentes por usuario e incidente
CREATE INDEX IX_incidente_usuario   ON INCIDENTE(id_usuario);
CREATE INDEX IX_incidente_estado    ON INCIDENTE(id_estado);
CREATE INDEX IX_asignacion_incidente ON ASIGNACION(id_incidente);
CREATE INDEX IX_asignacion_taller   ON ASIGNACION(id_taller);
CREATE INDEX IX_evidencia_incidente ON EVIDENCIA(id_incidente);
CREATE INDEX IX_notif_usuario       ON NOTIFICACION(id_usuario);
CREATE INDEX IX_notif_taller        ON NOTIFICACION(id_taller);
CREATE INDEX IX_vehiculo_usuario    ON VEHICULO(id_usuario);
CREATE INDEX IX_tecnico_taller      ON TECNICO(id_taller);