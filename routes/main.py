from flask import Blueprint, g, redirect, render_template, url_for

from models import Mascota, Consulta
from routes.utils import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel de resumen para el usuario autenticado."""
    if g.usuario.rol == 'veterinario':
        return redirect(url_for('veterinario.bandeja'))

    mascotas_count = (Mascota.query
                      .filter_by(usuario_id=g.usuario.id)
                      .count())

    consultas_count = (Consulta.query
                       .join(Mascota)
                       .filter(Mascota.usuario_id == g.usuario.id)
                       .count())

    consultas_pendientes = (Consulta.query
                            .join(Mascota)
                            .filter(Mascota.usuario_id == g.usuario.id,
                                    Consulta.estado == 'Pendiente')
                            .count())

    consultas_urgentes = (Consulta.query
                          .join(Mascota)
                          .filter(Mascota.usuario_id == g.usuario.id,
                                  Consulta.nivel_urgencia == 'Urgente',
                                  Consulta.estado != 'Cerrada')
                          .count())

    ultimas_consultas = (Consulta.query
                         .join(Mascota)
                         .filter(Mascota.usuario_id == g.usuario.id)
                         .order_by(Consulta.fecha_creacion.desc())
                         .limit(5)
                         .all())

    return render_template(
        'dashboard.html',
        mascotas_count=mascotas_count,
        consultas_count=consultas_count,
        consultas_pendientes=consultas_pendientes,
        consultas_urgentes=consultas_urgentes,
        ultimas_consultas=ultimas_consultas,
    )
