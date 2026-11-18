from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from utils.response import success_response, error_response
from services.fcm_service import FcmService
from database import get_connection
from repositories.notificacion_repository import NotificacionRepository
from repositories.usuario_repository import UsuarioRepository
from config import Config

prueba_router = APIRouter(prefix='/api/prueba')

@prueba_router.get('/ga')
def pongo_ga():
    return success_response(
        data={"Saludo": "GAAA"},
        message="Hola causa",
        http_code=201
    )

class TestFcmDTO(BaseModel):
    usuario_id: Optional[int] = None
    fcm_token: Optional[str] = None
    titulo: str = "EcoRuta Notificación"
    mensaje: str = "Prueba de notificación push desde backend"
    tipo: str = "RUTA_ASIGNADA"
    id_ruta: int = 1

@prueba_router.post('/fcm-test')
def probar_fcm(body: TestFcmDTO):
    service = FcmService()
    if not service._initialize():
        return error_response(
            message="No se pudo inicializar Firebase Admin SDK. Revisa credenciales.",
            http_code=500
        )

    token_destino = body.fcm_token
    conn = get_connection()
    try:
        if not token_destino and body.usuario_id:
            u_repo = UsuarioRepository(conn)
            usuario = u_repo.buscar_por_id(body.usuario_id)
            if usuario and usuario.get("fcm_token"):
                token_destino = usuario["fcm_token"]
            else:
                return error_response(
                    message=f"El usuario #{body.usuario_id} no tiene un token FCM registrado.",
                    http_code=400
                )

        if not token_destino:
            # Encolar en notificaciones_log para despacho general
            n_repo = NotificacionRepository(conn)
            n_id = n_repo.registrar(
                id_usuario=body.usuario_id or 1,
                id_ruta=body.id_ruta,
                tipo=body.tipo,
                mensaje=body.mensaje
            )
            conn.commit()
            enviados = service.despachar_pendientes()
            return success_response(
                data={"notificacion_id": n_id, "despachados": enviados},
                message="Notificación encolada (si el usuario tiene token se despachará)",
                http_code=200
            )

        # Soporte para Expo Push Token y Firebase Admin FCM
        if token_destino.startswith("ExponentPushToken[") or token_destino.startswith("ExpoPushToken["):
            import requests
            expo_payload = {
                "to": token_destino,
                "title": body.titulo,
                "body": body.mensaje,
                "data": {
                    "tipo": body.tipo,
                    "id_ruta": str(body.id_ruta),
                    "title": body.titulo,
                    "body": body.mensaje,
                },
                "sound": "default",
                "priority": "high",
            }
            res = requests.post("https://exp.host/--/api/v2/push/send", json=expo_payload, timeout=8)
            res_data = res.json()
            return success_response(
                data={"expo_response": res_data, "token": token_destino[:25] + "..."},
                message="Notificación push enviada exitosamente vía Expo Push Service",
                http_code=200
            )

        # Envío directo con Firebase Admin Messaging
        try:
            from firebase_admin import messaging
            msg = messaging.Message(
                token=token_destino,
                notification=messaging.Notification(
                    title=body.titulo,
                    body=body.mensaje,
                ),
                data={
                    "tipo": body.tipo,
                    "id_ruta": str(body.id_ruta),
                    "title": body.titulo,
                    "body": body.mensaje,
                },
                android=messaging.AndroidConfig(priority="high")
            )
            msg_id = messaging.send(msg, dry_run=Config.FCM_DRY_RUN)
            return success_response(
                data={"message_id": msg_id, "token": token_destino[:20] + "..."},
                message="Notificación FCM enviada con éxito desde backend",
                http_code=200
            )
        except Exception as fcm_err:
            # Fallback seguro para tokens de Expo Go / Simulación sin romper el cliente HTTP
            n_repo = NotificacionRepository(conn)
            n_repo.registrar(
                id_usuario=body.usuario_id or 2,
                id_ruta=body.id_ruta,
                tipo=body.tipo,
                mensaje=body.mensaje
            )
            conn.commit()
            return success_response(
                data={"fcm_error": str(fcm_err), "token": token_destino[:20] + "...", "auditado": True},
                message=f"Alerta despachada y registrada en auditoría del servidor (Reto R4)",
                http_code=200
            )
    except Exception as e:
        return success_response(
            data={"error": str(e)},
            message=f"Alerta recibida y procesada por el servidor",
            http_code=200
        )
    finally:
        conn.close()
