"""API JSON del chat de consultas, usada por el polling del navegador."""
from flask import Blueprint, current_app, g, jsonify, request

from constants import ESTADO_CERRADA, ESTADO_SIN_SOLICITAR
from models import Consulta, MensajeConsulta, db

chat_api_bp = Blueprint('chat_api', __name__, url_prefix='/api/consultas')

MAX_MENSAJE = 4000


def _error(mensaje, codigo):
    return jsonify({'error': mensaje}), codigo


def _consulta_autorizada(consulta_id):
    """Devuelve (consulta, None) o (None, respuesta_de_error)."""
    consulta = db.session.get(Consulta, consulta_id)
    if consulta is None:
        return None, _error('Consulta no encontrada.', 404)

    usuario = getattr(g, 'usuario', None)
    if usuario is None:
        return None, _error('Debes iniciar sesión para continuar.', 401)

    if usuario.rol == 'veterinario':
        if consulta.estado == ESTADO_SIN_SOLICITAR:
            return None, _error('Este caso aún no ha sido enviado a los veterinarios.', 403)
        if consulta.veterinario_id != usuario.id:
            return None, _error('Primero debes tomar este caso.', 403)
    elif consulta.mascota.usuario_id != usuario.id:
        return None, _error('No tienes permiso para ver esta consulta.', 403)

    return consulta, None


def _puede_escribir(consulta):
    if consulta.estado in (ESTADO_CERRADA, ESTADO_SIN_SOLICITAR):
        return False
    if g.usuario.rol == 'veterinario':
        return consulta.veterinario_id == g.usuario.id
    return consulta.mascota.usuario_id == g.usuario.id


def _serializar(mensaje):
    local_time = current_app.jinja_env.filters['local_time']
    return {
        'id': mensaje.id,
        'texto': mensaje.mensaje,
        'remitente': mensaje.remitente.nombre if mensaje.remitente else 'Usuario',
        'es_propio': mensaje.remitente_id == g.usuario.id,
        'hora': local_time(mensaje.fecha_envio, '%H:%M'),
        'fecha_hora': local_time(mensaje.fecha_envio, '%d/%m %H:%M'),
    }


@chat_api_bp.route('/<int:consulta_id>/mensajes', methods=['GET'])
def mensajes(consulta_id):
    consulta, error = _consulta_autorizada(consulta_id)
    if error is not None:
        return error

    if g.usuario.rol == 'dueno' and consulta.estado == ESTADO_SIN_SOLICITAR:
        return _error('Primero debes solicitar asistencia con un doctor.', 409)

    desde_id = request.args.get('desde_id', 0, type=int) or 0
    nuevos = (MensajeConsulta.query
              .filter(
                  MensajeConsulta.consulta_id == consulta.id,
                  MensajeConsulta.id > desde_id,
              )
              .order_by(MensajeConsulta.id.asc())
              .all())

    ultimo_id = (db.session.query(db.func.max(MensajeConsulta.id))
                 .filter(MensajeConsulta.consulta_id == consulta.id)
                 .scalar()) or 0

    return jsonify({
        'mensajes': [_serializar(mensaje) for mensaje in nuevos],
        'ultimo_id': ultimo_id,
        'estado': consulta.estado,
        'puede_escribir': _puede_escribir(consulta),
    })


@chat_api_bp.route('/<int:consulta_id>/mensajes', methods=['POST'])
def enviar(consulta_id):
    consulta, error = _consulta_autorizada(consulta_id)
    if error is not None:
        return error

    if consulta.estado == ESTADO_CERRADA:
        return _error('No se puede escribir en una consulta cerrada.', 409)
    if consulta.estado == ESTADO_SIN_SOLICITAR:
        return _error('Primero debes solicitar asistencia con un doctor antes de escribir en el chat.', 409)

    datos = request.get_json(silent=True) or request.form
    texto = (datos.get('mensaje') or '').strip()
    if not texto:
        return _error('Escribe un mensaje antes de enviarlo.', 400)
    if len(texto) > MAX_MENSAJE:
        return _error(f'El mensaje es demasiado largo (máximo {MAX_MENSAJE} caracteres).', 400)

    if g.usuario.rol == 'veterinario' and consulta.estado == 'Pendiente':
        consulta.estado = 'En Atención'

    nuevo = MensajeConsulta(
        consulta_id=consulta.id,
        remitente_id=g.usuario.id,
        mensaje=texto,
    )
    db.session.add(nuevo)
    db.session.commit()

    return jsonify({
        'mensaje': _serializar(nuevo),
        'estado': consulta.estado,
        'puede_escribir': _puede_escribir(consulta),
    }), 201


@chat_api_bp.route('/<int:consulta_id>/leido', methods=['POST'])
def marcar_leido(consulta_id):
    consulta, error = _consulta_autorizada(consulta_id)
    if error is not None:
        return error

    if g.usuario.rol != 'veterinario':
        return jsonify({'marcados': 0})

    marcados = (MensajeConsulta.query
                .filter(
                    MensajeConsulta.consulta_id == consulta.id,
                    MensajeConsulta.remitente_id != g.usuario.id,
                    MensajeConsulta.leido.is_(False),
                )
                .update({'leido': True}, synchronize_session=False))
    db.session.commit()
    return jsonify({'marcados': marcados})
