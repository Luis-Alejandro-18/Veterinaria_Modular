import re
from datetime import datetime
from io import BytesIO

from geoalchemy2.elements import WKTElement

from app import app
from data.primeros_auxilios import obtener_guia
from models import (Clinica, Consulta, Evidencia, Mascota, MensajeConsulta,
                    RespuestaOrientacion, Usuario, db)


def _registrar(client, email, nombre='Usuario Test', rol='dueno', cedula=None):
    datos = {
        'nombre': nombre,
        'email': email,
        'password': 'secreto123',
    }
    if cedula is not None:
        datos['cedula_profesional'] = cedula
    ruta = '/registro/veterinario' if rol == 'veterinario' else '/registro/dueno'
    return client.post(ruta, data=datos, follow_redirects=True)


def _login(client, email):
    return client.post(
        '/login',
        data={'email': email, 'password': 'secreto123'},
        follow_redirects=True,
    )


def _crear_mascota(client, nombre='Firulais', especie='Perro'):
    return client.post(
        '/mascotas/nueva',
        data={'nombre': nombre, 'especie': especie},
        follow_redirects=True,
    )


def _crear_mascota_con_next(client, nombre='Firulais', especie='Perro', next_url='triaje'):
    return client.post(
        '/mascotas/nueva',
        data={'nombre': nombre, 'especie': especie, 'next': next_url},
        follow_redirects=False,
    )


def _id_mascota(email):
    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()
        mascota = (Mascota.query
                   .filter_by(usuario_id=usuario.id)
                   .order_by(Mascota.id.desc())
                   .first())
        return mascota.id


def _crear_consulta(client, mascota_id, sintomas, solicitar=True):
    client.post(
        '/triaje/nueva',
        data={
            'mascota_id': str(mascota_id),
            'motivo': sintomas,
            'acepta_terminos_triage': 'on',
        },
        follow_redirects=True,
    )
    with app.app_context():
        consulta = (Consulta.query
                    .filter_by(mascota_id=mascota_id)
                    .order_by(Consulta.id.desc())
                    .first())
    if solicitar:
        client.post(
            f'/triaje/{consulta.id}/solicitar',
            follow_redirects=True,
        )
    return consulta.id


def _csrf_token(html):
    coincidencia = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert coincidencia is not None
    return coincidencia.group(1)


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
        respuesta = client.post('/registro/dueno', data={'nombre': 'x' * 100})
        assert respuesta.status_code == 413
    finally:
        app.config['MAX_CONTENT_LENGTH'] = original


def test_csrf_protege_formularios(client_csrf):
    html = client_csrf.get('/registro/dueno').get_data(as_text=True)
    token = _csrf_token(html)
    datos = {
        'nombre': 'CSRF Test',
        'email': 'csrf@test.local',
        'password': 'secreto123',
    }

    sin_token = client_csrf.post('/registro/dueno', data=datos)
    assert sin_token.status_code == 400
    assert 'Solicitud inválida' in sin_token.get_data(as_text=True)

    token = _csrf_token(client_csrf.get('/registro/dueno').get_data(as_text=True))
    con_token = client_csrf.post(
        '/registro/dueno',
        data={**datos, 'csrf_token': token},
        follow_redirects=True,
    )
    assert con_token.status_code == 200
    assert 'Registro exitoso' in con_token.get_data(as_text=True)


