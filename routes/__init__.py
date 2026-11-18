from routes.auth_routes import auth_router
from routes.incidencia_routes import evidencia_router, incidencia_router
from routes.prueba_routes import prueba_router
from routes.punto_routes import punto_router
from routes.ruta_routes import ruta_router
from routes.supervision_routes import supervision_router
from routes.usuario_routes import usuario_router
from routes.vehiculo_routes import vehiculo_router

routers = (
    auth_router, usuario_router, ruta_router, punto_router, incidencia_router,
    evidencia_router, supervision_router, vehiculo_router, prueba_router,
)

__all__ = ["routers"]
