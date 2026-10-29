# app.py
import os
from flask import Flask, render_template, g
from dotenv import load_dotenv
from sqlalchemy import text
from models import db  # Importamos la instancia de la base de datos de nuestros modelos

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

        # Esto lee models.py y crea las 6 tablas automáticamente en PostgreSQL
        db.create_all()
        print("[OK] Base de datos inicializada y tablas creadas exitosamente.")
    except Exception as e:
        print(f"[ERROR] Error al inicializar la base de datos: {e}")

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
    load_logged_in_user()


@app.context_processor
def inject_usuario():
    return {'usuario_actual': getattr(g, 'usuario', None)}


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
