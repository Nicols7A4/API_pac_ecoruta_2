from unittest.mock import MagicMock

import pytest
from pymysql.err import OperationalError, ProgrammingError

from repositories.notificacion_repository import NotificacionRepository


def crear_repositorio():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [{"id": 1, "fcm_token": "token-prueba"}]
    return NotificacionRepository(connection), cursor


def test_listar_pendientes_usa_bloqueo_sin_join():
    repo, cursor = crear_repositorio()

    assert repo.listar_pendientes(10) == [{"id": 1, "fcm_token": "token-prueba"}]
    sql, parametros = cursor.execute.call_args.args
    assert "JOIN usuarios" not in sql
    assert "EXISTS" in sql
    assert " ".join(sql.split()).endswith("FOR UPDATE SKIP LOCKED")
    assert parametros == (10,)


def test_listar_pendientes_reintenta_sin_skip_locked_si_no_es_compatible():
    repo, cursor = crear_repositorio()
    cursor.execute.side_effect = [ProgrammingError(1064, "sintaxis"), None]

    repo.listar_pendientes()

    assert cursor.execute.call_count == 2
    assert "SKIP LOCKED" in cursor.execute.call_args_list[0].args[0]
    assert "SKIP LOCKED" not in cursor.execute.call_args_list[1].args[0]


def test_listar_pendientes_propagara_errores_no_relacionados_con_sintaxis():
    repo, cursor = crear_repositorio()
    cursor.execute.side_effect = OperationalError(1105, "error de base de datos")

    with pytest.raises(OperationalError):
        repo.listar_pendientes()

    assert cursor.execute.call_count == 1
