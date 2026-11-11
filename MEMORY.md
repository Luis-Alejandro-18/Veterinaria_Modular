# MEMORY.md — Veterinaria_Modular

> Última actualización: 2026-11-10 (Fase 4 — mapa solo con clínicas reales de Overpass)
> Lee este archivo al empezar una tarea y actualízalo al terminarla (máx. ~50 líneas).

## Estado actual
- Rama activa: `feature/fase4-frontend` (Fase 4 completada).
- MVP académico con Flask + SQLAlchemy + PostgreSQL/PostGIS. 6 tablas.
- Endpoints en Blueprints (`routes/`): auth, mascotas (CRUD), triaje (consulta, evidencias, respuesta, estado, chat) y mapa (Leaflet + Overpass).
- Mapa completado: solo clínicas reales vía Overpass API (OpenStreetMap), geolocalización automática, marcador de usuario, radio 2/5/10/20 km (default 5 km). Sin selector de origen ni fallback a BD local.
- Registro separado completado: `/registro` (landing), `/registro/dueno`, `/registro/veterinario` (cédula obligatoria).
- Vista veterinario tipo Uber completada: `/veterinario/consultas-disponibles`, tomar consulta, `/veterinario/mis-consultas`.
- Bandeja de veterinario = cola de **solicitudes por tomar** (solo `Pendiente` sin veterinario). Al tomar un caso desaparece de la bandeja y pasa a Tablero/Agenda; cerrados y en revisión no aparecen. Menú renombrado a "Solicitudes" con badge de casos disponibles.
- Sección **Mensajes** (antes "Mensajes a dueños"): solo muestra conversaciones de casos ya tomados por el veterinario (incluye cerrados como historial). El badge de no leídos cuenta solo esos casos. En Solicitudes, un contador marca los mensajes previos del dueño antes de tomar el caso.
- Chat bidireccional sin recargas: API JSON `/api/consultas/<id>/mensajes` (GET/POST) y `/leido`, con polling cada 2.5 s (`static/js/chat.js`). Envío optimista, auto-scroll, Enter para enviar, pausa al ocultar la pestaña y CSRF por header `X-CSRFToken`. Sin dependencias nuevas.
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
- Endpoint único `GET /clinicas/reales?lat=&lng=&radio=` con consulta `nwr["amenity"="veterinary"](around:...)`. Si Overpass falla devuelve 503 con lista vacía; **nunca** consulta la BD local. Default de radio: 5000 m.
- Consulta Overpass por GET con parámetro `data` + header User-Agent, timeout 60 s, varias instancias en paralelo (se usa la primera que responda) y caché en memoria de 10 min por lat/lng redondeadas + radio. Se soportan node/way/relation vía `out center`.
- `urllib.request` de stdlib para no añadir dependencias.
- `pytest` reinicia solo `veterinaria_db_test`; no ejecutar pruebas contra `veterinaria_db`.

## Aprendizajes y errores a evitar
- Overpass puede estar lento (30-50 s), devolver 502 o no responder; por eso hay mirror en paralelo, timeout amplio y caché. No reintroducir el fallback a BD local: mostraría datos que no son clínicas reales y ocultaría el fallo.
- No añadir claves de API al repo.
- Los tests generales desactivan CSRF; el test dedicado usa `client_csrf`.
- Jinja2: verificar `{% block %}`/`{% endblock %}` balanceados y evitar `{% endif }` con espacio.

## Próximos pasos
- Navegación por rol: navbar condicional en base.html; veterinarios ven Consultas disponibles y Mis consultas (sin Clínicas, Mis mascotas, Triaje).
- Opcional: historial de estados, cierre con motivo, notificaciones, prioridad manual, calificación, estadísticas.
- Opcional: CI con PostgreSQL/PostGIS.

## Tests
- `tests/test_smoke.py`: 12 smoke tests + 4 tests del flujo sin mascotas + 5 tests del flujo sin solicitar + 3 tests de bandeja + 3 tests de mensajes + 8 tests de la API de chat + 4 tests del mapa real (mapeo node/way/relation, sin fallback local, validación de parámetros, caché).
- `tests/test_triaje.py`: nuevo, 38 casos parametrizados de `clasificar_urgencia` (incluye tu caso reportado: diarrea + tos + no come → Moderado) + 2 unitarios de mapas.
- Total: 90 passed, 0 failed.
