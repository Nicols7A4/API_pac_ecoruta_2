from datetime import datetime
from database import get_connection
from repositories.usuario_repository import UsuarioRepository


class UsuarioService:
    def obtener_perfil(self, usuario_id: int):
        connection = get_connection()
        try:
            repo = UsuarioRepository(connection)
            usuario = repo.buscar_por_id(usuario_id)
            if not usuario:
                return None, "Usuario no encontrado", 404

            data = {
                "id": usuario["id"],
                "nombre": usuario["nombre"],
                "correo": usuario["correo"],
                "rol": usuario["rol"],
                "activo": bool(usuario["activo"]),
            }
            return data, "Perfil obtenido", 200
        finally:
            connection.close()

    def listar_operarios(self, fecha: str = None, turno: str = None, excluir_id_ruta: int = None, todos: bool = False):
        if (fecha and not turno) or (turno and not fecha):
            return None, "Los parámetros fecha y turno deben enviarse juntos", 400

        if turno and turno not in ["MANANA", "TARDE", "NOCHE"]:
            return None, "Turno inválido. Valores permitidos: MANANA, TARDE, NOCHE", 400

        if fecha:
            try:
                datetime.strptime(fecha, "%Y-%m-%d")
            except ValueError:
                return None, "Fecha mal formada. Formato esperado: YYYY-MM-DD", 400

        if excluir_id_ruta is not None and excluir_id_ruta < 1:
            return None, "excluir_id_ruta debe ser un identificador válido", 400

        connection = get_connection()
        try:
            repo = UsuarioRepository(connection)
            operarios = repo.listar_operarios_disponibles(
                fecha,
                turno,
                excluir_id_ruta,
                incluir_todos=todos,
            )
            return {"operarios": operarios}, "Operarios obtenidos", 200
        finally:
            connection.close()
