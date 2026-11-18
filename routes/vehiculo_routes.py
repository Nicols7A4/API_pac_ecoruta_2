from typing import Optional
from fastapi import APIRouter, Depends

from services.vehiculo_service import VehiculoService
from utils.response import success_response, error_response
from utils.security import requerir_roles

vehiculo_router = APIRouter(prefix="/api/vehiculos", tags=["Vehículos"])


# ===== ENDPOINT 21 =========================
@vehiculo_router.get("")
def listar_vehiculos(
    estado: Optional[str] = "DISPONIBLE",
    todos: bool = False,
    _: dict = Depends(requerir_roles("SUPERVISOR", "FISCALIZADOR")),
):
    service = VehiculoService()
    data, message, http_code = service.listar_vehiculos(None if todos else estado)
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)
