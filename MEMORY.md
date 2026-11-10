# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-11-10 (Fase 4 — bandeja de solicitudes y mensajes solo de casos tomados)
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- Rama activa: `feature/fase4-frontend` (Fase 4 completada).
- MVP académico con Flask + SQLAlchemy + PostgreSQL/PostGIS. 6 tablas.
- Endpoints en Blueprints (`routes/`): auth, mascotas (CRUD), triaje (consulta, evidencias, respuesta, estado, chat) y mapa (Leaflet + PostGIS).
- Mapa completado: clínicas reales vía Overpass API (OpenStreetMap), geolocalización automática, marcador de usuario, toggle real/local, fallback a BD local, radio 2/5/10/20 km (default 5 km).
- Registro separado completado: `/registro` (landing), `/registro/dueno`, `/registro/veterinario` (cédula obligatoria).
- Vista veterinario tipo Uber completada: `/veterinario/consultas-disponibles`, tomar consulta, `/veterinario/mis-consultas`.
- Bandeja de veterinario = cola de **solicitudes por tomar** (solo `Pendiente` sin veterinario). Al tomar un caso desaparece de la bandeja y pasa a Tablero/Agenda; cerrados y en revisión no aparecen. Menú renombrado a "Solicitudes" con badge de casos disponibles.
- Sección **Mensajes** (antes "Mensajes a dueños"): solo muestra conversaciones de casos ya tomados por el veterinario (incluye cerrados como historial). El badge de no leídos cuenta solo esos casos. En Solicitudes, un contador marca los mensajes previos del dueño antes de tomar el caso.
- Chat de seguimiento completado: modelo MensajeConsulta, GET/POST /triaje/<id>/chat, historial y chat rápido en detalle.

## Triaje Virtual (estado actual)
- Formulario rediseñado: tarjeta única de dos columnas (datos del paciente + estado general a la izquierda; síntomas por gravedad a la derecha), sin indicador de "Paso 1 de 3".
- Flujo para usuarios nuevos: si no hay mascotas registradas, `/triaje/nueva` redirige a `/mascotas/nueva?next=triaje`; tras crear la mascota, vuelve al triaje con la mascota preseleccionada (`?mascota_id=<id>`). El parámetro `next` solo acepta `'triaje'` (evita open redirect).
- Botón "Evaluar Gravedad y Contactar Veterinario" funcional: validación en `submit`, siempre habilitado; alerta si no hay síntoma/radio/motivo.
- Checkbox `acepta_terminos_triage` obligatorio (exigido por el backend y la BD).
- Clasificación de urgencia corregida: normalización (minúsculas, sin acentos), límites de palabra (evita "tos" dentro de "vómitos"), estado general crítico → Urgente, predefinidos urgentes/moderados/leves, clasifica solo el `motivo` como texto libre (no el texto combinado) para evitar falsos positivos como "Heridas abiertas: no", regla de herida refinada ("herida abierta/grave/profunda" = Urgente, "herida" genérica = Moderado). Matriz de 38 casos: 38/38 correctos.
- Se guardan etiquetas amigables (no claves) en `Consulta.sintomas`.
- Nuevo estado `Sin solicitar` al crear una consulta: el dueño ve clasificación + guía de primeros auxilios + botón "Solicitar asistencia con un doctor". Evidencias, respuestas del veterinario y chat quedan ocultos hasta solicitar. Al solicitar pasa a `Pendiente` y aparece en la bandeja veterinaria. Veterinarios no ven ni pueden tomar consultas `Sin solicitar`.
- Chat de seguimiento: tras enviar un mensaje, vuelve al historial de chat (no sale de la conversación).

## Decisiones (y por qué)
- Overpass API (OpenStreetMap) sin clave de API; gratis y sin registro.
- Endpoint `GET /clinicas/reales?lat=&lng=&radio=` consulta `amenity=veterinary` y hace fallback a BD local si Overpass no responde o devuelve 0 elementos. Default de radio: 5000 m.
- Consulta Overpass via GET con parametro `data` + header User-Agent. Múltiples instancias con retry.
- `urllib.request` de stdlib para no añadir dependencias.
- `pytest` reinicia solo `veterinaria_db_test`; no ejecutar pruebas contra `veterinaria_db`.

## Aprendizajes y errores a evitar
- Overpass puede estar lento, no responder o rechazar peticiones sin User-Agent; siempre tener fallback a BD local.
- No añadir claves de API al repo.
- Los tests generales desactivan CSRF; el test dedicado usa `client_csrf`.
- Jinja2: verificar `{% block %}`/`{% endblock %}` balanceados y evitar `{% endif }` con espacio.

## Próximos pasos
- Navegación por rol: navbar condicional en base.html; veterinarios ven Consultas disponibles y Mis consultas (sin Clínicas, Mis mascotas, Triaje).
- Opcional: historial de estados, cierre con motivo, notificaciones, prioridad manual, calificación, estadísticas.
- Opcional: CI con PostgreSQL/PostGIS.

## Tests
- `tests/test_smoke.py`: 13 smoke tests + 4 tests del flujo sin mascotas + 5 tests del flujo sin solicitar + 3 tests de bandeja + 3 tests de mensajes (solo casos tomados, badge solo de tomados, indicador de chat previo).
- `tests/test_triaje.py`: nuevo, 38 casos parametrizados de `clasificar_urgencia` (incluye tu caso reportado: diarrea + tos + no come → Moderado) + 2 unitarios de mapas.
- Total: 79 passed, 0 failed.
