# app.py
import os
from datetime import timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request
from sqlalchemy import text

from models import db  # Instancia de la base de datos de nuestros modelos

# Cargar las variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración de conexión a PostgreSQL
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "veterinaria_db")

# URI de conexión para SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Aseguramos que exista la carpeta de subidas de evidencias
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializamos la base de datos con la aplicación
db.init_app(app)

# Crear las tablas al iniciar el servidor (si no existen)
with app.app_context():
    try:
        # Aseguramos que PostGIS esté activado antes de crear las tablas
        db.session.execute(text('CREATE EXTENSION IF NOT EXISTS postgis;'))
        db.session.commit()

        # Lee models.py y crea las 6 tablas automáticamente en PostgreSQL
        db.create_all()
        print("[OK] Base de datos inicializada y tablas creadas exitosamente.")
    except Exception as e:
        print(f"[ERROR] Error al inicializar la base de datos: {e}")

# Zona horaria local. En Windows puede faltar la base IANA (tzdata);
# en ese caso usamos UTC-6 fijo (Guadalajara no aplica horario de verano).
try:
    from zoneinfo import ZoneInfo
    TZ_LOCAL = ZoneInfo('America/Mexico_City')
except Exception:
    TZ_LOCAL = timezone(timedelta(hours=-6), name='America/Mexico_City')


@app.template_filter('local_time')
def local_time(value, fmt='%Y-%m-%d %H:%M'):
    """Convierte una fecha UTC naive a la hora local de Guadalajara."""
    if value is None:
        return '—'
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(TZ_LOCAL).strftime(fmt)


# Registro de blueprints
from routes.auth import auth_bp
from routes.mascotas import mascotas_bp
from routes.triaje import triaje_bp
from routes.mapa import mapa_bp
from routes.utils import load_logged_in_user

app.register_blueprint(auth_bp)
app.register_blueprint(mascotas_bp)
app.register_blueprint(triaje_bp)
app.register_blueprint(mapa_bp)


@app.before_request
def before_request():
    # Evita consultar la BD por cada archivo estático
    if request.endpoint == 'static':
        return
    load_logged_in_user()


@app.context_processor
def inject_usuario():
    return {'usuario_actual': getattr(g, 'usuario', None)}


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/clinicas'):
        return jsonify({'error': 'Recurso no encontrado.'}), 404
    return render_template('errors/404.html'), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    return render_template('errors/413.html'), 413


@app.errorhandler(500)
def internal_error(error):
    try:
        db.session.rollback()
    except Exception:
        pass
    # Evita que la plantilla de error consulte una sesión de BD rota
    g.usuario = None
    if request.path.startswith('/clinicas'):
        return jsonify({'error': 'Error interno del servidor.'}), 500
    return render_template('errors/500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
