import json

from pymysql.err import ProgrammingError


class NotificacionRepository:
    def __init__(self, connection):
        self.connection = connection

    def registrar(self, id_usuario, id_ruta, tipo, mensaje, fcm_result=None,
                  incidencia_id=None, payload=None):
        payload = payload or {"tipo": tipo, "id_ruta": str(id_ruta)}
        if incidencia_id:
            payload["id_incidencia"] = str(incidencia_id)
        with self.connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO notificaciones_log
                    (id_usuario, id_ruta, id_incidencia, tipo, mensaje, payload_json,
                     estado_envio, fcm_result, intentos)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDIENTE', %s, 0)
            """, (id_usuario, id_ruta, incidencia_id, tipo, mensaje,
                  json.dumps(payload, ensure_ascii=False), fcm_result))
            return cursor.lastrowid

    def registrar_para_usuarios(self, usuarios, id_ruta, tipo, mensaje, fcm_result=None,
                                incidencia_id=None, payload=None):
        ids = []
        for usuario in usuarios:
            usuario_id = usuario["id"] if isinstance(usuario, dict) else usuario
            ids.append(self.registrar(usuario_id, id_ruta, tipo, mensaje, fcm_result,
                                      incidencia_id, dict(payload or {})))
        return ids

    def listar_pendientes(self, limite=20):
        with self.connection.cursor() as cursor:
            # TiDB falla al combinar JOIN y SKIP LOCKED en esta consulta.
            consulta = """
                SELECT n.id, n.id_usuario, n.id_ruta, n.id_incidencia, n.tipo,
                       n.mensaje, n.payload_json,
                       (SELECT u.fcm_token FROM usuarios u WHERE u.id = n.id_usuario) AS fcm_token
                FROM notificaciones_log n
                WHERE n.estado_envio IN ('PENDIENTE', 'REINTENTO')
                  AND n.intentos < 5
                  AND EXISTS (SELECT 1 FROM usuarios u
                              WHERE u.id = n.id_usuario AND u.fcm_token IS NOT NULL)
                ORDER BY n.id ASC LIMIT %s FOR UPDATE
            """
            try:
                # MySQL 8 y MariaDB 10.6+ permiten no esperar por filas que ya
                # esten siendo procesadas por otro despachador.
                cursor.execute(f"{consulta} SKIP LOCKED", (limite,))
            except ProgrammingError as exc:
                if not exc.args or exc.args[0] != 1064:
                    raise
                # MariaDB anterior a 10.6 no reconoce SKIP LOCKED. FOR UPDATE
                # conserva la exclusion mutua, aunque el segundo proceso espere.
                cursor.execute(consulta, (limite,))
            return cursor.fetchall()

    def actualizar_resultado(self, notificacion_id, estado, resultado):
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE notificaciones_log
                SET estado_envio=%s, fcm_result=%s, intentos=intentos+1, ultimo_intento=NOW()
                WHERE id=%s
            """, (estado, str(resultado)[:500], notificacion_id))
