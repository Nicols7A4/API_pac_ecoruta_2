from datetime import datetime


class RutaRepository:
    def __init__(self, connection):
        self.connection = connection

    def listar_rutas(
        self,
        id_operario: int = None,
        fecha: str = None,
        fecha_desde: str = None,
        fecha_hasta: str = None,
        estado: str = None,
        id_vehiculo: int = None,
    ):
        cursor = self.connection.cursor()
        try:
            sql = """
                SELECT
                    r.id,
                    r.codigo,
                    DATE_FORMAT(r.fecha, '%%Y-%%m-%%d') AS fecha,
                    r.turno,
                    r.estado,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM validaciones_ruta vr
                        WHERE vr.id_ruta = r.id AND vr.vigente = 1
                    ) THEN 1 ELSE 0 END AS validada,
                    u.id AS operario_id,
                    u.nombre AS operario_nombre,
                    v.id AS vehiculo_id,
                    v.placa AS vehiculo_placa,
                    COUNT(rp.id) AS puntos_total,
                    SUM(CASE WHEN rp.estado = 'ATENDIDO' THEN 1 ELSE 0 END) AS puntos_atendidos,
                    SUM(CASE WHEN rp.estado = 'CON_INCIDENCIA' THEN 1 ELSE 0 END) AS puntos_con_incidencia
                FROM rutas r
                LEFT JOIN usuarios u ON u.id = r.id_operario
                LEFT JOIN vehiculos v ON v.id = r.id_vehiculo
                LEFT JOIN ruta_puntos rp ON rp.id_ruta = r.id
                WHERE 1 = 1
            """
            params = []

            if id_operario is not None:
                sql += " AND r.id_operario = %s"
                params.append(id_operario)
            if id_vehiculo is not None:
                sql += " AND r.id_vehiculo = %s"
                params.append(id_vehiculo)

            if fecha:
                sql += " AND r.fecha = %s"
                params.append(fecha)
            elif fecha_desde and fecha_hasta:
                sql += " AND r.fecha BETWEEN %s AND %s"
                params.extend([fecha_desde, fecha_hasta])
            elif fecha_desde:
                sql += " AND r.fecha >= %s"
                params.append(fecha_desde)
            elif fecha_hasta:
                sql += " AND r.fecha <= %s"
                params.append(fecha_hasta)

            if estado:
                sql += " AND r.estado = %s"
                params.append(estado)

            sql += " GROUP BY r.id, r.codigo, r.fecha, r.turno, r.estado, u.id, u.nombre, v.id, v.placa ORDER BY r.fecha DESC, r.codigo ASC"

            cursor.execute(sql, params)
            filas = cursor.fetchall()

            rutas = []
            for f in filas:
                total = f["puntos_total"] or 0
                atendidos = int(f["puntos_atendidos"] or 0)
                incidencias = int(f["puntos_con_incidencia"] or 0)
                avance = round(((atendidos + incidencias) / total * 100), 1) if total > 0 else 0.0

                rutas.append({
                    "id": f["id"],
                    "codigo": f["codigo"],
                    "fecha": f["fecha"],
                    "turno": f["turno"],
                    "estado": f["estado"],
                    "validada": bool(f["validada"]),
                    "operario": {"id": f["operario_id"], "nombre": f["operario_nombre"]} if f["operario_id"] else None,
                    "vehiculo": {"id": f["vehiculo_id"], "placa": f["vehiculo_placa"]} if f["vehiculo_id"] else None,
                    "puntos_total": total,
                    "puntos_atendidos": atendidos,
                    "puntos_con_incidencia": incidencias,
                    "avance_porcentaje": avance,
                })

            return rutas
        finally:
            cursor.close()

    def buscar_por_id(self, ruta_id: int, for_update: bool = False):
        cursor = self.connection.cursor()
        try:
            if for_update:
                cursor.execute("SELECT id FROM rutas WHERE id = %s FOR UPDATE", (ruta_id,))
                if cursor.fetchone() is None:
                    return None
            sql = """
                SELECT
                    r.id,
                    r.codigo,
                    DATE_FORMAT(r.fecha, '%%Y-%%m-%%d') AS fecha,
                    r.turno,
                    r.estado,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM validaciones_ruta vr
                        WHERE vr.id_ruta = r.id AND vr.vigente = 1
                    ) THEN 1 ELSE 0 END AS validada,
                    r.id_operario,
                    r.id_vehiculo,
                    r.hora_inicio,
                    r.hora_fin,
                    u.nombre AS operario_nombre,
                    v.placa AS vehiculo_placa,
                    COUNT(rp.id) AS puntos_total,
                    SUM(CASE WHEN rp.estado = 'ATENDIDO' THEN 1 ELSE 0 END) AS puntos_atendidos,
                    SUM(CASE WHEN rp.estado = 'CON_INCIDENCIA' THEN 1 ELSE 0 END) AS puntos_con_incidencia
                FROM rutas r
                LEFT JOIN usuarios u ON u.id = r.id_operario
                LEFT JOIN vehiculos v ON v.id = r.id_vehiculo
                LEFT JOIN ruta_puntos rp ON rp.id_ruta = r.id
                WHERE r.id = %s
                GROUP BY r.id, r.codigo, r.fecha, r.turno, r.estado, r.id_operario, r.id_vehiculo, r.hora_inicio, r.hora_fin, u.nombre, v.placa
                LIMIT 1
            """
            cursor.execute(sql, (ruta_id,))
            f = cursor.fetchone()
            if not f:
                return None

            total = f["puntos_total"] or 0
            atendidos = int(f["puntos_atendidos"] or 0)
            incidencias = int(f["puntos_con_incidencia"] or 0)
            avance = round(((atendidos + incidencias) / total * 100), 1) if total > 0 else 0.0

            return {
                "id": f["id"],
                "codigo": f["codigo"],
                "fecha": f["fecha"],
                "turno": f["turno"],
                "estado": f["estado"],
                "validada": bool(f["validada"]),
                "id_operario": f["id_operario"],
                "id_vehiculo": f["id_vehiculo"],
                "operario": {"id": f["id_operario"], "nombre": f["operario_nombre"]} if f["id_operario"] else None,
                "vehiculo": {"id": f["id_vehiculo"], "placa": f["vehiculo_placa"]} if f["id_vehiculo"] else None,
                "puntos_total": total,
                "puntos_atendidos": atendidos,
                "puntos_con_incidencia": incidencias,
                "avance_porcentaje": avance,
                "hora_inicio": f["hora_inicio"].isoformat() if f["hora_inicio"] else None,
                "hora_fin": f["hora_fin"].isoformat() if f["hora_fin"] else None,
            }
        finally:
            cursor.close()

    def operario_tiene_ruta_en_curso(self, id_operario: int, excluir_id_ruta: int = None):
        cursor = self.connection.cursor()
        try:
            sql = "SELECT id FROM rutas WHERE id_operario = %s AND estado = 'EN_CURSO'"
            params = [id_operario]
            if excluir_id_ruta:
                sql += " AND id != %s"
                params.append(excluir_id_ruta)
            cursor.execute(sql, params)
            return cursor.fetchone() is not None
        finally:
            cursor.close()

    def asignar_operario_y_vehiculo(self, id_ruta: int, id_operario: int, id_vehiculo: int):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE rutas SET id_operario = %s, id_vehiculo = %s WHERE id = %s"
            cursor.execute(sql, (id_operario, id_vehiculo, id_ruta))
        finally:
            cursor.close()

    def iniciar_ruta(self, id_ruta: int, hora_inicio: datetime):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE rutas SET estado = 'EN_CURSO', hora_inicio = %s WHERE id = %s"
            cursor.execute(sql, (hora_inicio, id_ruta))
        finally:
            cursor.close()

    def finalizar_ruta(self, id_ruta: int, hora_fin: datetime):
        cursor = self.connection.cursor()
        try:
            sql = "UPDATE rutas SET estado = 'FINALIZADA', hora_fin = %s WHERE id = %s"
            cursor.execute(sql, (hora_fin, id_ruta))
        finally:
            cursor.close()

    def cambiar_estado(self, id_ruta: int, nuevo_estado: str, limpiar_hora_fin: bool = False):
        cursor = self.connection.cursor()
        try:
            if limpiar_hora_fin:
                sql = "UPDATE rutas SET estado = %s, hora_fin = NULL WHERE id = %s"
            else:
                sql = "UPDATE rutas SET estado = %s WHERE id = %s"
            cursor.execute(sql, (nuevo_estado, id_ruta))
        finally:
            cursor.close()

    def obtener_resumen_supervision(self, fecha_inicio: str, fecha_fin: str = None):
        fecha_fin = fecha_fin or fecha_inicio
        cursor = self.connection.cursor()
        try:
            # 1. Contadores de rutas
            sql_rutas = """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN estado = 'PROGRAMADA' THEN 1 ELSE 0 END) AS programadas,
                    SUM(CASE WHEN estado = 'EN_CURSO' THEN 1 ELSE 0 END) AS en_curso,
                    SUM(CASE WHEN estado = 'FINALIZADA' THEN 1 ELSE 0 END) AS finalizadas,
                    SUM(CASE WHEN estado = 'OBSERVADA' THEN 1 ELSE 0 END) AS observadas
                FROM rutas
                WHERE fecha BETWEEN %s AND %s
            """
            cursor.execute(sql_rutas, (fecha_inicio, fecha_fin))
            r_rutas = cursor.fetchone() or {}

            # 2. Contadores de puntos de las rutas de esa fecha
            sql_puntos = """
                SELECT
                    COUNT(rp.id) AS total,
                    SUM(CASE WHEN rp.estado = 'ATENDIDO' THEN 1 ELSE 0 END) AS atendidos,
                    SUM(CASE WHEN rp.estado = 'CON_INCIDENCIA' THEN 1 ELSE 0 END) AS con_incidencia,
                    SUM(CASE WHEN rp.estado = 'PENDIENTE' THEN 1 ELSE 0 END) AS pendientes
                FROM ruta_puntos rp
                INNER JOIN rutas r ON r.id = rp.id_ruta
                WHERE r.fecha BETWEEN %s AND %s
            """
            cursor.execute(sql_puntos, (fecha_inicio, fecha_fin))
            r_puntos = cursor.fetchone() or {}

            # 3. Contadores de incidencias
            sql_inc = """
                SELECT
                    COUNT(i.id) AS total,
                    SUM(CASE WHEN i.estado = 'ABIERTA' THEN 1 ELSE 0 END) AS abiertas,
                    SUM(CASE WHEN i.estado = 'EN_REVISION' THEN 1 ELSE 0 END) AS en_revision,
                    SUM(CASE WHEN i.estado = 'RESUELTA' THEN 1 ELSE 0 END) AS resueltas,
                    SUM(CASE WHEN i.es_critica = 1 THEN 1 ELSE 0 END) AS criticas
                FROM incidencias i
                INNER JOIN ruta_puntos rp ON rp.id = i.id_ruta_punto
                INNER JOIN rutas r ON r.id = rp.id_ruta
                WHERE r.fecha BETWEEN %s AND %s
            """
            cursor.execute(sql_inc, (fecha_inicio, fecha_fin))
            r_inc = cursor.fetchone() or {}

            # 4. Indicadores específicos para el rol Fiscalizador.
            # Una ruta FINALIZADA queda pendiente mientras no tenga una
            # validación vigente. OBSERVADA ya representa una revisión no conforme.
            sql_fiscalizacion = """
                SELECT
                    SUM(CASE WHEN r.estado = 'FINALIZADA' AND vr.id_ruta IS NULL THEN 1 ELSE 0 END)
                        AS pendientes_revision,
                    SUM(CASE WHEN r.estado = 'FINALIZADA' AND vr.id_ruta IS NOT NULL THEN 1 ELSE 0 END)
                        AS conformes,
                    SUM(CASE WHEN r.estado = 'OBSERVADA' THEN 1 ELSE 0 END)
                        AS observadas
                FROM rutas r
                LEFT JOIN (
                    SELECT id_ruta, MAX(id) AS id
                    FROM validaciones_ruta
                    WHERE vigente = 1
                    GROUP BY id_ruta
                ) vr ON vr.id_ruta = r.id
                WHERE r.fecha BETWEEN %s AND %s
            """
            cursor.execute(sql_fiscalizacion, (fecha_inicio, fecha_fin))
            r_fiscalizacion = cursor.fetchone() or {}

            p_total = int(r_puntos.get("total") or 0)
            p_atendidos = int(r_puntos.get("atendidos") or 0)
            p_incidencias = int(r_puntos.get("con_incidencia") or 0)
            avance_gen = round(((p_atendidos + p_incidencias) / p_total * 100), 1) if p_total > 0 else 0.0

            return {
                "fecha": fecha_inicio,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "total_rutas": int(r_rutas.get("total") or 0),
                "rutas_activas": int(r_rutas.get("en_curso") or 0),
                "rutas_completadas": int(r_rutas.get("finalizadas") or 0) + int(r_rutas.get("observadas") or 0),
                "total_puntos": p_total,
                "puntos_atendidos": p_atendidos,
                "total_incidencias": int(r_inc.get("abiertas") or 0) + int(r_inc.get("en_revision") or 0) + int(r_inc.get("resueltas") or 0),
                "incidencias_criticas": int(r_inc.get("criticas") or 0),
                "porcentaje_cumplimiento": avance_gen,
                "rutas_por_revisar": int(r_fiscalizacion.get("pendientes_revision") or 0),
                "rutas_conformes": int(r_fiscalizacion.get("conformes") or 0),
                "rutas_observadas": int(r_fiscalizacion.get("observadas") or 0),
                "rutas": {
                    "total": int(r_rutas.get("total") or 0),
                    "programadas": int(r_rutas.get("programadas") or 0),
                    "en_curso": int(r_rutas.get("en_curso") or 0),
                    "finalizadas": int(r_rutas.get("finalizadas") or 0),
                    "observadas": int(r_rutas.get("observadas") or 0),
                },
                "puntos": {
                    "total": p_total,
                    "atendidos": p_atendidos,
                    "con_incidencia": p_incidencias,
                    "pendientes": int(r_puntos.get("pendientes") or 0),
                },
                "incidencias": {
                    "abiertas": int(r_inc.get("abiertas") or 0),
                    "en_revision": int(r_inc.get("en_revision") or 0),
                    "resueltas": int(r_inc.get("resueltas") or 0),
                    "criticas": int(r_inc.get("criticas") or 0),
                },
                "fiscalizacion": {
                    "pendientes_revision": int(r_fiscalizacion.get("pendientes_revision") or 0),
                    "conformes": int(r_fiscalizacion.get("conformes") or 0),
                    "observadas": int(r_fiscalizacion.get("observadas") or 0),
                },
                "avance_general_porcentaje": avance_gen,
            }
        finally:
            cursor.close()

    def crear_ruta(
        self,
        codigo: str,
        fecha: str,
        turno: str,
        id_operario: int = None,
        id_vehiculo: int = None,
        estado: str = "PROGRAMADA",
    ) -> int:
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO rutas (codigo, fecha, turno, id_operario, id_vehiculo, estado)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (codigo, fecha, turno, id_operario, id_vehiculo, estado))
            return cursor.lastrowid
        finally:
            cursor.close()

    def asociar_punto(self, id_ruta: int, id_punto: int, orden: int) -> int:
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO ruta_puntos (id_ruta, id_punto, orden, estado)
                VALUES (%s, %s, %s, 'PENDIENTE')
            """
            cursor.execute(sql, (id_ruta, id_punto, orden))
            return cursor.lastrowid
        finally:
            cursor.close()

    def generar_siguiente_codigo(self) -> str:
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT codigo FROM rutas WHERE codigo REGEXP '^RUT-[0-9]+$' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row.get("codigo"):
                try:
                    num = int(row["codigo"].split("-")[1])
                    return f"RUT-{num + 1:03d}"
                except Exception:
                    pass
            cursor.execute("SELECT COUNT(*) AS total FROM rutas")
            total = cursor.fetchone().get("total", 0)
            return f"RUT-{total + 1:03d}"
        finally:
            cursor.close()
