from datetime import datetime
from io import BytesIO

from geoalchemy2.elements import WKTElement

from app import app
from data.primeros_auxilios import obtener_guia
from models import (Clinica, Consulta, Evidencia, Mascota, RespuestaOrientacion,
                    Usuario, db)


def _registrar(client, email, nombre='Usuario Test', rol='dueno', cedula=None):
    datos = {
        'nombre': nombre,
        'email': email,
        'password': 'secreto123',
        'rol': rol,
    }
    if cedula is not None:
        datos['cedula_profesional'] = cedula
    return client.post('/registro', data=datos, follow_redirects=True)


def _login(client, email):
    return client.post(
        '/login',
        data={'email': email, 'password': 'secreto123'},
        follow_redirects=True,
    )


def _crear_mascota(client, nombre='Firulais'):
    return client.post(
        '/mascotas/nueva',
        data={'nombre': nombre, 'especie': 'Perro'},
        follow_redirects=True,
    )


def _id_mascota(email):
    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()
        mascota = (Mascota.query
                   .filter_by(usuario_id=usuario.id)
                   .order_by(Mascota.id.desc())
                   .first())
        return mascota.id


def _crear_consulta(client, mascota_id, sintomas):
    client.post(
        '/triaje/nueva',
        data={
            'mascota_id': str(mascota_id),
            'sintomas': sintomas,
            'acepta_terminos_triage': 'on',
        },
        follow_redirects=True,
    )
    with app.app_context():
        consulta = (Consulta.query
                    .filter_by(mascota_id=mascota_id)
                    .order_by(Consulta.id.desc())
                    .first())
        return consulta.id


