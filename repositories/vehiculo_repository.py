class VehiculoRepository:
    def __init__(self, connection):
        self.connection = connection

    def buscar_por_id(self, vehiculo_id: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, placa, codigo_qr, tipo, capacidad, estado
                FROM vehiculos
                WHERE id = %s
                LIMIT 1
            """
            cursor.execute(sql, (vehiculo_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def bloquear_por_id(self, vehiculo_id: int):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM vehiculos WHERE id = %s FOR UPDATE", (vehiculo_id,))
            return cursor.fetchone() is not None

    def listar_por_estado(self, estado: str = "DISPONIBLE"):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, placa, tipo, capacidad, estado
                FROM vehiculos
                WHERE estado = %s
                ORDER BY placa ASC
            """
            cursor.execute(sql, (estado,))
            return cursor.fetchall()
        finally:
            cursor.close()

    def listar_todos(self):
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT id, placa, tipo, capacidad, estado
                FROM vehiculos
                ORDER BY placa ASC
                """
            )
            return cursor.fetchall()
        finally:
            cursor.close()

    def vehiculo_tiene_ruta(self, id_vehiculo: int, fecha: str, turno: str, excluir_id_ruta: int = None):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id FROM rutas
                WHERE id_vehiculo = %s AND fecha = %s AND turno = %s
            """
            params = [id_vehiculo, fecha, turno]
            if excluir_id_ruta:
                sql += " AND id != %s"
                params.append(excluir_id_ruta)
            cursor.execute(sql, params)
            return cursor.fetchone() is not None
        finally:
            cursor.close()

    def actualizar_estado(self, id_vehiculo: int, estado: str):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE vehiculos SET estado = %s WHERE id = %s"
            cursor.execute(sql, (estado, id_vehiculo))
        finally:
            cursor.close()
