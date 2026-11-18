class PuntoRepository:
    def __init__(self, connection):
        self.connection = connection

    def buscar_punto_por_qr(self, codigo_qr: str):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, codigo_qr, nombre, direccion, latitud, longitud, radio_validacion, activo
                FROM puntos_recoleccion
                WHERE codigo_qr = %s
                LIMIT 1
            """
            cursor.execute(sql, (codigo_qr.strip(),))
            return cursor.fetchone()
        finally:
            cursor.close()

    def buscar_ruta_punto_por_ruta_y_punto(self, id_ruta: int, id_punto: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, id_ruta, id_punto, orden, estado
                FROM ruta_puntos
                WHERE id_ruta = %s AND id_punto = %s
                LIMIT 1
            """
            cursor.execute(sql, (id_ruta, id_punto))
            return cursor.fetchone()
        finally:
            cursor.close()

    def listar_puntos_por_ruta(self, id_ruta: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    rp.id,
                    rp.orden,
                    rp.estado,
                    rp.fecha_atencion,
                    rp.lat_registro,
                    rp.lon_registro,
                    rp.observacion,
                    p.id AS punto_id,
                    p.codigo_qr,
                    p.nombre,
                    p.direccion,
                    p.latitud,
                    p.longitud,
                    p.radio_validacion
                FROM ruta_puntos rp
                INNER JOIN puntos_recoleccion p ON p.id = rp.id_punto
                WHERE rp.id_ruta = %s
                ORDER BY rp.orden ASC
            """
            cursor.execute(sql, (id_ruta,))
            rows = cursor.fetchall()
            puntos = []
            for r in rows:
                puntos.append({
                    "id": r["id"],
                    "orden": r["orden"],
                    "estado": r["estado"],
                    "fecha_atencion": r["fecha_atencion"].isoformat() if r["fecha_atencion"] else None,
                    "lat_registro": float(r["lat_registro"]) if r["lat_registro"] is not None else None,
                    "lon_registro": float(r["lon_registro"]) if r["lon_registro"] is not None else None,
                    "observacion": r["observacion"],
                    "punto": {
                        "id": r["punto_id"],
                        "codigo_qr": r["codigo_qr"],
                        "nombre": r["nombre"],
                        "direccion": r["direccion"],
                        "latitud": float(r["latitud"]),
                        "longitud": float(r["longitud"]),
                        "radio_validacion": r["radio_validacion"],
                    },
                })
            return puntos
        finally:
            cursor.close()

    def listar_puntos_activos_por_ruta(self, id_ruta: int):
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT rp.id_punto, rp.orden
                FROM ruta_puntos rp
                INNER JOIN puntos_recoleccion p ON p.id = rp.id_punto
                WHERE rp.id_ruta = %s AND p.activo = 1
                ORDER BY rp.orden ASC
                """,
                (id_ruta,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()

    def buscar_ruta_punto_por_id(self, id_ruta_punto: int, for_update: bool = False):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    rp.id,
                    rp.id_ruta,
                    rp.id_punto,
                    rp.orden,
                    rp.estado,
                    rp.fecha_atencion,
                    rp.lat_registro,
                    rp.lon_registro,
                    rp.observacion,
                    rp.uuid_operacion,
                    rp.id_usuario_atencion,
                    rp.payload_hash,
                    r.estado AS ruta_estado,
                    r.id_operario AS ruta_id_operario,
                    r.codigo AS ruta_codigo,
                    p.codigo_qr,
                    p.latitud AS punto_latitud,
                    p.longitud AS punto_longitud,
                    p.radio_validacion
                FROM ruta_puntos rp
                INNER JOIN rutas r ON r.id = rp.id_ruta
                INNER JOIN puntos_recoleccion p ON p.id = rp.id_punto
                WHERE rp.id = %s
                LIMIT 1
            """
            if for_update:
                sql += " FOR UPDATE"
            cursor.execute(sql, (id_ruta_punto,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def buscar_ruta_punto_por_uuid(self, uuid_operacion: str):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, id_ruta, estado, fecha_atencion, uuid_operacion,
                       id_usuario_atencion, payload_hash
                FROM ruta_puntos
                WHERE uuid_operacion = %s
                LIMIT 1
            """
            cursor.execute(sql, (uuid_operacion,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def atender_punto(
        self,
        id_ruta_punto: int,
        fecha_atencion,
        lat_registro: float,
        lon_registro: float,
        observacion: str,
        uuid_operacion: str,
        id_usuario_atencion: int,
        payload_hash: str,
    ):
        cursor = self.connection.cursor()
        try:
            sql = """
                UPDATE ruta_puntos
                SET estado = 'ATENDIDO',
                    fecha_atencion = %s,
                    lat_registro = %s,
                    lon_registro = %s,
                    observacion = %s,
                    uuid_operacion = %s,
                    id_usuario_atencion = %s,
                    payload_hash = %s
                WHERE id = %s AND estado = 'PENDIENTE' AND uuid_operacion IS NULL
            """
            cursor.execute(
                sql,
                (fecha_atencion, lat_registro, lon_registro, observacion, uuid_operacion,
                 id_usuario_atencion, payload_hash, id_ruta_punto),
            )
            return cursor.rowcount
        finally:
            cursor.close()

    def actualizar_estado_punto(self, id_ruta_punto: int, nuevo_estado: str):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE ruta_puntos SET estado = %s WHERE id = %s"
            cursor.execute(sql, (nuevo_estado, id_ruta_punto))
        finally:
            cursor.close()

    def listar_puntos_pendientes_por_ruta(self, id_ruta: int):
        cursor = self.connection.cursor()
        try:
            sql = "SELECT id FROM ruta_puntos WHERE id_ruta = %s AND estado = 'PENDIENTE' ORDER BY orden ASC"
            cursor.execute(sql, (id_ruta,))
            return [row["id"] for row in cursor.fetchall()]
        finally:
            cursor.close()

    def listar_todos(self, solo_activos: bool = True):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, codigo_qr, nombre, direccion, latitud, longitud, radio_validacion, activo
                FROM puntos_recoleccion
            """
            if solo_activos:
                sql += " WHERE activo = 1"
            sql += " ORDER BY id ASC"
            cursor.execute(sql)
            filas = cursor.fetchall()
            for f in filas:
                if "latitud" in f and f["latitud"] is not None:
                    f["latitud"] = float(f["latitud"])
                if "longitud" in f and f["longitud"] is not None:
                    f["longitud"] = float(f["longitud"])
            return filas
        finally:
            cursor.close()
