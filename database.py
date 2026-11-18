import pymysql
import pymysql.cursors

from config import Config


def get_connection():
    conn_params = {
        "host": Config.MYSQL_HOST,
        "port": Config.MYSQL_PORT,
        "user": Config.MYSQL_USER,
        "password": Config.MYSQL_PASSWORD,
        "database": Config.MYSQL_DATABASE,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
        "init_command": "SET time_zone = '-05:00'",
    }

    if Config.MYSQL_HOST not in ["localhost", "127.0.0.1"]:
        conn_params.update(
            ssl={},
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )

    return pymysql.connect(**conn_params)
