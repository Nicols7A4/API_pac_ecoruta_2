-- EcoRuta: seed reproducible. Ejecutar solo sobre pac_ecoruta de desarrollo.
-- Requiere que schema_base.sql o la migración hayan creado el esquema actual.
USE pac_ecoruta_t3;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE validaciones_ruta;
TRUNCATE TABLE notificaciones_log;
TRUNCATE TABLE historial_ruta;
TRUNCATE TABLE evidencias;
TRUNCATE TABLE incidencias;
TRUNCATE TABLE ruta_puntos;
TRUNCATE TABLE rutas;
TRUNCATE TABLE puntos_recoleccion;
TRUNCATE TABLE vehiculos;
TRUNCATE TABLE usuarios;
SET FOREIGN_KEY_CHECKS = 1;

-- Contraseñas: Supervisor123 / Operario123 / Fiscal123
INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES
('Carlos Supervisor', 'supervisor@ecoruta.pe',
 'scrypt:32768:8:1$64L09cZgMgKTgixg$d1a9671c8582979cd5db9033a7102f1be9523944c65e6d4f12f622cc56111073799d7f5a9885d8a638ca03b7d0c87fe23871206e9195bc28254425ff84890968', 'SUPERVISOR'),
('Luis Operario', 'operario@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04', 'OPERARIO'),
('Rosa Fiscalizadora', 'fiscalizador@ecoruta.pe',
 'scrypt:32768:8:1$SQ8wgZNKB5hjKDJj$d615e915337f426d9477f870a4ee4a844092925e95d22cad91103fca2600627acdb2d8f45bdf56916a9ea069dd4e1e4c8f17ca66072b9f5b1998129162ac63d1', 'FISCALIZADOR');

INSERT INTO vehiculos (placa, codigo_qr, tipo, capacidad, estado) VALUES
('ABC-123', 'VEH-001', 'Camión compactador', 8.00, 'EN_USO'),
('XYZ-789', 'VEH-002', 'Camión baranda', 5.00, 'DISPONIBLE');

INSERT INTO puntos_recoleccion
    (codigo_qr, nombre, direccion, latitud, longitud, radio_validacion) VALUES
('PTO-001', 'Parque Principal',       'Plaza de Armas, Chiclayo',     -6.7714300, -79.8387700, 50),
('PTO-002', 'Catedral de Chiclayo',   'San José y Elías Aguirre',     -6.7716830, -79.8376410, 50),
('PTO-003', 'Mercado Modelo',         'Av. Balta / Arica, Chiclayo',  -6.7658846, -79.8391493, 50),
('PTO-004', 'Paseo de las Musas',     'La Florida, Chiclayo',         -6.7792000, -79.8388900, 50),
('PTO-005', 'Hospital Las Mercedes',  'Av. Luis Gonzales 635',        -6.7725417, -79.8428267, 50),
('PTO-006', 'Plazuela Elías Aguirre', 'San José y Elías Aguirre',     -6.7710800, -79.8430000, 50),
('PTO-007', 'Óvalo Quiñones',         'Av. Salaverry 40, Chiclayo',   -6.7700663, -79.8553199, 50),
('PTO-008', 'Terminal Emtrafesa',     'Av. Balta 110, Chiclayo',      -6.7766111, -79.8388333, 50);

INSERT INTO rutas
    (codigo, fecha, turno, id_operario, id_vehiculo, estado, hora_inicio, hora_fin) VALUES
