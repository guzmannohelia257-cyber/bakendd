-- ============================================================
-- PLATAFORMA INTELIGENTE DE ATENCION DE EMERGENCIAS VEHICULARES
-- Schema PostgreSQL - SNAPSHOT desde localhost:5432/emergencias_vehiculares
-- Generado automaticamente por scripts/dump_schema.py
-- NO EDITAR A MANO: regenerar con `python -m scripts.dump_schema`
-- ============================================================


-- ==========================================
-- 25 tablas reflejadas
-- ==========================================

-- ----- Tabla: categoria_problema -----
CREATE TABLE categoria_problema (
	id_categoria SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	descripcion VARCHAR(200), 
	icono_url VARCHAR(255), 
	CONSTRAINT categoria_problema_pkey PRIMARY KEY (id_categoria)
);

-- ----- Tabla: estado_asignacion -----
CREATE TABLE estado_asignacion (
	id_estado_asignacion SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	CONSTRAINT estado_asignacion_pkey PRIMARY KEY (id_estado_asignacion)
);

-- ----- Tabla: estado_incidente -----
CREATE TABLE estado_incidente (
	id_estado SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	descripcion VARCHAR(200), 
	CONSTRAINT estado_incidente_pkey PRIMARY KEY (id_estado)
);

-- ----- Tabla: estado_pago -----
CREATE TABLE estado_pago (
	id_estado_pago SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	CONSTRAINT estado_pago_pkey PRIMARY KEY (id_estado_pago)
);

-- ----- Tabla: metodo_pago -----
CREATE TABLE metodo_pago (
	id_metodo_pago SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	CONSTRAINT metodo_pago_pkey PRIMARY KEY (id_metodo_pago)
);

-- ----- Tabla: prioridad -----
CREATE TABLE prioridad (
	id_prioridad SERIAL NOT NULL, 
	nivel VARCHAR(50) NOT NULL, 
	orden INTEGER NOT NULL, 
	CONSTRAINT prioridad_pkey PRIMARY KEY (id_prioridad)
);

-- ----- Tabla: rol -----
CREATE TABLE rol (
	id_rol SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	CONSTRAINT rol_pkey PRIMARY KEY (id_rol)
);

-- ----- Tabla: taller -----
CREATE TABLE taller (
	id_taller SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	telefono VARCHAR(20), 
	password_hash VARCHAR(255) NOT NULL, 
	push_token VARCHAR(255), 
	latitud DOUBLE PRECISION, 
	longitud DOUBLE PRECISION, 
	direccion VARCHAR(255), 
	capacidad_max INTEGER DEFAULT 5 NOT NULL, 
	activo BOOLEAN DEFAULT true NOT NULL, 
	verificado BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	disponible BOOLEAN DEFAULT true NOT NULL, 
	CONSTRAINT taller_pkey PRIMARY KEY (id_taller), 
	CONSTRAINT taller_email_key UNIQUE NULLS DISTINCT (email)
);

CREATE UNIQUE INDEX IF NOT EXISTS "taller_email_key" ON "taller" (email);

-- ----- Tabla: tipo_evidencia -----
CREATE TABLE tipo_evidencia (
	id_tipo_evidencia SERIAL NOT NULL, 
	nombre VARCHAR(50) NOT NULL, 
	CONSTRAINT tipo_evidencia_pkey PRIMARY KEY (id_tipo_evidencia)
);

-- ----- Tabla: taller_servicio -----
CREATE TABLE taller_servicio (
	id_taller_servicio SERIAL NOT NULL, 
	id_taller INTEGER NOT NULL, 
	id_categoria INTEGER NOT NULL, 
	servicio_movil BOOLEAN DEFAULT false NOT NULL, 
	CONSTRAINT taller_servicio_pkey PRIMARY KEY (id_taller_servicio), 
	CONSTRAINT taller_servicio_id_categoria_fkey FOREIGN KEY(id_categoria) REFERENCES categoria_problema (id_categoria), 
	CONSTRAINT taller_servicio_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller), 
	CONSTRAINT uq_taller_categoria UNIQUE NULLS DISTINCT (id_taller, id_categoria)
);

CREATE UNIQUE INDEX IF NOT EXISTS "uq_taller_categoria" ON "taller_servicio" (id_taller, id_categoria);

