from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.punto_service import PuntoService
from utils.response import success_response, error_response
from utils.security import obtener_usuario_actual, requerir_roles

punto_router = APIRouter(prefix="/api", tags=["Puntos y Atención"])


class AtenderDTO(BaseModel):
    uuid_operacion: Optional[str] = None
    uuid: Optional[str] = None
    codigo_qr: Optional[str] = None
    codigoQr: Optional[str] = None
    latitud: float
    longitud: float
    fecha_atencion: Optional[str] = None
    fechaAtencion: Optional[str] = None
    observacion: Optional[str] = None


# ===== CATÁLOGO DE PUNTOS ==================
@punto_router.get("/puntos")
def listar_catalogo_puntos(usuario: dict = Depends(obtener_usuario_actual)):
    service = PuntoService()
    data, message, http_code = service.listar_puntos()
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 11 =========================
@punto_router.get("/puntos/{codigo_qr}")
def buscar_punto_por_qr(
    codigo_qr: str,
    id_ruta: Optional[int] = None,
    usuario: dict = Depends(obtener_usuario_actual),
):
    service = PuntoService()
    data, message, http_code = service.buscar_por_qr(
        codigo_qr, id_ruta, usuario["id"], usuario["rol"]
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)

# ===== ENDPOINT 12 =========================
@punto_router.post("/ruta-puntos/{id}/atender")
def atender_punto(
    id: int,
    body: AtenderDTO,
    mode: Optional[str] = None,
    operario: dict = Depends(requerir_roles("OPERARIO")),
):
    service = PuntoService()
    uuid_op = body.uuid_operacion or body.uuid
    qr_code = body.codigo_qr or body.codigoQr
    fecha_at = body.fecha_atencion or body.fechaAtencion

    data, message, http_code = service.atender_punto(
        id_ruta_punto=id,
        operario_id=operario["id"],
        uuid_operacion=uuid_op,
        codigo_qr=qr_code,
        latitud=body.latitud,
        longitud=body.longitud,
        fecha_atencion=fecha_at,
        observacion=body.observacion,
        modo_dev=(mode == "dev"),
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)
