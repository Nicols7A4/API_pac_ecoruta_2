import pytest
from fastapi.testclient import TestClient

from app import app
from utils.security import crear_token


class FakeConnection:
    def close(self):
        pass


class FakeUsuarioRepository:
    def __init__(self, _connection):
        pass

    def buscar_por_id(self, usuario_id):
        roles = {1: "SUPERVISOR", 2: "OPERARIO", 3: "FISCALIZADOR"}
        return {
            "id": usuario_id, "nombre": "Demo", "correo": "demo@ecoruta.pe",
            "rol": roles[usuario_id], "activo": 1,
        }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("utils.security.get_connection", lambda: FakeConnection())
    monkeypatch.setattr("utils.security.UsuarioRepository", FakeUsuarioRepository)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def auth(usuario_id, rol):
    token = crear_token({"id": usuario_id, "nombre": "Demo", "rol": rol})
    return {"Authorization": f"Bearer {token}"}


def test_health_uses_single_envelope(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": True, "message": "API disponible",
        "data": {"app": "EcoRuta API REST", "framework": "FastAPI"},
    }


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/rutas")
    assert response.status_code == 401
    assert response.json()["status"] is False
    assert set(response.json()) == {"status", "message", "data"}


def test_role_is_enforced_before_service(client):
    response = client.post("/api/rutas/1/iniciar", headers=auth(1, "SUPERVISOR"))
    assert response.status_code == 403
    assert response.json()["status"] is False


def test_login_contract(client, monkeypatch):
    class Auth:
        def login(self, correo, password):
            return {
                "token": "jwt", "tipo": "Bearer",
                "usuario": {"id": 1, "nombre": "Supervisor", "rol": "SUPERVISOR"},
            }, "Login correcto", 200

    monkeypatch.setattr("routes.auth_routes.AuthService", Auth)
    response = client.post(
        "/api/auth/login",
        json={"correo": "supervisor@ecoruta.pe", "password": "Supervisor123"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["usuario"]["rol"] == "SUPERVISOR"


def test_finalization_conflict_preserves_data(client, monkeypatch):
    class Rutas:
        def finalizar(self, *_args, **_kwargs):
            return {"puntos_pendientes": [7, 8]}, "Hay puntos sin atender ni justificar", 409

    monkeypatch.setattr("routes.ruta_routes.RutaService", Rutas)
    response = client.post("/api/rutas/2/finalizar", headers=auth(2, "OPERARIO"), json={})
    assert response.status_code == 409
    assert response.json()["status"] is False
    assert response.json()["data"]["puntos_pendientes"] == [7, 8]


def test_fiscalizador_can_validate_conforme(client, monkeypatch):
    class Rutas:
        def validar_conforme(self, **kwargs):
            return {
                "validacion": {"id_ruta": kwargs["id_ruta"], "resultado": "CONFORME", "vigente": True}
            }, "Ruta validada conforme", 200

    monkeypatch.setattr("routes.ruta_routes.RutaService", Rutas)
    response = client.post(
        "/api/rutas/1/validar",
        headers=auth(3, "FISCALIZADOR"),
        json={"comentario": "Conforme"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["validacion"]["resultado"] == "CONFORME"


def test_minimum_routes_are_registered():
    rules = set(app.openapi()["paths"])
    required = {
        "/api/auth/login", "/api/auth/fcm-token", "/api/rutas", "/api/rutas/{id}",
        "/api/rutas/{id}/puntos", "/api/rutas/{id}/asignar",
        "/api/rutas/{id}/iniciar", "/api/rutas/{id}/finalizar",
        "/api/puntos/{codigo_qr}", "/api/ruta-puntos/{id}/atender",
        "/api/ruta-puntos/{id}/incidencias", "/api/rutas/{id}/incidencias",
        "/api/incidencias/{id}/estado", "/api/rutas/{id}/historial",
        "/api/supervision/resumen", "/api/usuarios/operarios", "/api/vehiculos",
    }
    assert required <= rules


def test_supervision_panel_is_served(client):
    page = client.get("/supervision")
    script = client.get("/supervision-assets/app.js")
    assert page.status_code == 200
    assert "EcoRuta" in page.text
    assert script.status_code == 200
    assert "setInterval" in script.text


def test_dev_mode_rejected_when_disabled(client, monkeypatch):
    monkeypatch.setattr("services.punto_service.Config.ALLOW_DEV_MODE", False)
    body = {"uuid_operacion": "3f2b8c1e-9d4a-4c55-8a1b-6d7e2f0a9b11", "codigo_qr": "PTO-001",
            "latitud": -6.77, "longitud": -79.84}
    response = client.post("/api/ruta-puntos/1/atender?mode=dev", json=body, headers=auth(2, "OPERARIO"))
    assert response.status_code == 403
    assert response.json()["status"] is False
