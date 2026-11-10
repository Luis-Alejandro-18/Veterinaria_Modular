from datetime import datetime, timedelta

from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, url_for)
from sqlalchemy import case, or_

from constants import (ESTADO_CERRADA, ESTADO_SIN_SOLICITAR, ESTADOS_CONSULTA,
                       TRANSICIONES_ESTADO)
from models import Consulta, Mascota, MensajeConsulta, RespuestaOrientacion, db, utcnow
from routes.utils import (componer_respuesta, condicion_consulta_visible,
                          puede_ver_consulta, veterinario_required)

veterinario_bp = Blueprint('veterinario', __name__, url_prefix='/veterinario')

# Los casos urgentes primero y, dentro del mismo nivel, los más antiguos primero.
ORDEN_URGENCIA = case(
    (Consulta.nivel_urgencia == 'Urgente', 0),
    (Consulta.nivel_urgencia == 'Moderado', 1),
    else_=2,
)

FILTROS_BANDEJA = ('todos', 'urgentes')


def _mensajes_de(consulta):
    return sorted(consulta.mensajes_chat, key=lambda mensaje: mensaje.fecha_envio)


def _marcar_mensajes_leidos(consulta):
    """Marca como leídos los mensajes que el dueño envió al veterinario."""
    cambio = False
    for mensaje in consulta.mensajes_chat:
        if mensaje.remitente_id != g.usuario.id and not mensaje.leido:
            mensaje.leido = True
            cambio = True
    if cambio:
        db.session.commit()


def _leer_con_permiso(consulta_id):
    consulta = db.session.get(Consulta, consulta_id)
    if consulta is None:
        abort(404)
    if not puede_ver_consulta(consulta):
        if consulta.estado == ESTADO_SIN_SOLICITAR:
            flash('Este caso aún no ha sido enviado a los veterinarios.', 'error')
        else:
            flash('No tienes permiso para ver esta consulta.', 'error')
        return None
    return consulta


def _puede_actuar(consulta):
    """Solo el veterinario asignado (o cualquiera si sigue libre) puede actuar."""
    return consulta.veterinario_id in (None, g.usuario.id)


@veterinario_bp.route('/')
@veterinario_bp.route('/bandeja')
@veterinario_required
def bandeja():
    """Solicitudes entrantes: casos pendientes que aún no tienen veterinario."""
    q = request.args.get('q', '').strip()
    filtro = request.args.get('filtro', 'todos')
    if filtro not in FILTROS_BANDEJA:
        filtro = 'todos'

    disponibles = (Consulta.query
                   .join(Mascota)
                   .filter(
                       Consulta.estado == 'Pendiente',
                       Consulta.veterinario_id.is_(None),
                   ))

    stats = {
        'total': disponibles.count(),
        'urgentes': disponibles.filter(
            Consulta.nivel_urgencia == 'Urgente',
        ).count(),
    }

    consulta_query = disponibles
    if q:
        like = f'%{q}%'
        criterios = [Mascota.nombre.ilike(like), Consulta.sintomas.ilike(like)]
        numero = q.lstrip('#')
        if numero.isdigit():
            criterios.append(Consulta.id == int(numero))
        consulta_query = consulta_query.filter(or_(*criterios))

    if filtro == 'urgentes':
        consulta_query = consulta_query.filter(
            Consulta.nivel_urgencia == 'Urgente',
        )

    consultas = (consulta_query
                 .order_by(ORDEN_URGENCIA, Consulta.fecha_creacion.asc())
                 .all())

    siguiente_caso = (Consulta.query
                      .filter(
                          Consulta.estado == 'Pendiente',
                          Consulta.veterinario_id.is_(None),
                      )
                      .order_by(ORDEN_URGENCIA, Consulta.fecha_creacion.asc())
                      .first())

    return render_template(
        'veterinario/bandeja.html',
        consultas=consultas,
        stats=stats,
        filtro=filtro,
        q=q,
        siguiente_caso=siguiente_caso,
    )


