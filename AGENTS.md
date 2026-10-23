# AGENTS.md — Veterinaria_Modular

## Propósito del proyecto
Plataforma e-health para triaje digital de emergencias veterinarias, primeros auxilios y geolocalización de clínicas 24/7 en el Área Metropolitana de Guadalajara (AMG).

## Stack
Python 3.10+, Flask, Flask-SQLAlchemy, GeoAlchemy2, PostgreSQL + PostGIS, python-dotenv, Pillow. Frontend: HTML5 (Jinja2), CSS3, JS nativo (Leaflet / Google Maps API).

## Entrypoint y ejecución
- Archivo principal: `app.py` (Flask). Ejecutar: `python app.py` desde la raíz del repo con el venv activo (`.venv\Scripts\activate` en Windows).
- No hay `requirements.txt`, tests ni CI.
- Hoy solo existe la ruta `GET /`; triage, mapa y demás endpoints aún no están implementados.

## Base de datos
- Motor: PostgreSQL con extensión PostGIS (SRID 4326 para coordenadas GPS).
- Credenciales en `.env` (no versionar): `DB_HOST=localhost`, `DB_PORT=5432`, `DB_NAME=veterinaria_db`, `DB_USER=postgres`, `DB_PASSWORD=123456`, `SECRET_KEY=...`, `FLASK_ENV=development`.
- `app.py` ejecuta `CREATE EXTENSION IF NOT EXISTS postgis;` y `db.create_all()` al iniciar. Si PostgreSQL/PostGIS no están instalados ni la base `veterinaria_db` creada, falla silenciosamente (solo imprime error).
- `database.py` está DEPRECADO: usa psycopg2 directamente. La conexión y el esquema reales viven en `app.py` vía SQLAlchemy.

## Modelos (models.py, 6 tablas)
`usuarios`, `mascotas`, `clinicas`, `consultas`, `evidencias`, `respuestas_orientacion`. Las clínicas guardan `coordenadas` como `Geometry(POINT, srid=4326)`. No hay migraciones (Alembic); las tablas se crean al arrancar Flask.

## Frontend (vacío hoy)
- `templates/index.html` y `static/css/estilosGlobales.css` existen pero tienen 0 líneas. Plantillas planeadas: `index.html`, `triage.html`, `mapa.html`.
- `static/uploads/` (imágenes de evidencias médicas) aún no existe.

## Gotchas (probable fuente de errores)
- No tratar `database.py` como activo: es legacy; no añadir esquemas ahí.
- `.env` es fuente de verdad para credenciales; no adivinar valores.
- Las tablas de la app están vacías hasta que se inserte datos; verificar con pgAdmin o consulta SQL antes de asumir que hay registros.