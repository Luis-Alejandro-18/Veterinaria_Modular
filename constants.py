"""Constantes compartidas de la aplicación."""

ROLES = ('dueno', 'veterinario')

NIVELES_URGENCIA = ('Leve', 'Moderado', 'Urgente')

ESTADOS_CONSULTA = ('Pendiente', 'En Atención', 'Requiere Presencial', 'Cerrada')

ESTADO_CERRADA = 'Cerrada'

# Transiciones permitidas para el MVP.
TRANSICIONES_ESTADO = {
    'Pendiente': ('En Atención', 'Requiere Presencial', 'Cerrada'),
    'En Atención': ('Requiere Presencial', 'Cerrada'),
    'Requiere Presencial': ('En Atención', 'Cerrada'),
    'Cerrada': (),
}
