import mimetypes
import os
import re
import unicodedata
from uuid import uuid4

from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, send_from_directory, url_for)
from PIL import Image, UnidentifiedImageError
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from constants import (ESTADOS_CONSULTA, ESTADO_CERRADA, NIVELES_URGENCIA,
                       SINTOMAS_PREDEFINIDOS, TRANSICIONES_ESTADO)
from data.primeros_auxilios import obtener_guia
from models import Consulta, Evidencia, Mascota, MensajeConsulta, RespuestaOrientacion, db
from routes.utils import (componer_respuesta, login_required, puede_ver_consulta,
                          ruta_fisica_evidencia, veterinario_required)

triaje_bp = Blueprint('triaje', __name__, url_prefix='/triaje')

EXTENSIONES_IMAGEN = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
EXTENSIONES_VIDEO = {'mp4', 'mov', 'avi', 'webm'}

# Mapa clave -> etiqueta amigable para los síntomas predefinidos.
SINTOMA_ETIQUETA = {}
for _nivel, _sintomas in SINTOMAS_PREDEFINIDOS.items():
    for _clave, _etiqueta in _sintomas:
        SINTOMA_ETIQUETA[_clave] = _etiqueta

# Mapa clave -> nivel de urgencia para los síntomas predefinidos.
SINTOMA_NIVEL = {}
for _nivel, _sintomas in SINTOMAS_PREDEFINIDOS.items():
    for _clave, _etiqueta in _sintomas:
        SINTOMA_NIVEL[_clave] = _nivel


def _normalizar(texto):
    """Pasa a minúsculas, quita acentos y colapsa espacios."""
    if not texto:
        return ''
    texto = texto.lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return re.sub(r'\s+', ' ', texto).strip()


# Expresiones regulares con límite de palabra para evitar falsos positivos
# (p. ej. "tos" dentro de "vómitos"). Se aplican sobre texto ya normalizado.
PALABRAS_URGENTES = [
    r'\bsangr', r'\bhemorragi', r'\bveneno', r'\btoxico', r'\bintoxicaci',
    r'\bconvuls', r'\bdesmay', r'\binconsciente', r'\bno respira',
    r'\bdificultad para respirar', r'\bdificultad respir', r'\bcuesta respir',
    r'\batropell', r'\baccidente', r'\bfractura', r'\bgolpe fuerte',
    r'\bquemadura', r'\bparto', r'\bsangre en la heces',
    r'\bherida abierta\b', r'\bherida grave\b', r'\bherida profunda\b',
    r'\bno puede caminar',
]
PALABRAS_MODERADAS = [
    r'\bvomita', r'\bvomit', r'\bdiarrea', r'\bfiebre', r'\bcoje',
    r'\bdolor', r'\bhinch\w*', r'\binflamaci', r'\bletargo', r'\bdecaed',
    r'\bdecai', r'\bno come', r'\bno quiere comer', r'\btos\b',
    r'\bherida\w*',  # herida genérica (no abierta/grave/profunda)
]


@triaje_bp.before_request
def _redirect_veterinarios_crear():
    """Redirige a veterinarios de crear/listar triaje (solo atienden consultas)."""
    if g.usuario and g.usuario.rol == 'veterinario':
        endpoint = request.endpoint or ''
        if endpoint in ('triaje.nueva', 'triaje.lista'):
            flash('Los veterinarios atienden consultas desde la bandeja de casos.', 'error')
            return redirect(url_for('veterinario.bandeja'))


def _coincide(texto_norm, patrones):
    return any(re.search(p, texto_norm) for p in patrones)


