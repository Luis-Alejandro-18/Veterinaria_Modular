# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-10-24
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- Backend Flask inicializado (`app.py`) con SQLAlchemy + PostgreSQL/PostGIS.
- 6 tablas en `veterinaria_db`: usuarios, mascotas, clinicas, consultas, evidencias, respuestas_orientacion. Todas **vacías**.
- PostGIS activo: `clinicas.coordenadas` = POINT SRID 4326.
- Solo existe la ruta `GET /`; frontend vacío (`index.html` y `estilosGlobales.css` en 0 líneas).
- `requirements.txt` y `.gitignore` creados; `.env` no versionado.
- `database.py` movido a `legacy/database.py` (no se usa).
- Repo Git aún no inicializado.

## Decisiones (y por qué)
- SQLAlchemy como única vía de conexión: evita duplicidad; `database.py` con psycopg2 quedó en `legacy/`.
- `db.create_all()` al arrancar: simple para la etapa inicial; sin Alembic/migraciones.
- PostGIS SRID 4326: estándar GPS lat/lng para geolocalización en el AMG.
- `.gitignore` excluye `.env` y `.venv/`: evitar subir credenciales y entorno local.
- `MEMORY.md` separado de `AGENTS.md`: mantener `AGENTS.md` corto y estable; lo volátil va aquí.

## Aprendizajes y errores a evitar
- `app.py` falla silenciosamente si PostgreSQL/PostGIS no están disponibles: revisar la consola al iniciar.
- No asumir que las tablas tienen datos: están vacías hasta insertar registros.
- No editar `legacy/database.py` como si fuera activo.
- Verificar el estado real de la BD antes de codificar contra ella (pgAdmin o consulta SQL de solo lectura).
- En PowerShell, invocar el venv con `& "...\.venv\Scripts\python.exe" "script.py"`.

## Próximos pasos
- Inicializar Git y subir a GitHub (`.gitignore` ya listo).
- Diseñar endpoints de triaje, registro y mapa.
- Crear `triage.html` y `mapa.html` + estilos en `estilosGlobales.css`.
- Integrar Leaflet/Google Maps para clínicas 24/7.
- Añadir `static/uploads/` y lógica de evidencias (Pillow).
