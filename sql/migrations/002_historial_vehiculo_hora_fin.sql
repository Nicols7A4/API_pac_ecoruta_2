ALTER TABLE historial_ruta
  ADD COLUMN id_vehiculo INT NULL AFTER id_usuario,
  ADD COLUMN hora_fin DATETIME NULL AFTER id_vehiculo,
  ADD CONSTRAINT fk_h_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculos(id) ON DELETE SET NULL;
