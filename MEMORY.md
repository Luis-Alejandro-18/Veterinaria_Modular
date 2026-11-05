# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-11-05 (Fase 4 completada)
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- Rama activa: `feature/fase4-frontend` (Fase 4 en progreso).
- MVP académico con Flask + SQLAlchemy + PostgreSQL/PostGIS. 6 tablas.
- Endpoints en Blueprints (`routes/`): auth, mascotas (CRUD), triaje (consulta, evidencias, respuesta, estado) y mapa (Leaflet + PostGIS).
- Fase 4 completada (mapa): clínicas reales vía Overpass API (OpenStreetMap), geolocalización automática al cargar, marcador de ubicación del usuario, toggle entre clínicas reales y base local, fallback automático a BD local si Overpass falla, radio de búsqueda configurable (2/5/10/20 km, default 5 km).
- Registro separado completado: `/registro` (landing de selección), `/registro/dueno` (sin cédula), `/registro/veterinario` (cédula obligatoria).
- Vista veterinario tipo Uber completada: `/veterinario/consultas-disponibles`, tomar consulta, `/veterinario/mis-consultas`.
- Chat de seguimiento completado: modelo MensajeConsulta, endpoints GET/POST /triaje/<id>/chat, historial y chat rápido en detalle.
- Frontend mejorado: diseño con SVG icons, dashboard con estadísticas, plantillas reestructuradas.

## Decisiones (y por qué)
- Overpass API (OpenStreetMap) sin clave de API; gratis y sin registro.
- Endpoint `GET /clinicas/reales?lat=&lng=&radio=` consulta `amenity=veterinary` y hace fallback a BD local si Overpass no responde o devuelve 0 elementos. Default de radio: 5000 m.
- Consulta Overpass via GET con parametro `data` + header User-Agent (formato estandar del API).
- Múltiples instancias de Overpass con retry: overpass-api.de y overpass.kumi.systems.
- Timeout de 60s para consultas Overpass.
- Distancia haversine calculada en Python para resultados de Overpass (no hay PostGIS en esa respuesta).
- IDs de clínicas Overpass con prefijo `overpass-{tipo}-{id}` para no colisionar con IDs de BD.
- `urllib.request` de stdlib para no añadir dependencias (`requests` no está en requirements).

## Aprendizajes y errores a evitar
- Overpass puede estar lento, no responder o rechazar peticiones sin User-Agent; siempre tener fallback a BD local.
- Los datos de OpenStreetMap dependen de lo mapeado en cada zona; no garantiza cobertura completa de clínicas reales en el AMG.
- No añadir claves de API al repo; Overpass no necesita clave, pero si se cambia a Google Places se usaría `.env`.
- Los tests generales desactivan CSRF; el test dedicado usa `client_csrf`.
- `pytest` reinicia solo `veterinaria_db_test`; no ejecutar pruebas contra `veterinaria_db`.

## Próximos pasos
- Fase 4 completada: mapa con Overpass, registro separado, vista veterinario tipo Uber, chat de seguimiento.
- Opcional: CI con PostgreSQL/PostGIS.
