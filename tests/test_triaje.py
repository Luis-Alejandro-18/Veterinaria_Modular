import pytest

from routes.triaje import clasificar_urgencia

# Cada caso: (texto_libre, sintomas_predefinidos, estado_general, esperado)
CASOS_CLASIFICACION = [
    # --- Texto libre urgente ---
    ('sangra mucho', [], {}, 'Urgente'),
    ('sangre en las heces', [], {}, 'Urgente'),
    ('comió veneno', [], {}, 'Urgente'),
    ('ingirió un tóxico', [], {}, 'Urgente'),
    ('convulsión', [], {}, 'Urgente'),
    ('convulsion', [], {}, 'Urgente'),
    ('fractura', [], {}, 'Urgente'),
    ('atropellado', [], {}, 'Urgente'),
    ('se desmayó', [], {}, 'Urgente'),
    ('no puede caminar', [], {}, 'Urgente'),
    ('herida abierta', [], {}, 'Urgente'),
    ('golpe fuerte', [], {}, 'Urgente'),
    ('dificultad respiratoria', [], {}, 'Urgente'),
    ('le cuesta respirar', [], {}, 'Urgente'),

    # --- Texto libre moderado ---
    ('vomito tres veces', [], {}, 'Moderado'),
    ('vómitos', [], {}, 'Moderado'),
    ('no quiere comer', [], {}, 'Moderado'),
    ('decaído', [], {}, 'Moderado'),
    ('cojera', [], {}, 'Moderado'),
    ('tos', [], {}, 'Moderado'),
    ('fiebre alta', [], {}, 'Moderado'),
    ('está hinchado', [], {}, 'Moderado'),

    # --- Texto libre leve ---
    ('control rutinario', [], {}, 'Leve'),

    # --- Síntomas predefinidos ---
    ('', ['vomita'], {}, 'Moderado'),
    ('', ['sangrado'], {}, 'Urgente'),
    ('', ['estornudos', 'vomita'], {}, 'Moderado'),
    ('', ['come_poco'], {}, 'Leve'),

    # --- Estado general (forzan Urgente) ---
    ('', [], {'estado_consciente': 'no'}, 'Urgente'),
    ('', [], {'estado_caminar': 'no'}, 'Urgente'),
    ('', [], {'estado_respiracion': 'dificil'}, 'Urgente'),
    ('', [], {'estado_heridas': 'si'}, 'Urgente'),
    ('', [], {'estado_consciente': 'si', 'estado_caminar': 'si',
              'estado_respiracion': 'normal', 'estado_heridas': 'no'}, 'Leve'),

    # --- Combinaciones: urgente gana sobre todo ---
    ('vomito', [], {'estado_consciente': 'no'}, 'Urgente'),
    ('tos', ['sangrado'], {}, 'Urgente'),

    # --- Sin acentos / mayúsculas ---
    ('SANGRADO ABUNDANTE', [], {}, 'Urgente'),
    ('NO RESPIRA BIEN', [], {}, 'Urgente'),

    # --- Caso reportado por el usuario: diarrea + tos + no come, estado normal ---
    ('mi perro empezo a tener problemas como de tos y no come como antes',
     ['diarrea', 'come_poco', 'picazon', 'cambios_comportamiento'],
     {'estado_consciente': 'si', 'estado_caminar': 'si',
      'estado_respiracion': 'normal', 'estado_heridas': 'no'}, 'Moderado'),

    # --- Estado general: heridas abiertas "no" no debe forzar Urgente ---
    ('', [], {'estado_consciente': 'si', 'estado_caminar': 'si',
              'estado_respiracion': 'normal', 'estado_heridas': 'no'}, 'Leve'),

    # --- Texto libre: herida abierta/grave/profunda → Urgente ---
    ('herida abierta en la pata', [], {}, 'Urgente'),
    ('herida grave en el abdomen', [], {}, 'Urgente'),
    ('herida profunda', [], {}, 'Urgente'),

    # --- Texto libre: herida genérica → Moderado (no abierta/grave/profunda) ---
    ('herida en la pata', [], {}, 'Moderado'),
    ('tiene una herida leve', [], {}, 'Moderado'),
]


@pytest.mark.parametrize('texto,predefinidos,estado,esperado', CASOS_CLASIFICACION)
def test_clasificar_urgencia(texto, predefinidos, estado, esperado):
    obtenido = clasificar_urgencia(texto, predefinidos, estado)
    assert obtenido == esperado, (
        f'para texto={texto!r} predef={predefinidos} estado={estado}: '
        f'esperado {esperado}, obtuvo {obtenido}'
    )


def test_sintoma_etiqueta_devuelve_etiqueta_amigable():
    from routes.triaje import SINTOMA_ETIQUETA
    assert SINTOMA_ETIQUETA['sangrado'] == 'Sangrado o herida grave'
    assert SINTOMA_ETIQUETA['come_poco'] == 'Come poco'


def test_sintoma_nivel_asigna_nivel_correcto():
    from routes.triaje import SINTOMA_NIVEL
    assert SINTOMA_NIVEL['sangrado'] == 'Urgente'
    assert SINTOMA_NIVEL['vomita'] == 'Moderado'
    assert SINTOMA_NIVEL['come_poco'] == 'Leve'
