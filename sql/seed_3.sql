-- =====================================================================
-- EcoRuta · Esquema y datos de demostración unificados
-- ---------------------------------------------------------------------
-- ADVERTENCIA: elimina y recrea las tablas de EcoRuta en la base seleccionada.
-- Se perderán todos sus datos actuales. No ejecutar en producción.
-- Requiere una base de datos existente y seleccionada en el cliente mysql.
-- Cargar desde la raíz del proyecto:
--   mysql -u root -p pac_ecoruta_t3 < pac_ecoruta/sql/seed_3.sql
-- Es una restauración de datos demo, no un backup de datos actuales ni archivos.
-- Las fechas de demostración son relativas a hoy en la zona horaria de Perú.
-- =====================================================================
SET time_zone = '-05:00';
SET NAMES utf8mb4;
SET SQL_SAFE_UPDATES = 0;

-- ---------- 0. Fechas de referencia ----------
SET @hoy      = CURDATE();
SET @ayer     = CURDATE() - INTERVAL 1 DAY;
SET @anteayer = CURDATE() - INTERVAL 2 DAY;
SET @manana   = CURDATE() + INTERVAL 1 DAY;

-- ---------- 1. Reconstrucción de las tablas de EcoRuta ----------
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS validaciones_ruta;
DROP TABLE IF EXISTS notificaciones_log;
DROP TABLE IF EXISTS historial_ruta;
DROP TABLE IF EXISTS evidencias;
DROP TABLE IF EXISTS incidencias;
DROP TABLE IF EXISTS ruta_puntos;
DROP TABLE IF EXISTS rutas;
DROP TABLE IF EXISTS puntos_recoleccion;
DROP TABLE IF EXISTS vehiculos;
DROP TABLE IF EXISTS usuarios;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------- TABLAS ----------

