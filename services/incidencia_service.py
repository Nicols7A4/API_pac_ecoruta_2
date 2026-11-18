import hashlib
import os
import uuid
from datetime import datetime

from config import Config
from database import get_connection
from repositories.incidencia_repository import IncidenciaRepository
from repositories.notificacion_repository import NotificacionRepository
from repositories.punto_repository import PuntoRepository
from repositories.ruta_repository import RutaRepository
from repositories.usuario_repository import UsuarioRepository
from utils.validation import detectar_imagen, fecha_iso, payload_hash, uuid_v4


class IncidenciaService:
    TIPOS = {"ACCESO_BLOQUEADO", "CONTENEDOR_DANADO", "RESIDUOS_NO_DISPONIBLES",
             "EXCESO_RESIDUOS", "VEHICULO", "OTRO"}

    def registrar(self, id_ruta_punto, operario_id, uuid_operacion, tipo, descripcion,
                  es_critica=False, foto_bytes=None, foto_filename=None, fecha_captura=None):
        operation_uuid = uuid_v4(uuid_operacion)
        tipo = str(tipo or "").strip().upper()
        descripcion = str(descripcion or "").strip()
        captura = fecha_iso(fecha_captura) if fecha_captura else None
        if not operation_uuid or not tipo or not descripcion:
            return None, "UUID v4, tipo y descripción son obligatorios", 400
        if tipo not in self.TIPOS:
            return None, f"Tipo inválido. Valores permitidos: {', '.join(sorted(self.TIPOS))}", 400
        if len(descripcion) > 500:
            return None, "La descripción no debe superar los 500 caracteres", 400
        if fecha_captura and captura is None:
            return None, "fecha_captura debe usar formato ISO 8601", 400
        if foto_bytes and len(foto_bytes) > Config.MAX_UPLOAD_BYTES:
            return None, "El archivo supera el tamaño máximo permitido de 2 MiB", 413
        extension = detectar_imagen(foto_bytes) if foto_bytes else None
        if foto_bytes and not extension:
            return None, "El contenido debe ser una imagen JPG o PNG válida", 400
        if tipo == "CONTENEDOR_DANADO" and not foto_bytes:
            return None, "La foto es obligatoria para CONTENEDOR_DANADO", 400

        fingerprint = payload_hash({
            "tipo_operacion": "INCIDENCIA", "id_ruta_punto": id_ruta_punto,
            "tipo": tipo, "descripcion": descripcion, "es_critica": bool(es_critica),
            "fecha_captura": captura.isoformat() if captura else None,
            "foto_sha256": hashlib.sha256(foto_bytes).hexdigest() if foto_bytes else None,
        })
        connection = get_connection()
        archivo_creado = None
        try:
            inc_repo, p_repo = IncidenciaRepository(connection), PuntoRepository(connection)
            existente = inc_repo.buscar_por_uuid(operation_uuid)
            if existente:
                if (existente["id_ruta_punto"] != id_ruta_punto or existente["id_usuario"] != operario_id
                        or existente.get("payload_hash") != fingerprint):
                    return None, "El UUID ya fue usado con otro recurso o contenido", 409
                detalle = inc_repo.buscar_por_id(existente["id"])
                detalle.pop("id_ruta", None)
                return {"duplicado": True, "incidencia": detalle}, "Incidencia ya registrada (replay idempotente)", 200

            rp = p_repo.buscar_ruta_punto_por_id(id_ruta_punto, for_update=True)
            if not rp:
                return None, "Punto de ruta no encontrado", 404
            if rp["ruta_id_operario"] != operario_id:
                return None, "No tiene permiso sobre este punto (ruta ajena)", 403
            if rp["ruta_estado"] != "EN_CURSO":
                return None, f"La ruta debe estar EN_CURSO (estado actual: {rp['ruta_estado']})", 409

            incidencia_id = inc_repo.crear_incidencia(
                id_ruta_punto, tipo, descripcion, bool(es_critica), "ABIERTA",
                operario_id, operation_uuid, captura, fingerprint,
            )
            if rp["estado"] == "PENDIENTE":
                p_repo.actualizar_estado_punto(id_ruta_punto, "CON_INCIDENCIA")

            evidencias = []
            if foto_bytes:
                directory = os.path.join(Config.UPLOAD_DIR, "incidencias")
                os.makedirs(directory, exist_ok=True)
                name = f"inc_{incidencia_id}_{uuid.uuid4().hex[:8]}.{extension}"
                archivo_creado = os.path.join(directory, name)
                with open(archivo_creado, "xb") as file:
                    file.write(foto_bytes)
                url = f"/uploads/incidencias/{name}"
                evidencia_id = inc_repo.crear_evidencia(incidencia_id, id_ruta_punto, url)
                evidencias.append({"id": evidencia_id, "url": url})

            if es_critica:
                usuarios = UsuarioRepository(connection).obtener_supervisores_activos()
                NotificacionRepository(connection).registrar_para_usuarios(
                    usuarios, rp["id_ruta"], "INCIDENCIA_CRITICA",
                    f"Incidencia crítica reportada en ruta {rp['ruta_codigo']}", incidencia_id=incidencia_id,
                )
            connection.commit()
            return {"duplicado": False, "incidencia": {
                "id": incidencia_id, "id_ruta_punto": id_ruta_punto, "tipo": tipo,
                "descripcion": descripcion, "es_critica": bool(es_critica), "estado": "ABIERTA",
                "fecha_captura": captura.isoformat() if captura else None,
                "fecha_registro": datetime.now().isoformat(), "evidencias": evidencias,
            }}, "Incidencia registrada", 201
        except Exception:
            connection.rollback()
            if archivo_creado and os.path.isfile(archivo_creado):
                os.remove(archivo_creado)
            raise
        finally:
            connection.close()

    def listar_por_ruta(self, id_ruta, usuario_id, rol, estado=None, id_ruta_punto=None):
        if estado and estado not in {"ABIERTA", "EN_REVISION", "RESUELTA"}:
            return None, "Estado de incidencia inválido", 400
        connection = get_connection()
        try:
            ruta = RutaRepository(connection).buscar_por_id(id_ruta)
            if not ruta:
                return None, "Ruta no encontrada", 404
            if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                return None, "No tiene permiso para consultar incidencias de esta ruta", 403
            incidencias = IncidenciaRepository(connection).listar_por_ruta(id_ruta, estado, id_ruta_punto)
            return {"incidencias": incidencias}, "Incidencias obtenidas", 200
        finally:
            connection.close()

    def obtener_detalle(self, id_incidencia, usuario_id, rol):
        connection = get_connection()
        try:
            incidencia = IncidenciaRepository(connection).buscar_por_id(id_incidencia)
            if not incidencia:
                return None, "Incidencia no encontrada", 404
            ruta = RutaRepository(connection).buscar_por_id(incidencia["id_ruta"])
            if not ruta:
                return None, "Ruta de la incidencia no encontrada", 404
            if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                return None, "No tiene permiso para consultar esta incidencia", 403
            return {"incidencia": incidencia}, "Incidencia obtenida", 200
        finally:
            connection.close()

    def cambiar_estado(self, id_incidencia, usuario_id, rol, nuevo_estado, observacion=None):
        if nuevo_estado not in {"EN_REVISION", "RESUELTA"}:
            return None, "Solo se permite EN_REVISION o RESUELTA", 400
        observacion = str(observacion).strip() if observacion else None
        if rol == "FISCALIZADOR" and not observacion:
            return None, "La observación es obligatoria para el fiscalizador", 400
        if observacion and len(observacion) > 500:
            return None, "La observación no debe superar los 500 caracteres", 400
        connection = get_connection()
        try:
            repo = IncidenciaRepository(connection)
            incidencia = repo.buscar_por_id(id_incidencia)
            if not incidencia:
                return None, "Incidencia no encontrada", 404
            actual = incidencia["estado"]
            if actual == "RESUELTA" or (actual == "EN_REVISION" and nuevo_estado != "RESUELTA"):
                return None, "Transición de incidencia no permitida", 409
            repo.actualizar_estado(id_incidencia, nuevo_estado, observacion or incidencia["observacion_control"])
            connection.commit()
            actualizada = repo.buscar_por_id(id_incidencia)
            actualizada.pop("id_ruta", None)
            return {"incidencia": actualizada}, "Estado de incidencia actualizado", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
