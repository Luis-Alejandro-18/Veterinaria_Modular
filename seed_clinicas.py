"""Carga clínicas de ejemplo para probar el mapa.

Datos ficticios solo para la demo académica. No usar para emergencias reales.

Uso:
    python seed_clinicas.py
    python seed_clinicas.py --force   # borra y recarga las clínicas de ejemplo
"""
import sys

from geoalchemy2.elements import WKTElement

from app import app
from models import Clinica, db

CLINICAS_DEMO = [
    ("Veterinaria Demo Centro", "Av. Juárez 100, Centro, Guadalajara, Jal.", "33 0000 0001", 20.6767, -103.3475),
    ("Veterinaria Demo Chapultepec", "Av. Chapultepec 500, Americana, Guadalajara, Jal.", "33 0000 0002", 20.6730, -103.3670),
    ("Veterinaria Demo Providencia", "Av. Pablo Neruda 3000, Providencia, Guadalajara, Jal.", "33 0000 0003", 20.7000, -103.3830),
    ("Veterinaria Demo Zapopan Norte", "Av. Tesistán 800, Zapopan Norte, Jal.", "33 0000 0004", 20.7300, -103.3900),
    ("Veterinaria Demo Andares", "Av. Real Acueducto 200, Andares, Zapopan, Jal.", "33 0000 0005", 20.7100, -103.4120),
    ("Veterinaria Demo Chapalita", "Av. Guadalupe 1200, Chapalita, Zapopan, Jal.", "33 0000 0006", 20.6650, -103.4080),
    ("Veterinaria Demo Plaza del Sol", "Av. López Mateos 1500, Plaza del Sol, Zapopan, Jal.", "33 0000 0007", 20.6480, -103.4020),
    ("Veterinaria Demo Tlaquepaque", "Av. Independencia 200, Tlaquepaque, Jal.", "33 0000 0008", 20.6400, -103.3120),
    ("Veterinaria Demo Tonalá", "Av. Tonaltecas 300, Tonalá, Jal.", "33 0000 0009", 20.6240, -103.2340),
    ("Veterinaria Demo Tlajomulco", "Carretera a Chapala 500, Tlajomulco, Jal.", "33 0000 0010", 20.4730, -103.4460),
    ("Veterinaria Demo Aeropuerto", "Carretera Guadalajara-Chapala km 15, Jal.", "33 0000 0011", 20.5210, -103.3110),
    ("Veterinaria Demo La Minerva", "Av. Vallarta 2500, La Minerva, Guadalajara, Jal.", "33 0000 0012", 20.6750, -103.3920),
]


def main():
    with app.app_context():
        existentes = Clinica.query.count()

        if existentes and '--force' not in sys.argv:
            print(f"[INFO] Ya hay {existentes} clinicas. Usa --force para recargar.")
            return

        if existentes:
            Clinica.query.delete()
            db.session.commit()

        for nombre, direccion, telefono, lat, lng in CLINICAS_DEMO:
            db.session.add(Clinica(
                nombre=nombre,
                direccion=direccion,
                telefono=telefono,
                coordenadas=WKTElement(f'POINT({lng} {lat})', srid=4326),
                abierto_24_7=True,
            ))

        db.session.commit()
        print(f"[OK] {len(CLINICAS_DEMO)} clinicas de ejemplo cargadas.")


if __name__ == '__main__':
    main()
