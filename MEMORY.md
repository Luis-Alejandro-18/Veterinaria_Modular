# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-11-05
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- Rama activa: `feature/fase4-frontend` (Fase 4 en progreso).
- MVP académico con Flask + SQLAlchemy + PostgreSQL/PostGIS. 6 tablas.
- Endpoints en Blueprints (`routes/`): auth, mascotas (CRUD), triaje (consulta, evidencias, respuesta, estado) y mapa (Leaflet + PostGIS).
- Fase 4 completada (mapa): clínicas reales vía Overpass API (OpenStreetMap), geolocalización automática al cargar, marcador de ubicación del usuario, toggle entre clínicas reales y base local, fallback automático a BD local si Overpass falla.
- Frontend mejorado: diseño con SVG icons, dashboard con estadísticas, plantillas reestructuradas.

## Decisiones (y por qué)
- Overpass API (OpenStreetMap) sin clave de API; gratis y sin registro.
- Endpoint `GET /clinicas/reales?lat=&lng=&radio=` consulta `amenity=veterinary` y hace fallback a BD local si Overpass no responde.
- Distancia haversine calculada en Python para resultados de Overpass (no hay PostGIS en esa respuesta).
- IDs de clínicas Overpass con prefijo `overpass-{tipo}-{id}` para no colisionar con IDs de BD.
- `urllib.request` de stdlib para no añadir dependencias (`requests` no está en requirements).

## Aprendizajes y errores a evitar
- Overpass puede estar lento o no responder; siempre tener fallback a BD local.
- Los datos de OpenStreetMap dependen de lo mapeado en cada zona; no garantiza cobertura completa de clínicas reales en el AMG.
- No añadir claves de API al repo; Overpass no necesita clave, pero si se cambia a Google Places se usaría `.env`.
- Los tests generales desactivan CSRF; el test dedicado usa `client_csrf`.
- `pytest` reinicia solo `veterinaria_db_test`; no ejecutar pruebas contra `veterinaria_db`.

## Próximos pasos
- Fase 4 pendiente: wizard de triaje y panel veterinario (vistas).
- Opcional: CI con PostgreSQL/PostGIS.
