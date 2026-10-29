# AGENTS.md — Veterinaria_Modular

## Propósito del proyecto
Plataforma e-health para triaje digital de emergencias veterinarias, primeros auxilios y geolocalización de clínicas 24/7 en el Área Metropolitana de Guadalajara (AMG).

## Stack
Python 3.10+, Flask, Flask-SQLAlchemy, GeoAlchemy2, PostgreSQL + PostGIS, python-dotenv, Pillow. Frontend: HTML5 (Jinja2), CSS3, JS nativo (Leaflet / Google Maps API).

## Entrypoint y ejecución
- Archivo principal: `app.py` (Flask). Ejecutar: `python app.py` desde la raíz del repo con el venv activo (`.venv\Scripts\activate` en Windows).
- `requirements.txt` existe (Flask, Flask-SQLAlchemy, GeoAlchemy2, Pillow, psycopg2-binary, etc.).
- No hay tests ni CI.
- Rutas organizadas en Blueprints dentro de `routes/`: `auth.py`, `mascotas.py`, `triaje.py`, `mapa.py`.

## Estado del repositorio
- `database.py` movido a `legacy/database.py` (fuera del flujo activo; no se usa).
- `.gitignore` creado (excluye `.env`, `.venv/`, `__pycache__/`, etc.).
- `requirements.txt` generado.
- Repo Git inicializado y publicado en GitHub (`origin/main`).

## Base de datos
- Motor: PostgreSQL con extensión PostGIS (SRID 4326 para coordenadas GPS).
- Credenciales en `.env` (no versionar): `DB_HOST=localhost`, `DB_PORT=5432`, `DB_NAME=veterinaria_db`, `DB_USER=postgres`, `DB_PASSWORD=123456`, `SECRET_KEY=...`, `FLASK_ENV=development`.
- `app.py` ejecuta `CREATE EXTENSION IF NOT EXISTS postgis;` y `db.create_all()` al iniciar. Si PostgreSQL/PostGIS no están instalados ni la base `veterinaria_db` creada, falla silenciosamente (solo imprime error).
- `database.py` está movido a `legacy/database.py` (legacy): usa psycopg2 directamente. La conexión y el esquema reales viven en `app.py` vía SQLAlchemy.

## Modelos (models.py, 6 tablas)
`usuarios`, `mascotas`, `clinicas`, `consultas`, `evidencias`, `respuestas_orientacion`. Las clínicas guardan `coordenadas` como `Geometry(POINT, srid=4326)`. No hay migraciones (Alembic); las tablas se crean al arrancar Flask.

## Rutas principales
- Auth: `/registro`, `/login`, `/logout` (sesiones Flask, contraseñas con hash).
- Mascotas: `/mascotas/` (listar, crear, ver, editar, eliminar).
- Triaje: `/triaje/` (crear consulta, evidencia, respuesta, cambio de estado). Urgencia por reglas de palabras clave.
- Mapa: `/mapa` (Leaflet), `/clinicas`, `/clinicas/cercanas?lat=&lng=&radio=` (PostGIS).

## Frontend
- Plantillas Jinja2 en `templates/` (base, auth, mascotas, triaje, mapa) y estilos en `static/css/estilosGlobales.css`.
- `static/uploads/` se crea al arrancar `app.py` y está excluido por `.gitignore`.

## Gotchas (probable fuente de errores)
- No tratar `legacy/database.py` como activo: es legacy; no añadir esquemas ahí.
- Al añadir rutas nuevas, crear un Blueprint en `routes/` y registrarlo en `app.py`.
- `.env` es fuente de verdad para credenciales; no adivinar valores.
- Las tablas de la app están vacías hasta que se inserte datos; verificar con pgAdmin o consulta SQL antes de asumir que hay registros.

## Forma de trabajar
- Haz solo lo que se pide: no añadas funcionalidades por tu cuenta.
- Cambios pequeños y enfocados; no reescribas lo que ya funciona.
- Al terminar, resume qué has cambiado y cualquier decisión que deba revisar.

## Memoria
- Al empezar, lee `MEMORY.md` para conocer el estado del proyecto y las decisiones tomadas.
- Al terminar una tarea, actualízalo: estado actual, decisiones importantes (con su porqué) y errores a evitar.
- Mantenlo breve (máximo ~50 líneas): resume o elimina lo que ya no aporte.
- Si algo se convierte en una regla permanente, propón moverlo a `AGENTS.md` en lugar de dejarlo en la memoria.
- No guardes nunca datos sensibles (claves, tokens, datos personales).
- Al empezar, si `MEMORY.md` contradice el código o el estado real, corrígelo antes de continuar.
- Registra la fecha de última actualización en `MEMORY.md` para detectar cuándo está desactualizado. 