def clasificar_urgencia(sintomas_texto, sintomas_predefinidos=None, estado_general=None):
    """Clasifica la urgencia con reglas simples por palabras clave, síntomas predefinidos y estado general.

    Args:
        sintomas_texto: Texto libre de síntomas.
        sintomas_predefinidos: Lista de claves de síntomas predefinidos seleccionados.
        estado_general: Dict con respuestas del formulario de estado general.

    Returns:
        Uno de 'Urgente', 'Moderado', 'Leve'.
    """
    texto = _normalizar(sintomas_texto)
    predefinidos = sintomas_predefinidos or []
    estado = estado_general or {}

    # Respuestas críticas del estado general que forzan Urgente.
    if estado.get('estado_consciente') == 'no':
        return 'Urgente'
    if estado.get('estado_caminar') == 'no':
        return 'Urgente'
    if estado.get('estado_respiracion') == 'dificil':
        return 'Urgente'
    if estado.get('estado_heridas') == 'si':
        return 'Urgente'

    # Síntomas predefinidos: el nivel más grave gana.
    for clave in predefinidos:
        if SINTOMA_NIVEL.get(clave) == 'Urgente':
            return 'Urgente'

    # Palabras clave urgentes en el texto libre.
    if _coincide(texto, PALABRAS_URGENTES):
        return 'Urgente'

    # Síntomas predefinidos moderados.
    for clave in predefinidos:
        if SINTOMA_NIVEL.get(clave) == 'Moderado':
            return 'Moderado'

    # Palabras clave moderadas en el texto libre.
    if _coincide(texto, PALABRAS_MODERADAS):
        return 'Moderado'

    return 'Leve'


@triaje_bp.route('/')
@login_required
def lista():
    q = request.args.get('q', '').strip()
    estado = request.args.get('estado', '').strip()
    urgencia = request.args.get('urgencia', '').strip()
    if estado not in ESTADOS_CONSULTA:
        estado = ''
    if urgencia not in NIVELES_URGENCIA:
        urgencia = ''
    pagina = max(request.args.get('page', 1, type=int) or 1, 1)

    consultas_query = Consulta.query.join(Mascota)
    if g.usuario.rol != 'veterinario':
        consultas_query = consultas_query.filter(Mascota.usuario_id == g.usuario.id)
    if q:
        like = f'%{q}%'
        consultas_query = consultas_query.filter(
            or_(Mascota.nombre.ilike(like), Consulta.sintomas.ilike(like))
        )
    if estado:
        consultas_query = consultas_query.filter(Consulta.estado == estado)
    if urgencia:
        consultas_query = consultas_query.filter(Consulta.nivel_urgencia == urgencia)

    paginacion = (consultas_query
                  .order_by(Consulta.fecha_creacion.desc())
                  .paginate(page=pagina, per_page=10, error_out=False))
    return render_template(
        'triaje/lista.html',
        consultas=paginacion.items,
        paginacion=paginacion,
        q=q,
        estado=estado,
        urgencia=urgencia,
        estados=ESTADOS_CONSULTA,
        niveles=NIVELES_URGENCIA,
    )


