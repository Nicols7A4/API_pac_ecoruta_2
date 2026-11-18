from werkzeug.security import check_password_hash
from database import get_connection
from repositories.usuario_repository import UsuarioRepository
from utils.security import crear_token


class AuthService:
    def login(self, correo: str, password: str):
        if not correo or not password:
            return None, "Correo y contraseña obligatorios", 400

        connection = get_connection()
        try:
            repo = UsuarioRepository(connection)
            usuario = repo.buscar_por_correo(correo)

            if not usuario or not check_password_hash(usuario["password_hash"], password):
                return None, "Credenciales inválidas", 401

            if not usuario["activo"]:
                return None, "Usuario inactivo", 403

            token = crear_token(usuario)
            data = {
                "token": token,
                "tipo": "Bearer",
                "usuario": {
                    "id": usuario["id"],
                    "nombre": usuario["nombre"],
                    "rol": usuario["rol"],
                },
            }
            return data, "Login correcto", 200
        finally:
            connection.close()

    def registrar_fcm(self, usuario_id: int, fcm_token: str):
        if not fcm_token or not str(fcm_token).strip():
            return None, "fcm_token obligatorio y no vacío", 400

        connection = get_connection()
        try:
            repo = UsuarioRepository(connection)
            repo.actualizar_fcm_token(usuario_id, str(fcm_token).strip())
            connection.commit()
            return None, "Token FCM registrado", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def desasociar_fcm(self, usuario_id: int):
        connection = get_connection()
        try:
            repo = UsuarioRepository(connection)
            repo.desasociar_fcm_token(usuario_id)
            connection.commit()
            return None, "Token FCM desasociado", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