-- ----- Tabla: tecnico -----
CREATE TABLE tecnico (
	id_tecnico SERIAL NOT NULL, 
	id_taller INTEGER NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	telefono VARCHAR(20), 
	disponible BOOLEAN DEFAULT true NOT NULL, 
	latitud DOUBLE PRECISION, 
	longitud DOUBLE PRECISION, 
	activo BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	email VARCHAR(100), 
	password_hash VARCHAR(255), 
	CONSTRAINT tecnico_pkey PRIMARY KEY (id_tecnico), 
	CONSTRAINT tecnico_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller)
);

CREATE UNIQUE INDEX IF NOT EXISTS "ix_tecnico_email" ON "tecnico" (email);
CREATE INDEX IF NOT EXISTS "ix_tecnico_taller" ON "tecnico" (id_taller);

-- ----- Tabla: usuario -----
CREATE TABLE usuario (
	id_usuario SERIAL NOT NULL, 
	id_rol INTEGER NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	telefono VARCHAR(20), 
	password_hash VARCHAR(255) NOT NULL, 
	push_token VARCHAR(255), 
	activo BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario), 
	CONSTRAINT usuario_id_rol_fkey FOREIGN KEY(id_rol) REFERENCES rol (id_rol), 
	CONSTRAINT usuario_email_key UNIQUE NULLS DISTINCT (email)
);

CREATE UNIQUE INDEX IF NOT EXISTS "usuario_email_key" ON "usuario" (email);

-- ----- Tabla: usuario_taller -----
CREATE TABLE usuario_taller (
	id_usuario_taller SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_taller INTEGER NOT NULL, 
	disponible BOOLEAN DEFAULT true NOT NULL, 
	activo BOOLEAN DEFAULT true NOT NULL, 
	latitud DOUBLE PRECISION, 
	longitud DOUBLE PRECISION, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	CONSTRAINT usuario_taller_pkey PRIMARY KEY (id_usuario_taller), 
	CONSTRAINT usuario_taller_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller) ON DELETE CASCADE, 
	CONSTRAINT usuario_taller_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario) ON DELETE CASCADE, 
	CONSTRAINT usuario_taller_id_usuario_id_taller_key UNIQUE NULLS DISTINCT (id_usuario, id_taller)
);

CREATE INDEX IF NOT EXISTS "idx_usuario_taller_disponible" ON "usuario_taller" (disponible);
CREATE INDEX IF NOT EXISTS "idx_usuario_taller_id_taller" ON "usuario_taller" (id_taller);
CREATE INDEX IF NOT EXISTS "idx_usuario_taller_id_usuario" ON "usuario_taller" (id_usuario);
CREATE UNIQUE INDEX IF NOT EXISTS "usuario_taller_id_usuario_id_taller_key" ON "usuario_taller" (id_usuario, id_taller);

-- ----- Tabla: vehiculo -----
CREATE TABLE vehiculo (
	id_vehiculo SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	placa VARCHAR(20) NOT NULL, 
	marca VARCHAR(50), 
	modelo VARCHAR(50), 
	anio INTEGER, 
	color VARCHAR(30), 
	activo BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT vehiculo_pkey PRIMARY KEY (id_vehiculo), 
	CONSTRAINT vehiculo_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
);

CREATE INDEX IF NOT EXISTS "ix_vehiculo_usuario" ON "vehiculo" (id_usuario);

-- ----- Tabla: incidente -----
CREATE TABLE incidente (
	id_incidente SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_vehiculo INTEGER NOT NULL, 
	id_estado INTEGER NOT NULL, 
	id_categoria INTEGER, 
	id_prioridad INTEGER, 
	latitud DOUBLE PRECISION NOT NULL, 
	longitud DOUBLE PRECISION NOT NULL, 
	descripcion_usuario TEXT, 
	resumen_ia TEXT, 
	clasificacion_ia_confianza DOUBLE PRECISION, 
	requiere_revision_manual BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT incidente_pkey PRIMARY KEY (id_incidente), 
	CONSTRAINT incidente_id_categoria_fkey FOREIGN KEY(id_categoria) REFERENCES categoria_problema (id_categoria), 
	CONSTRAINT incidente_id_estado_fkey FOREIGN KEY(id_estado) REFERENCES estado_incidente (id_estado), 
	CONSTRAINT incidente_id_prioridad_fkey FOREIGN KEY(id_prioridad) REFERENCES prioridad (id_prioridad), 
	CONSTRAINT incidente_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario), 
	CONSTRAINT incidente_id_vehiculo_fkey FOREIGN KEY(id_vehiculo) REFERENCES vehiculo (id_vehiculo)
);

CREATE INDEX IF NOT EXISTS "ix_incidente_estado" ON "incidente" (id_estado);
CREATE INDEX IF NOT EXISTS "ix_incidente_usuario" ON "incidente" (id_usuario);

