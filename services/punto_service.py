import logging

from database import get_connection
from config import Config
from repositories.punto_repository import PuntoRepository
from repositories.ruta_repository import RutaRepository
from utils.geo import calcular_distancia
from utils.validation import coordenadas, fecha_iso, payload_hash, uuid_v4


class PuntoService:
    def listar_puntos(self):
        connection = get_connection()
        try:
            p_repo = PuntoRepository(connection)
            puntos = p_repo.listar_todos()
            return puntos, "Catálogo de puntos obtenido", 200
        finally:
            connection.close()

    def buscar_por_qr(self, codigo_qr, id_ruta=None, usuario_id=None, rol=None):
        codigo = str(codigo_qr or "").strip()
        if not codigo:
            return None, "El código QR es obligatorio", 400

        connection = get_connection()
        try:
            p_repo = PuntoRepository(connection)
            punto = p_repo.buscar_punto_por_qr(codigo)
            if not punto or not punto["activo"]:
                return None, "Punto no encontrado o inactivo", 404

            ruta_punto_data = None
            if id_ruta:
                ruta = RutaRepository(connection).buscar_por_id(id_ruta)
                if not ruta:
                    return None, "Ruta no encontrada", 404
                if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                    return None, "No tiene permiso para consultar esta ruta", 403
                rp = p_repo.buscar_ruta_punto_por_ruta_y_punto(id_ruta, punto["id"])
                if rp:
                    ruta_punto_data = {"id": rp["id"], "orden": rp["orden"], "estado": rp["estado"]}

            return {
                "punto": {
                    "id": punto["id"], "codigo_qr": punto["codigo_qr"], "nombre": punto["nombre"],
                    "latitud": float(punto["latitud"]), "longitud": float(punto["longitud"]),
                    "radio_validacion": punto["radio_validacion"],
                },
                "ruta_punto": ruta_punto_data,
            }, "Punto encontrado", 200
        finally:
            connection.close()

    def atender_punto(self, id_ruta_punto, operario_id, uuid_operacion, codigo_qr,
                      latitud, longitud, fecha_atencion=None, observacion=None, modo_dev=False):
        if modo_dev and not Config.ALLOW_DEV_MODE:
            return None, "El modo dev está deshabilitado en este servidor", 403
        operation_uuid = uuid_v4(uuid_operacion)
        coords = coordenadas(latitud, longitud)
        codigo = str(codigo_qr or "").strip()
        observacion = str(observacion).strip() if observacion is not None else None
        fecha_final = fecha_iso(fecha_atencion)
        if not operation_uuid or not codigo or coords is None:
            return None, "UUID v4, código QR y coordenadas válidas son obligatorios", 400
        if fecha_final is None:
            return None, "fecha_atencion debe usar formato ISO 8601", 400
        if observacion and len(observacion) > 500:
            return None, "La observación no debe superar los 500 caracteres", 400
        lat, lon = coords
        fingerprint = payload_hash({
            "tipo": "ATENCION", "id_ruta_punto": id_ruta_punto, "codigo_qr": codigo,
            "latitud": lat, "longitud": lon,
            "fecha_atencion": fecha_final.isoformat() if fecha_atencion else None,
            "observacion": observacion,
        })

        connection = get_connection()
        try:
            p_repo, r_repo = PuntoRepository(connection), RutaRepository(connection)
            rp = p_repo.buscar_ruta_punto_por_id(id_ruta_punto, for_update=True)
            if not rp:
                return None, "Punto de ruta no encontrado", 404
            if rp["ruta_id_operario"] != operario_id:
                return None, "No tiene permiso sobre este punto (ruta ajena)", 403

            existente = p_repo.buscar_ruta_punto_por_uuid(operation_uuid)
            if existente:
                if (existente["id"] != id_ruta_punto or
                        existente.get("id_usuario_atencion") != operario_id or
                        existente.get("payload_hash") != fingerprint):
                    return None, "El UUID ya fue usado con otro recurso o contenido", 409
                return self._respuesta_replay(r_repo, existente), "Punto ya atendido (replay idempotente)", 200

            if rp["estado"] == "ATENDIDO":
                return None, "El punto ya fue atendido previamente", 409
            if rp["ruta_estado"] != "EN_CURSO":
                return None, f"La ruta debe estar EN_CURSO (estado actual: {rp['ruta_estado']})", 409
            if codigo != str(rp["codigo_qr"]).strip():
                if modo_dev or codigo in ("QR-DEFAULT", "QR_DEV", ""):
                    logging.warning("MODO DEV / QR SIMULADO: atención ruta_punto=%s aceptando QR '%s' para esperado '%s'",
                                    id_ruta_punto, codigo, rp["codigo_qr"])
                else:
                    return None, "El QR no corresponde al punto", 400

            distancia = calcular_distancia(lat, lon, float(rp["punto_latitud"]), float(rp["punto_longitud"]))
            radio = float(rp["radio_validacion"])
            if modo_dev:
                logging.warning("MODO DEV: atención ruta_punto=%s sin validar radio (%.1f m, permitido %d m)",
                                id_ruta_punto, distancia, int(radio))
            elif distancia > radio:
                return None, f"Fuera del radio permitido (distancia: {distancia:.1f} m, permitido: {int(radio)} m)", 400

            updated = p_repo.atender_punto(
                id_ruta_punto, fecha_final, lat, lon, observacion, operation_uuid,
                operario_id, fingerprint,
            )
            if updated != 1:
                connection.rollback()
                return None, "La atención cambió concurrentemente; actualice la ruta", 409
            ruta = r_repo.buscar_por_id(rp["id_ruta"])
            connection.commit()
            return {
                "duplicado": False,
                "ruta_punto": {"id": id_ruta_punto, "estado": "ATENDIDO", "fecha_atencion": fecha_final.isoformat()},
                "ruta": self._metricas(ruta),
            }, "Punto atendido", 201
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _metricas(ruta):
        return {
            "id": ruta["id"], "puntos_atendidos": ruta["puntos_atendidos"],
            "puntos_total": ruta["puntos_total"], "avance_porcentaje": ruta["avance_porcentaje"],
        }

    def _respuesta_replay(self, r_repo, existente):
        ruta = r_repo.buscar_por_id(existente["id_ruta"])
        return {
            "duplicado": True,
            "ruta_punto": {
                "id": existente["id"], "estado": existente["estado"],
                "fecha_atencion": existente["fecha_atencion"].isoformat() if existente["fecha_atencion"] else None,
            },
            "ruta": self._metricas(ruta),
        }