@triaje_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    mascotas = (Mascota.query
                .filter_by(usuario_id=g.usuario.id)
                .order_by(Mascota.nombre)
                .all())

    # Si no hay mascotas registradas, guiar al usuario a crear una primero.
    if not mascotas:
        flash('Primero registra a tu mascota para poder iniciar un triaje.', 'info')
        return redirect(url_for('mascotas.nueva', next='triaje'))

    # mascota_id preseleccionada desde el registro de mascota.
    preseleccionada = request.args.get('mascota_id', type=int)

    if request.method == 'POST':
        mascota_id = request.form.get('mascota_id')
        motivo = request.form.get('motivo', '').strip()
        sintomas_predefinidos = request.form.getlist('sintomas_predefinidos')
        estado_consciente = request.form.get('estado_consciente', '')
        estado_caminar = request.form.get('estado_caminar', '')
        estado_respiracion = request.form.get('estado_respiracion', '')
        estado_heridas = request.form.get('estado_heridas', '')
        acepta = request.form.get('acepta_terminos_triage') == 'on'

        # Construir el texto de síntomas combinando motivo + predefinidos + estado general.
        partes_sintomas = []
        if motivo:
            partes_sintomas.append('Motivo: ' + motivo)
        if sintomas_predefinidos:
            etiquetas = [SINTOMA_ETIQUETA.get(c, c) for c in sintomas_predefinidos]
            partes_sintomas.append('Síntomas: ' + ', '.join(etiquetas))

        estado_partes = []
        if estado_consciente:
            estado_partes.append(f'Consciente: {estado_consciente}')
        if estado_caminar:
            estado_partes.append(f'Camina: {estado_caminar}')
        if estado_respiracion:
            estado_partes.append(f'Respiración: {estado_respiracion}')
        if estado_heridas:
            estado_partes.append(f'Heridas abiertas: {estado_heridas}')
        if estado_partes:
            partes_sintomas.append('Estado general: ' + '; '.join(estado_partes))

        sintomas_combinados = ' | '.join(partes_sintomas)

        if not mascota_id or not sintomas_combinados or not acepta:
            flash('Selecciona una mascota, describe los síntomas y acepta los términos.', 'error')
            return redirect(url_for('triaje.nueva'))

        mascota = Mascota.query.get_or_404(int(mascota_id))
        if mascota.usuario_id != g.usuario.id:
            flash('No puedes crear una consulta para esa mascota.', 'error')
            return redirect(url_for('triaje.nueva'))

        estado_general = {
            'estado_consciente': estado_consciente,
            'estado_caminar': estado_caminar,
            'estado_respiracion': estado_respiracion,
            'estado_heridas': estado_heridas,
        }

        consulta = Consulta(
            mascota_id=mascota.id,
            sintomas=sintomas_combinados,
            nivel_urgencia=clasificar_urgencia(motivo, sintomas_predefinidos, estado_general),
            estado='Pendiente',
            acepta_terminos_triage=True,
        )
        db.session.add(consulta)
        db.session.commit()
        flash(f'Consulta creada. Nivel de urgencia: {consulta.nivel_urgencia}.', 'success')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    return render_template('triaje/form.html', mascotas=mascotas,
                           sintomas_predefinidos=SINTOMAS_PREDEFINIDOS,
                           mascota_preseleccionada=preseleccionada)


@triaje_bp.route('/<int:consulta_id>')
@login_required
def detalle(consulta_id):
    consulta = Consulta.query.get_or_404(consulta_id)
    if not puede_ver_consulta(consulta):
        flash('No tienes permiso para ver esta consulta.', 'error')
        return redirect(url_for('triaje.lista'))
    if g.usuario.rol == 'veterinario':
        return redirect(url_for('veterinario.caso', consulta_id=consulta.id))
    return render_template(
        'triaje/detalle.html',
        consulta=consulta,
        guia=obtener_guia(consulta.nivel_urgencia),
        estados_disponibles=TRANSICIONES_ESTADO.get(consulta.estado, ()),
    )


@triaje_bp.route('/evidencia/<int:evidencia_id>')
@login_required
def ver_evidencia(evidencia_id):
    evidencia = Evidencia.query.get_or_404(evidencia_id)
    if not puede_ver_consulta(evidencia.consulta):
        abort(404)

    nombre = os.path.basename(evidencia.ruta_archivo)
    ruta = ruta_fisica_evidencia(evidencia)
    if not os.path.isfile(ruta):
        abort(404)

    mimetype = mimetypes.guess_type(nombre)[0] or 'application/octet-stream'
    respuesta = send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        nombre,
        mimetype=mimetype,
        conditional=True,
    )
    respuesta.headers['Cache-Control'] = 'private, no-store'
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    return respuesta


