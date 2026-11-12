"""Constantes compartidas de la aplicación."""

ROLES = ('dueno', 'veterinario')

NIVELES_URGENCIA = ('Leve', 'Moderado', 'Urgente')

ESTADOS_CONSULTA = ('Sin solicitar', 'Pendiente', 'En Atención', 'Requiere Presencial', 'Cerrada')

ESTADO_CERRADA = 'Cerrada'
ESTADO_SIN_SOLICITAR = 'Sin solicitar'

# Transiciones permitidas para el MVP.
TRANSICIONES_ESTADO = {
    'Sin solicitar': ('Pendiente',),
    'Pendiente': ('En Atención', 'Requiere Presencial', 'Cerrada'),
    'En Atención': ('Requiere Presencial', 'Cerrada'),
    'Requiere Presencial': ('En Atención', 'Cerrada'),
    'Cerrada': (),
}

# Síntomas predefinidos para el triaje guiado, organizados por nivel de urgencia.
# Cada entrada es (valor, etiqueta_amigable).
SINTOMAS_PREDEFINIDOS = {
    'Urgente': [
        ('sangrado', 'Sangrado o herida grave'),
        ('dificultad_respirar', 'Dificultad para respirar'),
        ('convulsion', 'Convulsión'),
        ('inconsciente', 'Inconsciente o desmayo'),
        ('vomita_sangre', 'Vomita sangre'),
        ('fractura', 'Fractura o golpe fuerte'),
        ('atropello', 'Atropello o accidente'),
        ('envenenamiento', 'Envenenamiento o ingestión tóxica'),
        ('parto', 'Parto o dificultad para parir'),
    ],
    'Moderado': [
        ('vomita', 'Vomita (sin sangre)'),
        ('diarrea', 'Diarrea'),
        ('fiebre', 'Fiebre'),
        ('cojea', 'Cojera o dificultad para caminar'),
        ('dolor', 'Dolor evidente'),
        ('hinchazon', 'Hinchazón o inflamación'),
        ('letargo', 'Letargo o decaimiento'),
        ('no_come', 'No come'),
        ('tos', 'Tos persistente'),
    ],
    'Leve': [
        ('come_poco', 'Come poco'),
        ('estornudos', 'Estornudos o secreción nasal'),
        ('picazon', 'Picazón o rascado excesivo'),
        ('ojos_rojos', 'Ojos rojos o con secreción'),
        ('cambios_comportamiento', 'Cambios leves de comportamiento'),
    ],
}
