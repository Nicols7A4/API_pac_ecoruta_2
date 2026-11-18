from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import app
from config import Config
from services.fcm_service import FcmService
from utils.security import obtener_usuario_actual


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[obtener_usuario_actual] = lambda: {"id": 2, "rol": "OPERARIO"}
    monkeypatch.setattr("services.fcm_service.FcmService.despachar_pendientes", lambda self: 0)
    monkeypatch.setattr("routes.prueba_routes.get_connection", lambda: MagicMock())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(obtener_usuario_actual, None)


def test_prueba_sin_token_no_reporta_exito(client, monkeypatch):
    repo = MagicMock()
    repo.buscar_por_id.return_value = {"fcm_token": None}
    monkeypatch.setattr("routes.prueba_routes.UsuarioRepository", lambda conn: repo)
    response = client.post("/api/prueba/fcm-test", json={})
    assert response.status_code == 400
    assert response.json()["status"] is False


def test_prueba_usa_token_del_usuario_y_muestra_fallos(client, monkeypatch):
    repo = MagicMock()
    repo.buscar_por_id.return_value = {"fcm_token": "token-prueba"}
    monkeypatch.setattr("routes.prueba_routes.UsuarioRepository", lambda conn: repo)
    monkeypatch.setattr(FcmService, "_initialize", lambda self: True)
    enviar = MagicMock(side_effect=RuntimeError("fallo simulado"))
    monkeypatch.setattr(FcmService, "enviar", enviar)

    response = client.post("/api/prueba/fcm-test", json={"fcm_token": "otro-token"})
    assert response.status_code == 502
    assert response.json()["status"] is False
    repo.buscar_por_id.assert_called_once_with(2)
    assert enviar.call_args.args[0] == "token-prueba"


def test_prueba_distingue_simulacion_de_envio(client, monkeypatch):
    repo = MagicMock()
    repo.buscar_por_id.return_value = {"fcm_token": "token-prueba"}
    monkeypatch.setattr("routes.prueba_routes.UsuarioRepository", lambda conn: repo)
    monkeypatch.setattr(FcmService, "_initialize", lambda self: True)
    monkeypatch.setattr(FcmService, "enviar", lambda *args: "id-prueba")
    monkeypatch.setattr(Config, "FCM_DRY_RUN", True)
    response = client.post("/api/prueba/fcm-test", json={})
    assert response.status_code == 200
    assert response.json()["data"]["dry_run"] is True
    assert "no la entrega" in response.json()["message"]


def test_prueba_exitosa_confirma_aceptacion_no_entrega(client, monkeypatch):
    repo = MagicMock()
    repo.buscar_por_id.return_value = {"fcm_token": "token-prueba"}
    monkeypatch.setattr("routes.prueba_routes.UsuarioRepository", lambda conn: repo)
    monkeypatch.setattr(FcmService, "_initialize", lambda self: True)
    monkeypatch.setattr(FcmService, "enviar", lambda *args: "id-prueba")
    monkeypatch.setattr(Config, "FCM_DRY_RUN", False)
    response = client.post("/api/prueba/fcm-test", json={})
    assert response.status_code == 200
    assert response.json()["data"] == {"message_id": "id-prueba", "dry_run": False}
    assert "aceptada" in response.json()["message"]


def test_mensaje_fcm_incluye_notificacion_visible_y_datos(monkeypatch):
    from firebase_admin import messaging

    enviar = MagicMock(return_value="id-prueba")
    monkeypatch.setattr(messaging, "send", enviar)
    monkeypatch.setattr(Config, "FCM_DRY_RUN", False)
    result = FcmService().enviar("token-prueba", "Título", "Mensaje", {"id_ruta": 2})
    mensaje = enviar.call_args.args[0]
    assert result == "id-prueba"
    assert mensaje.notification.title == "Título"
    assert mensaje.notification.body == "Mensaje"
    assert mensaje.data["id_ruta"] == "2"
    assert mensaje.android.notification.channel_id == "ecoruta_default"
    assert enviar.call_args.kwargs["dry_run"] is False


def test_expo_rechazado_no_se_considera_enviado(monkeypatch):
    import requests

    response = MagicMock()
    response.json.return_value = {"data": {"status": "error", "message": "token inválido"}}
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)
    monkeypatch.setattr(Config, "FCM_DRY_RUN", False)
    with pytest.raises(ValueError, match="Expo rechazó"):
        FcmService().enviar("ExpoPushToken[prueba]", "Título", "Mensaje", {})


def test_dry_run_no_consume_cola(monkeypatch):
    monkeypatch.setattr(Config, "FCM_DRY_RUN", True)
    conexion = MagicMock()
    monkeypatch.setattr("services.fcm_service.get_connection", conexion)
    assert FcmService().despachar_pendientes() == 0
    conexion.assert_not_called()
