from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    data: dict[str, Any] | None = None
    message: str
    status: bool


class LoginRequest(BaseModel):
    correo: str
    password: str