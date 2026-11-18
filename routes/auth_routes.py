from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from services.auth_service import AuthService
from utils.response import success_response, error_response
from utils.security import obtener_usuario_actual

auth_router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


class LoginDTO(BaseModel):
    correo: str
    password: Optional[str] = None
    contrasena: Optional[str] = None


class FcmTokenDTO(BaseModel):
    fcm_token: str


# ===== ENDPOINT 01 =========================
@auth_router.post("/login")
def login(body: LoginDTO):
    service = AuthService()
    pwd = body.password or body.contrasena or ""
    data, message, http_code = service.login(body.correo, pwd)
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 03 =========================
@auth_router.post("/fcm-token")
def registrar_fcm_token(body: FcmTokenDTO, usuario: dict = Depends(obtener_usuario_actual)):
    service = AuthService()
    data, message, http_code = service.registrar_fcm(usuario["id"], body.fcm_token)
    if http_code >= 400:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 04 =========================
@auth_router.delete("/fcm-token")
def desasociar_fcm_token(usuario: dict = Depends(obtener_usuario_actual)):
    service = AuthService()
    data, message, http_code = service.desasociar_fcm(usuario["id"])
    if http_code >= 400:
        return error_response(message, http_code)
    return success_response(data, message, http_code)
