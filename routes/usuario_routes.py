from typing import Optional
from fastapi import APIRouter, Depends

from services.usuario_service import UsuarioService
from utils.response import success_response, error_response
from utils.security import obtener_usuario_actual, requerir_roles

usuario_router = APIRouter(prefix="/api", tags=["Usuarios"])


# ===== ENDPOINT 02 =========================
@usuario_router.get("/usuario/perfil")
def obtener_perfil(usuario: dict = Depends(obtener_usuario_actual)):
    service = UsuarioService()
    data, message, http_code = service.obtener_perfil(usuario["id"])
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 20 =========================
@usuario_router.get("/usuarios/operarios")
def listar_operarios(
    fecha: Optional[str] = None,
    turno: Optional[str] = None,
    excluir_id_ruta: Optional[int] = None,
    todos: bool = False,
    _: dict = Depends(requerir_roles("SUPERVISOR", "FISCALIZADOR")),
):
    service = UsuarioService()
    data, message, http_code = service.listar_operarios(fecha, turno, excluir_id_ruta, todos=todos)
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)