@veterinario_bp.route('/casos/<int:consulta_id>/tomar', methods=['POST'])
@veterinario_bp.route('/consultas-disponibles/<int:consulta_id>/tomar', methods=['POST'])
@veterinario_required
def tomar_consulta(consulta_id):
    """Toma un caso pendiente y lo asigna al veterinario autenticado."""
    consulta = db.session.get(Consulta, consulta_id)
    if consulta is None:
        abort(404)

    if consulta.veterinario_id == g.usuario.id:
        flash('Ya tienes este caso asignado.', 'success')
        return redirect(url_for('veterinario.caso', consulta_id=consulta.id))

    if consulta.estado != 'Pendiente' or consulta.veterinario_id is not None:
        flash('Esta consulta ya no está disponible.', 'error')
        return redirect(url_for('veterinario.bandeja'))

    consulta.veterinario_id = g.usuario.id
    consulta.estado = 'En Atención'
    db.session.commit()

    flash(f'Has tomado el caso de {consulta.mascota.nombre}.', 'success')
    return redirect(url_for('veterinario.caso', consulta_id=consulta.id))


@veterinario_bp.route('/tablero')
@veterinario_required
def tablero():
    """Vista kanban con los casos agrupados por estado real."""
    consultas = (Consulta.query
                 .join(Mascota)
                 .filter(condicion_consulta_visible(g.usuario))
                 .order_by(ORDEN_URGENCIA, Consulta.fecha_creacion.asc())
                 .all())

    columnas = {estado: [] for estado in ESTADOS_CONSULTA if estado != ESTADO_SIN_SOLICITAR}
    for consulta in consultas:
        columnas.setdefault(consulta.estado, []).append(consulta)

    return render_template('veterinario/tablero.html', columnas=columnas)


@veterinario_bp.route('/agenda')
@veterinario_required
def agenda():
    """Agenda de seguimiento con los casos activos asignados al veterinario."""
    filtro_local = current_app.jinja_env.filters['local_time']

    consultas = (Consulta.query
                 .join(Mascota)
                 .filter(
                     Consulta.veterinario_id == g.usuario.id,
                     Consulta.estado != ESTADO_CERRADA,
                 )
                 .order_by(ORDEN_URGENCIA, Consulta.fecha_creacion.asc())
                 .all())

    cerradas = (Consulta.query
                .join(Mascota)
                .filter(
                    Consulta.veterinario_id == g.usuario.id,
                    Consulta.estado == ESTADO_CERRADA,
                )
                .order_by(Consulta.fecha_creacion.desc())
                .limit(6)
                .all())

    prioritarias = [
        consulta for consulta in consultas
        if consulta.nivel_urgencia == 'Urgente'
        or consulta.estado == 'Requiere Presencial'
    ]

    hoy = filtro_local(utcnow(), '%Y-%m-%d')
    ayer = filtro_local(utcnow() - timedelta(days=1), '%Y-%m-%d')

    grupos = {}
    for consulta in consultas:
        clave = filtro_local(consulta.fecha_creacion, '%Y-%m-%d')
        grupos.setdefault(clave, []).append(consulta)

    dias = []
    for clave in sorted(grupos, reverse=True):
        if clave == hoy:
            etiqueta = 'Hoy'
        elif clave == ayer:
            etiqueta = 'Ayer'
        else:
            etiqueta = filtro_local(grupos[clave][0].fecha_creacion, '%d/%m/%Y')
        dias.append({'fecha': clave, 'etiqueta': etiqueta, 'consultas': grupos[clave]})

    return render_template(
        'veterinario/agenda.html',
        dias=dias,
        prioritarias=prioritarias,
        cerradas=cerradas,
        total_activas=len(consultas),
    )


