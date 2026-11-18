from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.ruta_service import RutaService
from utils.response import success_response, error_response
from utils.security import obtener_usuario_actual, requerir_roles

ruta_router = APIRouter(prefix="/api/rutas", tags=["Rutas"])


class AsignarDTO(BaseModel):
    id_operario: int
    id_vehiculo: int


class FinalizarDTO(BaseModel):
    comentario: Optional[str] = None


class ComentarioDTO(BaseModel):
    comentario: str


class ValidarDTO(BaseModel):
    comentario: Optional[str] = None


class CrearRutaDTO(BaseModel):
    codigo: Optional[str] = None
    fecha: str
    turno: str
    id_operario: Optional[int] = None
    id_vehiculo: Optional[int] = None
    puntos_ids: Optional[list[int]] = None


class DuplicarRutaDTO(BaseModel):
    fecha: Optional[str] = None
    turno: Optional[str] = None
    id_operario: Optional[int] = None
    id_vehiculo: Optional[int] = None


# ===== CREAR RUTA ==========================
@ruta_router.post("", status_code=201)
def crear_ruta(
    body: CrearRutaDTO,
    supervisor: dict = Depends(requerir_roles("SUPERVISOR")),
):
    service = RutaService()
    data, message, http_code = service.crear_ruta(
        supervisor_id=supervisor["id"],
        fecha=body.fecha,
        turno=body.turno,
        codigo=body.codigo,
        id_operario=body.id_operario,
        id_vehiculo=body.id_vehiculo,
        puntos_ids=body.puntos_ids or [],
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== DUPLICAR RUTA =======================
@ruta_router.post("/{id}/duplicar", status_code=201)
def duplicar_ruta(
    id: int,
    body: Optional[DuplicarRutaDTO] = None,
    supervisor: dict = Depends(requerir_roles("SUPERVISOR")),
):
    service = RutaService()
    b_fecha = body.fecha if body else None
    b_turno = body.turno if body else None
    b_operario = body.id_operario if body else None
    b_vehiculo = body.id_vehiculo if body else None
    data, message, http_code = service.duplicar_ruta(
        id_ruta_origen=id,
        supervisor_id=supervisor["id"],
        fecha=b_fecha,
        turno=b_turno,
        id_operario=b_operario,
        id_vehiculo=b_vehiculo,
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 05 =========================
@ruta_router.get("")
def listar_rutas(
    fecha: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    estado: Optional[str] = None,
    id_operario: Optional[int] = None,
    id_vehiculo: Optional[int] = None,
    usuario: dict = Depends(obtener_usuario_actual),
):
    service = RutaService()
    data, message, http_code = service.listar(
        usuario_id=usuario["id"],
        rol=usuario["rol"],
        fecha=fecha,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado=estado,
        id_operario_filtro=id_operario,
        id_vehiculo_filtro=id_vehiculo,
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 06 =========================
@ruta_router.get("/{id}")
def obtener_detalle_ruta(id: int, usuario: dict = Depends(obtener_usuario_actual)):
    service = RutaService()
    data, message, http_code = service.obtener_detalle(id, usuario["id"], usuario["rol"])
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 07 =========================
@ruta_router.get("/{id}/puntos")
def obtener_puntos_ruta(id: int, usuario: dict = Depends(obtener_usuario_actual)):
    service = RutaService()
    data, message, http_code = service.obtener_puntos(id, usuario["id"], usuario["rol"])
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 08 =========================
@ruta_router.put("/{id}/asignar")
def asignar_operario_y_vehiculo(
    id: int,
    body: AsignarDTO,
    supervisor: dict = Depends(requerir_roles("SUPERVISOR")),
):
    service = RutaService()
    data, message, http_code = service.asignar(
        id_ruta=id,
        id_operario=body.id_operario,
        id_vehiculo=body.id_vehiculo,
        supervisor_id=supervisor["id"],
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 09 =========================
@ruta_router.post("/{id}/iniciar")
def iniciar_ruta(
    id: int,
    operario: dict = Depends(requerir_roles("OPERARIO")),
):
    service = RutaService()
    data, message, http_code = service.iniciar(id_ruta=id, operario_id=operario["id"])
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 10 =========================
@ruta_router.post("/{id}/finalizar")
def finalizar_ruta(
    id: int,
    body: Optional[FinalizarDTO] = None,
    usuario: dict = Depends(requerir_roles("OPERARIO", "SUPERVISOR")),
):
    comentario = body.comentario if body else None
    service = RutaService()
    resultado = service.finalizar(
        id_ruta=id,
        usuario_id=usuario["id"],
        rol=usuario["rol"],
        comentario=comentario,
    )
    if len(resultado) == 4:
        data, message, http_code, extra = resultado
        return error_response(message, http_code, data=extra)
    data, message, http_code = resultado
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 16 =========================
@ruta_router.get("/{id}/historial")
def obtener_historial_ruta(id: int, usuario: dict = Depends(obtener_usuario_actual)):
    service = RutaService()
    data, message, http_code = service.obtener_historial(id, usuario["id"], usuario["rol"])
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 17 =========================
@ruta_router.post("/{id}/observar")
def observar_ruta(
    id: int,
    body: ComentarioDTO,
    fiscalizador: dict = Depends(requerir_roles("FISCALIZADOR")),
):
    service = RutaService()
    data, message, http_code = service.observar(
        id_ruta=id,
        fiscalizador_id=fiscalizador["id"],
        comentario=body.comentario,
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 18 =========================
@ruta_router.post("/{id}/reabrir")
def reabrir_ruta(
    id: int,
    body: ComentarioDTO,
    supervisor: dict = Depends(requerir_roles("SUPERVISOR")),
):
    service = RutaService()
    data, message, http_code = service.reabrir(
        id_ruta=id,
        supervisor_id=supervisor["id"],
        comentario=body.comentario,
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


@ruta_router.post("/{id}/validar")
def validar_ruta_conforme(
    id: int,
    body: Optional[ValidarDTO] = None,
    fiscalizador: dict = Depends(requerir_roles("FISCALIZADOR")),
):
    service = RutaService()
    data, message, http_code = service.validar_conforme(
        id_ruta=id,
        fiscalizador_id=fiscalizador["id"],
        comentario=body.comentario if body else None,
    )
    if http_code >= 400:
        return error_response(message, http_code, data)
    return success_response(data, message, http_code)
