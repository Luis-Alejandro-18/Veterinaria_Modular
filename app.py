# app.py
import os
from flask import Flask
from dotenv import load_dotenv
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

# Inicializamos la base de datos con la aplicación
db.init_app(app)

# Crear las tablas al iniciar el servidor (si no existen)
with app.app_context():
    try:
        # Aseguramos que PostGIS esté activado antes de crear las tablas
        db.session.execute(db.text('CREATE EXTENSION IF NOT EXISTS postgis;'))
        db.session.commit()
        
        # Esto lee models.py y crea las 6 tablas automáticamente en PostgreSQL
        db.create_all()
        print("✅ Base de datos inicializada y tablas creadas exitosamente.")
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")

@app.route('/')
def index():
    return "¡Servidor de Emergencias Veterinarias en línea y conectado a PostgreSQL!"

if __name__ == '__main__':
    app.run(debug=True)