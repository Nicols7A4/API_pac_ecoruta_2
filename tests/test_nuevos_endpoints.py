import pytest
import uuid
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_catalogo_puntos():
    login_res = client.post('/api/auth/login', json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'})
    token = login_res.json()['data']['token']
    headers = {'Authorization': f'Bearer {token}'}

    res = client.get('/api/puntos', headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body['status'] is True
    assert isinstance(body['data'], list)
    assert len(body['data']) >= 5


def test_filtrar_rutas_por_vehiculo():
    login_res = client.post(
        '/api/auth/login',
        json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'},
    )
    headers = {'Authorization': f"Bearer {login_res.json()['data']['token']}"}

    res = client.get('/api/rutas?id_vehiculo=1', headers=headers)
    assert res.status_code == 200
    rutas = res.json()['data']['rutas']
    assert rutas
    assert all(r['vehiculo']['id'] == 1 for r in rutas)


def test_crear_y_duplicar_ruta():
    login_res = client.post('/api/auth/login', json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'})
    token = login_res.json()['data']['token']
    headers = {'Authorization': f'Bearer {token}'}

    # 1. Crear ruta
    nueva = {
        'fecha': (date.today() + timedelta(days=1)).isoformat(),
        'turno': 'MANANA',
        'puntos_ids': [1, 2, 3]
    }
    res_crear = client.post('/api/rutas', json=nueva, headers=headers)
    assert res_crear.status_code == 201
    body_crear = res_crear.json()
    assert body_crear['status'] is True
    id_creada = body_crear['data']['id']

    # 2. Duplicar ruta
    res_dup = client.post(
        f'/api/rutas/{id_creada}/duplicar',
        json={
            'fecha': (date.today() + timedelta(days=2)).isoformat(),
            'turno': 'TARDE',
        },
        headers=headers,
    )
    assert res_dup.status_code == 201
    body_dup = res_dup.json()
    assert body_dup['status'] is True
    assert body_dup['data']['puntos_asignados'] == 3


def test_duplicar_ruta_reglas_validacion_y_origen_intacto():
    sup_login = client.post(
        '/api/auth/login',
        json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'},
    )
    sup_headers = {'Authorization': f"Bearer {sup_login.json()['data']['token']}"}

    op_login = client.post(
        '/api/auth/login',
        json={'correo': 'operario@ecoruta.pe', 'password': 'Operario123'},
    )
    op_headers = {'Authorization': f"Bearer {op_login.json()['data']['token']}"}

    sin_fecha = client.post('/api/rutas/2/duplicar', json={}, headers=sup_headers)
    assert sin_fecha.status_code == 400

    fecha_pasada = client.post(
        '/api/rutas/2/duplicar',
        json={'fecha': '2000-01-01'},
        headers=sup_headers,
    )
    assert fecha_pasada.status_code == 400

    no_encontrada = client.post(
        '/api/rutas/999999/duplicar',
        json={'fecha': (date.today() + timedelta(days=1)).isoformat()},
        headers=sup_headers,
    )
    assert no_encontrada.status_code == 404

    no_supervisor = client.post(
        '/api/rutas/2/duplicar',
        json={'fecha': (date.today() + timedelta(days=1)).isoformat()},
        headers=op_headers,
    )
    assert no_supervisor.status_code == 403

    origen_antes = client.get('/api/rutas/2', headers=sup_headers).json()['data']['ruta']
    fecha_nueva = (date.today() + timedelta(days=3)).isoformat()
    duplicada = client.post(
        '/api/rutas/2/duplicar',
        json={'fecha': fecha_nueva, 'turno': 'MANANA'},
        headers=sup_headers,
    )
    assert duplicada.status_code == 201
    nueva = duplicada.json()['data']
    assert nueva['estado'] == 'PROGRAMADA'
    assert nueva['fecha'] == fecha_nueva
    assert nueva['id_operario'] is None
    assert nueva['id_vehiculo'] is None

    puntos = client.get(f"/api/rutas/{nueva['id']}/puntos", headers=sup_headers).json()['data']
    puntos_lista = puntos if isinstance(puntos, list) else puntos.get('puntos', [])
    assert puntos_lista
    assert all(p['estado'] == 'PENDIENTE' for p in puntos_lista)

    historial = client.get(
        f"/api/rutas/{nueva['id']}/historial",
        headers=sup_headers,
    ).json()['data']
    registros = historial if isinstance(historial, list) else historial.get('historial', [])
    assert any(
        r['estado_anterior'] is None
        and r['estado_nuevo'] == 'PROGRAMADA'
        and r['comentario'] == 'Duplicada de RUT-002'
        for r in registros
    )

    origen_despues = client.get('/api/rutas/2', headers=sup_headers).json()['data']['ruta']
    assert origen_despues['codigo'] == origen_antes['codigo']
    assert origen_despues['estado'] == origen_antes['estado']


def test_supervisor_gestiona_incidencias():
    # 1. Login Operario
    op_login = client.post('/api/auth/login', json={'correo': 'operario@ecoruta.pe', 'password': 'Operario123'})
    op_token = op_login.json()['data']['token']
    op_headers = {'Authorization': f'Bearer {op_token}'}

    # 2. Reportar incidencia en ruta_punto 5 (perteneciente a ruta 2 que está EN_CURSO)
    inc_payload = {
        'uuid_operacion': str(uuid.uuid4()),
        'tipo': 'OBSTACULO_VIA',
        'descripcion': 'Contenedor bloqueado por vehículo mal estacionado',
        'es_critica': True,
    }
    res_inc = client.post('/api/ruta-puntos/5/incidencias', json=inc_payload, headers=op_headers)
    assert res_inc.status_code == 201
    inc_data = res_inc.json()['data']
    inc_id = inc_data['incidencia']['id']

    # 3. Login Supervisor
    sup_login = client.post('/api/auth/login', json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'})
    sup_token = sup_login.json()['data']['token']
    sup_headers = {'Authorization': f'Bearer {sup_token}'}

    # 4. Supervisor lista incidencias de la ruta 2
    res_list = client.get('/api/rutas/2/incidencias', headers=sup_headers)
    assert res_list.status_code == 200
    assert res_list.json()['status'] is True

    # 5. Supervisor cambia estado a EN_REVISION
    res_rev = client.put(
        f'/api/incidencias/{inc_id}/estado',
        json={'estado': 'EN_REVISION', 'observacion': 'Se envía personal de maestranza a verificar daño'},
        headers=sup_headers,
    )
    assert res_rev.status_code == 200
    assert res_rev.json()['data']['incidencia']['estado'] == 'EN_REVISION'

    # 6. Supervisor cambia estado a RESUELTA
    res_res = client.put(
        f'/api/incidencias/{inc_id}/estado',
        json={'estado': 'RESUELTA', 'observacion': 'Contenedor reemplazado satisfactoriamente'},
        headers=sup_headers,
    )
    assert res_res.status_code == 200
    assert res_res.json()['data']['incidencia']['estado'] == 'RESUELTA'


def test_reabrir_conserva_hora_fin_en_historial():
    sup_login = client.post(
        '/api/auth/login',
        json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'},
    )
    sup_headers = {'Authorization': f"Bearer {sup_login.json()['data']['token']}"}

    ruta = client.get('/api/rutas/4', headers=sup_headers).json()['data']['ruta']
    if ruta['estado'] not in ('FINALIZADA', 'OBSERVADA'):
        return

    hora_fin_antes = ruta.get('hora_fin')
    reabrir = client.post(
        '/api/rutas/4/reabrir',
        json={'comentario': 'Prueba de conservación en historial'},
        headers=sup_headers,
    )
    assert reabrir.status_code in (200, 409)

    if reabrir.status_code == 200:
        historial = client.get('/api/rutas/4/historial', headers=sup_headers).json()['data']['historial']
        reapertura = next(
            (h for h in historial if h['estado_nuevo'] == 'EN_CURSO'
             and h['comentario'] == 'Prueba de conservación en historial'),
            None,
        )
        assert reapertura is not None
        assert reapertura['vehiculo'] is not None
        assert reapertura['hora_fin'] == hora_fin_antes


def test_reasignar_reabrir_y_validada():
    sup_login = client.post(
        '/api/auth/login',
        json={'correo': 'supervisor@ecoruta.pe', 'password': 'Supervisor123'},
    )
    sup_headers = {'Authorization': f"Bearer {sup_login.json()['data']['token']}"}

    fisc_login = client.post(
        '/api/auth/login',
        json={'correo': 'fiscalizador@ecoruta.pe', 'password': 'Fiscal123'},
    )
    fisc_headers = {'Authorization': f"Bearer {fisc_login.json()['data']['token']}"}

    reasignar_curso = client.put(
        '/api/rutas/2/asignar',
        json={'id_operario': 2, 'id_vehiculo': 1},
        headers=sup_headers,
    )
    assert reasignar_curso.status_code == 409

    ruta1_antes = client.get('/api/rutas/1', headers=sup_headers).json()['data']['ruta']
    assert ruta1_antes['estado'] == 'FINALIZADA'

    validar = client.post(
        '/api/rutas/1/validar',
        json={'comentario': 'Evidencias conformes'},
        headers=fisc_headers,
    )
    assert validar.status_code in (200, 409)

    ruta1_validada = client.get('/api/rutas/1', headers=sup_headers).json()['data']['ruta']
    assert ruta1_validada['validada'] is True

    reabrir = client.post(
        '/api/rutas/4/reabrir',
        json={'comentario': 'Corregir evidencia omitida'},
        headers=sup_headers,
    )
    assert reabrir.status_code in (200, 409)

    ruta4_reabierta = client.get('/api/rutas/4', headers=sup_headers).json()['data']['ruta']
    if reabrir.status_code == 200:
        assert ruta4_reabierta['estado'] == 'EN_CURSO'
        assert ruta4_reabierta['validada'] is False

    conflicto_operario = client.post(
        '/api/rutas/1/reabrir',
        json={'comentario': 'Corregir punto omitido'},
        headers=sup_headers,
    )
    assert conflicto_operario.status_code == 409

    reabrir_sin_comentario = client.post(
        '/api/rutas/2/reabrir',
        json={'comentario': '   '},
        headers=sup_headers,
    )
    assert reabrir_sin_comentario.status_code in (400, 409)


def test_fiscalizador_restricciones():
    # 1. Login Fiscalizador
    fisc_login = client.post('/api/auth/login', json={'correo': 'fiscalizador@ecoruta.pe', 'password': 'Fiscal123'})
    fisc_token = fisc_login.json()['data']['token']
    fisc_headers = {'Authorization': f'Bearer {fisc_token}'}

    # 2. Fiscalizador NO puede iniciar ruta (403)
    res_iniciar = client.post('/api/rutas/1/iniciar', headers=fisc_headers)
    assert res_iniciar.status_code == 403

    # 3. Fiscalizador NO puede atender punto (403)
    res_atender = client.post('/api/ruta-puntos/1/atender', json={'latitud': -6.7, 'longitud': -79.8, 'codigo_qr': 'PTO-1'}, headers=fisc_headers)
    assert res_atender.status_code == 403
