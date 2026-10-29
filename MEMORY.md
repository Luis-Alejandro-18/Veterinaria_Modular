# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-10-28
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- Backend Flask inicializado (`app.py`) con SQLAlchemy + PostgreSQL/PostGIS.
- 6 tablas en `veterinaria_db`: usuarios, mascotas, clinicas, consultas, evidencias, respuestas_orientacion. Todas **vacías**.
- PostGIS activo: `clinicas.coordenadas` = POINT SRID 4326.
- Endpoints implementados en Blueprints (`routes/`): auth (registro/login/logout), mascotas (CRUD), triaje (consulta, evidencias, respuestas, estado) y mapa (Leaflet + PostGIS).
- Frontend básico con plantillas Jinja2 y `estilosGlobales.css`; `static/uploads/` se crea al arrancar.
- `requirements.txt` y `.gitignore` creados; `.env` no versionado.
- `README.md` con instrucciones de instalación, configuración y estructura creado.
- `CONTRIBUTING.md` con el flujo de ramas, commits y PRs creado.
- `database.py` movido a `legacy/database.py` (no se usa).
- Repo Git inicializado y sincronizado con `origin/main` en GitHub (Luis-Alejandro-18/Veterinaria_Modular).

## Decisiones (y por qué)
- SQLAlchemy como única vía de conexión: evita duplicidad; `database.py` con psycopg2 quedó en `legacy/`.
- `db.create_all()` al arrancar: simple para la etapa inicial; sin Alembic/migraciones.
- PostGIS SRID 4326: estándar GPS lat/lng para geolocalización en el AMG.
- `.gitignore` excluye `.env` y `.venv/`: evitar subir credenciales y entorno local.
- `MEMORY.md` separado de `AGENTS.md`: mantener `AGENTS.md` corto y estable; lo volátil va aquí.
- Blueprints por módulo: permiten trabajo en paralelo sin conflictos en `app.py`.
- Sesiones Flask para auth: simple y suficiente para el MVP; contraseñas con `werkzeug.security`.
- Urgencia por reglas de palabras clave: rápido de implementar y explicable; se puede mejorar luego.
- Leaflet para el mapa: gratuito y sin API key; el backend expone JSON (`/clinicas`).

## Aprendizajes y errores a evitar
- `app.py` falla silenciosamente si PostgreSQL/PostGIS no están disponibles: revisar la consola al iniciar.
- No asumir que las tablas tienen datos: están vacías hasta insertar registros.
- No editar `legacy/database.py` como si fuera activo.
- Verificar el estado real de la BD antes de codificar contra ella (pgAdmin o consulta SQL de solo lectura).
- En PowerShell, invocar el venv con `& "...\.venv\Scripts\python.exe" "script.py"`.
- En Windows, evitar emojis en `print()` de Python (cp1252 lanza `UnicodeEncodeError`); usar `[OK]`/`[ERROR]`.

## Próximos pasos
- Insertar clínicas de ejemplo (seed) para probar el mapa en el AMG.
- Añadir pruebas automatizadas del flujo (pytest) y CI.
- Mejorar validación de formularios y manejo de errores.
- Revisar roles/permisos (veterinario vs dueño) y cierre de consultas.
