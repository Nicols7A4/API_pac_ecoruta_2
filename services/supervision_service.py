from datetime import datetime
from zoneinfo import ZoneInfo
from database import get_connection
from repositories.ruta_repository import RutaRepository


class SupervisionService:
    def obtener_resumen(self, fecha: str = None, fecha_inicio: str = None, fecha_fin: str = None):
        lima = ZoneInfo("America/Lima")

        if fecha_inicio or fecha_fin:
            if not fecha_inicio or not fecha_fin:
                return None, "Debe indicar fecha_inicio y fecha_fin", 400
            try:
                datetime.strptime(fecha_inicio, "%Y-%m-%d")
                datetime.strptime(fecha_fin, "%Y-%m-%d")
            except ValueError:
                return None, "Fechas mal formadas. Formato esperado: YYYY-MM-DD", 400
            if fecha_inicio > fecha_fin:
                return None, "fecha_inicio no puede ser posterior a fecha_fin", 400
            inicio_consulta = fecha_inicio
            fin_consulta = fecha_fin
        elif not fecha:
            inicio_consulta = datetime.now(lima).strftime("%Y-%m-%d")
            fin_consulta = inicio_consulta
        else:
            try:
                datetime.strptime(fecha, "%Y-%m-%d")
                inicio_consulta = fecha
                fin_consulta = fecha
            except ValueError:
                return None, "Fecha mal formada. Formato esperado: YYYY-MM-DD", 400

        connection = get_connection()
        try:
            repo = RutaRepository(connection)
            resumen = repo.obtener_resumen_supervision(inicio_consulta, fin_consulta)
            return resumen, "Resumen obtenido", 200
        finally:
            connection.close()
