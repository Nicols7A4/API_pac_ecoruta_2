-- =====================================================
-- EcoRuta - Datos de prueba ampliados
-- =====================================================
-- Ejecutar después de sql/schema_base.sql.
-- No elimina la base de datos ni reemplaza los datos existentes.
-- Contraseña de todos los usuarios de prueba: Operario123

-- La base se toma del argumento de mysql. Ejemplo:
--   mysql -u root -p'mariaroot' pac_ecoruta_t2 < sql/inserts_mejorados.sql

START TRANSACTION;

-- ---------- USUARIOS ----------
-- Se conserva el usuario supervisor/fiscalizador del script base y se agregan
-- cinco operarios para probar asignaciones, filtros y disponibilidad.
INSERT IGNORE INTO usuarios (nombre, correo, password_hash, rol) VALUES
('Ana Operaria', 'ana.operaria@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04',
 'OPERARIO'),
('Miguel Operario', 'miguel.operario@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04',
 'OPERARIO'),
('Sofia Operaria', 'sofia.operaria@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04',
 'OPERARIO'),
('Jorge Operario', 'jorge.operario@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04',
 'OPERARIO'),
('Valeria Operaria', 'valeria.operaria@ecoruta.pe',
 'scrypt:32768:8:1$QZFJhwVjlFUADK8H$2c4fa57830bb6e6030d30efefaa0b05276beec7140cf118077313c734272b94d33d555616153fba7c8769c1bbd5c2dbedb43467c5ee136bdaa69ac402a92cb04',
 'OPERARIO');

-- ---------- VEHÍCULOS ----------
INSERT IGNORE INTO vehiculos (placa, codigo_qr, tipo, capacidad, estado) VALUES
('ECO-101', 'VEH-101', 'Camión compactador', 8.00, 'DISPONIBLE'),
('ECO-202', 'VEH-202', 'Camión compactador', 10.00, 'DISPONIBLE'),
('ECO-303', 'VEH-303', 'Camión baranda', 5.00, 'DISPONIBLE'),
('ECO-404', 'VEH-404', 'Camión baranda', 6.50, 'MANTENIMIENTO'),
('ECO-505', 'VEH-505', 'Camión compactador', 8.00, 'DISPONIBLE');

-- ---------- PUNTOS DE RECOLECCIÓN ----------
INSERT IGNORE INTO puntos_recoleccion
    (codigo_qr, nombre, direccion, latitud, longitud, radio_validacion)
VALUES
('PTO-009', 'Urbanización Santa Victoria', 'Av. Santa Victoria, Chiclayo', -6.7781000, -79.8421000, 50),
('PTO-010', 'P.J. José Olaya', 'Av. José Olaya, Chiclayo', -6.7805000, -79.8369000, 50),
('PTO-011', 'Parque Infantil', 'Av. Grau, Chiclayo', -6.7758000, -79.8463000, 50),
('PTO-012', 'Complejo Jaime Zea', 'Av. Salaverry, Chiclayo', -6.7629000, -79.8491000, 50),
('PTO-013', 'Los Parques', 'Av. Chiclayo, Chiclayo', -6.7584000, -79.8417000, 50),
('PTO-014', 'Mercado Moshoqueque', 'Av. México, Chiclayo', -6.7617000, -79.8512000, 50),
('PTO-015', 'La Victoria', 'Av. Víctor Raúl, Chiclayo', -6.7932000, -79.8358000, 50),
('PTO-016', 'Santa Rosa', 'Av. Santa Rosa, Chiclayo', -6.7861000, -79.8276000, 50);

-- ---------- RUTAS ----------
-- Los identificadores se resuelven por código, por lo que el script no
-- depende de que los AUTO_INCREMENT comiencen en un valor específico.
INSERT IGNORE INTO rutas
    (codigo, fecha, turno, id_operario, id_vehiculo, estado, hora_inicio, hora_fin)
VALUES
('RUT-101', CURDATE() + INTERVAL 1 DAY, 'MANANA',
 (SELECT id FROM usuarios WHERE correo = 'ana.operaria@ecoruta.pe'),
 (SELECT id FROM vehiculos WHERE codigo_qr = 'VEH-101'), 'PROGRAMADA', NULL, NULL),
