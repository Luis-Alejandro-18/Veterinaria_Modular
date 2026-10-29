# models.py
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry

# Inicializamos la instancia de SQLAlchemy
db = SQLAlchemy()


def utcnow():
    """Fecha/hora actual en UTC, sin tzinfo, para columnas DateTime sin zona."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # Contraseña hasheada
    rol = db.Column(db.String(20), nullable=False)  # 'dueno' o 'veterinario'
    cedula_profesional = db.Column(db.String(50), nullable=True)  # Solo para veterinarios
    fecha_registro = db.Column(db.DateTime, default=utcnow)

    # Relaciones
    mascotas = db.relationship(
        'Mascota',
        backref='dueno',
        lazy=True,
        cascade='all, delete-orphan',
    )


class Mascota(db.Model):
    __tablename__ = 'mascotas'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    especie = db.Column(db.String(50), nullable=False)  # Perro, Gato, etc.
    raza = db.Column(db.String(50), nullable=True)
    edad_anios = db.Column(db.Integer, nullable=True)
    peso_kg = db.Column(db.Float, nullable=True)
    condiciones_previas = db.Column(db.Text, nullable=True)  # Alergias, enfermedades

    # Relaciones
    consultas = db.relationship(
        'Consulta',
        backref='mascota',
        lazy=True,
        cascade='all, delete-orphan',
    )


class Clinica(db.Model):
    __tablename__ = 'clinicas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    direccion = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    # PostGIS: SRID 4326 es el estándar GPS para latitud/longitud
    coordenadas = db.Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    abierto_24_7 = db.Column(db.Boolean, default=True)


class Consulta(db.Model):
    __tablename__ = 'consultas'

    id = db.Column(db.Integer, primary_key=True)
    mascota_id = db.Column(db.Integer, db.ForeignKey('mascotas.id'), nullable=False)
    veterinario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)  # Se llena al tomar el caso

    sintomas = db.Column(db.Text, nullable=False)
    nivel_urgencia = db.Column(db.String(20), nullable=True)  # 'Leve', 'Moderado', 'Urgente'
    estado = db.Column(db.String(50), default='Pendiente')  # 'Pendiente', 'En Atención', 'Requiere Presencial', 'Cerrada'

    # Seguro legal: el usuario acepta que esto es triaje, no un diagnóstico definitivo
    acepta_terminos_triage = db.Column(db.Boolean, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=utcnow)

    # Relaciones
    evidencias = db.relationship(
        'Evidencia',
        backref='consulta',
        lazy=True,
        cascade='all, delete-orphan',
    )
    respuestas = db.relationship(
        'RespuestaOrientacion',
        backref='consulta',
        lazy=True,
        cascade='all, delete-orphan',
    )
    veterinario = db.relationship('Usuario', backref='consultas_atendidas', lazy=True)


class Evidencia(db.Model):
    __tablename__ = 'evidencias'

    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'), nullable=False)
    ruta_archivo = db.Column(db.String(255), nullable=False)  # Nombre/ruta del archivo; se sirve desde instance/uploads
    tipo = db.Column(db.String(20), nullable=False)  # 'imagen' o 'video'
    fecha_subida = db.Column(db.DateTime, default=utcnow)


class RespuestaOrientacion(db.Model):
    __tablename__ = 'respuestas_orientacion'

    id = db.Column(db.Integer, primary_key=True)
    consulta_id = db.Column(db.Integer, db.ForeignKey('consultas.id'), nullable=False)
    veterinario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)  # Indicaciones de estabilización
    fecha_respuesta = db.Column(db.DateTime, default=utcnow)

    veterinario = db.relationship('Usuario', backref='respuestas_orientacion', lazy=True)
