"""Contenido orientativo de primeros auxilios para el MVP."""

GUIA_PRIMEROS_AUXILIOS = {
    'Urgente': {
        'titulo': 'Actúa ahora: traslado urgente',
        'resumen': (
            'Los signos descritos pueden indicar una emergencia. '
            'Mantén la calma y busca atención veterinaria inmediata.'
        ),
        'pasos': [
            'Llama a la clínica 24/7 más cercana y avisa que vas en camino.',
            'Mantén a tu mascota en un lugar seguro, tranquilo y con temperatura estable.',
            'No le administres medicamentos humanos ni alimentos.',
            'Si hay hemorragia, presiona con una gasa o tela limpia sin retirarla.',
            'Si sospechas una lesión en columna o huesos, evita moverla bruscamente.',
            'Durante una convulsión, aparta objetos peligrosos y no le metas las manos en la boca.',
            'Si fue envenenamiento, conserva el empaque o la sustancia y no induzcas el vómito.',
        ],
        'advertencia': (
            'Esta guía es orientativa y no sustituye la valoración de un veterinario.'
        ),
    },
    'Moderado': {
        'titulo': 'Vigila de cerca y consulta pronto',
        'resumen': (
            'Los signos no parecen críticos, pero conviene una revisión veterinaria '
            'en las próximas horas.'
        ),
        'pasos': [
            'Observa si los síntomas empeoran o aparecen signos de alarma.',
            'Mantén agua limpia disponible y evita cambios bruscos de alimentación.',
            'No administres medicamentos sin indicación veterinaria.',
            'Aísla a tu mascota de otros animales si hay vómito, diarrea o secreciones.',
            'Anota la hora de inicio de los síntomas y los cambios que observes.',
        ],
        'advertencia': (
            'Si aparece dificultad para respirar, sangrado, convulsión o decaimiento '
            'extremo, acude de inmediato.'
        ),
    },
    'Leve': {
        'titulo': 'Observación en casa',
        'resumen': (
            'Por ahora no se detectaron signos de alarma, pero conviene monitorear.'
        ),
        'pasos': [
            'Vigila durante las próximas 24 horas el apetito, la energía y las deposiciones.',
            'Mantén agua limpia y un lugar cómodo para descansar.',
            'Evita automedicar y no fuerces a comer si no quiere.',
            'Si los síntomas persisten o empeoran, solicita una consulta veterinaria.',
        ],
        'advertencia': (
            'Ante cualquier duda o cambio brusco, contacta a tu veterinario.'
        ),
    },
}


def obtener_guia(nivel_urgencia):
    """Devuelve la guía de primeros auxilios para el nivel indicado."""
    return GUIA_PRIMEROS_AUXILIOS.get(nivel_urgencia, GUIA_PRIMEROS_AUXILIOS['Leve'])
