"""
Configuración de base de datos — Sistema de Turnos · Canchas de Pádel Pablo
Soporta SQLite (desarrollo) y PostgreSQL (producción en Railway).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base

# Railway inyecta DATABASE_URL automáticamente cuando agregás el plugin PostgreSQL.
# En local usa SQLite por defecto.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./turnos_pablo.db")

# Railway a veces entrega postgres:// pero SQLAlchemy requiere postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite necesita check_same_thread=False; PostgreSQL no acepta ese parámetro
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def crear_tablas():
    """Crea todas las tablas si no existen."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency de FastAPI — sesión de BD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