@veterinario_bp.route('/mensajes')
@veterinario_required
def mensajes():
    """Bandeja de conversaciones con los dueños."""
    consulta_id = request.args.get('consulta_id', type=int)

    consultas = (Consulta.query
                 .join(Mascota)
                 .filter(Consulta.veterinario_id == g.usuario.id)
                 .order_by(Consulta.fecha_creacion.desc())
                 .all())

    seleccionada = None
    if consulta_id:
        seleccionada = next(
            (consulta for consulta in consultas if consulta.id == consulta_id),
            None,
        )
        if seleccionada is None:
            flash('Ese caso no está disponible en tu bandeja de mensajes.', 'error')
        else:
            _marcar_mensajes_leidos(seleccionada)

    hilos = []
    for consulta in consultas:
        mensajes_consulta = _mensajes_de(consulta)
        if not mensajes_consulta and consulta.veterinario_id != g.usuario.id:
            continue
        ultimo = mensajes_consulta[-1] if mensajes_consulta else None
        no_leidos = sum(
            1 for mensaje in mensajes_consulta
            if mensaje.remitente_id != g.usuario.id and not mensaje.leido
        )
        hilos.append({
            'consulta': consulta,
            'ultimo': ultimo,
            'no_leidos': no_leidos,
            'total': len(mensajes_consulta),
        })

    hilos.sort(
        key=lambda hilo: (
            hilo['ultimo'].fecha_envio if hilo['ultimo'] else datetime.min
        ),
        reverse=True,
    )

    mensajes_conv = _mensajes_de(seleccionada) if seleccionada else []

    return render_template(
        'veterinario/mensajes.html',
        hilos=hilos,
        seleccionada=seleccionada,
        mensajes=mensajes_conv,
    )


@veterinario_bp.route('/casos/<int:consulta_id>')
@veterinario_required
def caso(consulta_id):
    """Detalle veterinario del caso, con reporte, evidencia e historial."""
    consulta = _leer_con_permiso(consulta_id)
    if consulta is None:
        return redirect(url_for('veterinario.bandeja'))

    mensajes_consulta = _mensajes_de(consulta)
    no_leidos = sum(
        1 for mensaje in mensajes_consulta
        if mensaje.remitente_id != g.usuario.id and not mensaje.leido
    )

    return render_template(
        'veterinario/caso.html',
        consulta=consulta,
        estados_disponibles=TRANSICIONES_ESTADO.get(consulta.estado, ()),
        puede_tomar=(consulta.estado == 'Pendiente'
                     and consulta.veterinario_id is None),
        es_mio=(consulta.veterinario_id == g.usuario.id),
        respuestas=sorted(
            consulta.respuestas,
            key=lambda respuesta: respuesta.fecha_respuesta,
        ),
        mensajes_no_leidos=no_leidos,
        total_mensajes=len(mensajes_consulta),
    )


@veterinario_bp.route('/casos/<int:consulta_id>/chat')
@veterinario_required
def chat(consulta_id):
    """Conversación del caso dentro del panel veterinario."""
    consulta = _leer_con_permiso(consulta_id)
    if consulta is None:
        return redirect(url_for('veterinario.bandeja'))

    if not _puede_actuar(consulta):
        flash('Este caso está asignado a otro veterinario.', 'error')
        return redirect(url_for('veterinario.caso', consulta_id=consulta.id))

    _marcar_mensajes_leidos(consulta)

    return render_template(
        'veterinario/chat.html',
        consulta=consulta,
        mensajes=_mensajes_de(consulta),
    )


@veterinario_bp.route('/casos/<int:consulta_id>/chat', methods=['POST'])
@veterinario_required
def enviar_mensaje(consulta_id):
    """Envía un mensaje del veterinario al dueño."""
    consulta = _leer_con_permiso(consulta_id)
    if consulta is None:
        return redirect(url_for('veterinario.bandeja'))

    volver = request.form.get('volver', 'chat')
    if volver == 'mensajes':
        destino = url_for('veterinario.mensajes', consulta_id=consulta.id)
    elif volver == 'caso':
        destino = url_for('veterinario.caso', consulta_id=consulta.id)
    else:
        destino = url_for('veterinario.chat', consulta_id=consulta.id)

    if not _puede_actuar(consulta):
        flash('Este caso está asignado a otro veterinario.', 'error')
        return redirect(url_for('veterinario.caso', consulta_id=consulta.id))

    if consulta.estado == ESTADO_CERRADA:
        flash('No se puede escribir en una consulta cerrada.', 'error')
        return redirect(destino)

    mensaje = request.form.get('mensaje', '').strip()
    if not mensaje:
        flash('Escribe un mensaje antes de enviarlo.', 'error')
        return redirect(destino)

    if consulta.veterinario_id is None:
        consulta.veterinario_id = g.usuario.id
        if consulta.estado == 'Pendiente':
            consulta.estado = 'En Atención'

    db.session.add(MensajeConsulta(
        consulta_id=consulta.id,
        remitente_id=g.usuario.id,
        mensaje=mensaje,
    ))
    db.session.commit()
    flash('Mensaje enviado al dueño.', 'success')
    return redirect(destino)


