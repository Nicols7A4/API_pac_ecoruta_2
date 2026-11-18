from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import Config
from database import get_connection
from repositories.usuario_repository import UsuarioRepository

bearer_scheme = HTTPBearer(auto_error=False)


def crear_token(usuario: dict) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario["id"]), "nombre": usuario["nombre"], "rol": usuario["rol"],
        "iat": ahora, "exp": ahora + Config.JWT_ACCESS_TOKEN_EXPIRES,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credenciales is None:
        raise HTTPException(status_code=401, detail="Token requerido")
    try:
        payload = jwt.decode(
            credenciales.credentials, Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
        )
        usuario_id = int(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expirado") from exc
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc

    connection = get_connection()
    try:
        usuario = UsuarioRepository(connection).buscar_por_id(usuario_id)
    finally:
        connection.close()
    if not usuario or not usuario.get("activo"):
        raise HTTPException(status_code=401, detail="Usuario inactivo o inexistente")
    if usuario["rol"] != payload.get("rol"):
        raise HTTPException(status_code=401, detail="La sesión ya no es válida")
    return {"id": usuario_id, "nombre": usuario["nombre"], "rol": usuario["rol"]}


def requerir_roles(*permitidos):
    def dependencia(usuario: dict = Depends(obtener_usuario_actual)):
        if usuario["rol"] not in permitidos:
            raise HTTPException(status_code=403, detail="No tiene permisos para esta operación")
        return usuario
    return dependencia
