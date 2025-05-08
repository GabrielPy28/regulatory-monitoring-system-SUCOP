-- Esquema de base de datos para el Sistema de Monitoreo Regulatorio

-- Tabla de entidades reguladoras
CREATE TABLE entidades (
    id_entidad SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de estados de normativas
CREATE TABLE estados (
    id_estado SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,
    es_activo BOOLEAN DEFAULT true
);

-- Tabla de tipos de documentos
CREATE TABLE tipos_documento (
    id_tipo_documento SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    es_activo BOOLEAN DEFAULT true
);

-- Tabla principal de normativas
CREATE TABLE normativas (
    id_normativa SERIAL PRIMARY KEY,
    id_entidad INTEGER REFERENCES entidades(id_entidad),
    id_estado INTEGER REFERENCES estados(id_estado),
    id_tipo_documento INTEGER REFERENCES tipos_documento(id_tipo_documento),
    titulo TEXT NOT NULL,
    url TEXT NOT NULL,
    fecha_publicacion DATE NOT NULL,
    fecha_cierre DATE,
    fecha_ultima_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    num_comentarios INTEGER DEFAULT 0,
    CONSTRAINT uk_normativa_url UNIQUE (url)
);

-- Tabla para almacenar palabras clave estratégicas
CREATE TABLE palabras_clave (
    id_palabra_clave SERIAL PRIMARY KEY,
    palabra VARCHAR(100) NOT NULL,
    categoria VARCHAR(50),
    prioridad INTEGER DEFAULT 1,
    es_activa BOOLEAN DEFAULT true,
    CONSTRAINT uk_palabra UNIQUE (palabra)
);

-- Tabla de relación entre normativas y palabras clave
CREATE TABLE normativas_palabras_clave (
    id_normativa INTEGER REFERENCES normativas(id_normativa),
    id_palabra_clave INTEGER REFERENCES palabras_clave(id_palabra_clave),
    PRIMARY KEY (id_normativa, id_palabra_clave)
);

-- Tabla para almacenar documentos adjuntos
CREATE TABLE documentos (
    id_documento SERIAL PRIMARY KEY,
    id_normativa INTEGER REFERENCES normativas(id_normativa),
    nombre_archivo VARCHAR(255) NOT NULL,
    tipo_archivo VARCHAR(50),
    url_documento TEXT,
    contenido_texto TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de alertas configuradas
CREATE TABLE alertas (
    id_alerta SERIAL PRIMARY KEY,
    tipo_alerta VARCHAR(50) NOT NULL,
    descripcion TEXT,
    dias_anticipacion INTEGER,
    es_activa BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de registro de alertas generadas
CREATE TABLE registro_alertas (
    id_registro SERIAL PRIMARY KEY,
    id_alerta INTEGER REFERENCES alertas(id_alerta),
    id_normativa INTEGER REFERENCES normativas(id_normativa),
    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado_notificacion VARCHAR(50),
    mensaje TEXT
);

-- Índices para optimizar búsquedas
CREATE INDEX idx_normativas_fecha_publicacion ON normativas(fecha_publicacion);
CREATE INDEX idx_normativas_fecha_cierre ON normativas(fecha_cierre);
CREATE INDEX idx_normativas_estado ON normativas(id_estado);
CREATE INDEX idx_palabras_clave_palabra ON palabras_clave(palabra);

-- Vistas para análisis
CREATE VIEW v_normativas_activas AS
SELECT 
    n.id_normativa,
    n.titulo,
    e.nombre as entidad,
    td.nombre as tipo_documento,
    s.nombre as estado,
    n.fecha_publicacion,
    n.fecha_cierre,
    n.num_comentarios
FROM normativas n
JOIN entidades e ON n.id_entidad = e.id_entidad
JOIN tipos_documento td ON n.id_tipo_documento = td.id_tipo_documento
JOIN estados s ON n.id_estado = s.id_estado
WHERE s.nombre = 'Activa';

CREATE VIEW v_alertas_proximas AS
SELECT 
    n.id_normativa,
    n.titulo,
    n.fecha_cierre,
    e.nombre as entidad,
    (n.fecha_cierre - CURRENT_DATE) as dias_restantes
FROM normativas n
JOIN entidades e ON n.id_entidad = e.id_entidad
WHERE n.fecha_cierre >= CURRENT_DATE
ORDER BY n.fecha_cierre ASC; 