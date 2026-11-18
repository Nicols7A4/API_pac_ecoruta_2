-- Ejecutar una sola vez sobre una instalación existente de EcoRuta.
-- No elimina bases ni datos. Realice copia de seguridad antes de migrar.
USE pac_ecoruta;

ALTER TABLE ruta_puntos
    ADD COLUMN id_usuario_atencion INT NULL AFTER uuid_operacion,
    ADD COLUMN payload_hash CHAR(64) NULL AFTER id_usuario_atencion,
    ADD CONSTRAINT fk_rp_usuario FOREIGN KEY (id_usuario_atencion) REFERENCES usuarios(id);

ALTER TABLE incidencias
    ADD COLUMN fecha_captura DATETIME NULL AFTER fecha_registro,
    ADD COLUMN payload_hash CHAR(64) NULL AFTER uuid_operacion;

ALTER TABLE notificaciones_log
    ADD COLUMN id_incidencia INT NULL AFTER id_ruta,
    ADD COLUMN payload_json JSON NULL AFTER mensaje,
    ADD COLUMN estado_envio ENUM('PENDIENTE','REINTENTO','ENVIADA','FALLIDA') NOT NULL DEFAULT 'PENDIENTE' AFTER payload_json,
    ADD COLUMN intentos INT NOT NULL DEFAULT 0 AFTER estado_envio,
    ADD COLUMN ultimo_intento DATETIME NULL AFTER intentos,
    MODIFY COLUMN fcm_result VARCHAR(500) NULL,
    ADD CONSTRAINT fk_n_incidencia FOREIGN KEY (id_incidencia) REFERENCES incidencias(id) ON DELETE SET NULL,
    ADD INDEX idx_notificaciones_pendientes (estado_envio, intentos);

UPDATE notificaciones_log
SET estado_envio = CASE WHEN fcm_result IS NULL OR fcm_result = 'SIMULATED_SUCCESS'
                        THEN 'PENDIENTE' ELSE 'ENVIADA' END;

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
