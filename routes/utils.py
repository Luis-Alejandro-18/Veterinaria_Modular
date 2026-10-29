import os
from functools import wraps

from flask import current_app, flash, g, redirect, session, url_for

from models import db, Usuario


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


def eliminar_evidencias_de_consulta(consulta):
    """Elimina del disco las evidencias de una consulta antes de borrarla en BD."""
    for evidencia in consulta.evidencias:
        ruta = os.path.join(current_app.static_folder, evidencia.ruta_archivo)
        if os.path.exists(ruta):
            os.remove(ruta)


def eliminar_evidencias_de_mascota(mascota):
    """Elimina del disco todas las evidencias de las consultas de una mascota."""
    for consulta in mascota.consultas:
        eliminar_evidencias_de_consulta(consulta)
