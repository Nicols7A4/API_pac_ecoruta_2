from datetime import datetime, date
from database import get_connection
from repositories.ruta_repository import RutaRepository
from repositories.punto_repository import PuntoRepository
from repositories.usuario_repository import UsuarioRepository
from repositories.vehiculo_repository import VehiculoRepository
from repositories.historial_repository import HistorialRepository
from repositories.notificacion_repository import NotificacionRepository
from repositories.revision_repository import RevisionRepository


class RutaService:
    def listar(
        self,
        usuario_id: int,
        rol: str,
        fecha: str = None,
        fecha_desde: str = None,
        fecha_hasta: str = None,
        estado: str = None,
        id_operario_filtro: int = None,
        id_vehiculo_filtro: int = None,
    ):
        # Estados válidos
        estados_validos = ["PROGRAMADA", "EN_CURSO", "FINALIZADA", "OBSERVADA"]
        if estado and estado not in estados_validos:
            return (
                None,
                f"Estado fuera del catálogo. Valores permitidos: {', '.join(estados_validos)}",
                400,
            )

        # Validar fechas
        for f, nombre in [(fecha, "fecha"), (fecha_desde, "fecha_desde"), (fecha_hasta, "fecha_hasta")]:
            if f:
                try:
                    datetime.strptime(f, "%Y-%m-%d")
                except ValueError:
                    return None, f"Parámetro {nombre} mal formado. Use YYYY-MM-DD", 400

        # Filtro de operario según rol
        id_operario_final = None
        if rol == "OPERARIO":
            id_operario_final = usuario_id
        else:
            id_operario_final = id_operario_filtro
        id_vehiculo_final = id_vehiculo_filtro if rol != "OPERARIO" else None

        # Sin filtros de fecha se devuelven todas las fechas. La app móvil
        # ofrece filtros por estado, pero no obliga a seleccionar una fecha;
        # así Supervisor y Fiscalizador también ven rutas futuras/programadas.
        fecha_consulta = fecha
        fecha_desde_c = fecha_desde
        fecha_hasta_c = fecha_hasta

        connection = get_connection()
        try:
            repo = RutaRepository(connection)
            rutas = repo.listar_rutas(
                id_operario=id_operario_final,
                fecha=fecha_consulta,
                fecha_desde=fecha_desde_c,
                fecha_hasta=fecha_hasta_c,
                estado=estado,
                id_vehiculo=id_vehiculo_final,
            )
            return {"rutas": rutas}, "Rutas obtenidas", 200
        finally:
            connection.close()

    def obtener_detalle(self, id_ruta: int, usuario_id: int, rol: str):
        connection = get_connection()
        try:
            repo = RutaRepository(connection)
            ruta = repo.buscar_por_id(id_ruta)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                return None, "No tiene permiso para consultar esta ruta", 403

            # Ocultar IDs internos y entregar formato limpio
            ruta_data = dict(ruta)
            ruta_data.pop("id_operario", None)
            ruta_data.pop("id_vehiculo", None)

            return {"ruta": ruta_data}, "Detalle de ruta obtenido", 200
        finally:
            connection.close()

    def obtener_puntos(self, id_ruta: int, usuario_id: int, rol: str):
        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            ruta = r_repo.buscar_por_id(id_ruta)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                return None, "No tiene permiso para consultar los puntos de esta ruta", 403

            p_repo = PuntoRepository(connection)
            puntos = p_repo.listar_puntos_por_ruta(id_ruta)
            return {"id_ruta": id_ruta, "puntos": puntos}, "Puntos obtenidos", 200
        finally:
            connection.close()

    def asignar(self, id_ruta: int, id_operario: int, id_vehiculo: int, supervisor_id: int):
        if not id_operario or not id_vehiculo:
            return None, "id_operario e id_vehiculo son obligatorios", 400

        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            u_repo = UsuarioRepository(connection)
            v_repo = VehiculoRepository(connection)
            h_repo = HistorialRepository(connection)
            n_repo = NotificacionRepository(connection)

            ruta = r_repo.buscar_por_id(id_ruta, for_update=True)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if ruta["estado"] != "PROGRAMADA":
                return None, f"La ruta no está en estado PROGRAMADA (estado actual: {ruta['estado']})", 409

            # Validar operario
            u_repo.bloquear_por_id(id_operario)
            operario = u_repo.buscar_por_id(id_operario)
            if not operario or not operario["activo"] or operario["rol"] != "OPERARIO":
                return None, "El usuario debe existir, estar activo y tener rol OPERARIO", 400

            # Validar vehículo
            v_repo.bloquear_por_id(id_vehiculo)
            vehiculo = v_repo.buscar_por_id(id_vehiculo)
            if not vehiculo or vehiculo["estado"] == "MANTENIMIENTO":
                return None, "El vehículo no existe o se encuentra en MANTENIMIENTO", 400

            # Validar choque de turno para operario y vehículo
            if u_repo.operario_tiene_ruta(id_operario, ruta["fecha"], ruta["turno"], excluir_id_ruta=id_ruta):
                return None, "El operario ya tiene otra ruta asignada en la misma fecha y turno", 409

            if v_repo.vehiculo_tiene_ruta(id_vehiculo, ruta["fecha"], ruta["turno"], excluir_id_ruta=id_ruta):
                return None, "El vehículo ya tiene otra ruta asignada en la misma fecha y turno", 409

            # Transacción
            r_repo.asignar_operario_y_vehiculo(id_ruta, id_operario, id_vehiculo)
            h_repo.registrar(
                id_ruta=id_ruta,
                estado_anterior="PROGRAMADA",
                estado_nuevo="PROGRAMADA",
                comentario="Asignación de operario y vehículo",
                id_usuario=supervisor_id,
            )
            n_repo.registrar(
                id_usuario=id_operario,
                id_ruta=id_ruta,
                tipo="RUTA_ASIGNADA",
                mensaje=f"Se le ha asignado la ruta {ruta['codigo']}",
            )

            connection.commit()

            data = {
                "ruta": {
                    "id": id_ruta,
                    "codigo": ruta["codigo"],
                    "estado": "PROGRAMADA",
                    "operario": {"id": operario["id"], "nombre": operario["nombre"]},
                    "vehiculo": {"id": vehiculo["id"], "placa": vehiculo["placa"]},
                }
            }
            return data, "Ruta asignada", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def iniciar(self, id_ruta: int, operario_id: int):
        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            v_repo = VehiculoRepository(connection)
            h_repo = HistorialRepository(connection)

            ruta = r_repo.buscar_por_id(id_ruta, for_update=True)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if ruta["id_operario"] != operario_id:
                return None, "La ruta no está asignada al operario autenticado", 403

            u_repo = UsuarioRepository(connection)
            u_repo.bloquear_por_id(operario_id)
            if ruta["id_vehiculo"]:
                v_repo.bloquear_por_id(ruta["id_vehiculo"])

            if ruta["estado"] == "EN_CURSO":
                return {
                    "ruta": {
                        "id": id_ruta,
                        "estado": "EN_CURSO",
                        "hora_inicio": ruta["hora_inicio"],
                    }
                }, "La ruta ya estaba iniciada", 200

            if ruta["estado"] != "PROGRAMADA":
                return None, f"La ruta debe estar en estado PROGRAMADA para iniciarla (estado actual: {ruta['estado']})", 409

            if r_repo.operario_tiene_ruta_en_curso(operario_id, excluir_id_ruta=id_ruta):
                return None, "El operario ya tiene otra ruta en curso", 409

            now = datetime.now()
            r_repo.iniciar_ruta(id_ruta, now)

            if ruta["id_vehiculo"]:
                v_repo.actualizar_estado(ruta["id_vehiculo"], "EN_USO")

            h_repo.registrar(
                id_ruta=id_ruta,
                estado_anterior="PROGRAMADA",
                estado_nuevo="EN_CURSO",
                comentario="Inicio de ruta",
                id_usuario=operario_id,
            )

            connection.commit()

            data = {
                "ruta": {
                    "id": id_ruta,
                    "estado": "EN_CURSO",
                    "hora_inicio": now.isoformat(),
                }
            }
            return data, "Ruta iniciada", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def finalizar(self, id_ruta: int, usuario_id: int, rol: str, comentario: str = None):
        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            p_repo = PuntoRepository(connection)
            v_repo = VehiculoRepository(connection)
            h_repo = HistorialRepository(connection)
            u_repo = UsuarioRepository(connection)
            n_repo = NotificacionRepository(connection)

            ruta = r_repo.buscar_por_id(id_ruta, for_update=True)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                return None, "No tiene permiso para finalizar una ruta asignada a otro operario", 403

            if ruta["id_operario"]:
                u_repo.bloquear_por_id(ruta["id_operario"])
            if ruta["id_vehiculo"]:
                v_repo.bloquear_por_id(ruta["id_vehiculo"])

            if ruta["estado"] != "EN_CURSO":
                return None, f"La ruta debe estar en estado EN_CURSO para finalizarla (estado actual: {ruta['estado']})", 409

            # Verificar si hay puntos PENDIENTES
            puntos_pendientes = p_repo.listar_puntos_pendientes_por_ruta(id_ruta)
            if puntos_pendientes:
                return (
                    {"puntos_pendientes": puntos_pendientes},
                    "Hay puntos sin atender ni justificar",
                    409,
                )

            now = datetime.now()
            r_repo.finalizar_ruta(id_ruta, now)

            if ruta["id_vehiculo"]:
                v_repo.actualizar_estado(ruta["id_vehiculo"], "DISPONIBLE")

            h_repo.registrar(
                id_ruta=id_ruta,
                estado_anterior="EN_CURSO",
                estado_nuevo="FINALIZADA",
                comentario=comentario or "Ruta finalizada",
                id_usuario=usuario_id,
            )

            supervisores = u_repo.obtener_supervisores_activos()
            n_repo.registrar_para_usuarios(
                supervisores,
                id_ruta,
                "RUTA_FINALIZADA",
                f"La ruta {ruta['codigo']} ha finalizado",
            )

            connection.commit()

            data = {
                "ruta": {
                    "id": id_ruta,
                    "estado": "FINALIZADA",
                    "hora_fin": now.isoformat(),
                }
            }
            return data, "Ruta finalizada", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def observar(self, id_ruta: int, fiscalizador_id: int, comentario: str):
        if not comentario or not str(comentario).strip():
            return None, "El comentario de observación es obligatorio", 400

        if len(str(comentario).strip()) > 255:
            return None, "El comentario no debe superar los 255 caracteres", 400

        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            h_repo = HistorialRepository(connection)
            u_repo = UsuarioRepository(connection)
            n_repo = NotificacionRepository(connection)

            ruta = r_repo.buscar_por_id(id_ruta, for_update=True)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if ruta["estado"] != "FINALIZADA":
                return None, f"Solo se pueden observar rutas en estado FINALIZADA (estado actual: {ruta['estado']})", 409

            comentario_limpio = str(comentario).strip()
            r_repo.cambiar_estado(id_ruta, "OBSERVADA")

            h_repo.registrar(
                id_ruta=id_ruta,
                estado_anterior="FINALIZADA",
                estado_nuevo="OBSERVADA",
                comentario=comentario_limpio,
                id_usuario=fiscalizador_id,
            )

            supervisores = u_repo.obtener_supervisores_activos()
            n_repo.registrar_para_usuarios(
                supervisores,
                id_ruta,
                "OBSERVACION",
                f"Ruta {ruta['codigo']} observada: {comentario_limpio}",
            )

            connection.commit()

            data = {
                "ruta": {
                    "id": id_ruta,
                    "estado": "OBSERVADA",
                }
            }
            return data, "Ruta observada", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def reabrir(self, id_ruta: int, supervisor_id: int, comentario: str):
        if not comentario or not str(comentario).strip():
            return None, "El comentario de reapertura es obligatorio", 400

        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            h_repo = HistorialRepository(connection)
            n_repo = NotificacionRepository(connection)
            v_repo = VehiculoRepository(connection)
            revision_repo = RevisionRepository(connection)

            ruta = r_repo.buscar_por_id(id_ruta, for_update=True)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if ruta["estado"] not in ["FINALIZADA", "OBSERVADA"]:
                return (
                    None,
                    f"Solo se pueden reabrir rutas en estado FINALIZADA u OBSERVADA (estado actual: {ruta['estado']})",
                    409,
                )

            if ruta["id_operario"]:
                UsuarioRepository(connection).bloquear_por_id(ruta["id_operario"])
            if ruta["id_vehiculo"]:
                v_repo.bloquear_por_id(ruta["id_vehiculo"])

            # Verificar si el operario asignado ya tiene otra ruta EN_CURSO
            if ruta["id_operario"] and r_repo.operario_tiene_ruta_en_curso(ruta["id_operario"], excluir_id_ruta=id_ruta):
                return None, "El operario asignado ya tiene otra ruta en curso actualmente", 409

            estado_anterior = ruta["estado"]
            r_repo.cambiar_estado(id_ruta, "EN_CURSO", limpiar_hora_fin=True)
            revision_repo.invalidar(id_ruta)

            if ruta["id_vehiculo"]:
                v_repo.actualizar_estado(ruta["id_vehiculo"], "EN_USO")

            comentario_limpio = str(comentario).strip()
            h_repo.registrar(
                id_ruta=id_ruta,
                estado_anterior=estado_anterior,
                estado_nuevo="EN_CURSO",
                comentario=comentario_limpio,
                id_usuario=supervisor_id,
                hora_fin=ruta["hora_fin"],
            )

            if ruta["id_operario"]:
                n_repo.registrar(
                    id_usuario=ruta["id_operario"],
                    id_ruta=id_ruta,
                    tipo="RUTA_ASIGNADA",
                    mensaje=f"La ruta {ruta['codigo']} ha sido reabierta",
                )

            connection.commit()

            data = {
                "ruta": {
                    "id": id_ruta,
                    "estado": "EN_CURSO",
                }
            }
            return data, "Ruta reabierta", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def validar_conforme(self, id_ruta: int, fiscalizador_id: int, comentario: str = None):
        comentario = str(comentario or "Ruta validada conforme").strip()
        if len(comentario) > 255:
            return None, "El comentario no debe superar los 255 caracteres", 400
        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            ruta = r_repo.buscar_por_id(id_ruta, for_update=True)
            if not ruta:
                return None, "Ruta no encontrada", 404
            if ruta["estado"] != "FINALIZADA":
                return None, "Solo se validan rutas en estado FINALIZADA", 409
            revision_repo = RevisionRepository(connection)
            if revision_repo.vigente(id_ruta):
                return None, "La ruta ya cuenta con una validación vigente", 409
            validacion_id = revision_repo.registrar_conforme(id_ruta, fiscalizador_id, comentario)
            HistorialRepository(connection).registrar(
                id_ruta=id_ruta, estado_anterior="FINALIZADA", estado_nuevo="FINALIZADA",
                comentario=f"VALIDADA_CONFORME: {comentario}", id_usuario=fiscalizador_id,
            )
            connection.commit()
            return {"validacion": {
                "id": validacion_id, "id_ruta": id_ruta, "resultado": "CONFORME",
                "comentario": comentario, "vigente": True,
            }, "ruta": {"id": id_ruta, "estado": "FINALIZADA"}}, "Ruta validada conforme", 200
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def obtener_historial(self, id_ruta: int, usuario_id: int, rol: str):
        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            ruta = r_repo.buscar_por_id(id_ruta)
            if not ruta:
                return None, "Ruta no encontrada", 404

            if rol == "OPERARIO" and ruta["id_operario"] != usuario_id:
                return None, "No tiene permiso para consultar el historial de esta ruta", 403

            h_repo = HistorialRepository(connection)
            historial = h_repo.listar_por_ruta(id_ruta)
            return {"historial": historial}, "Historial obtenido", 200
        finally:
            connection.close()

    def crear_ruta(
        self,
        supervisor_id: int,
        fecha: str,
        turno: str,
        codigo: str = None,
        id_operario: int = None,
        id_vehiculo: int = None,
        puntos_ids: list = None,
        comentario_historial: str = "Creación de ruta",
        estado_anterior_historial: str = "PROGRAMADA",
    ):
        turnos_validos = ["MANANA", "TARDE", "NOCHE"]
        if turno not in turnos_validos:
            return None, f"Turno inválido. Valores permitidos: {', '.join(turnos_validos)}", 400

        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return None, "Parámetro fecha mal formado. Use YYYY-MM-DD", 400

        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            u_repo = UsuarioRepository(connection)
            v_repo = VehiculoRepository(connection)
            h_repo = HistorialRepository(connection)
            n_repo = NotificacionRepository(connection)

            if not codigo:
                codigo = r_repo.generar_siguiente_codigo()

            operario = None
            if id_operario:
                u_repo.bloquear_por_id(id_operario)
                operario = u_repo.buscar_por_id(id_operario)
                if not operario or not operario["activo"] or operario["rol"] != "OPERARIO":
                    return None, "El usuario asignado debe existir, estar activo y tener rol OPERARIO", 400
                if u_repo.operario_tiene_ruta(id_operario, fecha, turno):
                    return None, "El operario ya tiene otra ruta asignada en la misma fecha y turno", 409

            vehiculo = None
            if id_vehiculo:
                v_repo.bloquear_por_id(id_vehiculo)
                vehiculo = v_repo.buscar_por_id(id_vehiculo)
                if not vehiculo or vehiculo["estado"] == "MANTENIMIENTO":
                    return None, "El vehículo no existe o se encuentra en MANTENIMIENTO", 400
                if v_repo.vehiculo_tiene_ruta(id_vehiculo, fecha, turno):
                    return None, "El vehículo ya tiene otra ruta asignada en la misma fecha y turno", 409

            id_ruta = r_repo.crear_ruta(
                codigo=codigo,
                fecha=fecha,
                turno=turno,
                id_operario=id_operario,
                id_vehiculo=id_vehiculo,
                estado="PROGRAMADA",
            )

            puntos_insertados = 0
            if puntos_ids and isinstance(puntos_ids, list):
                for posicion, punto in enumerate(puntos_ids, start=1):
                    if isinstance(punto, dict):
                        id_punto = punto["id_punto"]
                        orden = punto["orden"]
                    else:
                        id_punto = punto
                        orden = posicion
                    r_repo.asociar_punto(id_ruta, id_punto, orden)
                    puntos_insertados += 1

            h_repo.registrar(
                id_ruta=id_ruta,
                estado_anterior=estado_anterior_historial,
                estado_nuevo="PROGRAMADA",
                comentario=comentario_historial,
                id_usuario=supervisor_id,
            )

            if id_operario:
                n_repo.registrar(
                    id_usuario=id_operario,
                    id_ruta=id_ruta,
                    tipo="RUTA_ASIGNADA",
                    mensaje=f"Se le ha asignado la nueva ruta {codigo}",
                )

            connection.commit()

            data = {
                "id": id_ruta,
                "codigo": codigo,
                "fecha": fecha,
                "turno": turno,
                "estado": "PROGRAMADA",
                "id_operario": id_operario,
                "id_vehiculo": id_vehiculo,
                "puntos_asignados": puntos_insertados,
            }
            return data, "Ruta creada con éxito", 201
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def duplicar_ruta(
        self,
        id_ruta_origen: int,
        supervisor_id: int,
        fecha: str = None,
        turno: str = None,
        id_operario: int = None,
        id_vehiculo: int = None,
    ):
        if not fecha or not str(fecha).strip():
            return None, "El campo fecha es obligatorio para reprogramar la ruta", 400

        fecha = str(fecha).strip()
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            return None, "Parámetro fecha mal formado. Use YYYY-MM-DD", 400

        if fecha_obj < date.today():
            return None, "La fecha de reprogramación no puede ser anterior a hoy", 400

        connection = get_connection()
        try:
            r_repo = RutaRepository(connection)
            p_repo = PuntoRepository(connection)

            ruta_origen = r_repo.buscar_por_id(id_ruta_origen)
            if not ruta_origen:
                return None, "Ruta de origen no encontrada", 404

            puntos_activos = p_repo.listar_puntos_activos_por_ruta(id_ruta_origen)
            if not puntos_activos:
                return None, "La ruta origen no tiene puntos activos para duplicar", 409

            puntos_ids = [
                {"id_punto": p["id_punto"], "orden": p["orden"]}
                for p in puntos_activos
            ]

            fecha_final = fecha
            turno_final = turno or ruta_origen["turno"]
            if turno_final not in ["MANANA", "TARDE", "NOCHE"]:
                return None, "Turno inválido. Valores permitidos: MANANA, TARDE, NOCHE", 400

            nuevo_codigo = r_repo.generar_siguiente_codigo()
        finally:
            connection.close()

        return self.crear_ruta(
            supervisor_id=supervisor_id,
            fecha=fecha_final,
            turno=turno_final,
            codigo=nuevo_codigo,
            id_operario=id_operario,
            id_vehiculo=id_vehiculo,
            puntos_ids=puntos_ids,
            comentario_historial=f"Duplicada de {ruta_origen['codigo']}",
            estado_anterior_historial=None,
        )
