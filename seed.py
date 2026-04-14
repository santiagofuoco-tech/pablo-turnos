"""
Seed inicial — Crea las 4 canchas de pádel
Generado por Gestion-AI · SIGMA

Uso standalone: python seed.py
También se llama desde main.py al arrancar (idempotente).
"""
from database import SessionLocal, crear_tablas
from models import Cancha


def seed():
    """Crea las 4 canchas si todavía no existen. Idempotente."""
    db = SessionLocal()
    try:
        if db.query(Cancha).count() > 0:
            return  # ya sembrado
        canchas = [
            Cancha(numero=1, nombre="Cancha 1", descripcion="Cancha cubierta - iluminación LED"),
            Cancha(numero=2, nombre="Cancha 2", descripcion="Cancha cubierta - iluminación LED"),
            Cancha(numero=3, nombre="Cancha 3", descripcion="Cancha semicubierta"),
            Cancha(numero=4, nombre="Cancha 4", descripcion="Cancha semicubierta"),
        ]
        db.add_all(canchas)
        db.commit()
        print("Seed: 4 canchas creadas.")
    finally:
        db.close()


if __name__ == "__main__":
    crear_tablas()
    seed()
    print("Listo.")
