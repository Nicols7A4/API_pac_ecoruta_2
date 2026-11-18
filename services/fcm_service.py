import json
import logging
import os
from datetime import timedelta

from config import Config
from database import get_connection
from repositories.notificacion_repository import NotificacionRepository

logger = logging.getLogger(__name__)


class FcmService:
    _initialized = False

    def enviar(self, token, titulo, mensaje, data):
        data = {str(key): str(value) for key, value in data.items() if value is not None}
        data["title"] = titulo
        data["body"] = mensaje
        if token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
            if Config.FCM_DRY_RUN:
                raise ValueError("FCM_DRY_RUN no permite validar tokens Expo")
            import requests
            response = requests.post(
                "https://exp.host/--/api/v2/push/send",
                json={"to": token, "title": titulo, "body": mensaje, "data": data,
                      "sound": "default", "priority": "high"},
                timeout=8,
            )
            response.raise_for_status()
            ticket = response.json().get("data", {})
            if ticket.get("status") != "ok" or not ticket.get("id"):
                raise ValueError(f"Expo rechazó la notificación: {ticket.get('message', 'respuesta inválida')}")
            return ticket["id"]

        from firebase_admin import messaging
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=titulo, body=mensaje),
            data=data,
            android=messaging.AndroidConfig(
                priority="high",
                ttl=timedelta(hours=6),
                notification=messaging.AndroidNotification(channel_id="ecoruta_default"),
            ),
        )
        return messaging.send(message, dry_run=Config.FCM_DRY_RUN)

    def _initialize(self):
        if self.__class__._initialized:
            return True
        if not Config.FCM_ENABLED:
            return False
        try:
            import firebase_admin
            from firebase_admin import credentials
            if not firebase_admin._apps:
                options = {"projectId": Config.FIREBASE_PROJECT_ID} if Config.FIREBASE_PROJECT_ID else None
                credential_path = Config.FIREBASE_CREDENTIALS.strip()
                if credential_path:
                    if not os.path.isabs(credential_path):
                        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        credential_path = os.path.join(base, credential_path)
                    credential_path = os.path.abspath(os.path.expandvars(credential_path))
                    if not os.path.isfile(credential_path):
                        logger.error("No existe FIREBASE_CREDENTIALS: %s", credential_path)
                        return False
                    credential = credentials.Certificate(credential_path)
                else:
                    # Application Default Credentials: usa GOOGLE_APPLICATION_CREDENTIALS
                    # localmente o la identidad administrada del servidor en Google Cloud.
                    credential = credentials.ApplicationDefault()
                firebase_admin.initialize_app(credential, options)
            self.__class__._initialized = True
            return True
        except Exception:
            logger.exception("No se pudo inicializar Firebase Admin")
            return False

    def despachar_pendientes(self, limite=20):
        if Config.FCM_DRY_RUN:
            logger.info("FCM_DRY_RUN activo: se conserva la cola de notificaciones.")
            return 0
        if not self._initialize():
            return 0
        connection = get_connection()
        enviados = 0
        try:
            repo = NotificacionRepository(connection)
            pendientes = repo.listar_pendientes(limite)
            for item in pendientes:
                try:
                    data = json.loads(item["payload_json"] or "{}")
                    data = {str(key): str(value) for key, value in data.items() if value is not None}
                    data.setdefault("tipo", str(item["tipo"]))
                    data.setdefault("id_ruta", str(item["id_ruta"]))
                    if item.get("id_incidencia"):
                        data.setdefault("id_incidencia", str(item["id_incidencia"]))
                    data.setdefault("title", "EcoRuta")
                    data.setdefault("body", str(item["mensaje"]))
                    message_id = self.enviar(
                        item["fcm_token"], data["title"], data["body"], data,
                    )
                    repo.actualizar_resultado(item["id"], "ENVIADA", message_id)
                    enviados += 1
                except Exception as exc:
                    logger.warning("FCM falló para notificación %s: %s", item["id"], exc)
                    repo.actualizar_resultado(item["id"], "REINTENTO", type(exc).__name__)
            connection.commit()
            return enviados
        except Exception:
            connection.rollback()
            logger.exception("No se pudo despachar la cola FCM")
            return enviados
        finally:
            connection.close()
