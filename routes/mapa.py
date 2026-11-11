"""Mapa de clínicas veterinarias reales usando Overpass API (OpenStreetMap)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from math import atan2, cos, radians, sin, sqrt

from flask import Blueprint, jsonify, render_template, request

mapa_bp = Blueprint('mapa', __name__)

# Instancias públicas de Overpass. Se consultan en paralelo y se usa la primera
# que responda correctamente.
OVERPASS_ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
]
# Overpass puede tardar hasta ~50 s en responder aunque el servicio esté sano.
OVERPASS_TIMEOUT = 60
OVERPASS_USER_AGENT = (
    'VeterinariaModular/1.0 (clinicas veterinarias; contacto: ejemplo@test.local)'
)
CACHE_TTL = 600  # 10 minutos
CACHE = {}

OVERPASS_QUERY = """
[out:json][timeout:{timeout}];
nwr["amenity"="veterinary"](around:{radio},{lat},{lng});
out center;
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


def _clave_cache(lat, lng, radio):
    return (round(lat, 3), round(lng, 3), int(radio))


def _pedir_endpoint(endpoint, consulta):
    """Consulta una instancia de Overpass por GET y devuelve el JSON.

    Se usa GET porque es el método que mejor funciona con las instancias
    públicas; algunos mirrors ignoran o retrasan los POST grandes.
    """
    url = endpoint + '?data=' + urllib.parse.quote(consulta)
    peticion = urllib.request.Request(
        url,
        headers={
            'User-Agent': OVERPASS_USER_AGENT,
            'Accept': 'application/json',
        },
    )
    with urllib.request.urlopen(peticion, timeout=OVERPASS_TIMEOUT) as respuesta:
        return json.loads(respuesta.read().decode('utf-8'))


def _consultar_overpass(lat, lng, radio=5000):
    """Consulta Overpass en paralelo y devuelve el primer resultado válido.

    Retorna None si todas las instancias fallan. Los resultados exitosos se
    guardan en memoria durante CACHE_TTL segundos.
    """
    clave = _clave_cache(lat, lng, radio)
    guardado = CACHE.get(clave)
    if guardado and time.time() - guardado[0] < CACHE_TTL:
        return guardado[1]

    consulta = OVERPASS_QUERY.format(
        timeout=OVERPASS_TIMEOUT, radio=int(radio), lat=lat, lng=lng
    )

    datos = None
    pool = ThreadPoolExecutor(max_workers=len(OVERPASS_ENDPOINTS))
    try:
        futuros = {
            pool.submit(_pedir_endpoint, endpoint, consulta)
            for endpoint in OVERPASS_ENDPOINTS
        }
        for futuro in as_completed(futuros, timeout=OVERPASS_TIMEOUT + 5):
            try:
                resultado = futuro.result()
            except (urllib.error.URLError, urllib.error.HTTPError,
                    OSError, ValueError):
                continue
            if isinstance(resultado, dict):
                datos = resultado
                break
    except TimeoutError:
        pass
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    if datos is not None:
        CACHE[clave] = (time.time(), datos)
    return datos


def _mapear_elemento_overpass(elemento, lat_ref, lng_ref):
    """Convierte un elemento de Overpass al formato usado por el frontend."""
    tipo = elemento.get('type')
    if tipo == 'node':
        el_lat = elemento.get('lat')
        el_lng = elemento.get('lon')
    elif tipo in ('way', 'relation'):
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


@mapa_bp.route('/clinicas/reales')
def clinicas_reales():
    """Clínicas veterinarias reales cercanas usando Overpass API (OpenStreetMap)."""
    try:
        lat = float(request.args['lat'])
        lng = float(request.args['lng'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Los parámetros lat y lng son obligatorios.'}), 400

    try:
        radio = float(request.args.get('radio', 5000))
    except ValueError:
        return jsonify({'error': 'El radio debe ser un número en metros.'}), 400

    if radio <= 0 or radio > 50_000:
        return jsonify({'error': 'El radio debe estar entre 1 y 50000 metros.'}), 400

    datos = _consultar_overpass(lat, lng, radio)
    if datos is None:
        return jsonify({
            'error': ('No se pudieron obtener clínicas reales en este momento. '
                      'Overpass puede estar saturado; intenta de nuevo en unos segundos.'),
            'fuente': 'overpass',
            'clinicas': [],
        }), 503

    clinicas = []
    for elemento in datos.get('elements', []):
        mapeado = _mapear_elemento_overpass(elemento, lat, lng)
        if mapeado is not None:
            clinicas.append(mapeado)

    clinicas.sort(key=lambda clinica: clinica['distancia_m'])
    return jsonify({'fuente': 'overpass', 'clinicas': clinicas})
