class HistorialRepository:
    def __init__(self, connection):
        self.connection = connection

    def registrar(
        self,
        id_ruta: int,
        estado_anterior: str,
        estado_nuevo: str,
        comentario: str,
        id_usuario: int,
        hora_fin=None,
    ) -> int:
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO historial_ruta
                    (id_ruta, estado_anterior, estado_nuevo, comentario, id_usuario, id_vehiculo, hora_fin)
                SELECT r.id, %s, %s, %s, %s, r.id_vehiculo, COALESCE(%s, r.hora_fin)
                FROM rutas r
                WHERE r.id = %s
            """
            cursor.execute(
                sql,
                (estado_anterior, estado_nuevo, comentario, id_usuario, hora_fin, id_ruta),
            )
            return cursor.lastrowid
        finally:
            cursor.close()

    def listar_por_ruta(self, id_ruta: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    h.id,
                    h.estado_anterior,
                    h.estado_nuevo,
                    h.comentario,
                    h.fecha,
                    h.hora_fin,
                    u.id AS usuario_id,
                    u.nombre AS usuario_nombre,
                    v.id AS vehiculo_id,
                    v.placa AS vehiculo_placa
                FROM historial_ruta h
                INNER JOIN usuarios u ON u.id = h.id_usuario
                LEFT JOIN vehiculos v ON v.id = h.id_vehiculo
                WHERE h.id_ruta = %s
                ORDER BY h.fecha DESC, h.id DESC
            """
            cursor.execute(sql, (id_ruta,))
            filas = cursor.fetchall()
            resultado = []
            for f in filas:
                resultado.append({
                    "id": f["id"],
                    "estado_anterior": f["estado_anterior"],
                    "estado_nuevo": f["estado_nuevo"],
                    "comentario": f["comentario"],
                    "usuario": {"id": f["usuario_id"], "nombre": f["usuario_nombre"]},
                    "fecha": f["fecha"].isoformat() if f["fecha"] else None,
                    "hora_fin": f["hora_fin"].isoformat() if f["hora_fin"] else None,
                    "vehiculo": (
                        {"id": f["vehiculo_id"], "placa": f["vehiculo_placa"]}
                        if f["vehiculo_id"] else None
                    ),
                })
            return resultado
        finally:
            cursor.close()
