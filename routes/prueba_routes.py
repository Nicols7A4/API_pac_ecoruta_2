import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config import Config
from database import get_connection
from repositories.usuario_repository import UsuarioRepository
from services.fcm_service import FcmService
from utils.response import error_response, success_response
from utils.security import obtener_usuario_actual

logger = logging.getLogger(__name__)
prueba_router = APIRouter(prefix="/api/prueba")


@prueba_router.get("/ga")
def pongo_ga():
    return success_response(
        data={"Saludo": "GAAA"},
        message="Hola causa",
        http_code=201,
    )


class TestFcmDTO(BaseModel):
    titulo: str = "EcoRuta Notificación"
    mensaje: str = "Prueba de notificación push desde backend"
    tipo: str = "RUTA_ASIGNADA"
    id_ruta: int = 1


@prueba_router.post("/fcm-test")
def probar_fcm(body: TestFcmDTO, usuario: dict = Depends(obtener_usuario_actual)):
    conn = get_connection()
    try:
        destinatario = UsuarioRepository(conn).buscar_por_id(usuario["id"])
        token = destinatario.get("fcm_token") if destinatario else None
    finally:
        conn.close()
    if not token:
        return error_response("No tienes un token push registrado en el servidor.", 400)

    service = FcmService()
    if not service._initialize():
        return error_response("No se pudo inicializar Firebase Admin SDK. Revisa credenciales.", 500)
    try:
        message_id = service.enviar(
            token, body.titulo, body.mensaje,
            {"tipo": body.tipo, "id_ruta": body.id_ruta},
        )
    except Exception:
        logger.exception("No se pudo enviar la notificación de prueba")
        return error_response("No se pudo enviar la notificación push. Revisa los logs del servidor.", 502)

    mensaje = (
        "Notificación validada por Firebase; FCM_DRY_RUN no la entrega."
        if Config.FCM_DRY_RUN
        else "Notificación aceptada para envío; comprueba el dispositivo."
    )
    return success_response(
        data={"message_id": message_id, "dry_run": Config.FCM_DRY_RUN},
        message=mensaje,
        http_code=200,
    )
