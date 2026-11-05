from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from constants import ROLES
from models import Usuario, db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/registro', methods=['GET'])
def registro():
    """Página de selección de tipo de cuenta antes de registrarse."""
    return render_template('auth/registro_landing.html')


@auth_bp.route('/registro/dueno', methods=['GET', 'POST'])
def registro_dueno():
    """Registro para dueños de mascotas (sin cédula profesional)."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not nombre or not email or not password:
            flash('Nombre, email y contraseña son obligatorios.', 'error')
            return redirect(url_for('auth.registro_dueno'))
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('auth.registro_dueno'))
        if Usuario.query.filter_by(email=email).first():
            flash('Ese email ya está registrado.', 'error')
            return redirect(url_for('auth.registro_dueno'))

        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=generate_password_hash(password),
            rol='dueno',
            cedula_profesional=None,
        )
        db.session.add(usuario)
        db.session.commit()
        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro_dueno.html')


@auth_bp.route('/registro/veterinario', methods=['GET', 'POST'])
def registro_veterinario():
    """Registro para veterinarios (cédula profesional obligatoria)."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        cedula = request.form.get('cedula_profesional', '').strip() or None

        if not nombre or not email or not password:
            flash('Nombre, email y contraseña son obligatorios.', 'error')
            return redirect(url_for('auth.registro_veterinario'))
        if not cedula:
            flash('La cédula profesional es obligatoria para registrarse como veterinario.', 'error')
            return redirect(url_for('auth.registro_veterinario'))
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('auth.registro_veterinario'))
        if Usuario.query.filter_by(email=email).first():
            flash('Ese email ya está registrado.', 'error')
            return redirect(url_for('auth.registro_veterinario'))

        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=generate_password_hash(password),
            rol='veterinario',
            cedula_profesional=cedula,
        )
        db.session.add(usuario)
        db.session.commit()
        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro_veterinario.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario is None or not check_password_hash(usuario.password_hash, password):
            flash('Credenciales incorrectas.', 'error')
            return redirect(url_for('auth.login'))

        session.clear()
        session['usuario_id'] = usuario.id
        flash(f'Bienvenido, {usuario.nombre}.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Sesión cerrada.', 'success')
    return redirect(url_for('index'))
