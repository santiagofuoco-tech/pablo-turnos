"""
Modelos de base de datos — Sistema de Turnos · Canchas de Pádel Pablo
Generado por Gestion-AI · SIGMA
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class EstadoReserva(str, enum.Enum):
    PENDIENTE   = "pendiente"
    CONFIRMADA  = "confirmada"
    CANCELADA   = "cancelada"
    COMPLETADA  = "completada"


class Cancha(Base):
    __tablename__ = "canchas"

    id          = Column(Integer, primary_key=True, index=True)
    numero      = Column(Integer, unique=True, nullable=False)   # 1, 2, 3, 4
    nombre      = Column(String(50), nullable=False)             # "Cancha 1"
    descripcion = Column(String(200), default="")
    activa      = Column(Boolean, default=True)

    reservas = relationship("Reserva", back_populates="cancha")

    def __repr__(self):
        return f"<Cancha {self.numero}: {self.nombre}>"


class Reserva(Base):
    __tablename__ = "reservas"

    id               = Column(Integer, primary_key=True, index=True)
    cancha_id        = Column(Integer, ForeignKey("canchas.id"), nullable=False)

    # Datos del turno
    fecha            = Column(DateTime, nullable=False)          # fecha y hora inicio
    duracion_minutos = Column(Integer, default=60)               # 60 o 90 minutos
    estado           = Column(Enum(EstadoReserva), default=EstadoReserva.PENDIENTE)

    # Datos del cliente final (quien reserva la cancha)
    cliente_nombre   = Column(String(100), nullable=False)
    cliente_telefono = Column(String(30), default="")
    cliente_email    = Column(String(100), default="")

    # ManyChat / WhatsApp
    manychat_user_id = Column(String(100), default="")           # para responder al usuario
    canal_origen     = Column(String(50), default="manychat")    # manychat, web, telefono

    # Metadata
    notas            = Column(Text, default="")
    creado_en        = Column(DateTime, default=datetime.utcnow)
    actualizado_en   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cancha = relationship("Cancha", back_populates="reservas")

    def __repr__(self):
        return f"<Reserva {self.id}: {self.cliente_nombre} - Cancha {self.cancha_id} - {self.fecha}>"