@triaje_bp.route('/<int:consulta_id>/evidencia', methods=['POST'])
@login_required
def subir_evidencia(consulta_id):
    consulta = Consulta.query.get_or_404(consulta_id)
    if consulta.mascota.usuario_id != g.usuario.id:
        flash('No tienes permiso para subir evidencia de esta consulta.', 'error')
        return redirect(url_for('triaje.lista'))

    if consulta.estado == ESTADO_CERRADA:
        flash('No se puede subir evidencia a una consulta cerrada.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    archivo = request.files.get('archivo')
    if not archivo or archivo.filename == '':
        flash('Selecciona un archivo para subir.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    nombre = secure_filename(archivo.filename)
    extension = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
    if extension in EXTENSIONES_IMAGEN:
        tipo = 'imagen'
    elif extension in EXTENSIONES_VIDEO:
        tipo = 'video'
    else:
        flash('Formato no permitido. Usa imágenes o videos.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    nombre_unico = f'{uuid4().hex}_{nombre}'
    ruta = os.path.join(current_app.config['UPLOAD_FOLDER'], nombre_unico)
    archivo.save(ruta)

    if tipo == 'imagen':
        try:
            Image.open(ruta).verify()
        except (UnidentifiedImageError, OSError):
            os.remove(ruta)
            flash('El archivo no es una imagen válida.', 'error')
            return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    evidencia = Evidencia(
        consulta_id=consulta.id,
        ruta_archivo=f'uploads/{nombre_unico}',
        tipo=tipo,
    )
    db.session.add(evidencia)
    db.session.commit()
    flash('Evidencia subida correctamente.', 'success')
    return redirect(url_for('triaje.detalle', consulta_id=consulta.id))


@triaje_bp.route('/<int:consulta_id>/respuesta', methods=['POST'])
@veterinario_required
def responder(consulta_id):
    consulta = Consulta.query.get_or_404(consulta_id)
    if consulta.estado == ESTADO_CERRADA:
        flash('No se puede responder una consulta cerrada.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    mensaje = request.form.get('mensaje', '').strip()
    diagnostico = request.form.get('diagnostico', '').strip()
    recomendaciones = request.form.get('recomendaciones', '').strip()
    texto = componer_respuesta(diagnostico, recomendaciones, mensaje)
    if not texto:
        flash('Escribe una respuesta antes de enviarla.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    respuesta = RespuestaOrientacion(
        consulta_id=consulta.id,
        veterinario_id=g.usuario.id,
        mensaje=texto,
    )
    if consulta.veterinario_id is None:
        consulta.veterinario_id = g.usuario.id
    consulta.estado = 'En Atención'
    db.session.add(respuesta)
    db.session.commit()
    flash('Respuesta enviada.', 'success')
    return redirect(url_for('triaje.detalle', consulta_id=consulta.id))


@triaje_bp.route('/<int:consulta_id>/estado', methods=['POST'])
@veterinario_required
def cambiar_estado(consulta_id):
    consulta = Consulta.query.get_or_404(consulta_id)
    nuevo_estado = request.form.get('estado')
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
    return redirect(url_for('triaje.detalle', consulta_id=consulta.id))


@triaje_bp.route('/<int:consulta_id>/chat', methods=['GET'])
@login_required
def chat_historial(consulta_id):
    """Historial de mensajes del chat de una consulta."""
    consulta = Consulta.query.get_or_404(consulta_id)
    if not puede_ver_consulta(consulta):
        flash('No tienes permiso para ver esta consulta.', 'error')
        return redirect(url_for('triaje.lista'))
    if g.usuario.rol == 'veterinario':
        return redirect(url_for('veterinario.chat', consulta_id=consulta.id))
    mensajes = (MensajeConsulta.query
                .filter_by(consulta_id=consulta.id)
                .order_by(MensajeConsulta.fecha_envio.asc())
                .all())
    return render_template('triaje/chat_historial.html', consulta=consulta, mensajes=mensajes)


@triaje_bp.route('/<int:consulta_id>/chat', methods=['POST'])
@login_required
def chat_enviar(consulta_id):
    """Envía un mensaje al chat de una consulta."""
    consulta = Consulta.query.get_or_404(consulta_id)
    if not puede_ver_consulta(consulta):
        flash('No tienes permiso para escribir en esta consulta.', 'error')
        return redirect(url_for('triaje.lista'))
    if consulta.estado == ESTADO_CERRADA:
        flash('No se puede escribir en una consulta cerrada.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    mensaje = request.form.get('mensaje', '').strip()
    if not mensaje:
        flash('Escribe un mensaje antes de enviarlo.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    nuevo_mensaje = MensajeConsulta(
        consulta_id=consulta.id,
        remitente_id=g.usuario.id,
        mensaje=mensaje,
    )
    db.session.add(nuevo_mensaje)
    db.session.commit()
    flash('Mensaje enviado.', 'success')
    if g.usuario.rol == 'veterinario':
        return redirect(url_for('veterinario.chat', consulta_id=consulta.id))
    return redirect(url_for('triaje.detalle', consulta_id=consulta.id))
