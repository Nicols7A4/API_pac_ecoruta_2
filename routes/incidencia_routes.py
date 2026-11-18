import os
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import Config
from database import get_connection
from repositories.incidencia_repository import IncidenciaRepository
from services.incidencia_service import IncidenciaService
from utils.response import success_response, error_response
from utils.security import obtener_usuario_actual, requerir_roles

incidencia_router = APIRouter(prefix="/api", tags=["Incidencias"])
evidencia_router = APIRouter(tags=["Evidencias"])


class CambiarEstadoIncidenciaDTO(BaseModel):
    estado: str
    observacion: Optional[str] = None

# ===== ENDPOINT 13 =========================
@incidencia_router.post("/ruta-puntos/{id}/incidencias")
async def registrar_incidencia(
    id: int,
    request: Request,
    operario: dict = Depends(requerir_roles("OPERARIO")),
):
    content_type = request.headers.get("content-type", "")
    foto_bytes = None
    foto_filename = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        uuid_operacion = form.get("uuid_operacion") or form.get("uuid")
        tipo = form.get("tipo") or form.get("tipo_incidencia")
        descripcion = form.get("descripcion")
        fecha_captura = form.get("fecha_captura") or form.get("fechaCaptura")
        es_critica_raw = form.get("es_critica") or form.get("critica", "false")
        es_critica = str(es_critica_raw).lower() in ["true", "1", "yes"]

        foto = form.get("foto") or form.get("evidencia")
        if foto and hasattr(foto, "read"):
            foto_bytes = await foto.read(Config.MAX_UPLOAD_BYTES + 1)
            foto_filename = getattr(foto, "filename", "foto.jpg")
    else:
        # JSON body
        body = await request.json()
        uuid_operacion = body.get("uuid_operacion") or body.get("uuid")
        tipo = body.get("tipo") or body.get("tipo_incidencia")
        descripcion = body.get("descripcion")
        fecha_captura = body.get("fecha_captura") or body.get("fechaCaptura")
        es_critica = bool(body.get("es_critica", body.get("critica", False)))

    # Mapeo tolerante de tipos de incidencia
    tipo_raw = str(tipo or "").strip().upper()
    TIPO_MAP = {
        "CONTENEDOR_LLENO": "EXCESO_RESIDUOS",
        "OBSTACULO_VIA": "ACCESO_BLOQUEADO",
        "PUNTO_INACCESIBLE": "ACCESO_BLOQUEADO",
        "FALLA_MECANICA": "VEHICULO",
        "ACCIDENTE": "VEHICULO",
    }
    tipo = TIPO_MAP.get(tipo_raw, tipo_raw)

    service = IncidenciaService()
    data, message, http_code = service.registrar(
        id_ruta_punto=id,
        operario_id=operario["id"],
        uuid_operacion=uuid_operacion,
        tipo=tipo,
        descripcion=descripcion,
        es_critica=es_critica,
        foto_bytes=foto_bytes,
        foto_filename=foto_filename,
        fecha_captura=fecha_captura,
    )

    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


@incidencia_router.post("/incidencias")
async def registrar_incidencia_general(
    request: Request,
    operario: dict = Depends(requerir_roles("OPERARIO")),
):
    content_type = request.headers.get("content-type", "")
    punto_id = None
    if "multipart/form-data" in content_type:
        form = await request.form()
        punto_id = form.get("punto_id") or form.get("id_ruta_punto") or form.get("puntoId")
    else:
        body = await request.json()
        punto_id = body.get("punto_id") or body.get("id_ruta_punto") or body.get("puntoId")

    if not punto_id:
        return error_response("id_ruta_punto es requerido para registrar una incidencia", 400)

    return await registrar_incidencia(id=int(punto_id), request=request, operario=operario)


@incidencia_router.get("/ruta-puntos/{id}/incidencias")
def listar_incidencias_punto(
    id: int,
    usuario: dict = Depends(obtener_usuario_actual),
):
    connection = get_connection()
    try:
        inc_repo = IncidenciaRepository(connection)
        incidencias = inc_repo.listar_por_ruta_punto(id)
        return success_response({"incidencias": incidencias}, "Incidencias del punto obtenidas", 200)
    finally:
        connection.close()


@evidencia_router.get("/uploads/incidencias/{filename:path}")
def obtener_evidencia_protegida(
    filename: str,
):
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        return error_response("Ruta de evidencia inválida", 400)
    full_path = os.path.join(Config.UPLOAD_DIR, "incidencias", safe_name)
    if not os.path.isfile(full_path):
        return error_response("Archivo de evidencia no disponible", 404)
    ext = os.path.splitext(safe_name)[1].lower()
    media_type = "image/png" if ext == ".png" else "image/jpeg"
    return FileResponse(full_path, media_type=media_type)


# ===== ENDPOINT 14 =========================
@incidencia_router.get("/rutas/{id}/incidencias")
def listar_incidencias_ruta(
    id: int,
    estado: Optional[str] = None,
    id_ruta_punto: Optional[int] = None,
    usuario: dict = Depends(obtener_usuario_actual),
):
    service = IncidenciaService()
    data, message, http_code = service.listar_por_ruta(
        id_ruta=id,
        usuario_id=usuario["id"],
        rol=usuario["rol"],
        estado=estado,
        id_ruta_punto=id_ruta_punto,
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


# ===== ENDPOINT 15 =========================
@incidencia_router.get("/incidencias/{id}")
def obtener_detalle_incidencia(
    id: int,
    usuario: dict = Depends(obtener_usuario_actual),
):
    service = IncidenciaService()
    data, message, http_code = service.obtener_detalle(
        id_incidencia=id,
        usuario_id=usuario["id"],
        rol=usuario["rol"],
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)


@incidencia_router.put("/incidencias/{id}/estado")
def cambiar_estado_incidencia(
    id: int,
    body: CambiarEstadoIncidenciaDTO,
    usuario: dict = Depends(requerir_roles("SUPERVISOR", "FISCALIZADOR")),
):
    service = IncidenciaService()
    data, message, http_code = service.cambiar_estado(
        id_incidencia=id,
        usuario_id=usuario["id"],
        rol=usuario["rol"],
        nuevo_estado=body.estado,
        observacion=body.observacion,
    )
    if data is None:
        return error_response(message, http_code)
    return success_response(data, message, http_code)
