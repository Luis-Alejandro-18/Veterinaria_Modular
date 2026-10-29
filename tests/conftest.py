import os
import sys
from pathlib import Path

import psycopg2
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

TEST_DB_BASE = os.getenv('DB_NAME', 'veterinaria_db')
TEST_DB = TEST_DB_BASE if TEST_DB_BASE.endswith('_test') else f'{TEST_DB_BASE}_test'


def _crear_base_de_pruebas():
    """Crea la base de datos de pruebas si todavía no existe."""
    conexion = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD'),
        dbname='postgres',
        connect_timeout=5,
    )
    conexion.autocommit = True
    with conexion.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (TEST_DB,))
        if cursor.fetchone() is None:
            cursor.execute(f'CREATE DATABASE "{TEST_DB}"')
    conexion.close()


_crear_base_de_pruebas()
# app.py lee DB_NAME al importarse; debe apuntar a la base de pruebas.
os.environ['DB_NAME'] = TEST_DB

from app import app  # noqa: E402
from models import db  # noqa: E402

app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as cliente:
        yield cliente


@pytest.fixture
def client_csrf():
    """Cliente con CSRF activo para probar la protección de formularios."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        with app.test_client() as cliente:
            yield cliente
    finally:
        app.config['WTF_CSRF_ENABLED'] = False


@pytest.fixture(autouse=True)
def uploads_temporales(tmp_path):
    """Evita escribir evidencias reales durante las pruebas."""
    ruta_original = app.config['UPLOAD_FOLDER']
    ruta = tmp_path / 'uploads'
    ruta.mkdir()
    app.config['UPLOAD_FOLDER'] = str(ruta)
    try:
        yield ruta
    finally:
        app.config['UPLOAD_FOLDER'] = ruta_original


@pytest.fixture(autouse=True)
def base_limpia():
    """Deja las tablas vacías antes y después de cada prueba."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()
