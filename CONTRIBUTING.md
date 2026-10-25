# Guía de Contribución

Esta guía define el flujo de trabajo del equipo para mantener el código ordenado y evitar conflictos.

## 1. Preparación inicial

Configura tu identidad en Git (una sola vez):

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu.correo@ejemplo.com"
```

Clona el repositorio:

```bash
git clone https://github.com/Luis-Alejandro-18/Veterinaria_Modular.git
cd Veterinaria_Modular
```

Instala dependencias y crea tu `.env` siguiendo el `README.md`.

## 2. Reglas de ramas

- `main`: rama estable y protegida. **No se permite push directo.**
- `feature/...`: nuevas funcionalidades. Ej: `feature/rutas-clinicas`.
- `fix/...`: corrección de errores. Ej: `fix/error-login`.
- `docs/...`: documentación. Ej: `docs/readme`.

Usa minúsculas y guiones (kebab-case), sin espacios ni acentos.

### Crear una rama nueva

```bash
git checkout main
git pull origin main
git checkout -b feature/nombre-corto
```

## 3. Convención de commits

Usa mensajes claros en imperativo con estos prefijos:

- `feat:` nueva funcionalidad — `feat: agregar endpoint de triaje`
- `fix:` corrección de errores — `fix: corregir conexión a la base de datos`
- `docs:` documentación — `docs: actualizar README`
- `chore:` mantenimiento — `chore: actualizar dependencias`
- `refactor:` reorganización sin cambio funcional (opcional)

Cada commit debe ser atómico (un cambio lógico por commit).

## 4. Pull Requests

1. Sube tu rama:

```bash
git push -u origin feature/nombre-corto
```

2. Abre un Pull Request hacia `main` en GitHub.
3. Describe qué cambia y cómo probarlo.
4. Notifica al equipo. La aprobación la realiza el **revisor de código** (`Luis-Alejandro-18`) o el compañero que se designe. Se requiere al menos **1 aprobación** para fusionar.
5. Antes de fusionar, actualiza tu rama con `main`:

```bash
git fetch origin
git rebase origin/main
# Resolver conflictos si aparecen
git push --force-with-lease
```

## 5. Después del merge

Elimina la rama local y remota:

```bash
git checkout main
git pull origin main
git branch -d feature/nombre-corto
git push origin --delete feature/nombre-corto
```

## 6. Reglas generales

- Nunca subas `.env`, credenciales, tokens ni datos personales.
- No hagas commit de `.venv/`, `__pycache__/` ni archivos temporales (ya están en `.gitignore`).
- Prueba localmente antes del PR (`python app.py`).
- Un PR debe resolver un tema; evita mezclar cambios no relacionados.

## 7. Protección de `main` (solo el revisor)

Esta configuración la realiza **únicamente el dueño del repositorio y revisor de código: `Luis-Alejandro-18`**. Los demás colaboradores no necesitan ni pueden hacerlo.

1. Ir a **Settings → Branches → Add branch protection rule**.
2. Nombre del patrón: `main`.
3. Activar **Require a pull request before merging** y **Require approvals: 1**.

Una vez guardada, la regla se aplica automáticamente a todos los colaboradores: nadie puede hacer push directo a `main`.