('RUT-001', CURDATE() - INTERVAL 1 DAY, 'MANANA', 2, 1, 'FINALIZADA',
 CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:00:00'), CONCAT(CURDATE() - INTERVAL 1 DAY, ' 09:30:00')),
('RUT-002', CURDATE(), 'MANANA', 2, 1, 'EN_CURSO', CONCAT(CURDATE(), ' 07:00:00'), NULL),
('RUT-003', CURDATE() + INTERVAL 1 DAY, 'TARDE', NULL, NULL, 'PROGRAMADA', NULL, NULL);

INSERT INTO ruta_puntos
    (id_ruta, id_punto, orden, estado, fecha_atencion, lat_registro, lon_registro,
     observacion, uuid_operacion, id_usuario_atencion) VALUES
(1, 1, 1, 'ATENDIDO', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:15:00'), -6.7714400, -79.8387800, NULL, UUID(), 2),
(1, 2, 2, 'ATENDIDO', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:40:00'), -6.7716900, -79.8376500, NULL, UUID(), 2),
(1, 3, 3, 'CON_INCIDENCIA', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:10:00'), -6.7658900, -79.8391600, 'Contenedor dañado', UUID(), 2),
(1, 4, 4, 'ATENDIDO', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:50:00'), -6.7792100, -79.8389000, NULL, UUID(), 2),
(2, 5, 1, 'ATENDIDO', CONCAT(CURDATE(), ' 07:20:00'), -6.7725500, -79.8428300, NULL, UUID(), 2),
(2, 6, 2, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL),
(2, 7, 3, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL),
(2, 8, 4, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL),
(3, 1, 1, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL),
(3, 2, 2, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL),
(3, 3, 3, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL),
(3, 4, 4, 'PENDIENTE', NULL, NULL, NULL, NULL, NULL, NULL);

INSERT INTO incidencias
    (id_ruta_punto, tipo, descripcion, es_critica, estado, id_usuario,
     fecha_registro, fecha_captura, uuid_operacion, payload_hash) VALUES
(3, 'CONTENEDOR_DANADO', 'Contenedor roto; no se puede levantar con el compactador.', 1,
 'EN_REVISION', 2, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:08:00'),
 CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:07:30'), UUID(), NULL),
(5, 'ACCESO_BLOQUEADO', 'Vehículo mal estacionado bloqueando el acceso.', 0,
 'ABIERTA', 2, CONCAT(CURDATE(), ' 07:18:00'), CONCAT(CURDATE(), ' 07:17:30'), UUID(), NULL);

INSERT INTO evidencias (id_incidencia, id_ruta_punto, ruta_archivo, tipo, fecha) VALUES
(1, 3, '/uploads/incidencias/inc_4_bf6103.jpg', 'INCIDENCIA',
 CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:09:00'));

INSERT INTO historial_ruta
    (id_ruta, estado_anterior, estado_nuevo, comentario, id_usuario, id_vehiculo, hora_fin, fecha) VALUES
(1, NULL, 'PROGRAMADA', 'Ruta creada y asignada', 1, 1, NULL, CONCAT(CURDATE() - INTERVAL 2 DAY, ' 18:00:00')),
(1, 'PROGRAMADA', 'EN_CURSO', 'Inicio de ruta', 2, 1, NULL, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 07:00:00')),
(1, 'EN_CURSO', 'FINALIZADA', 'Ruta finalizada', 2, 1, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 09:30:00'), CONCAT(CURDATE() - INTERVAL 1 DAY, ' 09:30:00')),
(2, NULL, 'PROGRAMADA', 'Ruta creada y asignada', 1, 1, NULL, CONCAT(CURDATE() - INTERVAL 1 DAY, ' 18:00:00')),
(2, 'PROGRAMADA', 'EN_CURSO', 'Inicio de ruta', 2, 1, NULL, CONCAT(CURDATE(), ' 07:00:00')),
(3, NULL, 'PROGRAMADA', 'Ruta creada', 1, NULL, NULL, CONCAT(CURDATE(), ' 08:00:00'));

INSERT INTO notificaciones_log
    (id_usuario, id_ruta, tipo, mensaje, fcm_result, estado_envio, fecha) VALUES
(2, 2, 'RUTA_ASIGNADA', 'Se te asignó la ruta RUT-002', 'demo', 'ENVIADA',
 CONCAT(CURDATE() - INTERVAL 1 DAY, ' 18:01:00')),
(1, 1, 'INCIDENCIA_CRITICA', 'Incidencia crítica en RUT-001: contenedor dañado',
 'demo', 'ENVIADA', CONCAT(CURDATE() - INTERVAL 1 DAY, ' 08:08:30'));