@veterinario_bp.route('/casos/<int:consulta_id>/respuesta', methods=['POST'])
@veterinario_required
def responder(consulta_id):
    """Registra el diagnóstico y recomendaciones, y actualiza el estado del caso."""
    consulta = _leer_con_permiso(consulta_id)
    if consulta is None:
        return redirect(url_for('veterinario.bandeja'))

    destino = url_for('veterinario.caso', consulta_id=consulta.id)

    if not _puede_actuar(consulta):
        flash('Este caso está asignado a otro veterinario.', 'error')
        return redirect(destino)

    if consulta.estado == ESTADO_CERRADA:
        flash('No se puede responder una consulta cerrada.', 'error')
        return redirect(destino)

    diagnostico = request.form.get('diagnostico', '').strip()
    recomendaciones = request.form.get('recomendaciones', '').strip()
    mensaje = request.form.get('mensaje', '').strip()
    texto = componer_respuesta(diagnostico, recomendaciones, mensaje)

    if not texto:
        flash('Escribe un diagnóstico o recomendaciones antes de enviar.', 'error')
        return redirect(destino)

    permitidos = TRANSICIONES_ESTADO.get(consulta.estado, ())
    estado_elegido = request.form.get('estado', '').strip()
    recomendar_presencial = request.form.get('requiere_presencial') == 'on'

    if consulta.veterinario_id is None:
        consulta.veterinario_id = g.usuario.id

    if estado_elegido in permitidos:
        consulta.estado = estado_elegido
    elif recomendar_presencial and 'Requiere Presencial' in permitidos:
        consulta.estado = 'Requiere Presencial'
    elif consulta.estado == 'Pendiente':
        consulta.estado = 'En Atención'

    db.session.add(RespuestaOrientacion(
        consulta_id=consulta.id,
        veterinario_id=g.usuario.id,
        mensaje=texto,
    ))
    db.session.commit()
    flash('Diagnóstico enviado al dueño.', 'success')
    return redirect(destino)


@veterinario_bp.route('/casos/<int:consulta_id>/estado', methods=['POST'])
@veterinario_required
def cambiar_estado(consulta_id):
    """Cambia el estado del caso respetando las transiciones permitidas."""
    consulta = _leer_con_permiso(consulta_id)
    if consulta is None:
        return redirect(url_for('veterinario.bandeja'))

    if not _puede_actuar(consulta):
        flash('Este caso está asignado a otro veterinario.', 'error')
        return redirect(url_for('veterinario.caso', consulta_id=consulta.id))

    nuevo_estado = request.form.get('estado', '').strip()
    if nuevo_estado not in ESTADOS_CONSULTA:
        flash('Estado inválido.', 'error')
    elif nuevo_estado not in TRANSICIONES_ESTADO.get(consulta.estado, ()):
        flash(f'No se puede pasar de "{consulta.estado}" a "{nuevo_estado}".', 'error')
    else:
        if consulta.veterinario_id is None:
            consulta.veterinario_id = g.usuario.id
        consulta.estado = nuevo_estado
        db.session.commit()
        flash('Estado actualizado.', 'success')

    return redirect(url_for('veterinario.caso', consulta_id=consulta.id))


# Rutas anteriores: se conservan como redirecciones para no romper enlaces.
@veterinario_bp.route('/consultas-disponibles')
@veterinario_required
def consultas_disponibles():
    return redirect(url_for('veterinario.bandeja'))


@veterinario_bp.route('/mis-consultas')
@veterinario_required
def mis_consultas():
    return redirect(url_for('veterinario.bandeja'))
