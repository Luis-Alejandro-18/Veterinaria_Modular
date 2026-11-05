from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from constants import ESTADO_CERRADA, TRANSICIONES_ESTADO
from models import Consulta, Usuario, db
from routes.utils import veterinario_required

veterinario_bp = Blueprint('veterinario', __name__, url_prefix='/veterinario')


@veterinario_bp.route('/consultas-disponibles')
@veterinario_required
def consultas_disponibles():
    """Lista consultas en estado Pendiente sin veterinario asignado (tipo Uber)."""
    consultas = (Consulta.query
                 .filter_by(estado='Pendiente', veterinario_id=None)
                 .order_by(Consulta.fecha_creacion.asc())
                 .all())
    return render_template('veterinario/consultas_disponibles.html', consultas=consultas)


@veterinario_bp.route('/consultas-disponibles/<int:consulta_id>/tomar', methods=['POST'])
@veterinario_required
def tomar_consulta(consulta_id):
    """Un veterinario toma una consulta disponible (asigna veterinario y cambia a En Atención)."""
    consulta = Consulta.query.get_or_404(consulta_id)

    if consulta.estado != 'Pendiente':
        flash('Esta consulta ya no está disponible.', 'error')
        return redirect(url_for('veterinario.consultas_disponibles'))

    if consulta.veterinario_id is not None:
        flash('Esta consulta ya fue tomada por otro veterinario.', 'error')
        return redirect(url_for('veterinario.consultas_disponibles'))

    consulta.veterinario_id = g.usuario.id
    consulta.estado = 'En Atención'
    db.session.commit()

    flash(f'Has tomado la consulta de {consulta.mascota.nombre}.', 'success')
    return redirect(url_for('triaje.detalle', consulta_id=consulta.id))


@veterinario_bp.route('/mis-consultas')
@veterinario_required
def mis_consultas():
    """Lista las consultas atendidas por el veterinario autenticado."""
    consultas = (Consulta.query
                 .filter_by(veterinario_id=g.usuario.id)
                 .order_by(Consulta.fecha_creacion.desc())
                 .all())
    return render_template('veterinario/mis_consultas.html', consultas=consultas)
