import hashlib
import json
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import UUID

LIMA = ZoneInfo("America/Lima")


def uuid_v4(value):
    try:
        parsed = UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None
    return str(parsed) if parsed.version == 4 else None


def coordenadas(latitud, longitud):
    try:
        lat, lon = float(latitud), float(longitud)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return None
    return lat, lon


def fecha_iso(value):
    if not value:
        return datetime.now(LIMA).replace(tzinfo=None)
    try:
        fecha = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=LIMA)
        return fecha.astimezone(LIMA).replace(tzinfo=None)
    except ValueError:
        return None


def payload_hash(payload):
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def detectar_imagen(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None
