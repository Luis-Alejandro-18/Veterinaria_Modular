import mimetypes
import os
from uuid import uuid4

from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, send_from_directory, url_for)
from PIL import Image, UnidentifiedImageError
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from constants import (ESTADOS_CONSULTA, ESTADO_CERRADA, NIVELES_URGENCIA,
                       TRANSICIONES_ESTADO)
from data.primeros_auxilios import obtener_guia
from models import Consulta, Evidencia, Mascota, RespuestaOrientacion, db
from routes.utils import (login_required, puede_ver_consulta,
                          ruta_fisica_evidencia, veterinario_required)

triaje_bp = Blueprint('triaje', __name__, url_prefix='/triaje')

EXTENSIONES_IMAGEN = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
EXTENSIONES_VIDEO = {'mp4', 'mov', 'avi', 'webm'}

PALABRAS_URGENTES = [
    'sangra', 'sangrado', 'convulsion', 'convulsión', 'no respira',
    'dificultad para respirar', 'envenen', 'atropell', 'desmay',
    'inconsciente', 'fractura', 'vomita sangre', 'parto',
]
PALABRAS_MODERADAS = [
    'vomita', 'diarrea', 'fiebre', 'cojea', 'dolor', 'hinchaz',
    'letargo', 'no come', 'tos',
]


def clasificar_urgencia(sintomas):
    """Clasifica la urgencia con reglas simples por palabras clave."""
    texto = sintomas.lower()
    if any(palabra in texto for palabra in PALABRAS_URGENTES):
        return 'Urgente'
    if any(palabra in texto for palabra in PALABRAS_MODERADAS):
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

    if request.method == 'POST':
        mascota_id = request.form.get('mascota_id')
        sintomas = request.form.get('sintomas', '').strip()
        acepta = request.form.get('acepta_terminos_triage') == 'on'

        if not mascota_id or not sintomas or not acepta:
            flash('Selecciona una mascota, describe los síntomas y acepta los términos.', 'error')
            return redirect(url_for('triaje.nueva'))

        mascota = Mascota.query.get_or_404(int(mascota_id))
        if mascota.usuario_id != g.usuario.id:
            flash('No puedes crear una consulta para esa mascota.', 'error')
            return redirect(url_for('triaje.nueva'))

        consulta = Consulta(
            mascota_id=mascota.id,
            sintomas=sintomas,
            nivel_urgencia=clasificar_urgencia(sintomas),
            estado='Pendiente',
            acepta_terminos_triage=True,
        )
        db.session.add(consulta)
        db.session.commit()
        flash(f'Consulta creada. Nivel de urgencia: {consulta.nivel_urgencia}.', 'success')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    return render_template('triaje/form.html', mascotas=mascotas)


@triaje_bp.route('/<int:consulta_id>')
@login_required
def detalle(consulta_id):
    consulta = Consulta.query.get_or_404(consulta_id)
    if not puede_ver_consulta(consulta):
        flash('No tienes permiso para ver esta consulta.', 'error')
        return redirect(url_for('triaje.lista'))
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
    if not mensaje:
        flash('Escribe una respuesta antes de enviarla.', 'error')
        return redirect(url_for('triaje.detalle', consulta_id=consulta.id))

    respuesta = RespuestaOrientacion(
        consulta_id=consulta.id,
        veterinario_id=g.usuario.id,
        mensaje=mensaje,
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
