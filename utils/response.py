from datetime import date, datetime
from decimal import Decimal

from fastapi.responses import JSONResponse


def clean_data(value):
    if isinstance(value, dict):
        return {key: clean_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_data(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def success_response(data=None, message="Operación exitosa", http_code=200):
    return JSONResponse(
        status_code=http_code,
        content={"status": http_code < 400, "message": message, "data": clean_data(data)},
    )


def error_response(message="Ha ocurrido un error", http_code=400, data=None):
    return JSONResponse(
        status_code=http_code,
        content={"status": False, "message": message, "data": clean_data(data)},
    )
