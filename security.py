from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import Config

bearer_scheme = HTTPBearer(auto_error=False)


def crear_token(usuario: dict) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario["id"]),
        "nombre": usuario["nombre"],
        "rol": usuario["rol"],
        "iat": ahora,
        "exp": ahora + Config.JWT_ACCESS_TOKEN_EXPIRES,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def usuario_actual(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Dependencia: exige 'Authorization: Bearer <token>' y devuelve sus claims."""
    if cred is None:
        raise HTTPException(status_code=401, detail="Token requerido")
    try:
        payload = jwt.decode(
            cred.credentials, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"id": int(payload["sub"]), "nombre": payload["nombre"], "rol": payload["rol"]}
