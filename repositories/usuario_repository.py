class UsuarioRepository:
    def __init__(self, connection):
        self.connection = connection

    def buscar_por_correo(self, correo: str):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, nombre, correo, password_hash, rol, fcm_token, activo
                FROM usuarios
                WHERE correo = %s
                LIMIT 1
            """
            cursor.execute(sql, (correo.strip().lower(),))
            return cursor.fetchone()
        finally:
            cursor.close()

    def bloquear_por_id(self, usuario_id: int):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id FROM usuarios WHERE id = %s FOR UPDATE", (usuario_id,))
            return cursor.fetchone() is not None

    def buscar_por_id(self, usuario_id: int):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id, nombre, correo, rol, fcm_token, activo
                FROM usuarios
                WHERE id = %s
                LIMIT 1
            """
            cursor.execute(sql, (usuario_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    def actualizar_fcm_token(self, usuario_id: int, fcm_token: str):
        cursor = self.connection.cursor()
        try:
            # Si el token ya lo tenía otro usuario, se le quita
            sql_quitar = "UPDATE usuarios SET fcm_token = NULL WHERE fcm_token = %s AND id != %s"
            cursor.execute(sql_quitar, (fcm_token, usuario_id))

            sql_actualizar = "UPDATE usuarios SET fcm_token = %s WHERE id = %s"
            cursor.execute(sql_actualizar, (fcm_token, usuario_id))
        finally:
            cursor.close()

    def desasociar_fcm_token(self, usuario_id: int):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE usuarios SET fcm_token = NULL WHERE id = %s"
            cursor.execute(sql, (usuario_id,))
        finally:
            cursor.close()

    def listar_operarios_disponibles(
        self,
        fecha: str = None,
        turno: str = None,
        excluir_id_ruta: int = None,
        incluir_todos: bool = False,
    ):
        cursor = self.connection.cursor()
        try:
            if incluir_todos:
                sql = """
                    SELECT id, nombre, correo, 1 AS disponible
                    FROM usuarios
                    WHERE rol = 'OPERARIO'
                    ORDER BY nombre ASC
                """
                cursor.execute(sql)
                return [
                    {**r, "disponible": True}
                    for r in cursor.fetchall()
                ]
            if fecha and turno:
                sql = """
                    SELECT u.id, u.nombre, u.correo,
                           CASE WHEN EXISTS (
                               SELECT 1 FROM rutas r
                               WHERE r.id_operario = u.id
                                 AND r.fecha = %s
                                 AND r.turno = %s
                                 AND r.estado != 'OBSERVADA'
                """
                params = [fecha, turno]
                if excluir_id_ruta:
                    sql += " AND r.id != %s"
                    params.append(excluir_id_ruta)
                sql += """
                           ) THEN 0 ELSE 1 END AS disponible
                    FROM usuarios u
                    WHERE u.rol = 'OPERARIO' AND u.activo = 1
                    ORDER BY u.nombre ASC
                """
                cursor.execute(sql, params)
            else:
                sql = """
                    SELECT id, nombre, correo, 1 AS disponible
                    FROM usuarios
                    WHERE rol = 'OPERARIO' AND activo = 1
                    ORDER BY nombre ASC
                """
                cursor.execute(sql)
            rows = cursor.fetchall()
            for r in rows:
                r["disponible"] = bool(r["disponible"])
            return rows
        finally:
            cursor.close()

    def operario_tiene_ruta(self, id_operario: int, fecha: str, turno: str, excluir_id_ruta: int = None):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT id FROM rutas
                WHERE id_operario = %s AND fecha = %s AND turno = %s
            """
            params = [id_operario, fecha, turno]
            if excluir_id_ruta:
                sql += " AND id != %s"
                params.append(excluir_id_ruta)
            cursor.execute(sql, params)
            return cursor.fetchone() is not None
        finally:
            cursor.close()

    def obtener_supervisores_activos(self):
        cursor = self.connection.cursor()
        try:
            sql = "SELECT id, nombre, fcm_token FROM usuarios WHERE rol = 'SUPERVISOR' AND activo = 1"
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()
