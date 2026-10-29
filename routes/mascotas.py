from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from models import Mascota, db
from routes.utils import eliminar_evidencias_de_mascota, login_required

mascotas_bp = Blueprint('mascotas', __name__, url_prefix='/mascotas')


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@mascotas_bp.route('/')
@login_required
def lista():
    mascotas = (Mascota.query
                .filter_by(usuario_id=g.usuario.id)
                .order_by(Mascota.nombre)
                .all())
    return render_template('mascotas/lista.html', mascotas=mascotas)


@mascotas_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def nueva():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        especie = request.form.get('especie', '').strip()
        if not nombre or not especie:
            flash('Nombre y especie son obligatorios.', 'error')
            return redirect(url_for('mascotas.nueva'))

        mascota = Mascota(
            usuario_id=g.usuario.id,
            nombre=nombre,
            especie=especie,
            raza=request.form.get('raza', '').strip() or None,
            edad_anios=_to_int(request.form.get('edad_anios')),
            peso_kg=_to_float(request.form.get('peso_kg')),
            condiciones_previas=request.form.get('condiciones_previas', '').strip() or None,
        )
        db.session.add(mascota)
        db.session.commit()
        flash('Mascota registrada correctamente.', 'success')
        return redirect(url_for('mascotas.lista'))

    return render_template('mascotas/form.html', mascota=None)


@mascotas_bp.route('/<int:mascota_id>')
@login_required
def detalle(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)
    if mascota.usuario_id != g.usuario.id and g.usuario.rol != 'veterinario':
        flash('No tienes permiso para ver esta mascota.', 'error')
        return redirect(url_for('mascotas.lista'))
    return render_template('mascotas/detalle.html', mascota=mascota)


@mascotas_bp.route('/<int:mascota_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)
    if mascota.usuario_id != g.usuario.id:
        flash('No tienes permiso para editar esta mascota.', 'error')
        return redirect(url_for('mascotas.lista'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        especie = request.form.get('especie', '').strip()
        if not nombre or not especie:
            flash('Nombre y especie son obligatorios.', 'error')
            return redirect(url_for('mascotas.editar', mascota_id=mascota.id))

        mascota.nombre = nombre
        mascota.especie = especie
        mascota.raza = request.form.get('raza', '').strip() or None
        mascota.edad_anios = _to_int(request.form.get('edad_anios'))
        mascota.peso_kg = _to_float(request.form.get('peso_kg'))
        mascota.condiciones_previas = request.form.get('condiciones_previas', '').strip() or None
        db.session.commit()
        flash('Mascota actualizada.', 'success')
        return redirect(url_for('mascotas.detalle', mascota_id=mascota.id))

    return render_template('mascotas/form.html', mascota=mascota)


@mascotas_bp.route('/<int:mascota_id>/eliminar', methods=['POST'])
@login_required
def eliminar(mascota_id):
    mascota = Mascota.query.get_or_404(mascota_id)
    if mascota.usuario_id != g.usuario.id:
        flash('No tienes permiso para eliminar esta mascota.', 'error')
        return redirect(url_for('mascotas.lista'))

    # Borrado en cascada (MVP): primero archivos, luego registros.
    eliminar_evidencias_de_mascota(mascota)
    db.session.delete(mascota)
    db.session.commit()
    flash('Mascota eliminada.', 'success')
    return redirect(url_for('mascotas.lista'))