def test_evidencia_privada(client, uploads_temporales):
    _registrar(client, 'dueno5@test.local', nombre='Dueño Cinco')
    _login(client, 'dueno5@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('dueno5@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Revisión general')

    archivo = uploads_temporales / 'prueba.png'
    archivo.write_bytes(b'contenido-privado')
    with app.app_context():
        evidencia = Evidencia(
            consulta_id=consulta_id,
            ruta_archivo='uploads/prueba.png',
            tipo='imagen',
        )
        db.session.add(evidencia)
        db.session.commit()
        evidencia_id = evidencia.id

    html = client.get(f'/triaje/{consulta_id}').get_data(as_text=True)
    assert f'/triaje/evidencia/{evidencia_id}' in html

    respuesta = client.get(f'/triaje/evidencia/{evidencia_id}')
    assert respuesta.status_code == 200
    assert respuesta.data == b'contenido-privado'
    assert respuesta.headers['Cache-Control'] == 'private, no-store'
    assert respuesta.headers['X-Content-Type-Options'] == 'nosniff'

    client.post('/logout')
    _registrar(client, 'otro5@test.local', nombre='Otro Cinco')
    _login(client, 'otro5@test.local')
    assert client.get(f'/triaje/evidencia/{evidencia_id}').status_code == 404

    client.post('/logout')
    _registrar(
        client,
        'vet5@test.local',
        nombre='Vet Cinco',
        rol='veterinario',
        cedula='VET-5',
    )
    _login(client, 'vet5@test.local')
    assert client.get(f'/triaje/evidencia/{evidencia_id}').status_code == 200


def test_static_uploads_bloqueado(client):
    assert client.get('/static/uploads/prueba.png').status_code == 404


def test_filtros_y_paginacion_mascotas(client):
    _registrar(client, 'dueno6@test.local', nombre='Dueño Seis')
    _login(client, 'dueno6@test.local')
    for i in range(12):
        especie = 'Gato' if i % 2 else 'Perro'
        _crear_mascota(client, f'Mascota {i:02d}', especie)

    html = client.get('/mascotas/', query_string={'page': 2}).get_data(as_text=True)
    assert 'Página 2 de 2' in html
    assert 'Mascota 10' in html
    assert 'Mascota 11' in html
    assert 'Mascota 00' not in html

    html = client.get(
        '/mascotas/',
        query_string={'q': 'Mascota 03'},
    ).get_data(as_text=True)
    assert 'Mascota 03' in html
    assert 'Mascota 04' not in html

    html = client.get(
        '/mascotas/',
        query_string={'especie': 'Gato'},
    ).get_data(as_text=True)
    assert 'Mascota 01' in html
    assert 'Mascota 00' not in html


def test_filtros_y_paginacion_triaje(client):
    _registrar(client, 'dueno7@test.local', nombre='Dueño Siete')
    _login(client, 'dueno7@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('dueno7@test.local')

    ids = []
    for i in range(12):
        sintomas = f'consulta numero {i:02d}'
        if i == 0:
            sintomas += ' sangra'
        ids.append(_crear_consulta(client, mascota_id, sintomas))

    html = client.get('/triaje/', query_string={'page': 2}).get_data(as_text=True)
    assert 'Página 2 de 2' in html
    assert 'consulta numero 00' in html
    assert 'consulta numero 01' in html
    assert 'consulta numero 11' not in html

    html = client.get(
        '/triaje/',
        query_string={'urgencia': 'Urgente'},
    ).get_data(as_text=True)
    assert 'consulta numero 00' in html
    assert 'consulta numero 01' not in html

    html = client.get(
        '/triaje/',
        query_string={'q': 'numero 03'},
    ).get_data(as_text=True)
    assert 'consulta numero 03' in html
    assert 'consulta numero 04' not in html

    with app.app_context():
        consulta = db.session.get(Consulta, ids[3])
        consulta.estado = 'Cerrada'
        db.session.commit()

    html = client.get(
        '/triaje/',
        query_string={'estado': 'Cerrada'},
    ).get_data(as_text=True)
    assert 'consulta numero 03' in html
    assert 'consulta numero 04' not in html

def test_login_veterinario_redirige_al_panel(client):
    _registrar(
        client,
        'vet-panel@test.local',
        nombre='Dra. Panel',
        rol='veterinario',
        cedula='VET-PANEL',
    )

    html = client.post(
        '/login',
        data={
            'email': 'vet-panel@test.local',
            'password': 'secreto123',
            'perfil': 'veterinario',
            'mantener_sesion': 'on',
        },
        follow_redirects=True,
    ).get_data(as_text=True)

    assert 'Solicitudes' in html
    assert 'Dra. Panel' in html
    assert 'Agenda de seguimiento' in html


def test_login_veterinario_rechaza_dueno(client):
    _registrar(client, 'dueno-login-vet@test.local', nombre='Dueño Login')

    html = client.post(
        '/login',
        data={
            'email': 'dueno-login-vet@test.local',
            'password': 'secreto123',
            'perfil': 'veterinario',
        },
        follow_redirects=True,
    ).get_data(as_text=True)

    assert 'exclusivo para veterinarios' in html
    assert 'Iniciar sesión' in html


def test_dueno_no_accede_al_panel_veterinario(client):
    _registrar(client, 'dueno-sin-panel@test.local', nombre='Dueño Sin Panel')
    _login(client, 'dueno-sin-panel@test.local')

    html = client.get('/veterinario/bandeja', follow_redirects=True).get_data(as_text=True)
    assert 'Solo los veterinarios pueden realizar esta acción.' in html


def test_flujo_completo_del_panel_veterinario(client):
    _registrar(client, 'dueno-panel@test.local', nombre='Dueño Panel')
    _login(client, 'dueno-panel@test.local')
    _crear_mascota(client, 'Nube', 'Gato')
    mascota_id = _id_mascota('dueno-panel@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Vomita y no come')

    client.post(
        f'/triaje/{consulta_id}/chat',
        data={'mensaje': 'Hola, sigue vomitando.'},
        follow_redirects=True,
    )
    client.post('/logout')

    _registrar(
        client,
        'vet-flujo@test.local',
        nombre='Dra. Flujo',
        rol='veterinario',
        cedula='VET-FLUJO',
    )
    _login(client, 'vet-flujo@test.local')

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert 'Solicitudes' in bandeja
    assert 'Nube' in bandeja
    assert 'Tomar caso' in bandeja

    caso_html = client.post(
        f'/veterinario/casos/{consulta_id}/tomar',
        follow_redirects=True,
    ).get_data(as_text=True)
    assert 'Caso #' in caso_html
    assert 'Diagnóstico y respuesta' in caso_html
    assert 'Dra. Flujo' in caso_html

    assert 'Nube' in client.get('/veterinario/tablero').get_data(as_text=True)
    assert 'Nube' in client.get('/veterinario/agenda').get_data(as_text=True)

    mensajes = client.get('/veterinario/mensajes').get_data(as_text=True)
    assert 'Hola, sigue vomitando.' in mensajes

    conversacion = client.get(
        f'/veterinario/mensajes?consulta_id={consulta_id}'
    ).get_data(as_text=True)
    assert 'Hola, sigue vomitando.' in conversacion

    with app.app_context():
        mensaje = MensajeConsulta.query.filter_by(consulta_id=consulta_id).first()
        assert mensaje.leido is True

    client.post(
        f'/veterinario/casos/{consulta_id}/chat',
        data={'mensaje': 'Gracias, revisa si bebe agua.', 'volver': 'chat'},
        follow_redirects=True,
    )

    with app.app_context():
        assert MensajeConsulta.query.filter_by(consulta_id=consulta_id).count() == 2

    html = client.post(
        f'/veterinario/casos/{consulta_id}/respuesta',
        data={
            'diagnostico': 'Cuadro compatible con gastroenteritis.',
            'recomendaciones': 'Mantén hidratación y vigila señales de alarma.',
            'requiere_presencial': 'on',
        },
        follow_redirects=True,
    ).get_data(as_text=True)

    assert 'Diagnóstico enviado al dueño.' in html
    assert 'Cuadro compatible con gastroenteritis.' in html

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta.estado == 'Requiere Presencial'
        respuesta = RespuestaOrientacion.query.filter_by(consulta_id=consulta_id).one()
        assert 'Diagnóstico:' in respuesta.mensaje
        assert 'Recomendaciones:' in respuesta.mensaje

    client.post('/logout')
    _login(client, 'dueno-panel@test.local')
    detalle = client.get(f'/triaje/{consulta_id}').get_data(as_text=True)
    assert 'Cuadro compatible con gastroenteritis.' in detalle
    assert 'Mantén hidratación' in detalle
    assert 'Requiere Presencial' in detalle


def test_otro_veterinario_no_puede_responder_caso_asignado(client):
    _registrar(client, 'dueno-asignado@test.local', nombre='Dueño Asignado')
    _login(client, 'dueno-asignado@test.local')
    _crear_mascota(client, 'Toby', 'Perro')
    mascota_id = _id_mascota('dueno-asignado@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Cojea de la pata')
    client.post('/logout')

    _registrar(
        client,
        'vet-asignado@test.local',
        nombre='Vet Asignado',
        rol='veterinario',
        cedula='VET-A',
    )
    _login(client, 'vet-asignado@test.local')
    client.post(f'/veterinario/casos/{consulta_id}/tomar', follow_redirects=True)

    with app.app_context():
        vet_asignado = Usuario.query.filter_by(email='vet-asignado@test.local').first()
        vet_id = vet_asignado.id

    client.post('/logout')
    _registrar(
        client,
        'vet-otro@test.local',
        nombre='Vet Otro',
        rol='veterinario',
        cedula='VET-B',
    )
    _login(client, 'vet-otro@test.local')

    html = client.post(
        f'/veterinario/casos/{consulta_id}/respuesta',
        data={'diagnostico': 'No debería guardarse.'},
        follow_redirects=True,
    ).get_data(as_text=True)

    assert 'asignado a otro veterinario' in html

    with app.app_context():
        assert RespuestaOrientacion.query.filter_by(consulta_id=consulta_id).count() == 0
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta.veterinario_id == vet_id


def test_login_veterinario_requiere_csrf(client_csrf):
    html = client_csrf.get('/login?perfil=veterinario').get_data(as_text=True)
    assert 'name="csrf_token"' in html

    respuesta = client_csrf.post(
        '/login',
        data={
            'email': 'nadie@test.local',
            'password': 'x',
            'perfil': 'veterinario',
        },
    )
    assert respuesta.status_code == 400


def test_triaje_sin_mascotas_redirige_a_registro(client):
    _registrar(client, 'sin-mascotas@test.local', nombre='Sin Mascotas')
    _login(client, 'sin-mascotas@test.local')

    respuesta = client.get('/triaje/nueva', follow_redirects=False)
    assert respuesta.status_code == 302
    assert '/mascotas/nueva?next=triaje' in respuesta.headers['Location']


def test_crear_mascota_con_next_vuelve_al_triaje_con_preseleccion(client):
    _registrar(client, 'con-next@test.local', nombre='Con Next')
    _login(client, 'con-next@test.local')

    respuesta = _crear_mascota_con_next(client, 'Luna', 'Gato', 'triaje')
    assert '/triaje/nueva?mascota_id=' in respuesta.headers['Location']

    mascota_id = _id_mascota('con-next@test.local')
    assert f'/triaje/nueva?mascota_id={mascota_id}' in respuesta.headers['Location']

    html = client.get(f'/triaje/nueva?mascota_id={mascota_id}').get_data(as_text=True)
    assert f'value="{mascota_id}" selected' in html or f'value="{mascota_id}"\n              selected' in html


def test_flujo_sin_mascotas_registro_y_triaje_completo(client):
    _registrar(client, 'flujo-completo@test.local', nombre='Flujo Completo')
    _login(client, 'flujo-completo@test.local')

    # 1. Intenta hacer triaje sin mascotas → redirige a registrar mascota.
    respuesta = client.get('/triaje/nueva', follow_redirects=False)
    assert '/mascotas/nueva?next=triaje' in respuesta.headers['Location']

    # 2. Registra la mascota con next=triaje → vuelve al triaje preseleccionada.
    respuesta = _crear_mascota_con_next(client, 'Nube', 'Gato', 'triaje')
    mascota_id = _id_mascota('flujo-completo@test.local')
    assert f'/triaje/nueva?mascota_id={mascota_id}' in respuesta.headers['Location']

    # 3. Crea la consulta desde el triaje con la mascota ya seleccionada.
    _crear_consulta(client, mascota_id, 'Tos y no come')

    with app.app_context():
        consulta = (Consulta.query
                    .filter_by(mascota_id=mascota_id)
                    .order_by(Consulta.id.desc())
                    .first())
        assert consulta is not None
        assert consulta.nivel_urgencia == 'Moderado'


def test_next_invalido_no_redirige_fuera_del_sitio(client):
    _registrar(client, 'next-invalido@test.local', nombre='Next Invalido')
    _login(client, 'next-invalido@test.local')

    respuesta = client.get(
        '/mascotas/nueva',
        query_string={'next': 'https://sitio-malicioso.com/robar-datos'},
        follow_redirects=True,
    ).get_data(as_text=True)

    # Nunca redirige fuera del sitio; va a mascotas/nueva sin next o al listado.
    assert 'sitio-malicioso.com' not in respuesta
    assert 'Registro exitoso' not in respuesta


def test_consulta_nace_sin_solicitar(client):
    _registrar(client, 'nosolicitar1@test.local', nombre='No Solicitar Uno')
    _login(client, 'nosolicitar1@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('nosolicitar1@test.local')

    _crear_consulta(client, mascota_id, 'Tos leve', solicitar=False)

    with app.app_context():
        consulta = (Consulta.query
                    .filter_by(mascota_id=mascota_id)
                    .order_by(Consulta.id.desc())
                    .first())
        assert consulta.estado == 'Sin solicitar'
        assert consulta.nivel_urgencia == 'Moderado'

    html = client.get(f'/triaje/{consulta.id}').get_data(as_text=True)
    assert 'Moderado' in html
    assert 'Solicitar asistencia con un doctor' in html
    assert 'Evidencias' not in html
    assert 'Respuestas del veterinario' not in html
    assert 'Chat de seguimiento' not in html


def test_veterinario_no_ve_consulta_sin_solicitar(client):
    _registrar(client, 'nosolicitar2@test.local', nombre='No Solicitar Dos')
    _login(client, 'nosolicitar2@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('nosolicitar2@test.local')
    _crear_consulta(client, mascota_id, 'Vómito repetido', solicitar=False)

    client.post('/logout')
    _registrar(
        client,
        'vetnosol@test.local',
        nombre='Vet No Sol',
        rol='veterinario',
        cedula='VET-NS',
    )
    _login(client, 'vetnosol@test.local')

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert 'No hay solicitudes que coincidan con este filtro.' in bandeja

    # Intenta abrir el caso directamente: no debe verlo.
    with app.app_context():
        consulta_id = (Consulta.query
                       .filter_by(mascota_id=mascota_id)
                       .order_by(Consulta.id.desc())
                       .first().id)
    html = client.get(f'/triaje/{consulta_id}', follow_redirects=True).get_data(as_text=True)
    assert 'aún no ha sido enviado' in html or 'No tienes permiso' in html

    # Intenta tomarlo: no debe estar disponible.
    respuesta = client.post(
        f'/veterinario/casos/{consulta_id}/tomar',
        follow_redirects=True,
    ).get_data(as_text=True)
    assert 'ya no está disponible' in respuesta or 'No tienes permiso' in respuesta


def test_solicitar_asistencia_pasa_a_pendiente_y_se_habilitan_secciones(client):
    _registrar(client, 'solicitar1@test.local', nombre='Solicitar Uno')
    _login(client, 'solicitar1@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('solicitar1@test.local')
    _crear_consulta(client, mascota_id, 'Fiebre y tos', solicitar=False)

    with app.app_context():
        consulta_id = (Consulta.query
                       .filter_by(mascota_id=mascota_id)
                       .order_by(Consulta.id.desc())
                       .first().id)

    client.post(f'/triaje/{consulta_id}/solicitar', follow_redirects=True)

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta.estado == 'Pendiente'

    html = client.get(f'/triaje/{consulta_id}').get_data(as_text=True)
    assert 'Evidencias' in html
    assert 'Respuestas del veterinario' in html
    assert 'Chat de seguimiento' in html
    assert 'Solicitar asistencia con un doctor' not in html


def test_otro_dueno_no_puede_solicitar_asistencia_ajena(client):
    with app.app_context():
        from werkzeug.security import generate_password_hash
        usuario_a = Usuario(
            nombre='Dueño A',
            email='duenoA@test.local',
            password_hash=generate_password_hash('secreto123'),
            rol='dueno',
        )
        db.session.add(usuario_a)
        db.session.commit()
        mascota = Mascota(usuario_id=usuario_a.id, nombre='Firulais', especie='Perro')
        db.session.add(mascota)
        db.session.commit()
        mascota_id_a = mascota.id
        consulta = Consulta(
            mascota_id=mascota_id_a,
            sintomas='Motivo: Tos',
            nivel_urgencia='Moderado',
            estado='Sin solicitar',
            acepta_terminos_triage=True,
        )
        db.session.add(consulta)
        db.session.commit()
        consulta_id = consulta.id

    _login(client, 'duenoA@test.local')
    _registrar(client, 'duenoB@test.local', nombre='Dueño B')
    _login(client, 'duenoB@test.local')

    respuesta = client.post(
        f'/triaje/{consulta_id}/solicitar',
        follow_redirects=True,
    ).get_data(as_text=True)
    assert 'No puedes solicitar asistencia de esta consulta.' in respuesta


def test_solicitar_dos_veces_no_cambia_nada(client):
    _registrar(client, 'duplicar@test.local', nombre='Duplicar')
    _login(client, 'duplicar@test.local')
    _crear_mascota(client)
    mascota_id = _id_mascota('duplicar@test.local')
    _crear_consulta(client, mascota_id, 'Diarrea', solicitar=False)

    with app.app_context():
        consulta_id = (Consulta.query
                       .filter_by(mascota_id=mascota_id)
                       .order_by(Consulta.id.desc())
                       .first().id)

    client.post(f'/triaje/{consulta_id}/solicitar', follow_redirects=True)
    respuesta = client.post(
        f'/triaje/{consulta_id}/solicitar',
        follow_redirects=True,
    ).get_data(as_text=True)
    assert 'ya ha sido enviada' in respuesta

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        assert consulta.estado == 'Pendiente'


def test_bandeja_solo_muestra_solicitudes_por_tomar(client):
    _registrar(client, 'dueno-cola@test.local', nombre='Dueño Cola')
    _login(client, 'dueno-cola@test.local')
    _crear_mascota(client, 'Toby', 'Perro')
    mascota_id = _id_mascota('dueno-cola@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Tos persistente')
    client.post('/logout')

    _registrar(
        client,
        'vet-cola@test.local',
        nombre='Dra. Cola',
        rol='veterinario',
        cedula='VET-COLA',
    )
    _login(client, 'vet-cola@test.local')

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert 'Toby' in bandeja
    assert 'Tomar caso' in bandeja
    assert 'Disponibles' in bandeja

    client.post(f'/veterinario/casos/{consulta_id}/tomar', follow_redirects=True)

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert 'Toby' not in bandeja
    assert 'No hay solicitudes que coincidan con este filtro.' in bandeja

    assert 'Toby' in client.get('/veterinario/tablero').get_data(as_text=True)
    assert 'Toby' in client.get('/veterinario/agenda').get_data(as_text=True)


def test_bandeja_oculta_casos_cerrados(client):
    _registrar(client, 'dueno-cerrado@test.local', nombre='Dueño Cerrado')
    _login(client, 'dueno-cerrado@test.local')
    _crear_mascota(client, 'Luna', 'Gato')
    mascota_id = _id_mascota('dueno-cerrado@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Diarrea')
    client.post('/logout')

    _registrar(
        client,
        'vet-cerrado@test.local',
        nombre='Dr. Cerrado',
        rol='veterinario',
        cedula='VET-CERRADO',
    )
    _login(client, 'vet-cerrado@test.local')
    client.post(f'/veterinario/casos/{consulta_id}/tomar', follow_redirects=True)

    with app.app_context():
        consulta = db.session.get(Consulta, consulta_id)
        consulta.estado = 'Cerrada'
        db.session.commit()

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert 'Luna' not in bandeja
    assert 'No hay solicitudes que coincidan con este filtro.' in bandeja

    # El filtro de cerrados ya no existe: cae a "Todas" y tampoco los muestra.
    bandeja = client.get('/veterinario/bandeja?filtro=cerrados').get_data(as_text=True)
    assert 'Luna' not in bandeja

    # La agenda conserva el historial de cerrados recientes.
    assert 'Luna' in client.get('/veterinario/agenda').get_data(as_text=True)


def test_badge_de_solicitudes_disponibles(client):
    _registrar(client, 'dueno-badge@test.local', nombre='Dueño Badge')
    _login(client, 'dueno-badge@test.local')
    _crear_mascota(client, 'Kira', 'Perro')
    mascota_id = _id_mascota('dueno-badge@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Cojera')
    client.post('/logout')

    _registrar(
        client,
        'vet-badge@test.local',
        nombre='Dra. Badge',
        rol='veterinario',
        cedula='VET-BADGE',
    )
    _login(client, 'vet-badge@test.local')

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert '1 solicitud disponible' in bandeja

    client.post(f'/veterinario/casos/{consulta_id}/tomar', follow_redirects=True)

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert '1 solicitud disponible' not in bandeja


def test_mensajes_solo_muestra_casos_tomados(client):
    _registrar(client, 'dueno-msg@test.local', nombre='Dueño Mensajes')
    _login(client, 'dueno-msg@test.local')
    _crear_mascota(client, 'Rex', 'Perro')
    mascota_id = _id_mascota('dueno-msg@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Tos')
    client.post(
        f'/triaje/{consulta_id}/chat',
        data={'mensaje': 'Hola, sigue tosiendo.'},
        follow_redirects=True,
    )
    client.post('/logout')

    _registrar(
        client,
        'vet-msg@test.local',
        nombre='Dra. Mensajes',
        rol='veterinario',
        cedula='VET-MSG',
    )
    _login(client, 'vet-msg@test.local')

    html = client.get('/veterinario/mensajes').get_data(as_text=True)
    assert 'Rex' not in html
    assert 'Aún no has tomado ningún caso' in html

    client.post(f'/veterinario/casos/{consulta_id}/tomar', follow_redirects=True)

    html = client.get('/veterinario/mensajes').get_data(as_text=True)
    assert 'Rex' in html
    assert 'Hola, sigue tosiendo.' in html


def test_badge_mensajes_solo_cuenta_casos_tomados(client):
    _registrar(client, 'dueno-msg-badge@test.local', nombre='Dueño Msg Badge')
    _login(client, 'dueno-msg-badge@test.local')
    _crear_mascota(client, 'Mila', 'Gato')
    mascota_id = _id_mascota('dueno-msg-badge@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Vómito')
    client.post(
        f'/triaje/{consulta_id}/chat',
        data={'mensaje': 'Buenas, sigue vomitando.'},
        follow_redirects=True,
    )
    client.post('/logout')

    _registrar(
        client,
        'vet-msg-badge@test.local',
        nombre='Dr. Msg Badge',
        rol='veterinario',
        cedula='VET-MSG-BADGE',
    )
    _login(client, 'vet-msg-badge@test.local')

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert '1 mensaje sin leer' not in bandeja

    client.post(f'/veterinario/casos/{consulta_id}/tomar', follow_redirects=True)

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert '1 mensaje sin leer' in bandeja


def test_solicitud_muestra_indicador_de_chat_previo(client):
    _registrar(client, 'dueno-chat-previo@test.local', nombre='Dueño Chat Previo')
    _login(client, 'dueno-chat-previo@test.local')
    _crear_mascota(client, 'Nala', 'Gato')
    mascota_id = _id_mascota('dueno-chat-previo@test.local')
    consulta_id = _crear_consulta(client, mascota_id, 'Diarrea')
    client.post(
        f'/triaje/{consulta_id}/chat',
        data={'mensaje': 'Hola, tiene diarrea desde ayer.'},
        follow_redirects=True,
    )
    client.post('/logout')

    _registrar(
        client,
        'vet-chat-previo@test.local',
        nombre='Dra. Chat Previo',
        rol='veterinario',
        cedula='VET-CHAT-PREV',
    )
    _login(client, 'vet-chat-previo@test.local')

    bandeja = client.get('/veterinario/bandeja').get_data(as_text=True)
    assert 'Nala' in bandeja
    assert 'Mensajes del dueño antes de tomar el caso' in bandeja
