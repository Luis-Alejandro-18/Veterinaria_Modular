import os
from functools import wraps

from flask import current_app, flash, g, redirect, session, url_for
from sqlalchemy import and_, or_

from constants import ESTADO_SIN_SOLICITAR
from models import Consulta, MensajeConsulta, Usuario, db


def load_logged_in_user():
    """Carga el usuario de la sesión en g.usuario para usarlo en vistas y plantillas."""
    usuario_id = session.get('usuario_id')
    g.usuario = db.session.get(Usuario, usuario_id) if usuario_id else None


def login_required(view):
    """Redirige al login si no hay sesión activa."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if getattr(g, 'usuario', None) is None:
            flash('Debes iniciar sesión para continuar.', 'error')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)

    return wrapped_view


def veterinario_required(view):
    """Permite la acción solo a usuarios con rol veterinario."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        usuario = getattr(g, 'usuario', None)
        if usuario is None:
            flash('Debes iniciar sesión para continuar.', 'error')
            return redirect(url_for('auth.login'))
        if usuario.rol != 'veterinario':
            flash('Solo los veterinarios pueden realizar esta acción.', 'error')
            return redirect(url_for('index'))
        return view(*args, **kwargs)

    return wrapped_view


def puede_ver_consulta(consulta):
    """Un veterinario ve todas las consultas salvo las 'Sin solicitar'; un dueño solo las de sus mascotas."""
    usuario = getattr(g, 'usuario', None)
    if usuario is None:
        return False
    if usuario.rol == 'veterinario' and consulta.estado == ESTADO_SIN_SOLICITAR:
        return False
    return usuario.rol == 'veterinario' or consulta.mascota.usuario_id == usuario.id


def condicion_consulta_visible(usuario):
    """Casos que puede ver un veterinario: los suyos y los pendientes sin asignar."""
    return or_(
        Consulta.veterinario_id == usuario.id,
        and_(Consulta.estado == 'Pendiente', Consulta.veterinario_id.is_(None)),
    )


def mensajes_sin_leer_para(usuario):
    """Cuenta mensajes de dueños sin leer en los casos que el veterinario ya tomó."""
    if usuario is None or usuario.rol != 'veterinario':
        return 0
    return (MensajeConsulta.query
            .join(Consulta, MensajeConsulta.consulta_id == Consulta.id)
            .filter(
                Consulta.veterinario_id == usuario.id,
                MensajeConsulta.remitente_id != usuario.id,
                MensajeConsulta.leido.is_(False),
            )
            .count())


def solicitudes_disponibles_para(usuario):
    """Cuenta solicitudes pendientes sin veterinario: casos por tomar en la bandeja."""
    if usuario is None or usuario.rol != 'veterinario':
        return 0
    return (Consulta.query
            .filter(
                Consulta.estado == 'Pendiente',
                Consulta.veterinario_id.is_(None),
            )
            .count())


def componer_respuesta(diagnostico='', recomendaciones='', mensaje=''):
    """Combina diagnóstico, recomendaciones y mensaje libre en el texto que ve el dueño."""
    partes = []
    if diagnostico:
        partes.append(f'Diagnóstico: {diagnostico}')
    if recomendaciones:
        partes.append(f'Recomendaciones: {recomendaciones}')
    if mensaje:
        partes.append(mensaje)
    return '\n\n'.join(partes).strip()


def ruta_fisica_evidencia(evidencia):
    """Devuelve la ruta privada en disco de una evidencia, sin permitir traversal."""
    nombre = os.path.basename(evidencia.ruta_archivo)
    return os.path.join(current_app.config['UPLOAD_FOLDER'], nombre)


def eliminar_evidencias_de_consulta(consulta):
    """Elimina del disco las evidencias de una consulta antes de borrarla en BD."""
    for evidencia in consulta.evidencias:
        ruta = ruta_fisica_evidencia(evidencia)
        if os.path.exists(ruta):
            os.remove(ruta)


def eliminar_evidencias_de_mascota(mascota):
    """Elimina del disco todas las evidencias de las consultas de una mascota."""
    for consulta in mascota.consultas:
        eliminar_evidencias_de_consulta(consulta)
