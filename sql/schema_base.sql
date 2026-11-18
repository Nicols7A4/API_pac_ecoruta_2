-- =====================================================
-- EcoRuta - Script de creación y datos de prueba (MySQL 8+)
-- =====================================================
DROP DATABASE IF EXISTS pac_ecoruta_t3;
CREATE DATABASE pac_ecoruta_t3 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pac_ecoruta_t3;

-- ---------- TABLAS ----------

CREATE TABLE usuarios (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    correo        VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol           ENUM('SUPERVISOR','OPERARIO','FISCALIZADOR') NOT NULL,
    fcm_token     VARCHAR(255) NULL,
    activo        TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE vehiculos (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    placa     VARCHAR(10) NOT NULL UNIQUE,
    codigo_qr VARCHAR(50) NOT NULL UNIQUE,
    tipo      VARCHAR(50) NOT NULL,
    capacidad DECIMAL(6,2) NOT NULL COMMENT 'toneladas',
    estado    ENUM('DISPONIBLE','EN_USO','MANTENIMIENTO') NOT NULL DEFAULT 'DISPONIBLE'
) ENGINE=InnoDB;

CREATE TABLE puntos_recoleccion (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    codigo_qr        VARCHAR(50) NOT NULL UNIQUE,
    nombre           VARCHAR(100) NOT NULL,
    direccion        VARCHAR(200) NOT NULL,
    latitud          DECIMAL(10,7) NOT NULL,
    longitud         DECIMAL(10,7) NOT NULL,
    radio_validacion INT NOT NULL DEFAULT 50 COMMENT 'metros',
    activo           TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE rutas (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    codigo      VARCHAR(20) NOT NULL UNIQUE,
    fecha       DATE NOT NULL,
    turno       ENUM('MANANA','TARDE','NOCHE') NOT NULL,
    id_operario INT NULL,
    id_vehiculo INT NULL,
    estado      ENUM('PROGRAMADA','EN_CURSO','FINALIZADA','OBSERVADA') NOT NULL DEFAULT 'PROGRAMADA',
    hora_inicio DATETIME NULL,
    hora_fin    DATETIME NULL,
    CONSTRAINT fk_rutas_operario FOREIGN KEY (id_operario) REFERENCES usuarios(id),
    CONSTRAINT fk_rutas_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id),
    INDEX idx_rutas_fecha_estado (fecha, estado)
) ENGINE=InnoDB;

CREATE TABLE ruta_puntos (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta        INT NOT NULL,
    id_punto       INT NOT NULL,
    orden          INT NOT NULL,
    estado         ENUM('PENDIENTE','ATENDIDO','CON_INCIDENCIA') NOT NULL DEFAULT 'PENDIENTE',
    fecha_atencion DATETIME NULL,
    lat_registro   DECIMAL(10,7) NULL,
    lon_registro   DECIMAL(10,7) NULL,
    observacion    VARCHAR(255) NULL,
    uuid_operacion CHAR(36) NULL UNIQUE COMMENT 'idempotencia (offline/WorkManager)',
    id_usuario_atencion INT NULL,
    payload_hash  CHAR(64) NULL,
    CONSTRAINT fk_rp_ruta  FOREIGN KEY (id_ruta)  REFERENCES rutas(id) ON DELETE CASCADE,
    CONSTRAINT fk_rp_punto FOREIGN KEY (id_punto) REFERENCES puntos_recoleccion(id),
    CONSTRAINT fk_rp_usuario FOREIGN KEY (id_usuario_atencion) REFERENCES usuarios(id),
    UNIQUE KEY uq_ruta_punto (id_ruta, id_punto),
    UNIQUE KEY uq_ruta_orden (id_ruta, orden)
) ENGINE=InnoDB;

CREATE TABLE incidencias (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta_punto  INT NOT NULL,
    tipo           ENUM('ACCESO_BLOQUEADO','CONTENEDOR_DANADO','RESIDUOS_NO_DISPONIBLES',
                        'EXCESO_RESIDUOS','VEHICULO','OTRO') NOT NULL,
    descripcion    VARCHAR(500) NOT NULL,
    es_critica     TINYINT(1) NOT NULL DEFAULT 0,
    estado         ENUM('ABIERTA','EN_REVISION','RESUELTA') NOT NULL DEFAULT 'ABIERTA',
    observacion_control VARCHAR(500) NULL,
    id_usuario     INT NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_captura  DATETIME NULL,
    uuid_operacion CHAR(36) NULL UNIQUE COMMENT 'idempotencia (offline/WorkManager)',
    payload_hash   CHAR(64) NULL,
    CONSTRAINT fk_inc_rp  FOREIGN KEY (id_ruta_punto) REFERENCES ruta_puntos(id) ON DELETE CASCADE,
    CONSTRAINT fk_inc_usr FOREIGN KEY (id_usuario)    REFERENCES usuarios(id)
) ENGINE=InnoDB;

CREATE TABLE evidencias (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    id_incidencia INT NULL,
    id_ruta_punto INT NULL,
    ruta_archivo  VARCHAR(255) NOT NULL,
    tipo          ENUM('INCIDENCIA','ATENCION') NOT NULL,
    fecha         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ev_inc FOREIGN KEY (id_incidencia) REFERENCES incidencias(id) ON DELETE CASCADE,
    CONSTRAINT fk_ev_rp  FOREIGN KEY (id_ruta_punto) REFERENCES ruta_puntos(id) ON DELETE CASCADE,
    CONSTRAINT chk_ev_ref CHECK (id_incidencia IS NOT NULL OR id_ruta_punto IS NOT NULL)
) ENGINE=InnoDB;

CREATE TABLE historial_ruta (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta         INT NOT NULL,
    estado_anterior VARCHAR(20) NULL,
    estado_nuevo    VARCHAR(20) NOT NULL,
    comentario      VARCHAR(255) NULL,
    id_usuario      INT NOT NULL,
    id_vehiculo     INT NULL,
    hora_fin        DATETIME NULL,
    fecha           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_h_ruta FOREIGN KEY (id_ruta)    REFERENCES rutas(id) ON DELETE CASCADE,
    CONSTRAINT fk_h_usr  FOREIGN KEY (id_usuario) REFERENCES usuarios(id),
    CONSTRAINT fk_h_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE notificaciones_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    id_ruta    INT NULL,
    id_incidencia INT NULL,
    tipo       ENUM('RUTA_ASIGNADA','INCIDENCIA_CRITICA','RUTA_FINALIZADA','OBSERVACION') NOT NULL,
    mensaje    VARCHAR(255) NOT NULL,
    payload_json JSON NULL,
    estado_envio ENUM('PENDIENTE','REINTENTO','ENVIADA','FALLIDA') NOT NULL DEFAULT 'PENDIENTE',
    intentos INT NOT NULL DEFAULT 0,
    ultimo_intento DATETIME NULL,
    fcm_result VARCHAR(500) NULL,
    fecha      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_n_usr  FOREIGN KEY (id_usuario) REFERENCES usuarios(id),
    CONSTRAINT fk_n_ruta FOREIGN KEY (id_ruta) REFERENCES rutas(id) ON DELETE SET NULL,
    CONSTRAINT fk_n_incidencia FOREIGN KEY (id_incidencia) REFERENCES incidencias(id) ON DELETE SET NULL,
    INDEX idx_notificaciones_pendientes (estado_envio, intentos)
) ENGINE=InnoDB;

CREATE TABLE validaciones_ruta (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta INT NOT NULL,
    resultado ENUM('CONFORME') NOT NULL,
    comentario VARCHAR(255) NULL,
    id_fiscalizador INT NOT NULL,
    vigente TINYINT(1) NOT NULL DEFAULT 1,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_vr_ruta FOREIGN KEY (id_ruta) REFERENCES rutas(id) ON DELETE CASCADE,
    CONSTRAINT fk_vr_fiscalizador FOREIGN KEY (id_fiscalizador) REFERENCES usuarios(id),
    INDEX idx_validacion_vigente (id_ruta, vigente)
) ENGINE=InnoDB;

-- ---------- DATOS DE PRUEBA ----------
-- Contraseñas (hash Werkzeug/scrypt): Supervisor123 / Operario123 / Fiscal123

INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES
('Carlos Supervisor', 'supervisor@ecoruta.pe',
 'scrypt:32768:8:1$64L09cZgMgKTgixg$d1a9671c8582979cd5db9033a7102f1be9523944c65e6d4f12f622cc56111073799d7f5a9885d8a638ca03b7d0c87fe23871206e9195bc28254425ff84890968',
 'SUPERVISOR'),
('Luis Operario', 'operario@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04',
 'OPERARIO'),
('Rosa Fiscalizadora', 'fiscalizador@ecoruta.pe',
 'scrypt:32768:8:1$SQ8wgZNKB5hjKDJj$d615e915337f426d9477f870a4ee4a844092925e95d22cad91103fca2600627acdb2d8f45bdf56916a9ea069dd4e1e4c8f17ca66072b9f5b1998129162ac63d1',
 'FISCALIZADOR');

INSERT INTO vehiculos (placa, codigo_qr, tipo, capacidad, estado) VALUES
('ABC-123', 'VEH-001', 'Camión compactador', 8.00, 'EN_USO'),
('XYZ-789', 'VEH-002', 'Camión baranda',     5.00, 'DISPONIBLE');

-- Zona de prueba: Chiclayo. Fuentes y fecha de verificación en evidencias/COORDENADAS.md.
INSERT INTO puntos_recoleccion (codigo_qr, nombre, direccion, latitud, longitud, radio_validacion) VALUES
('PTO-001', 'Parque Principal',        'Plaza de Armas, Chiclayo',        -6.7714300, -79.8387700, 50),
('PTO-002', 'Catedral de Chiclayo',    'San José y Elías Aguirre',        -6.7716830, -79.8376410, 50),
('PTO-003', 'Mercado Modelo',          'Av. Balta / Arica, Chiclayo',     -6.7658846, -79.8391493, 50),
('PTO-004', 'Paseo de las Musas',      'La Florida, Chiclayo',            -6.7792000, -79.8388900, 50),
('PTO-005', 'Hospital Las Mercedes',   'Av. Luis Gonzales 635',           -6.7725417, -79.8428267, 50),
('PTO-006', 'Plazuela Elías Aguirre',  'San José y Elías Aguirre',        -6.7710800, -79.8430000, 50),
('PTO-007', 'Óvalo Quiñones',          'Av. Salaverry 40, Chiclayo',      -6.7700663, -79.8553199, 50),
('PTO-008', 'Terminal Emtrafesa',      'Av. Balta 110, Chiclayo',         -6.7766111, -79.8388333, 50);

-- 3 rutas: finalizada (ayer), en curso (hoy), programada (mañana)
INSERT INTO rutas (codigo, fecha, turno, id_operario, id_vehiculo, estado, hora_inicio, hora_fin) VALUES
('RUT-001', CURDATE() - INTERVAL 1 DAY, 'MANANA', 2, 1, 'FINALIZADA',
 CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:00:00'), CONCAT(CURDATE() - INTERVAL 1 DAY, ' 09:30:00')),
('RUT-002', CURDATE(), 'MANANA', 2, 1, 'EN_CURSO',
 CONCAT(CURDATE(), ' 07:00:00'), NULL),
('RUT-003', CURDATE() + INTERVAL 1 DAY, 'TARDE', NULL, NULL, 'PROGRAMADA', NULL, NULL);

-- RUT-001 (ayer): puntos 1-4, todos atendidos (uno con incidencia)
INSERT INTO ruta_puntos (id_ruta, id_punto, orden, estado, fecha_atencion, lat_registro, lon_registro, observacion, uuid_operacion) VALUES
(1, 1, 1, 'ATENDIDO',       CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:15:00'), -6.7714400, -79.8387800, NULL, UUID()),
(1, 2, 2, 'ATENDIDO',       CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:40:00'), -6.7716900, -79.8376500, NULL, UUID()),
(1, 3, 3, 'CON_INCIDENCIA', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:10:00'), -6.7658900, -79.8391600, 'Contenedor dañado', UUID()),
(1, 4, 4, 'ATENDIDO',       CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:50:00'), -6.7792100, -79.8389000, NULL, UUID());

-- RUT-002 (hoy): puntos 5-8, 1 atendido, 3 pendientes
INSERT INTO ruta_puntos (id_ruta, id_punto, orden, estado, fecha_atencion, lat_registro, lon_registro, observacion, uuid_operacion) VALUES
(2, 5, 1, 'ATENDIDO',  CONCAT(CURDATE(), ' 07:20:00'), -6.7725500, -79.8428300, NULL, UUID()),
(2, 6, 2, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL),
(2, 7, 3, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL),
(2, 8, 4, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL);

-- RUT-003 (mañana): puntos 1-4, sin atender
INSERT INTO ruta_puntos (id_ruta, id_punto, orden, estado) VALUES
(3, 1, 1, 'PENDIENTE'),
(3, 2, 2, 'PENDIENTE'),
(3, 3, 3, 'PENDIENTE'),
(3, 4, 4, 'PENDIENTE');

UPDATE ruta_puntos rp
INNER JOIN rutas r ON r.id = rp.id_ruta
SET rp.id_usuario_atencion = r.id_operario
WHERE rp.estado = 'ATENDIDO';

-- Incidencias (2 tipos distintos; la primera con foto)
INSERT INTO incidencias (id_ruta_punto, tipo, descripcion, es_critica, estado, id_usuario, fecha_registro, uuid_operacion) VALUES
(3, 'CONTENEDOR_DANADO', 'Contenedor roto, no se puede levantar con el compactador.', 1, 'EN_REVISION', 2,
 CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:08:00'), UUID()),
(5, 'ACCESO_BLOQUEADO', 'Vehículo mal estacionado bloqueando el acceso al contenedor.', 0, 'ABIERTA', 2,
 CONCAT(CURDATE(), ' 07:18:00'), UUID());

INSERT INTO evidencias (id_incidencia, id_ruta_punto, ruta_archivo, tipo, fecha) VALUES
(1, NULL, '/uploads/incidencias/inc_4_bf6103.jpg', 'INCIDENCIA', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:09:00'));

INSERT INTO historial_ruta (id_ruta, estado_anterior, estado_nuevo, comentario, id_usuario, fecha) VALUES
(1, NULL,         'PROGRAMADA', 'Ruta creada y asignada', 1, CONCAT(CURDATE() - INTERVAL 2 DAY, ' 18:00:00')),
(1, 'PROGRAMADA', 'EN_CURSO',   'Inicio de ruta',         2, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:00:00')),
(1, 'EN_CURSO',   'FINALIZADA', 'Ruta finalizada',        2, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 09:30:00')),
(2, NULL,         'PROGRAMADA', 'Ruta creada y asignada', 1, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 18:00:00')),
(2, 'PROGRAMADA', 'EN_CURSO',   'Inicio de ruta',         2, CONCAT(CURDATE(), ' 07:00:00')),
(3, NULL,         'PROGRAMADA', 'Ruta creada',            1, CONCAT(CURDATE(), ' 08:00:00'));

INSERT INTO notificaciones_log (id_usuario, id_ruta, tipo, mensaje, fcm_result, fecha) VALUES
(2, 2, 'RUTA_ASIGNADA',      'Se te asignó la ruta RUT-002',                 'demo', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 18:01:00')),
(1, 1, 'INCIDENCIA_CRITICA', 'Incidencia crítica en RUT-001: contenedor dañado', 'demo', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:08:30'));