-- ----- Tabla: asignacion -----
CREATE TABLE asignacion (
	id_asignacion SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_taller INTEGER NOT NULL, 
	id_usuario INTEGER, 
	id_estado_asignacion INTEGER NOT NULL, 
	eta_minutos INTEGER, 
	costo_estimado NUMERIC(10, 2), 
	nota_taller TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT asignacion_pkey PRIMARY KEY (id_asignacion), 
	CONSTRAINT asignacion_id_estado_asignacion_fkey FOREIGN KEY(id_estado_asignacion) REFERENCES estado_asignacion (id_estado_asignacion), 
	CONSTRAINT asignacion_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT asignacion_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller), 
	CONSTRAINT asignacion_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS "ix_asignacion_id_usuario" ON "asignacion" (id_usuario);
CREATE INDEX IF NOT EXISTS "ix_asignacion_incidente" ON "asignacion" (id_incidente);
CREATE INDEX IF NOT EXISTS "ix_asignacion_taller" ON "asignacion" (id_taller);
CREATE INDEX IF NOT EXISTS "ix_asignacion_usuario_estado" ON "asignacion" (id_usuario, id_estado_asignacion);

-- ----- Tabla: candidato_asignacion -----
CREATE TABLE candidato_asignacion (
	id_candidato SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_taller INTEGER NOT NULL, 
	distancia_km DOUBLE PRECISION, 
	score_total DOUBLE PRECISION, 
	seleccionado BOOLEAN DEFAULT false NOT NULL, 
	motivo_rechazo VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT candidato_asignacion_pkey PRIMARY KEY (id_candidato), 
	CONSTRAINT candidato_asignacion_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT candidato_asignacion_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller)
);

CREATE INDEX IF NOT EXISTS "ix_candidato_incidente" ON "candidato_asignacion" (id_incidente);

-- ----- Tabla: evaluacion -----
CREATE TABLE evaluacion (
	id_evaluacion SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	id_taller INTEGER NOT NULL, 
	id_tecnico INTEGER, 
	estrellas INTEGER NOT NULL, 
	comentario TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT evaluacion_pkey PRIMARY KEY (id_evaluacion), 
	CONSTRAINT evaluacion_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT evaluacion_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller), 
	CONSTRAINT evaluacion_id_tecnico_fkey FOREIGN KEY(id_tecnico) REFERENCES tecnico (id_tecnico), 
	CONSTRAINT evaluacion_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario), 
	CONSTRAINT evaluacion_id_incidente_key UNIQUE NULLS DISTINCT (id_incidente)
);

CREATE UNIQUE INDEX IF NOT EXISTS "evaluacion_id_incidente_key" ON "evaluacion" (id_incidente);
CREATE INDEX IF NOT EXISTS "ix_evaluacion_id_evaluacion" ON "evaluacion" (id_evaluacion);

-- ----- Tabla: evidencia -----
CREATE TABLE evidencia (
	id_evidencia SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_tipo_evidencia INTEGER NOT NULL, 
	url_archivo VARCHAR(500) NOT NULL, 
	transcripcion_audio TEXT, 
	descripcion_ia TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT evidencia_pkey PRIMARY KEY (id_evidencia), 
	CONSTRAINT evidencia_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT evidencia_id_tipo_evidencia_fkey FOREIGN KEY(id_tipo_evidencia) REFERENCES tipo_evidencia (id_tipo_evidencia)
);

CREATE INDEX IF NOT EXISTS "ix_evidencia_incidente" ON "evidencia" (id_incidente);

-- ----- Tabla: historial_estado_incidente -----
CREATE TABLE historial_estado_incidente (
	id_historial SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_estado_anterior INTEGER, 
	id_estado_nuevo INTEGER NOT NULL, 
	observacion VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT historial_estado_incidente_pkey PRIMARY KEY (id_historial), 
	CONSTRAINT historial_estado_incidente_id_estado_anterior_fkey FOREIGN KEY(id_estado_anterior) REFERENCES estado_incidente (id_estado), 
	CONSTRAINT historial_estado_incidente_id_estado_nuevo_fkey FOREIGN KEY(id_estado_nuevo) REFERENCES estado_incidente (id_estado), 
	CONSTRAINT historial_estado_incidente_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente)
);

