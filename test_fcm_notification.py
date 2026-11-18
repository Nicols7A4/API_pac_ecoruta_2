"""
Script para probar el envío de notificaciones push de Firebase (FCM v1).
Permite verificar la conexión del backend con Firebase Admin SDK y enviar
notificaciones de prueba a tokens reales o validar la cola de notificaciones.
"""
import sys
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_fcm")

# Asegurar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from database import get_connection
from services.fcm_service import FcmService
from repositories.notificacion_repository import NotificacionRepository
from repositories.usuario_repository import UsuarioRepository

def verificar_conexion_firebase():
    logger.info("=== 1. Verificando inicialización de Firebase Admin ===")
    service = FcmService()
    ok = service._initialize()
    if not ok:
        logger.error("No se pudo inicializar Firebase Admin.")
        return False
    import firebase_admin
    logger.info("Firebase Admin inicializado correctamente con proyecto: %s", Config.FIREBASE_PROJECT_ID)
    return True

def listar_tokens_usuarios():
    logger.info("=== 2. Consultando usuarios y tokens FCM en Base de Datos ===")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, correo, rol, fcm_token FROM usuarios")
        usuarios = cur.fetchall()
        for u in usuarios:
            token_preview = (u['fcm_token'][:20] + "...") if u['fcm_token'] else "Ninguno"
            logger.info("Usuario #%s (%s - %s): Token FCM = %s", u['id'], u['nombre'], u['rol'], token_preview)
        return usuarios
    finally:
        conn.close()

def probar_despacho_cola():
    logger.info("=== 3. Probando despacho de cola de notificaciones pendientes ===")
    service = FcmService()
    enviados = service.despachar_pendientes()
    logger.info("Notificaciones despachadas: %d", enviados)
    return enviados

def enviar_notificacion_directa(token, titulo="EcoRuta Alerta", cuerpo="Prueba de notificación push desde backend"):
    logger.info("=== 4. Enviando notificación directa a token ===")
    service = FcmService()
    if not service._initialize():
        logger.error("No se pudo inicializar Firebase.")
        return False
    from firebase_admin import messaging
    try:
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=titulo,
                body=cuerpo,
            ),
            data={
                "tipo": "PRUEBA",
                "id_ruta": "1",
                "title": titulo,
                "body": cuerpo,
            },
            android=messaging.AndroidConfig(
                priority="high"
            )
        )
        response = messaging.send(msg, dry_run=False)
        logger.info("Mensaje enviado exitosamente a FCM! Message ID: %s", response)
        return True
    except Exception as e:
        logger.error("Error al enviar mensaje FCM: %s (%s)", type(e).__name__, e)
        return False

if __name__ == "__main__":
    verificar_conexion_firebase()
    usuarios = listar_tokens_usuarios()
    
    # Si se pasa un token por línea de comando:
    if len(sys.argv) > 1:
        token_arg = sys.argv[1]
        enviar_notificacion_directa(token_arg)
    else:
        # Verificar si algún usuario ya tiene token registrado
        con_token = [u for u in usuarios if u['fcm_token']]
        if con_token:
            for u in con_token:
                logger.info("Enviando prueba al usuario %s...", u['nombre'])
                enviar_notificacion_directa(u['fcm_token'], "EcoRuta: Ruta Asignada", f"Hola {u['nombre']}, tienes una nueva ruta asignada")
        else:
            logger.info("Ningún usuario tiene token FCM registrado en BD aún.")
            logger.info("Inicia sesión en la app Android física para que registre su token mediante POST /api/auth/fcm-token")
    
    probar_despacho_cola()
