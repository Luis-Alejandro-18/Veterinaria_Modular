# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-10-28
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- MVP académico con Flask + SQLAlchemy + PostgreSQL/PostGIS. 6 tablas; 1 usuario real y 12 clínicas de ejemplo (resto vacío).
- Endpoints en Blueprints (`routes/`): auth, mascotas (CRUD), triaje (consulta, evidencias, respuesta, estado) y mapa (Leaflet + PostGIS).
- Fase 1 completada: borrado en cascada + limpieza de archivos, `veterinario_id`, hora local, cédula sin bloqueo, seed de clínicas y páginas 404/413/500.
- Frontend básico con Jinja2 y `estilosGlobales.css`; `static/uploads/` se crea al arrancar.
- Repo Git en `origin/main` (Luis-Alejandro-18/Veterinaria_Modular); `main` protegida (PR obligatorio).

## Decisiones (y por qué)
- SQLAlchemy como única vía de conexión; `legacy/database.py` no se usa.
- `db.create_all()` sin migraciones: el esquema actual alcanza para el MVP.
- PostGIS SRID 4326 para clínicas; Leaflet sin API key.
- Blueprints por módulo para trabajar en paralelo.
- Sesiones Flask + `werkzeug.security` para auth.
- Urgencia por reglas de palabras clave (MVP).
- Cédula obligatoria para veterinarios, pero sin verificación ni bloqueo de login (MVP).
- Borrado total en cascada (MVP); no se conserva historial.
- Clínicas por seed (`seed_clinicas.py`); sin CRUD de admin por ahora.
- Zona horaria: se guarda UTC naive y se muestra en `America/Mexico_City` (fallback UTC-6).

## Aprendizajes y errores a evitar
- `app.py` falla silenciosamente si PostgreSQL/PostGIS no están disponibles: revisar consola.
- No asumir datos existentes; las tablas están vacías hasta insertar.
- No editar `legacy/database.py`.
- En PowerShell: `& "...\.venv\Scripts\python.exe" "script.py"`.
- Evitar emojis en `print()` (cp1252 en Windows): usar `[OK]`/`[ERROR]`.
- Los datos de `seed_clinicas.py` son ficticios; no usar en producción.

## Próximos pasos
- Fase 2: primeros auxilios, consistencia de estados, tests smoke y docs.
- Fase 3: CSRF, evidencias privadas, filtros/paginación.
- Fase 4: frontend (diseño, dashboard, wizard, mapa, panel veterinario).
