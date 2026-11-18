from database import get_connection
from repositories.vehiculo_repository import VehiculoRepository


class VehiculoService:
    def listar_vehiculos(self, estado: str = "DISPONIBLE"):
        if estado is None:
            connection = get_connection()
            try:
                vehiculos = VehiculoRepository(connection).listar_todos()
                for v in vehiculos:
                    if v.get("capacidad") is not None:
                        v["capacidad"] = float(v["capacidad"])
                return {"vehiculos": vehiculos}, "Vehículos obtenidos", 200
            finally:
                connection.close()
        estados_validos = ["DISPONIBLE", "EN_USO", "MANTENIMIENTO"]
        if estado not in estados_validos:
            return (
                None,
                f"Estado fuera de catálogo. Valores permitidos: {', '.join(estados_validos)}",
                400,
            )

        connection = get_connection()
        try:
            repo = VehiculoRepository(connection)
            vehiculos = repo.listar_por_estado(estado)
            # Asegurar tipos flotantes para capacidad
            for v in vehiculos:
                if v.get("capacidad") is not None:
                    v["capacidad"] = float(v["capacidad"])
            return {"vehiculos": vehiculos}, "Vehículos obtenidos", 200
        finally:
            connection.close()
