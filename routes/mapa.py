from math import radians, sin, cos, sqrt, atan2
import json
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import text

from models import db

mapa_bp = Blueprint('mapa', __name__)

# Overpass API (OpenStreetMap) — sin clave de API requerida.
OVERPASS_ENDPOINT = 'https://overpass-api.de/api/interpreter'
OVERPASS_TIMEOUT = 30

OVERPASS_QUERY = """
[out:json][timeout:{timeout}];
(
  node["amenity"="veterinary"](around:{radio},{lat},{lng});
  way["amenity"="veterinary"](around:{radio},{lat},{lng});
);
out center;
"""

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


def _distancia_metros(lat1, lng1, lat2, lng2):
    """Distancia geodésica aproximada entre dos puntos (fórmula de haversine)."""
    radio_tierra = 6_371_000  # metros
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radio_tierra * c


def _consultar_overpass(lat, lng, radio=10000):
    """Consulta Overpass API para clínicas veterinarias cercanas."""
    query = OVERPASS_QUERY.format(
        timeout=OVERPASS_TIMEOUT, radio=radio, lat=lat, lng=lng
    )
    cuerpo = json.dumps({'data': query}).encode('utf-8')
    req = urllib.request.Request(
        OVERPASS_ENDPOINT,
        data=cuerpo,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=OVERPASS_TIMEOUT) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _mapear_elemento_overpass(elemento, lat_ref, lng_ref):
    """Convierte un elemento de Overpass al formato usado por el frontend."""
    tipo = elemento.get('type')
    if tipo == 'node':
        el_lat = elemento.get('lat')
        el_lng = elemento.get('lon')
    elif tipo == 'way':
        centro = elemento.get('center', {}) or {}
        el_lat = centro.get('lat')
        el_lng = centro.get('lon')
    else:
        return None

    if el_lat is None or el_lng is None:
        return None

    tags = elemento.get('tags', {}) or {}
    nombre = tags.get('name') or 'Clínica veterinaria'
    direccion_partes = []
    if tags.get('addr:street'):
        direccion_partes.append(tags['addr:street'])
    if tags.get('addr:housenumber'):
        direccion_partes.append(tags['addr:housenumber'])
    direccion = ' '.join(direccion_partes) or tags.get('addr:full') or ''
    telefono = tags.get('phone') or ''

    distancia_m = _distancia_metros(lat_ref, lng_ref, el_lat, el_lng)

    return {
        'id': f"overpass-{tipo}-{elemento.get('id')}",
        'nombre': nombre,
        'direccion': direccion,
        'telefono': telefono,
        'lat': el_lat,
        'lng': el_lng,
        'distancia_m': round(distancia_m, 1),
        'fuente': 'overpass',
    }


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


@mapa_bp.route('/clinicas/reales')
def clinicas_reales():
    """Clínicas veterinarias reales cercanas usando Overpass API (OpenStreetMap).

    Si Overpass no responde, hace fallback a las clínicas de la base local.
    """
    try:
        lat = float(request.args['lat'])
        lng = float(request.args['lng'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Los parámetros lat y lng son obligatorios.'}), 400

    try:
        radio = float(request.args.get('radio', 10000))
    except ValueError:
        return jsonify({'error': 'El radio debe ser un número en metros.'}), 400

    datos = _consultar_overpass(lat, lng, radio)

    if datos is None:
        # Fallback a BD local si Overpass no está disponible.
        filas = db.session.execute(
            text(SQL_CERCANAS),
            {'lat': lat, 'lng': lng, 'radio': radio},
        ).fetchall()
        return jsonify({
            'fuente': 'local',
            'clinicas': [
                {
                    'id': fila.id,
                    'nombre': fila.nombre,
                    'direccion': fila.direccion,
                    'telefono': fila.telefono,
                    'lat': fila.lat,
                    'lng': fila.lng,
                    'distancia_m': round(float(fila.distancia_m), 1),
                    'abierto_24_7': fila.abierto_24_7,
                    'fuente': 'local',
                }
                for fila in filas
            ],
        })

    clinicas = []
    for elemento in datos.get('elements', []):
        mapeado = _mapear_elemento_overpass(elemento, lat, lng)
        if mapeado is not None:
            clinicas.append(mapeado)

    clinicas.sort(key=lambda c: c['distancia_m'])
    return jsonify({'fuente': 'overpass', 'clinicas': clinicas})
