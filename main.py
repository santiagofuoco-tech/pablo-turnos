"""
Sistema de Turnos — Canchas de Pádel Pablo
Generado por Gestion-AI · SIGMA

API REST con:
- CRUD de reservas
- Consulta de disponibilidad por cancha y fecha
- Webhook para ManyChat (POST /webhook/manychat)
- Endpoint de estadísticas semanales para el dashboard
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db, crear_tablas
from models import Cancha, Reserva, EstadoReserva
from seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al iniciar: crear tablas y sembrar canchas si no existen
    crear_tablas()
    seed()
    yield


app = FastAPI(
    title="Sistema de Turnos · Canchas de Pádel Pablo",
    description="API para gestión de reservas de 4 canchas de pádel",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: en producción podés restringir a tu dominio via ALLOWED_ORIGINS
_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _origins_raw.split(",")] if _origins_raw != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class ReservaCreate(BaseModel):
    cancha_id:        int
    fecha:            datetime
    duracion_minutos: int = 60
    cliente_nombre:   str
    cliente_telefono: str = ""
    cliente_email:    str = ""
    notas:            str = ""


class ReservaUpdate(BaseModel):
    estado:  Optional[EstadoReserva] = None
    notas:   Optional[str] = None


class ManyChатWebhook(BaseModel):
    """Payload que envía ManyChat al confirmar una reserva."""
    user_id:          str
    first_name:       str
    last_name:        str = ""
    phone:            str = ""
    cancha_numero:    int
    fecha_str:        str   # "2026-04-15 18:00"
    duracion_minutos: int = 60


# ── Canchas ────────────────────────────────────────────────────────────────────

@app.get("/canchas")
def listar_canchas(db: Session = Depends(get_db)):
    canchas = db.query(Cancha).filter(Cancha.activa == True).all()
    return [
        {"id": c.id, "numero": c.numero, "nombre": c.nombre, "descripcion": c.descripcion}
        for c in canchas
    ]


@app.get("/canchas/{cancha_id}/disponibilidad")
def disponibilidad(cancha_id: int, fecha: date, db: Session = Depends(get_db)):
    """Retorna los turnos ocupados para una cancha en una fecha dada."""
    inicio_dia = datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0)
    fin_dia    = inicio_dia + timedelta(days=1)

    reservas = (
        db.query(Reserva)
        .filter(
            Reserva.cancha_id == cancha_id,
            Reserva.fecha >= inicio_dia,
            Reserva.fecha < fin_dia,
            Reserva.estado.notin_([EstadoReserva.CANCELADA]),
        )
        .all()
    )

    ocupados = [
        {
            "hora": r.fecha.strftime("%H:%M"),
            "hasta": (r.fecha + timedelta(minutes=r.duracion_minutos)).strftime("%H:%M"),
            "cliente": r.cliente_nombre,
        }
        for r in reservas
    ]
    return {"cancha_id": cancha_id, "fecha": str(fecha), "turnos_ocupados": ocupados}


# ── Reservas ───────────────────────────────────────────────────────────────────

@app.get("/reservas")
def listar_reservas(
    cancha_id:  Optional[int]  = None,
    estado:     Optional[str]  = None,
    desde:      Optional[date] = None,
    hasta:      Optional[date] = None,
    db:         Session        = Depends(get_db),
):
    q = db.query(Reserva)
    if cancha_id:
        q = q.filter(Reserva.cancha_id == cancha_id)
    if estado:
        q = q.filter(Reserva.estado == estado)
    if desde:
        q = q.filter(Reserva.fecha >= datetime(desde.year, desde.month, desde.day))
    if hasta:
        q = q.filter(Reserva.fecha < datetime(hasta.year, hasta.month, hasta.day) + timedelta(days=1))

    reservas = q.order_by(Reserva.fecha).all()
    return [_serializar_reserva(r) for r in reservas]


@app.post("/reservas", status_code=201)
def crear_reserva(data: ReservaCreate, db: Session = Depends(get_db)):
    # Verificar que la cancha existe
    cancha = db.query(Cancha).filter(Cancha.id == data.cancha_id).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")

    # Verificar disponibilidad
    fin_nueva = data.fecha + timedelta(minutes=data.duracion_minutos)
    conflicto = (
        db.query(Reserva)
        .filter(
            Reserva.cancha_id == data.cancha_id,
            Reserva.estado.notin_([EstadoReserva.CANCELADA]),
            Reserva.fecha < fin_nueva,
            # fecha_fin > data.fecha
        )
        .first()
    )
    # Chequeo manual de solapamiento
    reservas_dia = (
        db.query(Reserva)
        .filter(
            Reserva.cancha_id == data.cancha_id,
            Reserva.estado.notin_([EstadoReserva.CANCELADA]),
            Reserva.fecha >= data.fecha.replace(hour=0, minute=0, second=0),
            Reserva.fecha < data.fecha.replace(hour=23, minute=59, second=59),
        )
        .all()
    )
    for r in reservas_dia:
        fin_existente = r.fecha + timedelta(minutes=r.duracion_minutos)
        if data.fecha < fin_existente and fin_nueva > r.fecha:
            raise HTTPException(
                status_code=409,
                detail=f"La cancha ya está reservada de {r.fecha.strftime('%H:%M')} a {fin_existente.strftime('%H:%M')}",
            )

    reserva = Reserva(
        cancha_id=data.cancha_id,
        fecha=data.fecha,
        duracion_minutos=data.duracion_minutos,
        cliente_nombre=data.cliente_nombre,
        cliente_telefono=data.cliente_telefono,
        cliente_email=data.cliente_email,
        notas=data.notas,
        estado=EstadoReserva.CONFIRMADA,
        canal_origen="web",
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return _serializar_reserva(reserva)


@app.get("/reservas/{reserva_id}")
def obtener_reserva(reserva_id: int, db: Session = Depends(get_db)):
    r = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return _serializar_reserva(r)


@app.patch("/reservas/{reserva_id}")
def actualizar_reserva(reserva_id: int, data: ReservaUpdate, db: Session = Depends(get_db)):
    r = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if data.estado is not None:
        r.estado = data.estado
    if data.notas is not None:
        r.notas = data.notas
    db.commit()
    db.refresh(r)
    return _serializar_reserva(r)


@app.delete("/reservas/{reserva_id}")
def cancelar_reserva(reserva_id: int, db: Session = Depends(get_db)):
    r = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    r.estado = EstadoReserva.CANCELADA
    db.commit()
    return {"mensaje": f"Reserva #{reserva_id} cancelada"}


# ── Webhook ManyChat ───────────────────────────────────────────────────────────

@app.post("/webhook/manychat")
def webhook_manychat(payload: ManyChатWebhook, db: Session = Depends(get_db)):
    """
    Recibe una reserva desde ManyChat y la registra en la base de datos.
    Retorna set_attributes para ManyChat (confirma el turno al usuario).
    """
    # Buscar cancha por número
    cancha = db.query(Cancha).filter(Cancha.numero == payload.cancha_numero).first()
    if not cancha:
        return {
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": f"Lo siento, la cancha {payload.cancha_numero} no existe."}]
            }
        }

    # Parsear fecha
    try:
        fecha = datetime.strptime(payload.fecha_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return {
            "version": "v2",
            "content": {
                "messages": [{"type": "text", "text": "Formato de fecha incorrecto. Usá: YYYY-MM-DD HH:MM"}]
            }
        }

    # Verificar solapamiento
    fin_nueva = fecha + timedelta(minutes=payload.duracion_minutos)
    reservas_dia = (
        db.query(Reserva)
        .filter(
            Reserva.cancha_id == cancha.id,
            Reserva.estado.notin_([EstadoReserva.CANCELADA]),
            Reserva.fecha >= fecha.replace(hour=0, minute=0, second=0),
            Reserva.fecha < fecha.replace(hour=23, minute=59, second=59),
        )
        .all()
    )
    for r in reservas_dia:
        fin_existente = r.fecha + timedelta(minutes=r.duracion_minutos)
        if fecha < fin_existente and fin_nueva > r.fecha:
            return {
                "version": "v2",
                "content": {
                    "messages": [{
                        "type": "text",
                        "text": (
                            f"Lo siento {payload.first_name}, la {cancha.nombre} ya está "
                            f"ocupada de {r.fecha.strftime('%H:%M')} a {fin_existente.strftime('%H:%M')}. "
                            "¿Querés otro horario?"
                        )
                    }]
                },
                "set_attributes": {"reserva_estado": "no_disponible"},
            }

    # Crear reserva
    reserva = Reserva(
        cancha_id=cancha.id,
        fecha=fecha,
        duracion_minutos=payload.duracion_minutos,
        cliente_nombre=f"{payload.first_name} {payload.last_name}".strip(),
        cliente_telefono=payload.phone,
        manychat_user_id=payload.user_id,
        canal_origen="manychat",
        estado=EstadoReserva.CONFIRMADA,
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)

    return {
        "version": "v2",
        "content": {
            "messages": [{
                "type": "text",
                "text": (
                    f"Reserva confirmada, {payload.first_name}!\n"
                    f"Cancha: {cancha.nombre}\n"
                    f"Fecha: {fecha.strftime('%d/%m/%Y')}\n"
                    f"Hora: {fecha.strftime('%H:%M')} hs\n"
                    f"Duracion: {payload.duracion_minutos} min\n"
                    f"Tu codigo de reserva: #{reserva.id}"
                )
            }]
        },
        "set_attributes": {
            "reserva_id":     str(reserva.id),
            "reserva_estado": "confirmada",
            "reserva_cancha": cancha.nombre,
            "reserva_hora":   fecha.strftime("%H:%M"),
        },
    }


# ── Estadísticas (para el dashboard) ──────────────────────────────────────────

@app.get("/estadisticas/semana")
def estadisticas_semana(db: Session = Depends(get_db)):
    """Retorna estadísticas de la semana actual para el dashboard."""
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    inicio = datetime(lunes.year, lunes.month, lunes.day)
    fin    = datetime(domingo.year, domingo.month, domingo.day, 23, 59, 59)

    reservas = (
        db.query(Reserva)
        .filter(
            Reserva.fecha >= inicio,
            Reserva.fecha <= fin,
            Reserva.estado != EstadoReserva.CANCELADA,
        )
        .all()
    )

    # Agrupar por cancha
    por_cancha = {1: 0, 2: 0, 3: 0, 4: 0}
    por_dia    = {i: 0 for i in range(7)}  # 0=lunes, 6=domingo
    horas_pico = {}

    for r in reservas:
        cancha = db.query(Cancha).filter(Cancha.id == r.cancha_id).first()
        if cancha:
            por_cancha[cancha.numero] = por_cancha.get(cancha.numero, 0) + 1
        dia_semana = r.fecha.weekday()
        por_dia[dia_semana] += 1
        hora = r.fecha.strftime("%H:00")
        horas_pico[hora] = horas_pico.get(hora, 0) + 1

    return {
        "semana":        f"{lunes.strftime('%d/%m')} - {domingo.strftime('%d/%m/%Y')}",
        "total_reservas": len(reservas),
        "por_cancha":    [{"cancha": f"Cancha {k}", "reservas": v} for k, v in por_cancha.items()],
        "por_dia":       [
            {"dia": ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"][i], "reservas": v}
            for i, v in por_dia.items()
        ],
        "horas_pico":    sorted(
            [{"hora": k, "reservas": v} for k, v in horas_pico.items()],
            key=lambda x: x["reservas"],
            reverse=True,
        )[:5],
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serializar_reserva(r: Reserva) -> dict:
    return {
        "id":               r.id,
        "cancha_id":        r.cancha_id,
        "fecha":            r.fecha.isoformat(),
        "duracion_minutos": r.duracion_minutos,
        "estado":           r.estado.value,
        "cliente_nombre":   r.cliente_nombre,
        "cliente_telefono": r.cliente_telefono,
        "cliente_email":    r.cliente_email,
        "canal_origen":     r.canal_origen,
        "notas":            r.notas,
        "creado_en":        r.creado_en.isoformat() if r.creado_en else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