('RUT-102', CURDATE() + INTERVAL 1 DAY, 'TARDE',
 (SELECT id FROM usuarios WHERE correo = 'miguel.operario@ecoruta.pe'),
 (SELECT id FROM vehiculos WHERE codigo_qr = 'VEH-202'), 'PROGRAMADA', NULL, NULL),
('RUT-103', CURDATE() + INTERVAL 2 DAY, 'MANANA',
 (SELECT id FROM usuarios WHERE correo = 'sofia.operaria@ecoruta.pe'),
 (SELECT id FROM vehiculos WHERE codigo_qr = 'VEH-303'), 'PROGRAMADA', NULL, NULL),
('RUT-104', CURDATE() + INTERVAL 2 DAY, 'TARDE',
 (SELECT id FROM usuarios WHERE correo = 'jorge.operario@ecoruta.pe'),
 (SELECT id FROM vehiculos WHERE codigo_qr = 'VEH-505'), 'PROGRAMADA', NULL, NULL),
('RUT-105', CURDATE() - INTERVAL 2 DAY, 'NOCHE',
 (SELECT id FROM usuarios WHERE correo = 'valeria.operaria@ecoruta.pe'),
 (SELECT id FROM vehiculos WHERE codigo_qr = 'VEH-101'), 'FINALIZADA',
 CONCAT(CURDATE() - INTERVAL 2 DAY, ' 19:00:00'),
 CONCAT(CURDATE() - INTERVAL 2 DAY, ' 22:15:00')),
('RUT-106', CURDATE() - INTERVAL 3 DAY, 'TARDE',
 (SELECT id FROM usuarios WHERE correo = 'ana.operaria@ecoruta.pe'),
 (SELECT id FROM vehiculos WHERE codigo_qr = 'VEH-202'), 'OBSERVADA',
 CONCAT(CURDATE() - INTERVAL 3 DAY, ' 14:00:00'),
 CONCAT(CURDATE() - INTERVAL 3 DAY, ' 17:20:00'));

-- ---------- PUNTOS ASOCIADOS A LAS RUTAS ----------
INSERT IGNORE INTO ruta_puntos (id_ruta, id_punto, orden, estado)
SELECT r.id, pr.id, p.orden, p.estado
FROM (
    SELECT 'RUT-101' AS codigo_ruta, 'PTO-009' AS codigo_punto, 1 AS orden, 'PENDIENTE' AS estado
    UNION ALL SELECT 'RUT-101', 'PTO-010', 2, 'PENDIENTE'
    UNION ALL SELECT 'RUT-101', 'PTO-011', 3, 'PENDIENTE'
    UNION ALL SELECT 'RUT-102', 'PTO-012', 1, 'PENDIENTE'
    UNION ALL SELECT 'RUT-102', 'PTO-013', 2, 'PENDIENTE'
    UNION ALL SELECT 'RUT-102', 'PTO-014', 3, 'PENDIENTE'
    UNION ALL SELECT 'RUT-103', 'PTO-015', 1, 'PENDIENTE'
    UNION ALL SELECT 'RUT-103', 'PTO-016', 2, 'PENDIENTE'
    UNION ALL SELECT 'RUT-104', 'PTO-009', 1, 'PENDIENTE'
    UNION ALL SELECT 'RUT-104', 'PTO-012', 2, 'PENDIENTE'
    UNION ALL SELECT 'RUT-105', 'PTO-013', 1, 'ATENDIDO'
    UNION ALL SELECT 'RUT-105', 'PTO-014', 2, 'CON_INCIDENCIA'
    UNION ALL SELECT 'RUT-105', 'PTO-015', 3, 'ATENDIDO'
    UNION ALL SELECT 'RUT-106', 'PTO-016', 1, 'CON_INCIDENCIA'
) p
INNER JOIN rutas r ON r.codigo = p.codigo_ruta
INNER JOIN puntos_recoleccion pr ON pr.codigo_qr = p.codigo_punto
;

COMMIT;

-- Comprobación rápida de los datos cargados.
SELECT rol, COUNT(*) AS cantidad
FROM usuarios
GROUP BY rol
ORDER BY rol;

SELECT estado, COUNT(*) AS cantidad
FROM rutas
GROUP BY estado
ORDER BY estado;
