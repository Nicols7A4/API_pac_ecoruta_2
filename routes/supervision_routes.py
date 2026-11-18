from typing import Optional
from fastapi import APIRouter, Depends

from services.supervision_service import SupervisionService
from utils.response import success_response, error_response
from utils.security import requerir_roles

supervision_router = APIRouter(prefix="/api/supervision", tags=["Supervisión"])


# ===== ENDPOINT 19 =========================
@supervision_router.get("/resumen")
def obtener_resumen_supervision(
    fecha: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    _: dict = Depends(requerir_roles("SUPERVISOR", "FISCALIZADOR")),
):
    service = SupervisionService()
    data, message, http_code = service.obtener_resumen(fecha, fecha_inicio, fecha_fin)
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)
