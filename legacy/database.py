import os
import psycopg2
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

def get_db_connection():
    """Establece y retorna una conexión con la base de datos PostgreSQL."""
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "veterinaria_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD")
        )
        return connection
    except Exception as e:
        print(f"\n❌ Error de conexión a PostgreSQL: {e}")
        return None

def init_db():
    """Inicializa la base de datos activando la extensión PostGIS."""
    print("Intentando conectar a la base de datos PostgreSQL...")
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                # Activar la extensión espacial PostGIS
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                conn.commit()
                print("\n✅ Conexión exitosa. Base de datos e inicialización con PostGIS correctas.")
        except Exception as e:
            print(f"\n❌ Error al habilitar PostGIS: {e}")
            conn.rollback()
        finally:
            conn.close()

# Esta línea asegura que la prueba se ejecute al correr "python database.py"
if __name__ == "__main__":
    init_db()