class IncidenciaRepository:
    def __init__(self, connection):
        self.connection = connection

    def buscar_por_uuid(self, uuid_operacion: str):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, id_ruta_punto, tipo, descripcion, es_critica, estado, observacion_control,
                       id_usuario, fecha_registro, fecha_captura, uuid_operacion, payload_hash
                FROM incidencias
                WHERE uuid_operacion = %s
                LIMIT 1
            """
            cursor.execute(sql, (uuid_operacion,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def crear_incidencia(
        self,
        id_ruta_punto: int,
        tipo: str,
        descripcion: str,
        es_critica: bool,
        estado: str,
        id_usuario: int,
        uuid_operacion: str,
        fecha_captura,
        payload_hash: str,
    ) -> int:
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO incidencias (
                    id_ruta_punto, tipo, descripcion, es_critica, estado, id_usuario,
                    uuid_operacion, fecha_captura, payload_hash
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                sql,
                (id_ruta_punto, tipo, descripcion, 1 if es_critica else 0, estado, id_usuario,
                 uuid_operacion, fecha_captura, payload_hash),
            )
            return cursor.lastrowid
        finally:
            cursor.close()

    def crear_evidencia(self, id_incidencia: int, id_ruta_punto: int, ruta_archivo: str, tipo: str = "INCIDENCIA") -> int:
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO evidencias (id_incidencia, id_ruta_punto, ruta_archivo, tipo)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (id_incidencia, id_ruta_punto, ruta_archivo, tipo))
            return cursor.lastrowid
        finally:
            cursor.close()

    def buscar_por_id(self, incidencia_id: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    i.id,
                    i.id_ruta_punto,
                    i.tipo,
                    i.descripcion,
                    i.es_critica,
                    i.estado,
                    i.observacion_control,
                    i.id_usuario,
                    i.fecha_registro,
                    i.fecha_captura,
                    i.uuid_operacion,
                    p.id AS punto_id,
                    p.nombre AS punto_nombre,
                    u.nombre AS usuario_nombre,
                    rp.id_ruta
                FROM incidencias i
                INNER JOIN ruta_puntos rp ON rp.id = i.id_ruta_punto
                INNER JOIN puntos_recoleccion p ON p.id = rp.id_punto
                INNER JOIN usuarios u ON u.id = i.id_usuario
                WHERE i.id = %s
                LIMIT 1
            """
            cursor.execute(sql, (incidencia_id,))
            f = cursor.fetchone()
            if not f:
                return None

            evidencias = self.obtener_evidencias_por_incidencia(incidencia_id)

            return {
                "id": f["id"],
                "id_ruta_punto": f["id_ruta_punto"],
                "id_ruta": f["id_ruta"],
                "punto": {"id": f["punto_id"], "nombre": f["punto_nombre"]},
                "tipo": f["tipo"],
                "descripcion": f["descripcion"],
                "es_critica": bool(f["es_critica"]),
                "estado": f["estado"],
                "observacion_control": f["observacion_control"],
                "usuario": {"id": f["id_usuario"], "nombre": f["usuario_nombre"]},
                "fecha_registro": f["fecha_registro"].isoformat() if f["fecha_registro"] else None,
                "fecha_captura": f["fecha_captura"].isoformat() if f["fecha_captura"] else None,
                "evidencias": evidencias,
            }
        finally:
            cursor.close()

    def obtener_evidencias_por_incidencia(self, incidencia_id: int):
        cursor = self.connection.cursor()
        try:
            sql = "SELECT id, ruta_archivo AS url FROM evidencias WHERE id_incidencia = %s"
            cursor.execute(sql, (incidencia_id,))
            return cursor.fetchall()
        finally:
            cursor.close()

    def listar_por_ruta_punto(self, id_ruta_punto: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    i.id,
                    i.id_ruta_punto,
                    i.tipo,
                    i.descripcion,
                    i.es_critica,
                    i.estado,
                    i.observacion_control,
                    i.id_usuario,
                    i.fecha_registro,
                    i.fecha_captura,
                    p.id AS punto_id,
                    p.nombre AS punto_nombre,
                    u.nombre AS usuario_nombre
                FROM incidencias i
                INNER JOIN ruta_puntos rp ON rp.id = i.id_ruta_punto
                INNER JOIN puntos_recoleccion p ON p.id = rp.id_punto
                INNER JOIN usuarios u ON u.id = i.id_usuario
                WHERE i.id_ruta_punto = %s
                ORDER BY i.fecha_registro DESC
            """
            cursor.execute(sql, (id_ruta_punto,))
            filas = cursor.fetchall()

            resultado = []
            for f in filas:
                evs = self.obtener_evidencias_por_incidencia(f["id"])
                resultado.append({
                    "id": f["id"],
                    "id_ruta_punto": f["id_ruta_punto"],
                    "punto": {"id": f["punto_id"], "nombre": f["punto_nombre"]},
                    "tipo": f["tipo"],
                    "descripcion": f["descripcion"],
                    "es_critica": bool(f["es_critica"]),
                    "estado": f["estado"],
                    "observacion_control": f["observacion_control"],
                    "usuario": {"id": f["id_usuario"], "nombre": f["usuario_nombre"]},
                    "fecha_registro": f["fecha_registro"].isoformat() if f["fecha_registro"] else None,
                    "fecha_captura": f["fecha_captura"].isoformat() if f["fecha_captura"] else None,
                    "evidencias": evs,
                })

            return resultado
        finally:
            cursor.close()

    def listar_por_ruta(self, id_ruta: int, estado: str = None, id_ruta_punto: int = None):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    i.id,
                    i.id_ruta_punto,
                    i.tipo,
                    i.descripcion,
                    i.es_critica,
                    i.estado,
                    i.observacion_control,
                    i.id_usuario,
                    i.fecha_registro,
                    i.fecha_captura,
                    p.id AS punto_id,
                    p.nombre AS punto_nombre,
                    u.nombre AS usuario_nombre
                FROM incidencias i
                INNER JOIN ruta_puntos rp ON rp.id = i.id_ruta_punto
                INNER JOIN puntos_recoleccion p ON p.id = rp.id_punto
                INNER JOIN usuarios u ON u.id = i.id_usuario
                WHERE rp.id_ruta = %s
            """
            params = [id_ruta]

            if estado:
                sql += " AND i.estado = %s"
                params.append(estado)
            if id_ruta_punto:
                sql += " AND i.id_ruta_punto = %s"
                params.append(id_ruta_punto)

            sql += " ORDER BY i.fecha_registro DESC"
            cursor.execute(sql, params)
            filas = cursor.fetchall()

            resultado = []
            for f in filas:
                evs = self.obtener_evidencias_por_incidencia(f["id"])
                resultado.append({
                    "id": f["id"],
                    "id_ruta_punto": f["id_ruta_punto"],
                    "punto": {"id": f["punto_id"], "nombre": f["punto_nombre"]},
                    "tipo": f["tipo"],
                    "descripcion": f["descripcion"],
                    "es_critica": bool(f["es_critica"]),
                    "estado": f["estado"],
                    "observacion_control": f["observacion_control"],
                    "usuario": {"id": f["id_usuario"], "nombre": f["usuario_nombre"]},
                    "fecha_registro": f["fecha_registro"].isoformat() if f["fecha_registro"] else None,
                    "fecha_captura": f["fecha_captura"].isoformat() if f["fecha_captura"] else None,
                    "evidencias": evs,
                })

            return resultado
        finally:
            cursor.close()

    def actualizar_estado(self, incidencia_id: int, nuevo_estado: str, observacion_control: str = None):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE incidencias SET estado = %s, observacion_control = %s WHERE id = %s"
            cursor.execute(sql, (nuevo_estado, observacion_control, incidencia_id))
        finally:
            cursor.close()