-- ----- Tabla: mensaje -----
CREATE TABLE mensaje (
	id_mensaje SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_usuario INTEGER, 
	id_taller INTEGER, 
	contenido TEXT NOT NULL, 
	leido BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT mensaje_pkey PRIMARY KEY (id_mensaje), 
	CONSTRAINT mensaje_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT mensaje_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller), 
	CONSTRAINT mensaje_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario), 
	CONSTRAINT chk_msg_origen CHECK (id_usuario IS NOT NULL AND id_taller IS NULL OR id_usuario IS NULL AND id_taller IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS "ix_mensaje_incidente" ON "mensaje" (id_incidente);

-- ----- Tabla: metrica -----
CREATE TABLE metrica (
	id_metrica SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	fecha_inicio TIMESTAMP WITHOUT TIME ZONE, 
	fecha_asignacion TIMESTAMP WITHOUT TIME ZONE, 
	fecha_llegada_tecnico TIMESTAMP WITHOUT TIME ZONE, 
	fecha_fin TIMESTAMP WITHOUT TIME ZONE, 
	tiempo_respuesta_min INTEGER, 
	tiempo_llegada_min INTEGER, 
	tiempo_resolucion_min INTEGER, 
	calificacion_cliente INTEGER, 
	comentario_cliente TEXT, 
	CONSTRAINT metrica_pkey PRIMARY KEY (id_metrica), 
	CONSTRAINT metrica_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT metrica_id_incidente_key UNIQUE NULLS DISTINCT (id_incidente)
);

CREATE UNIQUE INDEX IF NOT EXISTS "metrica_id_incidente_key" ON "metrica" (id_incidente);

-- ----- Tabla: notificacion -----
CREATE TABLE notificacion (
	id_notificacion SERIAL NOT NULL, 
	id_usuario INTEGER, 
	id_taller INTEGER, 
	id_incidente INTEGER, 
	titulo VARCHAR(100) NOT NULL, 
	mensaje TEXT NOT NULL, 
	leido BOOLEAN DEFAULT false NOT NULL, 
	enviado_push BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT notificacion_pkey PRIMARY KEY (id_notificacion), 
	CONSTRAINT notificacion_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT notificacion_id_taller_fkey FOREIGN KEY(id_taller) REFERENCES taller (id_taller), 
	CONSTRAINT notificacion_id_usuario_fkey FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario), 
	CONSTRAINT chk_notif_destino CHECK (id_usuario IS NOT NULL AND id_taller IS NULL OR id_usuario IS NULL AND id_taller IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS "ix_notif_taller" ON "notificacion" (id_taller);
CREATE INDEX IF NOT EXISTS "ix_notif_usuario" ON "notificacion" (id_usuario);

-- ----- Tabla: pago -----
CREATE TABLE pago (
	id_pago SERIAL NOT NULL, 
	id_incidente INTEGER NOT NULL, 
	id_metodo_pago INTEGER NOT NULL, 
	id_estado_pago INTEGER NOT NULL, 
	monto_total NUMERIC(10, 2) NOT NULL, 
	comision_plataforma NUMERIC(10, 2) NOT NULL, 
	monto_taller NUMERIC(10, 2) NOT NULL, 
	referencia_externa VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pago_pkey PRIMARY KEY (id_pago), 
	CONSTRAINT pago_id_estado_pago_fkey FOREIGN KEY(id_estado_pago) REFERENCES estado_pago (id_estado_pago), 
	CONSTRAINT pago_id_incidente_fkey FOREIGN KEY(id_incidente) REFERENCES incidente (id_incidente), 
	CONSTRAINT pago_id_metodo_pago_fkey FOREIGN KEY(id_metodo_pago) REFERENCES metodo_pago (id_metodo_pago)
);

-- ----- Tabla: historial_estado_asignacion -----
CREATE TABLE historial_estado_asignacion (
	id_historial SERIAL NOT NULL, 
	id_asignacion INTEGER NOT NULL, 
	id_estado_anterior INTEGER, 
	id_estado_nuevo INTEGER NOT NULL, 
	observacion VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT historial_estado_asignacion_pkey PRIMARY KEY (id_historial), 
	CONSTRAINT historial_estado_asignacion_id_asignacion_fkey FOREIGN KEY(id_asignacion) REFERENCES asignacion (id_asignacion), 
	CONSTRAINT historial_estado_asignacion_id_estado_anterior_fkey FOREIGN KEY(id_estado_anterior) REFERENCES estado_asignacion (id_estado_asignacion), 
	CONSTRAINT historial_estado_asignacion_id_estado_nuevo_fkey FOREIGN KEY(id_estado_nuevo) REFERENCES estado_asignacion (id_estado_asignacion)
);
