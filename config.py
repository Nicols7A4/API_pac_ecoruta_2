import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    
    if os.getenv("USE_LOCAL", "false").lower() == "true":
        MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
        MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
        MYSQL_USER = os.getenv("MYSQL_USER", "root")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pac_ecoruta")
    else:
        MYSQL_HOST = os.getenv("CLOUD_MYSQL_HOST", "localhost")
        MYSQL_PORT = int(os.getenv("CLOUD_MYSQL_PORT", "3306"))
        MYSQL_USER = os.getenv("CLOUD_MYSQL_USER", "root")
        MYSQL_PASSWORD = os.getenv("CLOUD_MYSQL_PASSWORD", "")
        MYSQL_DATABASE = os.getenv("CLOUD_MYSQL_DATABASE", "pac_ecoruta")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CAMBIAR_EN_DESARROLLO_LOCAL")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256") 
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    UPLOAD_DIR = os.getenv("UPLOAD_DIR") or os.path.join(BASE_DIR, "uploads")
    MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES + 256 * 1024
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
    ALLOW_DEV_MODE = os.getenv("ALLOW_DEV_MODE", "false").lower() == "true"
    FCM_ENABLED = os.getenv("FCM_ENABLED", "false").lower() == "true"
    FCM_DRY_RUN = os.getenv("FCM_DRY_RUN", "false").lower() == "true"