CREATE TABLE usuarios (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    correo        VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol           ENUM('SUPERVISOR','OPERARIO','FISCALIZADOR') NOT NULL,
    fcm_token     VARCHAR(255) NULL,
    activo        TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE vehiculos (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    placa     VARCHAR(10) NOT NULL UNIQUE,
    codigo_qr VARCHAR(50) NOT NULL UNIQUE,
    tipo      VARCHAR(50) NOT NULL,
    capacidad DECIMAL(6,2) NOT NULL COMMENT 'toneladas',
    estado    ENUM('DISPONIBLE','EN_USO','MANTENIMIENTO') NOT NULL DEFAULT 'DISPONIBLE'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE puntos_recoleccion (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    codigo_qr        VARCHAR(50) NOT NULL UNIQUE,
    nombre           VARCHAR(100) NOT NULL,
    direccion        VARCHAR(200) NOT NULL,
    latitud          DECIMAL(10,7) NOT NULL,
    longitud         DECIMAL(10,7) NOT NULL,
    radio_validacion INT NOT NULL DEFAULT 50 COMMENT 'metros',
    activo           TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ---------- 2. Usuarios ----------
-- Contraseñas: Supervisor123 / Operario123 (Luis y Marta) / Fiscal123
SET @h_sup = 'scrypt:32768:8:1$64L09cZgMgKTgixg$d1a9671c8582979cd5db9033a7102f1be9523944c65e6d4f12f622cc56111073799d7f5a9885d8a638ca03b7d0c87fe23871206e9195bc28254425ff84890968';
SET @h_ope = 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04';
SET @h_fis = 'scrypt:32768:8:1$SQ8wgZNKB5hjKDJj$d615e915337f426d9477f870a4ee4a844092925e95d22cad91103fca2600627acdb2d8f45bdf56916a9ea069dd4e1e4c8f17ca66072b9f5b1998129162ac63d1';

INSERT INTO usuarios (id, nombre, correo, password_hash, rol) VALUES
(1, 'Carlos Supervisor',   'supervisor@ecoruta.pe',   @h_sup, 'SUPERVISOR'),
(2, 'Luis Operario',       'operario@ecoruta.pe',     @h_ope, 'OPERARIO'),
(3, 'Rosa Fiscalizadora',  'fiscalizador@ecoruta.pe', @h_fis, 'FISCALIZADOR'),
(4, 'Marta Operaria',      'operario2@ecoruta.pe',    @h_ope, 'OPERARIO');

-- ---------- 3. Vehículos ----------
-- 1 en uso (RUT-002), 1 disponible (para asignar), 1 en mantenimiento (prueba de error 400)
INSERT INTO vehiculos (id, placa, codigo_qr, tipo, capacidad, estado) VALUES
(1, 'ABC-123', 'VEH-001', 'Camión compactador', 8.00, 'EN_USO'),
(2, 'XYZ-789', 'VEH-002', 'Camión baranda',     5.00, 'DISPONIBLE'),
(3, 'DEF-456', 'VEH-003', 'Camión volquete',    6.50, 'MANTENIMIENTO');

-- ---------- 4. Puntos de recolección (catálogo fijo = contenedores) ----------
-- 001-008: centro de Chiclayo (verificados, ver evidencias/COORDENADAS.md)
-- 009-013: zona USAT / oeste (VERIFICAR con el celular antes de la demo)
INSERT INTO puntos_recoleccion (id, codigo_qr, nombre, direccion, latitud, longitud, radio_validacion) VALUES
( 1, 'PTO-001', 'Parque Principal',                   'Plaza de Armas, Chiclayo',                    -6.7714300, -79.8387700, 50),
( 2, 'PTO-002', 'Catedral de Chiclayo',               'San José y Elías Aguirre',                    -6.7716830, -79.8376410, 50),
( 3, 'PTO-003', 'Mercado Modelo',                     'Av. Balta / Arica, Chiclayo',                 -6.7658846, -79.8391493, 50),
( 4, 'PTO-004', 'Paseo de las Musas',                 'La Florida, Chiclayo',                        -6.7792000, -79.8388900, 50),
( 5, 'PTO-005', 'Hospital Las Mercedes',              'Av. Luis Gonzales 635',                       -6.7725417, -79.8428267, 50),
( 6, 'PTO-006', 'Plazuela Elías Aguirre',             'San José y Elías Aguirre',                    -6.7710800, -79.8430000, 50),
( 7, 'PTO-007', 'Óvalo Quiñones',                     'Av. Salaverry 40, Chiclayo',                  -6.7700663, -79.8553199, 50),
( 8, 'PTO-008', 'Terminal Emtrafesa',                 'Av. Balta 110, Chiclayo',                     -6.7766111, -79.8388333, 50),
( 9, 'PTO-009', 'Campus USAT - Pabellón Ingeniería',  'Av. San Josemaría Escrivá de Balaguer 855',   -6.7606500, -79.8632500, 50),
(10, 'PTO-010', 'Campus USAT - Puerta Principal',     'Av. San Josemaría Escrivá de Balaguer 855',   -6.7614500, -79.8621500, 50),
(11, 'PTO-011', 'Mall Aventura Chiclayo - Acceso Norte', 'Panamericana Norte / Av. Leguía',          -6.7634500, -79.8617500, 50),
(12, 'PTO-012', 'Sodimac Patazca - Contenedor Exterior', 'Av. Salaverry cdra. 12',                   -6.7676500, -79.8528500, 50),
(13, 'PTO-013', 'Parque Urb. La Primavera',           'Calle Los Álamos / Av. Belaúnde',             -6.7631500, -79.8568500, 50);

-- ---------- 5. Rutas ----------
--  RUT-001  ayer  MAÑANA  Luis   FINALIZADA   centro, para que el fiscalizador valide/observe
--  RUT-002  hoy   MAÑANA  Luis   EN_CURSO      USAT, ruta de la DEMO en vivo (todos pendientes)
--  RUT-003  mañana TARDE  sin asignar PROGRAMADA   para probar "Asignar" del supervisor
--  RUT-004  ayer  TARDE   Marta  OBSERVADA    con observación del fiscalizador (probar "Reabrir")
INSERT INTO rutas (id, codigo, fecha, turno, id_operario, id_vehiculo, estado, hora_inicio, hora_fin) VALUES
(1, 'RUT-001', @ayer,   'MANANA', 2,    1,    'FINALIZADA', TIMESTAMP(@ayer, '07:00:00'), TIMESTAMP(@ayer, '09:30:00')),
(2, 'RUT-002', @hoy,    'MANANA', 2,    1,    'EN_CURSO',   TIMESTAMP(@hoy,  '07:00:00'), NULL),
(3, 'RUT-003', @manana, 'TARDE',  NULL, NULL, 'PROGRAMADA', NULL, NULL),
(4, 'RUT-004', @ayer,   'TARDE',  4,    2,    'OBSERVADA',  TIMESTAMP(@ayer, '14:00:00'), TIMESTAMP(@ayer, '16:30:00'));

-- ---------- 6. Puntos de cada ruta ----------
-- (id, id_ruta, id_punto, orden, estado, fecha_atencion, observacion)
INSERT INTO ruta_puntos (id, id_ruta, id_punto, orden, estado, fecha_atencion, observacion) VALUES
-- RUT-001 (ayer, finalizada): 4 resueltos, uno con incidencia
( 1, 1,  1, 1, 'ATENDIDO',       TIMESTAMP(@ayer, '07:15:00'), NULL),
( 2, 1,  2, 2, 'ATENDIDO',       TIMESTAMP(@ayer, '07:40:00'), NULL),
( 3, 1,  3, 3, 'CON_INCIDENCIA', TIMESTAMP(@ayer, '08:10:00'), 'Contenedor dañado'),
( 4, 1,  4, 4, 'ATENDIDO',       TIMESTAMP(@ayer, '08:50:00'), NULL),
-- RUT-002 (hoy, en curso, DEMO USAT): todos pendientes
( 5, 2,  9, 1, 'PENDIENTE', NULL, NULL),
( 6, 2, 10, 2, 'PENDIENTE', NULL, NULL),
( 7, 2, 11, 3, 'PENDIENTE', NULL, NULL),
( 8, 2, 13, 4, 'PENDIENTE', NULL, NULL),
-- RUT-003 (mañana, programada, sin asignar)
( 9, 3,  5, 1, 'PENDIENTE', NULL, NULL),
(10, 3,  6, 2, 'PENDIENTE', NULL, NULL),
(11, 3,  7, 3, 'PENDIENTE', NULL, NULL),
(12, 3,  8, 4, 'PENDIENTE', NULL, NULL),
-- RUT-004 (ayer tarde, observada)
(13, 4, 13, 1, 'ATENDIDO',       TIMESTAMP(@ayer, '14:20:00'), NULL),
(14, 4, 12, 2, 'CON_INCIDENCIA', TIMESTAMP(@ayer, '14:50:00'), 'Acceso bloqueado'),
(15, 4, 11, 3, 'ATENDIDO',       TIMESTAMP(@ayer, '15:30:00'), NULL),
(16, 4, 10, 4, 'ATENDIDO',       TIMESTAMP(@ayer, '16:10:00'), NULL);

-- Datos derivados de las atenciones ya hechas. Se calculan desde el catálogo, así
-- siguen siendo coherentes aunque corrijan las coordenadas de un punto (~3 m de offset).
UPDATE ruta_puntos rp
JOIN rutas r             ON r.id = rp.id_ruta
JOIN puntos_recoleccion p ON p.id = rp.id_punto
SET rp.lat_registro        = p.latitud  + 0.0000200,
    rp.lon_registro        = p.longitud - 0.0000200,
    rp.id_usuario_atencion = r.id_operario,
    rp.uuid_operacion      = CONCAT('a0000000-0000-4000-8000-', LPAD(rp.id, 12, '0'))
WHERE rp.estado IN ('ATENDIDO', 'CON_INCIDENCIA');

-- ---------- 7. Incidencias (2 tipos distintos; la 1 con foto y crítica) ----------
INSERT INTO incidencias
 (id, id_ruta_punto, tipo, descripcion, es_critica, estado, observacion_control,
  id_usuario, fecha_registro, fecha_captura, uuid_operacion) VALUES
(1, 3,  'CONTENEDOR_DANADO', 'Contenedor roto; no se puede levantar con el compactador.', 1, 'EN_REVISION',
 'Se coordina el cambio del contenedor', 2, TIMESTAMP(@ayer, '08:08:00'), TIMESTAMP(@ayer, '08:07:30'),
 'b0000000-0000-4000-8000-000000000001'),
(2, 14, 'ACCESO_BLOQUEADO',   'Vehículo mal estacionado bloqueando el acceso al contenedor.', 0, 'ABIERTA',
 NULL, 4, TIMESTAMP(@ayer, '14:48:00'), TIMESTAMP(@ayer, '14:47:30'),
 'b0000000-0000-4000-8000-000000000002');

INSERT INTO evidencias (id, id_incidencia, id_ruta_punto, ruta_archivo, tipo, fecha) VALUES
(1, 1, 3, '/uploads/incidencias/inc_4_bf6103.jpg', 'INCIDENCIA', TIMESTAMP(@ayer, '08:09:00'));

-- ---------- 8. Historial de rutas ----------
INSERT INTO historial_ruta (id_ruta, estado_anterior, estado_nuevo, comentario, id_usuario, id_vehiculo, hora_fin, fecha) VALUES
(1, NULL,         'PROGRAMADA', 'Ruta creada y asignada', 1, 1, NULL, TIMESTAMP(@anteayer, '18:00:00')),
(1, 'PROGRAMADA', 'EN_CURSO',   'Inicio de ruta',         2, 1, NULL, TIMESTAMP(@ayer,     '07:00:00')),
(1, 'EN_CURSO',   'FINALIZADA', 'Ruta finalizada',        2, 1, TIMESTAMP(@ayer, '09:30:00'), TIMESTAMP(@ayer, '09:30:00')),
(2, NULL,         'PROGRAMADA', 'Ruta creada y asignada', 1, 1, NULL, TIMESTAMP(@ayer,     '18:00:00')),
(2, 'PROGRAMADA', 'EN_CURSO',   'Inicio de ruta',         2, 1, NULL, TIMESTAMP(@hoy,      '07:00:00')),
(3, NULL,         'PROGRAMADA', 'Ruta creada',            1, NULL, NULL, TIMESTAMP(@hoy,      '08:00:00')),
(4, NULL,         'PROGRAMADA', 'Ruta creada y asignada', 1, 2, NULL, TIMESTAMP(@anteayer, '18:00:00')),
(4, 'PROGRAMADA', 'EN_CURSO',   'Inicio de ruta',         4, 2, NULL, TIMESTAMP(@ayer,     '14:00:00')),
(4, 'EN_CURSO',   'FINALIZADA', 'Ruta finalizada',        4, 2, TIMESTAMP(@ayer, '16:30:00'), TIMESTAMP(@ayer, '16:30:00')),
(4, 'FINALIZADA', 'OBSERVADA',  'Hora de atención en PTO-012 no coincide con la ubicación registrada', 3, 2, TIMESTAMP(@ayer, '16:30:00'), TIMESTAMP(@ayer, '17:30:00'));

-- ---------- 9. Registro de notificaciones ----------
INSERT INTO notificaciones_log
 (id_usuario, id_ruta, id_incidencia, tipo, mensaje, estado_envio, intentos, fcm_result, fecha) VALUES
(2, 2, NULL, 'RUTA_ASIGNADA',      'Se te asignó la ruta RUT-002',                          'ENVIADA', 1, 'demo', TIMESTAMP(@ayer, '18:01:00')),
(1, 1, 1,    'INCIDENCIA_CRITICA', 'Incidencia crítica en RUT-001: contenedor dañado',      'ENVIADA', 1, 'demo', TIMESTAMP(@ayer, '08:08:30')),
(1, 4, NULL, 'OBSERVACION',        'La ruta RUT-004 fue observada por el fiscalizador',     'ENVIADA', 1, 'demo', TIMESTAMP(@ayer, '17:30:30'));

-- ---------- 10. Verificación rápida (debe mostrar 4 rutas) ----------
SELECT r.codigo, r.fecha, r.turno, r.estado,
       COALESCE(u.nombre, '— sin asignar —') AS operario,
       SUM(rp.estado <> 'PENDIENTE') AS resueltos, COUNT(*) AS total
FROM rutas r
LEFT JOIN usuarios u    ON u.id = r.id_operario
JOIN ruta_puntos rp     ON rp.id_ruta = r.id
GROUP BY r.id, r.codigo, r.fecha, r.turno, r.estado, u.nombre ORDER BY r.id;
