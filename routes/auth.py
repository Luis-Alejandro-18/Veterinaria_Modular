from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import Usuario, db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        rol = request.form.get('rol', 'dueno')
        cedula = request.form.get('cedula_profesional', '').strip() or None

        if not nombre or not email or not password:
            flash('Nombre, email y contraseña son obligatorios.', 'error')
            return redirect(url_for('auth.registro'))
        if rol not in ('dueno', 'veterinario'):
            flash('Rol inválido.', 'error')
            return redirect(url_for('auth.registro'))
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('auth.registro'))
        if Usuario.query.filter_by(email=email).first():
            flash('Ese email ya está registrado.', 'error')
            return redirect(url_for('auth.registro'))

        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=generate_password_hash(password),
            rol=rol,
            cedula_profesional=cedula if rol == 'veterinario' else None,
        )
        db.session.add(usuario)
        db.session.commit()
        flash('Registro exitoso. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html')


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
        return redirect(url_for('index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Sesión cerrada.', 'success')
    return redirect(url_for('index'))