def test_registro_login_y_triaje_urgente(client):
    _registrar(client, 'dueno1@test.local', nombre='Dueño Uno')
    _login(client, 'dueno1@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('dueno1@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Mi perro sangra mucho y convulsiona')

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta is not None
        assert consulta.nivel_urgencia == 'Urgente'

    html = client.get(f'/triaje/{consulta_id}').get_data(as_text=True)
    assert 'Actúa ahora' in html
    assert 'no sustituye' in html.lower()


def test_cedula_obligatoria_para_veterinario(client):
    _registrar(client, 'vetsin@test.local', nombre='Vet Sin', rol='veterinario')
    with app.app_context():
        assert Usuario.query.filter_by(email='vetsin@test.local').first() is None

    _registrar(
        client,
        'vetcon@test.local',
        nombre='Vet Con',
        rol='veterinario',
        cedula='123456',
    )
    with app.app_context():
        vet = Usuario.query.filter_by(email='vetcon@test.local').first()
        assert vet is not None
        assert vet.cedula_profesional == '123456'


def test_veterinario_responde_y_queda_asignado(client):
    _registrar(client, 'dueno2@test.local', nombre='Dueño Dos')
    _login(client, 'dueno2@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('dueno2@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Tiene fiebre y no come')

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta.estado == 'Pendiente'
        assert consulta.nivel_urgencia == 'Moderado'

    client.post('/logout')
    _registrar(
        client,
        'vet2@test.local',
        nombre='Vet Dos',
        rol='veterinario',
        cedula='VET-2',
    )
    _login(client, 'vet2@test.local')

    html = client.post(
        f'/triaje/{consulta_id}/respuesta',
        data={'mensaje': 'Llévalo a revisión hoy.'},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert 'Llévalo a revisión hoy.' in html
    assert 'Vet Dos' in html

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        vet = Usuario.query.filter_by(email='vet2@test.local').first()
        assert consulta.veterinario_id == vet.id
        assert consulta.estado == 'En Atención'
        assert RespuestaOrientacion.query.filter_by(consulta_id=consulta_id).count() == 1


def test_estado_cerrada_no_permite_reabrir_ni_responder(client):
    _registrar(client, 'dueno3@test.local', nombre='Dueño Tres')
    _login(client, 'dueno3@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('dueno3@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Cojera leve')

    client.post('/logout')
    _registrar(
        client,
        'vet3@test.local',
        nombre='Vet Tres',
        rol='veterinario',
        cedula='VET-3',
    )
    _login(client, 'vet3@test.local')

    client.post(
        f'/triaje/{consulta_id}/estado',
        data={'estado': 'Cerrada'},
        follow_redirects=True,
    )
    client.post(
        f'/triaje/{consulta_id}/estado',
        data={'estado': 'Pendiente'},
        follow_redirects=True,
    )
    client.post(
        f'/triaje/{consulta_id}/respuesta',
        data={'mensaje': 'Mensaje tardío'},
        follow_redirects=True,
    )
    client.post(
        f'/triaje/{consulta_id}/evidencia',
        data={'archivo': (BytesIO(b'x'), 'evidencia.png')},
        content_type='multipart/form-data',
        follow_redirects=True,
    )

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta.estado == 'Cerrada'
        assert RespuestaOrientacion.query.filter_by(consulta_id=consulta_id).count() == 0
        assert Evidencia.query.filter_by(consulta_id=consulta_id).count() == 0


def test_borrado_en_cascada(client):
    _registrar(
        client,
        'vet4@test.local',
        nombre='Vet Cuatro',
        rol='veterinario',
        cedula='VET-4',
    )
    _registrar(client, 'dueno4@test.local', nombre='Dueño Cuatro')
    _login(client, 'dueno4@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('dueno4@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Vomita')

    with app.app_context():
        vet = Usuario.query.filter_by(email='vet4@test.local').first()
        db.session.add(RespuestaOrientacion(
            consulta_id=consulta_id,
            veterinario_id=vet.id,
            mensaje='Respuesta de prueba.',
        ))
        db.session.add(Evidencia(
            consulta_id=consulta_id,
            ruta_archivo='uploads/no-existe.jpg',
            tipo='imagen',
        ))
        db.session.commit()

    client.post(f'/mascotas/{mascota_id}/eliminar', follow_redirects=True)

    with app.app_context():
        assert db.session.get(Mascota, mascota_id) is None
        assert db.session.get(Consulta, consulta_id) is None
        assert RespuestaOrientacion.query.filter_by(consulta_id=consulta_id).count() == 0
        assert Evidencia.query.filter_by(consulta_id=consulta_id).count() == 0


def test_mapa_devuelve_clinicas(client):
    with app.app_context():
        db.session.add(Clinica(
            nombre='Clínica Demo',
            direccion='Av. Demo 123',
            telefono='3312345678',
            coordenadas=WKTElement('POINT(-103.3475 20.6767)', srid=4326),
            abierto_24_7=True,
        ))
        db.session.commit()

    respuesta = client.get('/clinicas')
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert len(datos) == 1
    assert datos[0]['nombre'] == 'Clínica Demo'

    cercanas = client.get('/clinicas/cercanas?lat=20.6767&lng=-103.3475&radio=1000')
    assert cercanas.status_code == 200
    assert len(cercanas.get_json()) == 1
    assert cercanas.get_json()[0]['distancia_m'] < 10


def test_guias_de_primeros_auxilios():
    assert 'Vigila' in obtener_guia('Moderado')['titulo']
    assert 'Observación' in obtener_guia('Leve')['titulo']
    assert obtener_guia(None) == obtener_guia('Leve')


def test_hora_local_404_y_413(client):
    filtro = app.jinja_env.filters['local_time']
    assert filtro(datetime(2026, 1, 1, 12, 0)) == '2026-01-01 06:00'

    respuesta = client.get('/ruta-inexistente')
    assert respuesta.status_code == 404
    assert '404' in respuesta.get_data(as_text=True)

    respuesta_json = client.get('/clinicas/no-existe')
    assert respuesta_json.status_code == 404
    assert respuesta_json.is_json
    assert 'error' in respuesta_json.get_json()

    original = app.config['MAX_CONTENT_LENGTH']
    app.config['MAX_CONTENT_LENGTH'] = 10
    try:
        respuesta = client.post('/registro', data={'nombre': 'x' * 100})
        assert respuesta.status_code == 413
    finally:
        app.config['MAX_CONTENT_LENGTH'] = original
