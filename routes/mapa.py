from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import text

from models import db

mapa_bp = Blueprint('mapa', __name__)

SQL_CLINICAS = """
    SELECT id, nombre, direccion, telefono, abierto_24_7,
           ST_Y(coordenadas::geometry) AS lat,
           ST_X(coordenadas::geometry) AS lng
    FROM clinicas
    WHERE abierto_24_7 = TRUE
    ORDER BY nombre
"""

SQL_CERCANAS = """
    SELECT id, nombre, direccion, telefono, abierto_24_7,
           ST_Y(coordenadas::geometry) AS lat,
           ST_X(coordenadas::geometry) AS lng,
           ST_Distance(
               coordenadas::geography,
               ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
           ) AS distancia_m
    FROM clinicas
    WHERE abierto_24_7 = TRUE
      AND ST_DWithin(
          coordenadas::geography,
          ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
          :radio
      )
    ORDER BY distancia_m ASC
"""


@mapa_bp.route('/mapa')
def mapa():
    return render_template('mapa.html')


@mapa_bp.route('/clinicas')
def clinicas():
    filas = db.session.execute(text(SQL_CLINICAS)).fetchall()
    return jsonify([
        {
            'id': fila.id,
            'nombre': fila.nombre,
            'direccion': fila.direccion,
            'telefono': fila.telefono,
            'lat': fila.lat,
            'lng': fila.lng,
            'abierto_24_7': fila.abierto_24_7,
        }
        for fila in filas
    ])


@mapa_bp.route('/clinicas/cercanas')
def clinicas_cercanas():
    try:
        lat = float(request.args['lat'])
        lng = float(request.args['lng'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Los parámetros lat y lng son obligatorios.'}), 400

    try:
        radio = float(request.args.get('radio', 5000))
    except ValueError:
        return jsonify({'error': 'El radio debe ser un número en metros.'}), 400

    filas = db.session.execute(
        text(SQL_CERCANAS),
        {'lat': lat, 'lng': lng, 'radio': radio},
    ).fetchall()

    return jsonify([
        {
            'id': fila.id,
            'nombre': fila.nombre,
            'direccion': fila.direccion,
            'telefono': fila.telefono,
            'lat': fila.lat,
            'lng': fila.lng,
            'distancia_m': round(float(fila.distancia_m), 1),
            'abierto_24_7': fila.abierto_24_7,
        }
        for fila in filas
    ])
