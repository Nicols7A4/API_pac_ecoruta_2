import requests
import json
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import os
import datetime


def notificar(device_token, title, body):

    print("device_token="+device_token)
    
    # Ruta al archivo JSON de la cuenta de servicio
    # SERVICE_ACCOUNT_FILE = 'campusgo-lab-firebase-adminsdk-fbsvc-b34a03402b.json'
    # SERVICE_ACCOUNT_FILE = 'campusgo-fireb-vapc-firebase-adminsdk-fbsvc-baa5696339.json'
    SERVICE_ACCOUNT_FILE = 'ecoruta-pac-fireb-firebase-adminsdk-fbsvc-6966da4a33.json'

    # Construir la ruta absoluta al archivo JSON
    service_account_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), SERVICE_ACCOUNT_FILE)

    # Verificar si el archivo existe en la ruta especificada
    if not os.path.isfile(service_account_path):
        raise FileNotFoundError(f"El archivo {service_account_path} no se encuentra. Verifica la ruta.")

    # Definir el scope para la API de FCM
    SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

    # Autenticación y obtención del token de acceso
    credentials = service_account.Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
    credentials.refresh(Request())
    access_token = credentials.token

    # Obtener el project_id dinámicamente de las credenciales
    project_id = credentials.project_id or "ecoruta-pac-fireb"

    # URL de la API de FCM V1
    FCM_URL = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'

    # Encabezados de la solicitud
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json; UTF-8',  
    }

    # Datos del mensaje
    message = {
        'message': {
            'token': device_token,
            'notification': {
                'title': title,
                'body': body,
            },
            'data': {
                'timestamp': str(datetime.datetime.utcnow()),
                'key1': 'valor1',
                'key2': 'valor2',
            }
        }
    }

    # Enviar la solicitud POST a la API de FCM
    response = requests.post(FCM_URL, headers=headers, data=json.dumps(message), timeout=10)

    # Imprimir la respuesta
    print(response.status_code)
    print(response.json())




    