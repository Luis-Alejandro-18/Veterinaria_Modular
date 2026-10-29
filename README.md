# Veterinaria_Modular

Plataforma e-health para la atención y orientación preliminar en emergencias veterinarias mediante triaje digital, primeros auxilios y geolocalización de clínicas 24/7 en el Área Metropolitana de Guadalajara (AMG).

Backend construido con Python, Flask, Flask-SQLAlchemy, PostgreSQL y PostGIS.

## Requisitos previos

- Python 3.10+
- PostgreSQL (con extensión PostGIS disponible)
- Git

## Instalación y configuración local

1. Clonar el repositorio:

```bash
git clone https://github.com/Luis-Alejandro-18/Veterinaria_Modular.git
cd Veterinaria_Modular
```

2. Crear y activar el entorno virtual:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Crear la base de datos `veterinaria_db` (si no existe), desde terminal o pgAdmin 4:

```bash
createdb -U postgres veterinaria_db
```

5. Crear el archivo `.env` en la raíz (no se versiona):

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=veterinaria_db
DB_USER=postgres
DB_PASSWORD=tu_password
SECRET_KEY=cambia_esta_clave
FLASK_ENV=development
```

6. Ejecutar el servidor de desarrollo:

```bash
python app.py
```

Disponible en `http://localhost:5000`. Al iniciar, la aplicación habilita PostGIS y crea las tablas automáticamente.

## Datos de ejemplo para el mapa

La tabla `clinicas` empieza vacía. Para cargar 12 clínicas ficticias del AMG y probar el mapa:

```bash
python seed_clinicas.py
# Si ya existen y quieres recargarlas:
python seed_clinicas.py --force
```

> Los datos son ficticios y solo sirven para la demo académica. No deben usarse para emergencias reales.

## Primeros auxilios y estados de la consulta

- Cada consulta muestra una guía orientativa de primeros auxilios según el nivel de urgencia (`Leve`, `Moderado`, `Urgente`). No sustituye la valoración de un veterinario.
- Transiciones permitidas:
  - `Pendiente` → `En Atención`, `Requiere Presencial` o `Cerrada`
  - `En Atención` → `Requiere Presencial` o `Cerrada`
  - `Requiere Presencial` → `En Atención` o `Cerrada`
  - `Cerrada` → sin cambios
- Una consulta cerrada no acepta nuevas respuestas ni evidencias.

## Tests

```bash
python -m pytest -q
```

`tests/conftest.py` crea automáticamente la base `veterinaria_db_test` (a partir de `DB_NAME`) y reinicia sus tablas en cada prueba. Requiere PostgreSQL/PostGIS y permisos para crear bases. No usa la base de desarrollo.

## Estado actual

- Backend Flask con 6 tablas: `usuarios`, `mascotas`, `clinicas`, `consultas`, `evidencias`, `respuestas_orientacion`.
- Endpoints de autenticación, mascotas, triaje y mapa implementados (Blueprints en `routes/`).
- Fases 1 y 2 completadas: borrado en cascada con limpieza de archivos, veterinario responsable, hora local, cédula sin bloqueo, seed de clínicas, páginas 404/413/500, guía de primeros auxilios, transiciones de estado validadas y tests smoke con pytest.
- Frontend básico con plantillas Jinja2 y estilos; mapa con Leaflet.
- Sin migraciones: las tablas se crean con `db.create_all()` al iniciar.

## Estructura del proyecto

```
app.py               # Servidor Flask y configuración de la BD
models.py            # Modelos SQLAlchemy + GeoAlchemy2
constants.py         # Roles, niveles de urgencia y estados
data/                # Contenido de primeros auxilios
seed_clinicas.py     # Datos de ejemplo para el mapa
routes/              # Blueprints (auth, mascotas, triaje, mapa)
tests/               # Pruebas smoke (base de datos separada)
pytest.ini           # Configuración de pytest
requirements.txt     # Dependencias
templates/           # Plantillas Jinja2 (incluye errors/)
static/css/          # Estilos
static/uploads/      # Evidencias (creado al arrancar, no versionado)
legacy/              # Código deprecado (database.py)
```

## Contribución

- Trabaja en una rama propia (`feature/...`, `fix/...`).
- Abre un Pull Request hacia `main`.
- Usa convención de commits (`feat:`, `fix:`, `docs:`).
